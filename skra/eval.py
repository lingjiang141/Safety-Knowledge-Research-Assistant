"""Evaluation samples and baseline reports (Issue 07).

An evaluation question is anchored to *original-text spans* plus the conditions
that must appear together, never to chunk ids. Chunk ids are a function of the
splitter, so anchoring to them would make Recall incomparable across strategies
and would break on every re-import. Spans are mapped onto whatever chunks the
current strategy produced, which keeps the denominator stable.

The development set and the holdout set are separated twice over: they live in
different files, and this loader will not read the holdout unless explicitly
asked. That keeps holdout answers out of the tuning context by construction, not
by convention.
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .store import digest

HOLDOUT_FLAG = "holdout"


class EvalError(ValueError):
    """The evaluation sample or its annotations are not usable."""


@dataclass(frozen=True)
class EvidenceSpan:
    """One bundle of original text that must be retrieved together."""
    source: str
    start_line: int
    end_line: int
    must_include: tuple = ()
    required_together: bool = True


@dataclass(frozen=True)
class Case:
    id: str
    question: str
    expected_status: str
    evidence: tuple = ()
    note: str = ""


@dataclass(frozen=True)
class EvalSample:
    """The loaded evaluation sample, with its sets kept visibly separate."""
    cases: tuple = ()
    holdout: tuple = ()
    holdout_loaded: bool = False
    holdout_path: object = None

    def case_ids(self, kind="development"):
        chosen = self.cases if kind == "development" else self.holdout
        return [c.id for c in chosen]


def _span(raw, where):
    missing = [k for k in ("source", "start_line", "end_line") if k not in raw]
    if missing:
        raise EvalError(f"{where}：证据跨度缺少字段 {'、'.join(missing)}。")
    start, end = raw["start_line"], raw["end_line"]
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        raise EvalError(f"{where}：行号必须是满足 1 <= start <= end 的整数。")
    return EvidenceSpan(
        source=str(raw["source"]).strip(),
        start_line=start,
        end_line=end,
        must_include=tuple(raw.get("must_include", ())),
        required_together=bool(raw.get("required_together", True)),
    )


def load_cases(path, kind="development"):
    """Load one sample file. A file declaring itself `holdout` is refused outright.

    The file's own `kind` field is authoritative: renaming a holdout file, or
    passing it where the development set is expected, still fails. Only
    `load_sample(..., holdout=...)` opens the holdout, and only deliberately.
    """
    path = Path(path)
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EvalError(f"无法读取用例文件：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise EvalError(f"用例文件不是合法 JSON：{exc}") from exc

    declared = str(spec.get("kind", "development")).strip()
    if declared == HOLDOUT_FLAG and kind != HOLDOUT_FLAG:
        raise EvalError(
            f"该文件声明为保留集（kind=holdout）：{path}。"
            "保留集不能进入调参上下文；如需在最终评测中运行，请使用显式的 holdout 入口。")
    if kind == HOLDOUT_FLAG and declared != HOLDOUT_FLAG:
        raise EvalError(f"期望保留集，但文件声明为 {declared}：{path}。")

    raw_cases = spec.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise EvalError("用例文件必须包含非空的 cases 列表。")

    # Short source labels (S02) keep annotations readable; the file maps them to the
    # real source strings the corpus uses. An unknown label must fail loudly rather
    # than silently resemble a missing document.
    labels = spec.get("sources", {})
    if not isinstance(labels, dict):
        raise EvalError("sources 必须是「标签 → 来源」的映射。")

    def resolve_source(label, where):
        name = str(label).strip()
        if name in labels:
            return str(labels[name]).strip()
        if name in set(labels.values()):
            return name
        return name

    cases = []
    seen = set()
    for index, raw in enumerate(raw_cases, 1):
        where = f"第 {index} 个用例"
        cid = str(raw.get("id", "")).strip()
        if not cid:
            raise EvalError(f"{where}：缺少 id。")
        if cid in seen:
            raise EvalError(f"{where}：id 重复（{cid}）。")
        seen.add(cid)
        question = str(raw.get("question", "")).strip()
        if not question:
            raise EvalError(f"{where}（{cid}）：缺少 question。")
        raw_evidence = raw.get("evidence", [])
        if not raw_evidence:
            raise EvalError(
                f"{where}（{cid}）：没有标注任何原文跨度，无法评分；"
                "无答案题也必须标注“应当缺失的证据范围”。")
        evidence = []
        for raw_span in raw_evidence:
            span = _span(raw_span, f"{where}（{cid}）")
            evidence.append(EvidenceSpan(
                source=resolve_source(span.source, where),
                start_line=span.start_line,
                end_line=span.end_line,
                must_include=span.must_include,
                required_together=span.required_together,
            ))
        evidence = tuple(evidence)
        cases.append(Case(
            id=cid,
            question=question,
            expected_status=str(raw.get("expected_status", "")).strip(),
            evidence=evidence,
            note=str(raw.get("note", "")),
        ))
    return cases


def load_sample(development, holdout=None):
    """Load the development set, and the holdout set only when explicitly given.

    The default call cannot reach the holdout: it takes no holdout argument, and a
    file that declares itself `holdout` is refused even if it is passed as the
    development set. A final-evaluation run must therefore name the holdout path
    deliberately, which is what keeps tuned answers out of the tuning context.
    """
    cases = load_cases(development, kind="development")
    if holdout is None:
        return EvalSample(cases=tuple(cases), holdout=(), holdout_loaded=False,
                          holdout_path=None)
    holdout_cases = load_cases(holdout, kind=HOLDOUT_FLAG)
    dev_ids = {c.id for c in cases}
    overlap = dev_ids & {c.id for c in holdout_cases}
    if overlap:
        raise EvalError("开发集与保留集存在重复编号：" + "、".join(sorted(overlap)))
    return EvalSample(cases=tuple(cases), holdout=tuple(holdout_cases),
                      holdout_loaded=True, holdout_path=str(Path(holdout)))



def resolve_span(store, span):
    """Map an original-text span onto the active chunks that cover it.

    The mapping is by line range, so it keeps working when the splitter changes:
    only the chunk that happens to cover the span changes, the annotated
    denominator does not. A span that no longer matches the corpus raises rather
    than scoring zero, because a stale annotation and an honest miss look
    identical otherwise.
    """
    doc = None
    for candidate in store.documents():
        if candidate["source"] == span.source or candidate["id"] == span.source:
            doc = candidate
            break
    if doc is None:
        raise EvalError(
            f"标注的来源不存在于当前语料：{span.source}。"
            "语料已变化，请先核对标注再评分。")
    rows = store.db.execute(
        """SELECT * FROM chunks WHERE doc_id=? AND active=1
           AND start_line <= ? AND end_line >= ?
           ORDER BY start_line""",
        (doc["id"], span.end_line, span.start_line)).fetchall()
    if not rows:
        raise EvalError(
            f"来源 {span.source} 的第 {span.start_line}–{span.end_line} 行没有任何片段覆盖。")
    return [dict(r) for r in rows]


def _bundle_is_whole(covered, span, retrieved_ids):
    """A required-together bundle counts only if every covering chunk was retrieved.

    If the splitter cut the bundle across chunks, dropping one of them means the
    evidence the question depends on is no longer present together. Counting that
    as a hit would reward exactly the failure this annotation exists to catch.
    """
    if span.required_together:
        return all(c["id"] in retrieved_ids for c in covered)
    return any(c["id"] in retrieved_ids for c in covered)


def score_retrieval(store, case, search, k=5):
    """Score one case's retrieval against its annotated evidence bundles.

    Recall is measured over *bundles*, not chunks: the denominator is the number
    of annotated bundles, so it does not move when a strategy changes how many
    chunks a document becomes.
    """
    result = search(case.question, k)
    for candidate in result.get("candidates", ()):
        if "text" not in candidate and "id" in candidate:
            candidate.update(store.read(candidate["id"]))
    retrieved = list(result.get("candidates", ()))[:k]
    retrieved_ids = {c["id"] for c in retrieved}

    bundles = []
    for span in case.evidence:
        covered = resolve_span(store, span)
        whole = _bundle_is_whole(covered, span, retrieved_ids)
        included = [c for c in covered if c["id"] in retrieved_ids]
        bundles.append({
            "source": span.source,
            "start_line": span.start_line,
            "end_line": span.end_line,
            "required_together": span.required_together,
            "covering_chunks": [c["id"] for c in covered],
            "retrieved_chunks": [c["id"] for c in included],
            "whole": whole,
            "broken": bool(included) and not whole,
        })
    whole_count = sum(1 for b in bundles if b["whole"])
    relevant = len(bundles)
    return {
        "case_id": case.id,
        "question": case.question,
        "relevant_bundles": relevant,
        "retrieved_bundles": whole_count,
        "broken_bundles": sum(1 for b in bundles if b["broken"]),
        "recall_at_5": (whole_count / relevant) if relevant else 0.0,
        "retrieved_chunk_ids": [c["id"] for c in retrieved],
        "evidence_tokens": estimate_tokens(retrieved),
        "metadata_chunks": sum(1 for c in retrieved if c.get("kind") == "metadata"),
        "bundles": bundles,
    }


def estimate_tokens(chunks):
    """Rough evidence-size estimate for comparing strategies at equal budget.

    This is a deterministic character-based estimate, not a real tokenizer count:
    the offline test environment has no tokenizer for arbitrary text, and the point
    here is only to compare strategies under the same yardstick. Reports must label
    it as an estimate.
    """
    return sum(max(1, len(c.get("text", "")) // 4) for c in chunks)


TOKEN_ESTIMATE_NOTE = ("证据 token 为 字符数/4 的确定性估算，不是真实分词计数；"
                       "仅用于在同一把尺子下比较策略。")

# Which parts of the baseline this task (07) actually runs. Generation and
# citation-support judging need paid calls and human review, so they are named as
# not-run rather than quietly omitted: a report that looks complete but silently
# skips them is worse than one that says so.
NOT_RUN = (
    "生成侧指标（引用支持率、无答案正确说明率、误拒答率）：需付费调用与人工语义复核，本任务未运行。",
    "保留集执行：按设计延后到 Issue 12 的最终评测，本任务只用开发集。",
    "切分对照与混合检索比较：属于 Issue 15 / 08。",
)


def freeze_sample(cases, store, encoder=None):
    """Record the exact sample, corpus and configuration a baseline ran on.

    Uses the project's own digest so the ids match the ones the store uses. The
    hashes are what make a baseline reviewable later: without them a report cannot
    be tied back to the corpus and annotations it described.
    """
    sample_payload = json.dumps([
        {"id": c.id, "question": c.question, "expected_status": c.expected_status,
         "evidence": [{"source": s.source, "start_line": s.start_line,
                       "end_line": s.end_line, "must_include": list(s.must_include),
                       "required_together": s.required_together}
                      for s in c.evidence]}
        for c in cases], ensure_ascii=False, sort_keys=True)
    docs = sorted(store.documents(), key=lambda d: d["id"])
    corpus_payload = json.dumps(
        [(d["id"], d["hash"], d["splitter"]) for d in docs],
        ensure_ascii=False, sort_keys=True)
    splitters = sorted({d["splitter"] for d in docs})
    return {
        "sample_hash": digest(sample_payload),
        "corpus_hash": digest(corpus_payload),
        "splitter": splitters[0] if len(splitters) == 1 else splitters,
        "encoder": encoder.identity if encoder is not None else "(未使用向量编码器)",
        "documents": [{"id": d["id"], "title": d["title"], "hash": d["hash"],
                       "splitter": d["splitter"]} for d in docs],
    }


def run_baseline(store, sample_path, search, k=5, encoder=None, holdout=None,
                 kind=None):
    """Run one case set through one retriever and build a reviewable report.

    `sample_path` is the development set. The holdout is loaded only when its path
    is passed explicitly, so an ordinary baseline run cannot see holdout answers.

    Passing a holdout path IS the deliberate final-evaluation entry (Issue 12):
    `kind` then defaults to "holdout", so the run scores the holdout cases and
    labels the report accordingly. The explicit `kind` exists only to be
    overridden deliberately (e.g. loading both sets to record both freezes while
    still scoring development); defaulting from the argument makes the common call
    say what it means instead of relying on the caller to remember a second flag.
    """
    kind = kind or ("holdout" if holdout is not None else "development")
    if kind not in ("development", "holdout"):
        raise EvalError(f"未知的评测集类型：{kind}。")
    loaded = load_sample(sample_path, holdout=holdout)
    if kind == "holdout" and not loaded.holdout_loaded:
        raise EvalError("请求评测保留集，但未显式打开保留集文件；请提供 holdout 路径。")
    cases = loaded.holdout if kind == "holdout" else loaded.cases
    rows = []
    started = time.perf_counter()
    for case in cases:
        case_started = time.perf_counter()
        try:
            scored = score_retrieval(store, case, search, k=k)
            scored["error"] = None
        except EvalError as exc:
            # A stale annotation is a finding about the sample, not a zero score.
            scored = {"case_id": case.id, "question": case.question,
                      "relevant_bundles": len(case.evidence), "retrieved_bundles": 0,
                      "broken_bundles": 0, "recall_at_5": None,
                      "retrieved_chunk_ids": [], "evidence_tokens": 0,
                      "metadata_chunks": 0, "bundles": [], "error": str(exc)}
        scored["elapsed_ms"] = (time.perf_counter() - case_started) * 1000
        scored["expected_status"] = case.expected_status
        rows.append(scored)
    elapsed_ms = (time.perf_counter() - started) * 1000

    scored_rows = [r for r in rows if r["recall_at_5"] is not None]
    recall = (sum(r["recall_at_5"] for r in scored_rows) / len(scored_rows)
              if scored_rows else None)
    return {
        "kind": "evaluation-baseline",
        "sample": str(Path(sample_path)),
        "sample_kind": kind,
        "evaluated_case_ids": [c.id for c in cases],
        "holdout_loaded": loaded.holdout_loaded,
        "holdout_path": loaded.holdout_path,
        "freeze": freeze_sample(cases, store, encoder),
        "k": k,
        "case_count": len(cases),
        "scored_cases": len(scored_rows),
        "failed_cases": [r["case_id"] for r in rows if r["error"]],
        "aggregate": {
            "recall_at_5": recall,
            "mean_evidence_tokens": (sum(r["evidence_tokens"] for r in rows) / len(rows)
                                     if rows else None),
            "total_metadata_chunks": sum(r["metadata_chunks"] for r in rows),
            "broken_bundles": sum(r["broken_bundles"] for r in rows),
        },
        "cases": rows,
        "elapsed_ms": elapsed_ms,
        "network_called": False,
        "billed_calls": 0,
        "cost_rmb": 0,
        "budget_note": "本基线不联网、不记账；付费生成指标留待需要时在本机交互终端运行。",
        "evidence_tokens_estimate_note": TOKEN_ESTIMATE_NOTE,
        "complete": False,
        # A holdout run IS the holdout execution, so it must not also list it as
        # deferred; the other not-run items still apply to it unchanged.
        "not_run": [item for item in NOT_RUN
                    if not (kind == "holdout" and "保留集执行" in item)],
        "manual_review": "pending",
    }



