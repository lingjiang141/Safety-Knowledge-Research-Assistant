"""Compare document-splitting strategies on the frozen development sample (Issue 15).

One factor changes between runs: the splitter. The corpus text, the questions, the
annotations, the encoder, top-k and the evidence budget all stay fixed, so a
difference in the report can only come from how the document was cut.

Each strategy is materialised as its own database from the *same* stored snapshots,
which keeps the comparison honest: no strategy gets a corpus the others did not see,
and the baseline is not disturbed by being re-imported.

Without --live the script only does local retrieval. It never calls a paid model, so
it costs nothing and can be re-run freely.

    python scripts/compare_splitters.py                 # all Markdown strategies
    python scripts/compare_splitters.py --splitter heading-block-v2
    python scripts/compare_splitters.py --out docs/evidence/issue15-splitters.json
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.eval import NOT_RUN, TOKEN_ESTIMATE_NOTE, load_cases, run_baseline  # noqa: E402
from skra.store import SPLITTER  # noqa: E402
from skra.store import STRUCTURED_SPLITTER, PROCEDURE_SPLITTER  # noqa: E402
from skra.store import Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV_CASES = ROOT / "examples/eval-dev-cases.json"

# The PDF strategy is excluded on purpose: the corpus holds no PDF, and a PDF
# splitter cannot cut Markdown. The comparison covers what the corpus can actually
# exercise, and the omission is stated in the report instead of quietly skipped.
MARKDOWN_STRATEGIES = (SPLITTER, STRUCTURED_SPLITTER, PROCEDURE_SPLITTER)
NOT_COMPARED = {
    "pdf-pages-v1": "语料中没有 PDF，且该策略按页切分、不能处理 Markdown；未纳入本次对照。",
}

SPLITTER_SOURCE = ROOT / ".data/knowledge.sqlite3"


def load_corpus(source_db=SPLITTER_SOURCE):
    """Read the OWASP snapshots (plus their metadata) out of the working database.

    The synthetic CC0 fixture is left out: it exists to demo the CLI, and it must
    never take part in a real evaluation (same rule the dev sample records).
    """
    import sqlite3
    db = sqlite3.connect(source_db)
    db.row_factory = sqlite3.Row
    docs = [dict(r) for r in db.execute(
        "SELECT title,source,license,acquired,snapshot FROM documents "
        "WHERE source LIKE 'https://%' ORDER BY source")]
    db.close()
    return docs


def materialise(docs, splitter, workdir, tag):
    """Build a throwaway database holding the corpus cut by one strategy."""
    from skra.store import Store
    store = Store(Path(workdir) / f"{tag}.sqlite3")
    for doc in docs:
        path = Path(workdir) / f"{tag}-{len(doc['source'])}.md"
        path.write_text(doc["snapshot"], encoding="utf-8")
        store.ingest(path, doc["title"], doc["source"], doc["license"],
                     doc["acquired"], splitter=splitter)
    return store


def chunk_census(store):
    """Per-document chunk counts, so a strategy's granularity is visible."""
    rows = []
    for doc in sorted(store.documents(), key=lambda d: d["source"]):
        chunks = [dict(r) for r in store.db.execute(
            "SELECT kind,start_line,end_line,length(text) AS n FROM chunks "
            "WHERE doc_id=? AND active=1", (doc["id"],))]
        rows.append({
            "source": doc["source"],
            "title": doc["title"],
            "splitter": doc["splitter"],
            "chunks": len(chunks),
            "metadata": sum(1 for c in chunks if c["kind"] == "metadata"),
            "body": sum(1 for c in chunks if c["kind"] != "metadata"),
            "mean_chars": (round(sum(c["n"] for c in chunks) / len(chunks))
                           if chunks else 0),
        })
    return rows


def _source_lines(source_db, source):
    import sqlite3
    row = sqlite3.connect(source_db).execute(
        "SELECT snapshot FROM documents WHERE source=?", (source,)).fetchone()
    return [] if row is None else row[0].split("\n")


