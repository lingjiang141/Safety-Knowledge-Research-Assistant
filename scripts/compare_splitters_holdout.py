"""Compare splitters on the *holdout* sample (Issue 12 follow-up, free & offline).

Issue 15 compared splitters on the development sample and left the final choice
to Issue 12 ("最终取舍在 12 用保留集验收后定"). The sealed holdout run happened on
the baseline splitter (`heading-lines-v1:20`, recall_at_5 = 0.75). This script runs
the *same* holdout through the structural splitter `heading-block-v2` to answer the
one open question: does the finer splitter rescue the four retrieval gaps
(H03 / H04 / H09 / Q06, all "coarse 18-20-line block dilutes the answer")?

Honesty note (in the report too): the baseline 0.75 is the *sealed independent*
number (first open of the holdout, no tuning). This block-v2 run is a *post-hoc
comparison* to decide whether to adopt the structural splitter as the final
configuration. It is NOT a second independent score, and it must not silently
replace 0.75. Both numbers are reported side by side.

Run it free, no network, no ledger:

    python scripts/compare_splitters_holdout.py \
      --out docs/evidence/issue12-holdout-splitter-comparison-20260910.json
"""
import argparse
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.eval import NOT_RUN, TOKEN_ESTIMATE_NOTE, load_cases, run_baseline  # noqa: E402
from skra.store import SPLITTER, STRUCTURED_SPLITTER, Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV_CASES = ROOT / "examples/eval-dev-cases.json"
HOLDOUT_CASES = ROOT / "examples/eval-holdout-cases.json"
SOURCE_DB = ROOT / ".data/knowledge.sqlite3"


def load_corpus(source_db=SOURCE_DB):
    db = sqlite3.connect(source_db)
    db.row_factory = sqlite3.Row
    docs = [dict(r) for r in db.execute(
        "SELECT title,source,license,acquired,snapshot FROM documents "
        "WHERE source LIKE 'https://%' ORDER BY source")]
    db.close()
    return docs


def materialise(docs, splitter, workdir, tag):
    store = Store(Path(workdir) / f"{tag}.sqlite3")
    for doc in docs:
        path = Path(workdir) / f"{tag}-{len(doc['source'])}.md"
        path.write_text(doc["snapshot"], encoding="utf-8")
        store.ingest(path, doc["title"], doc["source"], doc["license"],
                     doc["acquired"], splitter=splitter)
    return store


def run(splitters, k=5, source_db=SOURCE_DB):
    docs = load_corpus(source_db)
    if not docs:
        raise SystemExit("工作库里没有真实资料，先导入 OWASP 快照再对照。")
    from skra.vector import VectorSearch
    runs = []
    with tempfile.TemporaryDirectory() as workdir:
        for splitter in splitters:
            tag = splitter.replace(":", "_").replace("-", "_")
            store = materialise(docs, splitter, workdir, tag)
            try:
                vector = VectorSearch(store)
                vector.build()
                started = time.perf_counter()
                report = run_baseline(store, DEV_CASES, vector.search, k=k,
                                      encoder=vector.encoder,
                                      holdout=HOLDOUT_CASES, kind="holdout")
                report["wall_ms"] = (time.perf_counter() - started) * 1000
                report["splitter"] = splitter
                runs.append(report)
            finally:
                store.close()
    return runs


