"""Compare retrieval modes on the frozen development sample (Issue 08).

One factor changes between runs: the retriever. The corpus, the splitter, the
questions, the annotations, the encoder, top-k all stay
fixed, so a difference in the report can only come from how candidates were
ranked. That is the whole point of the task -- "does adding keyword matching and
rank fusion to the vector retriever change what the same questions retrieve?"

Three modes are compared:

  vector      local exact-cosine over the MiniLM embeddings (the 07 baseline)
  bm25        Okapi BM25 over the same active chunks
  hybrid-rrf  Reciprocal Rank Fusion of the two above

RRF is deliberately rank-based, so the two very different score scales (cosine
in [-1,1], BM25 unbounded) are never added together; each candidate records which
retriever gave it which rank, so a fusion result can be audited.

The holdout set stays sealed: this script only ever names the development sample.
An ordinary run does no paid calls and costs nothing.

    python scripts/compare_retrievers.py
    python scripts/compare_retrievers.py --out docs/evidence/issue08-retrievers.json
    python scripts/compare_retrievers.py --mode vector --mode hybrid-rrf
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.bm25 import BM25Search  # noqa: E402
from skra.eval import (NOT_RUN, TOKEN_ESTIMATE_NOTE, load_cases,  # noqa: E402
                       run_baseline)
from skra.fusion import RRFSearch  # noqa: E402
from skra.store import SPLITTER, Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV_CASES = ROOT / "examples/eval-dev-cases.json"
SOURCE_DB = ROOT / ".data/knowledge.sqlite3"

VECTOR = "vector"
BM25 = "bm25"
HYBRID = "hybrid-rrf"
MODES = (VECTOR, BM25, HYBRID)


def load_corpus(source_db=SOURCE_DB):
    """The real OWASP snapshots; the synthetic CC0 fixture is excluded.

    Same rule the development sample records: the demo fixture exists to exercise
    the CLI and must never influence an evaluation.
    """
    import sqlite3
    db = sqlite3.connect(source_db)
    db.row_factory = sqlite3.Row
    docs = [dict(r) for r in db.execute(
        "SELECT title,source,license,acquired,snapshot FROM documents "
        "WHERE source LIKE 'https://%' ORDER BY source")]
    db.close()
    return docs


def materialise(docs, splitter=SPLITTER, workdir=None, tag="corpus"):
    """Build a throwaway database holding the corpus under one splitter.

    Every mode is scored on the *same* database, so the comparison is on the
    retriever alone -- a retriever that saw different chunks is not comparable.
    """
    store = Store(Path(workdir) / f"{tag}.sqlite3")
    for doc in docs:
        path = Path(workdir) / f"{tag}-{len(doc['source'])}.md"
        path.write_text(doc["snapshot"], encoding="utf-8")
        store.ingest(path, doc["title"], doc["source"], doc["license"],
                     doc["acquired"], splitter=splitter)
    return store


def build_retrievers(store, encoder):
    """The three `search(query, k)` callables, all over the same store."""
    from skra.vector import VectorSearch
    vector = VectorSearch(store, encoder=encoder)
    vector.build()
    bm25 = BM25Search(store)
    hybrid = RRFSearch(store, [
        (VECTOR, vector.search, 1.0),
        (BM25, bm25.search, 1.0),
    ])
    return {VECTOR: vector.search, BM25: bm25.search, HYBRID: hybrid.search}, {
        VECTOR: "cosine",
        BM25: f"bm25(k1={1.5},b={0.75})",
        HYBRID: "rrf(k=60, equal weights)",
    }


def run_modes(modes, k=5, source_db=SOURCE_DB, splitter=SPLITTER, verbose=True):
    docs = load_corpus(source_db)
    if not docs:
        raise SystemExit("工作库里没有真实资料，先导入 OWASP 快照再对照。")
    cases = load_cases(DEV_CASES)
    runs = []
    with tempfile.TemporaryDirectory() as workdir:
        from skra.vector import Encoder
        encoder = Encoder()
        store = materialise(docs, splitter, workdir, "retrievers")
        try:
            searches, labels = build_retrievers(store, encoder)
            for mode in modes:
                started = time.perf_counter()
                report = run_baseline(store, DEV_CASES, searches[mode], k=k,
                                      encoder=encoder)
                report["wall_ms"] = (time.perf_counter() - started) * 1000
                report["retriever"] = mode
                report["retriever_label"] = labels[mode]
                runs.append(report)
                if verbose:
                    agg = report["aggregate"]
                    print(f"{mode:11s} recall@5={agg['recall_at_5']:5.3f} "
                          f"tokens={agg['mean_evidence_tokens']:7.1f} "
                          f"meta={agg['total_metadata_chunks']:2d} "
                          f"broken={agg['broken_bundles']} "
                          f"failed={len(report['failed_cases'])}")
        finally:
            store.close()
    return build_report(runs, cases, k, splitter)


def _empty_candidate(result, case):
    return not result.get("candidates")


def per_case_detail(store, case, search, k):
    """The retrieval detail the report needs beyond the recall score.

    Recall alone cannot explain a delta: for the term-mismatch cases the finding
    is *why* a retriever returns nothing, and for the fusion cases it is which
    retriever contributed the winning chunk. Both are recorded here.
    """
    result = search(case.question, k)
    candidates = result.get("candidates", [])[:k]
    return {
        "mode": result.get("mode"),
        "candidate_count": len(result.get("candidates", [])),
        "top_ids": [c["id"] for c in candidates],
        "contributions": {c["id"]: c.get("contributions")
                          for c in candidates if c.get("contributions")},
    }


def _annotated_covering_ids(report, cid):
    """The chunk ids that cover a case's annotated bundles, per the scoring run.

    Recorded so a degradation can be explained from the report alone: whether a
    mode missed *because* it dropped a covering chunk, or because the chunk that
    covers the span was never a candidate.
    """
    scored = next((c for c in report["cases"] if c["case_id"] == cid), None)
    if not scored:
        return []
    ids = []
    for bundle in scored.get("bundles", ()):
        ids.extend(bundle.get("covering_chunks", ()))
    return sorted(set(ids))


def build_report(runs, cases, k, splitter):
    """The cross-mode table plus the per-case deltas that explain it."""
    by_mode = {r["retriever"]: r for r in runs}
    per_case = {}
    for case in cases:
        row = {"case_id": case.id, "question": case.question,
               "expected_status": case.expected_status,
               "annotated_bundles": len(case.evidence)}
        for mode, report in by_mode.items():
            scored = next((c for c in report["cases"] if c["case_id"] == case.id), None)
            covering = _annotated_covering_ids(report, case.id)
            row[mode] = None if scored is None else {
                "recall_at_5": scored["recall_at_5"],
                "retrieved_bundles": scored["retrieved_bundles"],
                "broken_bundles": scored["broken_bundles"],
                "retrieved_chunk_ids": scored.get("retrieved_chunk_ids", []),
                "annotated_covering_chunk_ids": covering,
                "covering_chunks_retrieved": sorted(
                    set(covering) & set(scored.get("retrieved_chunk_ids", ()))),
                "evidence_tokens": scored["evidence_tokens"],
                "metadata_chunks": scored["metadata_chunks"],
                "error": scored.get("error"),
            }
        per_case[case.id] = row

    baseline = by_mode.get(VECTOR)
    deltas = []
    if baseline:
        base_agg = baseline["aggregate"]
        for mode, report in by_mode.items():
            if mode == VECTOR:
                continue
            agg = report["aggregate"]
            gained, lost, same = [], [], []
            for case in cases:
                base = per_case[case.id][VECTOR]
                now = per_case[case.id][mode]
                if base is None or now is None:
                    continue
                b, n = base["recall_at_5"], now["recall_at_5"]
                if b is None or n is None:
                    continue
                if n > b:
                    gained.append(case.id)
                elif n < b:
                    lost.append(case.id)
                else:
                    same.append(case.id)
            deltas.append({
                "mode": mode,
                "vs": VECTOR,
                "retriever_label": report["retriever_label"],
                "recall_at_5": agg["recall_at_5"],
                "vector_recall_at_5": base_agg["recall_at_5"],
                "delta": ((agg["recall_at_5"] - base_agg["recall_at_5"])
                          if agg["recall_at_5"] is not None
                          and base_agg["recall_at_5"] is not None else None),
                "mean_evidence_tokens": agg["mean_evidence_tokens"],
                "vector_mean_evidence_tokens": base_agg["mean_evidence_tokens"],
                "gained_cases": gained,
                "lost_cases": lost,
                "unchanged_cases": same,
                "degenerate_cases": list(report["failed_cases"]),
            })

    return {
        "kind": "retriever-comparison",
        "sample": str(DEV_CASES.relative_to(ROOT)).replace("\\", "/"),
        "sample_kind": "development",
        "holdout_loaded": any(r["holdout_loaded"] for r in runs),
        "modes_compared": list(by_mode),
        "fixed_factors": {
            "corpus": "工作库中 source 以 https:// 开头的真实资料快照（排除合成夹具）",
            "splitter": splitter,
            "encoder": (runs[0]["freeze"]["encoder"] if runs else None),
            "k": k,
            "evidence_budget": f"固定 top-k={k}；未限制总 token，证据 token 为字符数/4 的估算",
            "questions": "开发集 D01–D10，标注与 07 冻结一致",
            "changed_factor": "仅检索与排序方式（向量 / BM25 / RRF 融合）",
        },
        "corpus_freeze": (runs[0]["freeze"]["corpus_hash"] if runs else None),
        "documents": (runs[0]["freeze"]["documents"] if runs else []),
        "retrievers": [
            {
                "mode": r["retriever"],
                "label": r["retriever_label"],
                "case_count": r["case_count"],
                "scored_cases": r["scored_cases"],
                "failed_cases": r["failed_cases"],
                "aggregate": r["aggregate"],
                "elapsed_ms": r["elapsed_ms"],
                "wall_ms": r["wall_ms"],
                "freeze": {"sample_hash": r["freeze"]["sample_hash"],
                           "corpus_hash": r["freeze"]["corpus_hash"]},
            }
            for r in runs
        ],
        "deltas_vs_vector": deltas,
        "per_case": per_case,
        "network_called": False,
        "billed_calls": 0,
        "cost_rmb": 0,
        "complete": False,
        "not_run": list(NOT_RUN) + [
            "生成侧与人工语义复核：本对照只做检索结构指标，未运行付费生成。",
            "保留集执行：按设计封存至 Issue 12。",
        ],
        "evidence_tokens_estimate_note": TOKEN_ESTIMATE_NOTE,
        "recheck_note": ("run 记录已写入对照数据库并随临时目录销毁；"
                         "如需离线重放，请对常驻工作库执行 skra replay。"),
        "manual_review": "pending",
    }


def print_case_table(report):
    modes = report["modes_compared"]
    width = max(len(m) for m in modes)
    header = "用例      " + "  ".join(f"{m:>{width}}" for m in modes)
    print("\n" + header)
    print("-" * len(header))
    for cid, row in report["per_case"].items():
        cells = []
        for m in modes:
            cell = row.get(m)
            if cell is None or cell["recall_at_5"] is None:
                cells.append(f"{'n/a':>{width}}")
            else:
                cells.append(f"{cell['recall_at_5']:>{width}.2f}")
        print(f"{cid:<9} " + "  ".join(cells))
    print("\n(n/a = 未能评分；0.00 = 有标注但未命中)")


def print_degradation_notes(report):
    """Explain each degradation from the recorded evidence, not from memory.

    A recall drop is only useful if it says *which* chunk went missing. For each
    degraded case this prints whether the annotated covering chunk was actually
    retrieved by each mode, which separates two very different failures:
      - the mode never had the covering chunk as a candidate (a retrieval miss);
      - the covering chunk exists but was ranked out (a ranking miss, which is what
        fusion can cause by promoting a look-alike).
    """
    tiers = {m: [] for m in report["modes_compared"]}
    for cid, row in report["per_case"].items():
        base, base_cell = row.get(VECTOR), None
        if not base:
            continue
        for m in report["modes_compared"]:
            cell = row.get(m)
            if not cell or cell["recall_at_5"] is None or base["recall_at_5"] is None:
                continue
            if cell["recall_at_5"] < base["recall_at_5"]:
                covering = set(cell.get("annotated_covering_chunk_ids", ()))
                got = set(cell.get("covering_chunks_retrieved", ()))
                if not covering:
                    why = "标注跨度没有覆盖片段（数据结构问题）"
                elif got:
                    why = "覆盖片段已取到但仍未完整命中（束被拆开）"
                elif covering & set(cell["retrieved_chunk_ids"]):
                    why = "取到覆盖片段但束不完整"
                else:
                    why = ("覆盖片段未被该路取到（排序/候选缺失）"
                           if cell["retrieved_chunk_ids"] else "该路零候选（词项错配）")
                tiers[m].append((cid, why))
    print("\n== 退化案例的机制（按报告记录复查）==")
    for m in report["modes_compared"]:
        if m == VECTOR or not tiers[m]:
            continue
        print(f"  {m}:")
        for cid, why in tiers[m]:
            print(f"    {cid}: {why}")


def print_zero_candidate_notes(report):
    """Surface the cases where a retriever returned nothing at all.

    This is the honest core of the term-mismatch finding: a Chinese question with
    no shared term against the English corpus gives BM25 an empty candidate list.
    Reporting it as a 0.00 recall without saying "no candidates" would hide why.
    """
    empties = {m: [] for m in report["modes_compared"]}
    for cid, row in report["per_case"].items():
        for m in report["modes_compared"]:
            cell = row.get(m)
            if cell and not cell["retrieved_chunk_ids"] and cell["recall_at_5"] is not None:
                empties[m].append(cid)
    print("\n== 零候选用例（检索器如实返回空，不伪造命中）==")
    for m, cids in empties.items():
        print(f"  {m:11s}: {', '.join(cids) if cids else '无'}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="在固定语料与问题上对照检索方式")
    parser.add_argument("--mode", action="append", default=None,
                        help="只跑指定检索方式，可重复；默认全部三种")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--splitter", default=SPLITTER)
    parser.add_argument("--db", default=str(SOURCE_DB), help="提供快照的真实工作库")
    parser.add_argument("--out", default=None, help="报告输出路径")
    parser.add_argument("--json", action="store_true", help="打印完整 JSON")
    args = parser.parse_args()

    modes = tuple(args.mode) if args.mode else MODES
    report = run_modes(modes, k=args.k, source_db=args.db, splitter=args.splitter)
    print_case_table(report)
    print("\n== 相对向量基线的变化 ==")
    for delta in report["deltas_vs_vector"]:
        r = delta["recall_at_5"]
        rd = delta["delta"]
        print(f"  {delta['mode']:11s}: recall {delta['vector_recall_at_5']:.3f} → "
              f"{r:.3f} ({rd:+.3f})  "
              f"token {delta['vector_mean_evidence_tokens']:.0f} → "
              f"{delta['mean_evidence_tokens']:.0f}  "
              f"提升={delta['gained_cases'] or '无'}  "
              f"退化={delta['lost_cases'] or '无'}")
    print_zero_candidate_notes(report)
    print_degradation_notes(report)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"\n报告已写入：{target}")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