def preview(strategies, source_db=SPLITTER_SOURCE, context=2):
    """Save the cut itself next to the original text it came from.

    Issue 15 asks for the split preview and the original-context对照 to be kept,
    not just the scores: a reader has to be able to see *what each strategy did
    to the same lines* in order to judge whether a number moved for the right
    reason. Every chunk is recorded with its line span, kind, and the untouched
    source lines for that span plus `context` lines on each side.
    """
    docs = load_corpus(source_db)
    by_source = {d["source"]: d for d in docs}
    out = {}
    for splitter in strategies:
        store = Store(":memory:")
        doc_previews = []
        for source in sorted(by_source):
            doc = by_source[source]
            store.ingest(_write_snapshot(source, doc["snapshot"]), doc["title"],
                         source, doc["license"], doc["acquired"], splitter=splitter)
            lines = doc["snapshot"].split("\n")
            rows = [dict(r) for r in store.db.execute(
                "SELECT id,kind,start_line,end_line,text FROM chunks "
                "WHERE active=1 ORDER BY start_line, id")]
            doc_previews.append({
                "source": source,
                "title": doc["title"],
                "line_count": len(lines),
                "chunks": [{
                    "id": r["id"],
                    "kind": r["kind"],
                    "start_line": r["start_line"],
                    "end_line": r["end_line"],
                    "chars": len(r["text"]),
                    "text": r["text"],
                    "context_before": lines[max(0, r["start_line"] - 1 - context):
                                            r["start_line"] - 1],
                    "context_after": lines[r["end_line"]:r["end_line"] + context],
                } for r in rows],
            })
        store.close()
        out[splitter] = doc_previews
    return {"kind": "splitter-preview", "sample": "working corpus",
            "context_lines": context, "strategies": out}


def _write_snapshot(source, snapshot):
    import tempfile
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8")
    handle.write(snapshot)
    handle.close()
    return Path(handle.name)


def compare(strategies, k=5, source_db=SPLITTER_SOURCE, verbose=True):
    docs = load_corpus(source_db)
    if not docs:
        raise SystemExit("工作库里没有真实资料，先导入 OWASP 快照再对照。")
    cases = load_cases(DEV_CASES)
    runs = []
    with tempfile.TemporaryDirectory() as workdir:
        from skra.vector import VectorSearch
        for splitter in strategies:
            tag = splitter.replace(":", "_").replace("-", "_")
            store = materialise(docs, splitter, workdir, tag)
            try:
                vector = VectorSearch(store)
                vector.build()
                started = time.perf_counter()
                report = run_baseline(store, DEV_CASES, vector.search, k=k,
                                      encoder=vector.encoder)
                report["wall_ms"] = (time.perf_counter() - started) * 1000
                report["census"] = chunk_census(store)
                report["splitter"] = splitter
                runs.append(report)
                if verbose:
                    agg = report["aggregate"]
                    recall = agg["recall_at_5"]
                    print(f"{splitter:24s} recall@5={recall:5.3f} "
                          f"tokens={agg['mean_evidence_tokens']:7.1f} "
                          f"meta={agg['total_metadata_chunks']:2d} "
                          f"broken={agg['broken_bundles']} "
                          f"failed={len(report['failed_cases'])}")
            finally:
                store.close()
    return build_report(runs, cases, k)