def build_report(runs, k):
    by_splitter = {r["splitter"]: r for r in runs}
    cases = load_cases(HOLDOUT_CASES, kind="holdout")
    per_case = {}
    for case in cases:
        row = {"case_id": case.id, "question": case.question,
               "annotated_bundles": len(case.evidence)}
        for splitter, report in by_splitter.items():
            scored = next((c for c in report["cases"] if c["case_id"] == case.id), None)
            row[splitter] = None if scored is None else {
                "recall_at_5": scored["recall_at_5"],
                "retrieved_bundles": scored["retrieved_bundles"],
                "broken_bundles": scored["broken_bundles"],
                "evidence_tokens": scored["evidence_tokens"],
            }
        per_case[case.id] = row

    base = by_splitter.get(SPLITTER)
    deltas = []
    if base:
        for splitter, report in by_splitter.items():
            if splitter == SPLITTER:
                continue
            gained, lost = [], []
            for case in cases:
                b = per_case[case.id][SPLITTER]
                n = per_case[case.id][splitter]
                if b is None or n is None:
                    continue
                if n["recall_at_5"] is None or b["recall_at_5"] is None:
                    continue
                if n["recall_at_5"] > b["recall_at_5"]:
                    gained.append(case.id)
                elif n["recall_at_5"] < b["recall_at_5"]:
                    lost.append(case.id)
            deltas.append({
                "splitter": splitter,
                "vs": SPLITTER,
                "recall_at_5": report["aggregate"]["recall_at_5"],
                "baseline_recall_at_5": base["aggregate"]["recall_at_5"],
                "delta": (report["aggregate"]["recall_at_5"]
                          - base["aggregate"]["recall_at_5"]),
                "gained_cases": gained,
                "lost_cases": lost,
            })

    return {
        "kind": "splitter-comparison-holdout",
        "sample": "examples/eval-holdout-cases.json",
        "sample_kind": "holdout",
        "splitter_compared": list(by_splitter),
        "fixed_factors": {
            "corpus": "工作库中 source 以 https:// 开头的真实资料快照（排除合成夹具）",
            "encoder": runs[0]["freeze"]["encoder"],
            "retriever": "local exact-cosine vector search",
            "k": k,
            "questions": "保留集 H01–H10（07 冻结、12 首次开封）",
        },
        "honesty": (
            "基线 recall_at_5=0.75 是保留集首次开封的「密封独立成绩」；"
            "本对照是开封后的切分取舍比较，不是第二个独立成绩，两者并列、不互相替换。"
        ),
        "strategies": [
            {"splitter": r["splitter"], "aggregate": r["aggregate"],
             "wall_ms": r["wall_ms"]} for r in runs
        ],
        "deltas_vs_baseline": deltas,
        "per_case": per_case,
        "network_called": False,
        "billed_calls": 0,
        "cost_rmb": 0,
        "complete": False,
        "not_run": list(NOT_RUN) + ["生成侧与人工语义复核：本对照只做检索结构指标。"],
        "evidence_tokens_estimate_note": TOKEN_ESTIMATE_NOTE,
        "manual_review": "pending",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="保留集上对照基线切分与结构切分")
    parser.add_argument("--splitter", action="append", default=None,
                        help="只跑指定策略，可重复；默认基线 + heading-block-v2")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--out", default=None, help="报告输出路径")
    args = parser.parse_args()
    splitters = tuple(args.splitter) if args.splitter else (SPLITTER, STRUCTURED_SPLITTER)
    runs = run(splitters, k=args.k)
    report = build_report(runs, args.k)

    for r in runs:
        a = r["aggregate"]
        print(f"{r['splitter']:24s} recall@5={a['recall_at_5']:5.3f} "
              f"tokens={a['mean_evidence_tokens']:7.1f} "
              f"broken={a['broken_bundles']}")

    print("\n== 逐例（重点看 H03/H04/H09）==")
    splitters = list(report["splitter_compared"])
    w = max(len(s) for s in splitters)
    print("用例   " + "  ".join(f"{s[:w]:>{w}}" for s in splitters))
    for cid in sorted(report["per_case"]):
        row = report["per_case"][cid]
        cells = []
        for s in splitters:
            cell = row.get(s)
            cells.append("n/a" if (cell is None or cell["recall_at_5"] is None)
                         else f"{cell['recall_at_5']:.2f}".rjust(w))
        print(f"{cid:<6} " + "  ".join(cells))

    print("\n== 相对基线的变化 ==")
    for d in report["deltas_vs_baseline"]:
        print(f"  {d['splitter']}: {d['baseline_recall_at_5']:.3f} → "
              f"{d['recall_at_5']:.3f} ({d['delta']:+.3f})  "
              f"提升={d['gained_cases'] or '无'}  退化={d['lost_cases'] or '无'}")

    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"\n报告已写入：{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