def build_report(runs, cases, k):
    """Assemble the cross-strategy table plus the per-case deltas that explain it."""
    by_splitter = {r["splitter"]: r for r in runs}
    per_case = {}
    for case in cases:
        row = {"case_id": case.id, "question": case.question,
               "expected_status": case.expected_status,
               "annotated_bundles": len(case.evidence)}
        for splitter, report in by_splitter.items():
            scored = next((c for c in report["cases"] if c["case_id"] == case.id), None)
            row[splitter] = None if scored is None else {
                "recall_at_5": scored["recall_at_5"],
                "retrieved_bundles": scored["retrieved_bundles"],
                "broken_bundles": scored["broken_bundles"],
                "evidence_tokens": scored["evidence_tokens"],
                "metadata_chunks": scored["metadata_chunks"],
                "error": scored.get("error"),
            }
        per_case[case.id] = row

    baseline = by_splitter.get(SPLITTER)
    deltas = []
    if baseline:
        for splitter, report in by_splitter.items():
            if splitter == SPLITTER:
                continue
            gained, lost = [], []
            for case in cases:
                base = per_case[case.id][SPLITTER]
                now = per_case[case.id][splitter]
                if base is None or now is None:
                    continue
                if now["recall_at_5"] is None or base["recall_at_5"] is None:
                    continue
                if now["recall_at_5"] > base["recall_at_5"]:
                    gained.append(case.id)
                elif now["recall_at_5"] < base["recall_at_5"]:
                    lost.append(case.id)
            deltas.append({
                "splitter": splitter,
                "vs": SPLITTER,
                "recall_at_5": report["aggregate"]["recall_at_5"],
                "baseline_recall_at_5": baseline["aggregate"]["recall_at_5"],
                "delta": (report["aggregate"]["recall_at_5"]
                          - baseline["aggregate"]["recall_at_5"]),
                "mean_evidence_tokens": report["aggregate"]["mean_evidence_tokens"],
                "baseline_mean_evidence_tokens":
                    baseline["aggregate"]["mean_evidence_tokens"],
                "gained_cases": gained,
                "lost_cases": lost,
                "degenerate_cases": [c for c in report["failed_cases"]],
            })

    return {
        "kind": "splitter-comparison",
        "sample": str(DEV_CASES.relative_to(ROOT)).replace("\\", "/"),
        "sample_kind": "development",
        "splitter_compared": list(by_splitter),
        "splitter_not_compared": NOT_COMPARED,
        "fixed_factors": {
            "corpus": "工作库中 source 以 https:// 开头的真实资料快照（排除合成夹具）",
            "encoder": (runs[0]["freeze"]["encoder"] if runs else None),
            "retriever": "local exact-cosine vector search",
            "k": k,
            "evidence_budget": "固定 top-k=5；证据 token 为估算，同一把尺子比较",
            "questions": "开发集 D01–D10，标注与 07 冻结一致",
        },
        "corpus_freeze": (runs[0]["freeze"]["corpus_hash"] if runs else None),
        "documents": (runs[0]["freeze"]["documents"] if runs else []),
        "strategies": [
            {
                "splitter": r["splitter"],
                "case_count": r["case_count"],
                "scored_cases": r["scored_cases"],
                "failed_cases": r["failed_cases"],
                "aggregate": r["aggregate"],
                "elapsed_ms": r["elapsed_ms"],
                "wall_ms": r["wall_ms"],
                "census": r["census"],
                "freeze": {"sample_hash": r["freeze"]["sample_hash"],
                           "corpus_hash": r["freeze"]["corpus_hash"]},
            }
            for r in runs
        ],
        "deltas_vs_baseline": deltas,
        "per_case": per_case,
        "network_called": False,
        "billed_calls": 0,
        "cost_rmb": 0,
        "complete": False,
        "not_run": list(NOT_RUN) + [
            "生成侧与人工语义复核：本对照只做检索结构指标，未运行付费生成。",
            "PDF 策略对照：" + NOT_COMPARED["pdf-pages-v1"],
        ],
        "evidence_tokens_estimate_note": TOKEN_ESTIMATE_NOTE,
        "manual_review": "pending",
    }


def print_case_table(report):
    splitters = report["splitter_compared"]
    width = max(len(s) for s in splitters)
    header = "用例   " + "  ".join(f"{s[:width]:>{width}}" for s in splitters)
    print("\n" + header)
    print("-" * len(header))
    for cid, row in report["per_case"].items():
        cells = []
        for s in splitters:
            cell = row.get(s)
            if cell is None or cell["recall_at_5"] is None:
                cells.append(f"{'n/a':>{width}}")
            else:
                mark = "!"
                if cell["broken_bundles"]:
                    mark = "~"
                cells.append(f"{cell['recall_at_5']:>{width}.2f}".rjust(width))
        print(f"{cid:<6} " + "  ".join(cells))
    print("\n(~ = 有片段被切开而未被完整取回；n/a = 未能评分)")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="在固定语料与问题上对照切分策略")
    parser.add_argument("--splitter", action="append", default=None,
                        help="只跑指定策略，可重复；默认全部 Markdown 策略")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--db", default=str(SPLITTER_SOURCE),
                        help="提供快照的真实工作库")
    parser.add_argument("--out", default=None, help="报告输出路径")
    parser.add_argument("--preview", default=None,
                        help="另存切分预览与原文前后对照（Issue 15 证据）")
    parser.add_argument("--context", type=int, default=2,
                        help="预览中每个片段保留的原文前后行数")
    parser.add_argument("--json", action="store_true", help="打印完整 JSON")
    args = parser.parse_args()

    strategies = tuple(args.splitter) if args.splitter else MARKDOWN_STRATEGIES
    report = compare(strategies, k=args.k, source_db=args.db)
    print_case_table(report)
    print("\n== 相对基线的变化 ==")
    for delta in report["deltas_vs_baseline"]:
        print(f"  {delta['splitter']}: recall {delta['baseline_recall_at_5']:.3f} → "
              f"{delta['recall_at_5']:.3f} ({delta['delta']:+.3f})  "
              f"token {delta['baseline_mean_evidence_tokens']:.0f} → "
              f"{delta['mean_evidence_tokens']:.0f}  "
              f"提升={delta['gained_cases'] or '无'}  退化={delta['lost_cases'] or '无'}")
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"\n报告已写入：{target}")
    if args.preview:
        shots = preview(strategies, source_db=args.db, context=args.context)
        target = Path(args.preview)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(shots, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        total = sum(len(d["chunks"]) for s in shots["strategies"].values()
                    for d in s)
        print(f"\n切分预览已写入：{target}（{total} 个片段，含原文前后对照）")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
