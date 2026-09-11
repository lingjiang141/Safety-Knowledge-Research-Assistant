"""Switch supplementary retrieval on and off on the frozen development sample (Issue 10).

One factor changes between the two runs: whether the bounded orchestrator may run
its supplementary rounds. The corpus, the splitter, the questions, the
annotations, the encoder, top-k and the answer prompt all stay fixed, so any
difference in the report can only come from the number of *retrieval rounds*.

  off  one retrieval pass, top-k candidates, no further round
  on   the first pass plus at most two supplementary rounds, each widening the
       accumulated evidence (never replacing it)

Two honest caveats, both stated in the report rather than hidden:

  * Only the retrieval side is measured here. Whether the extra evidence makes
    the generated answer better is a semantic question that needs paid calls and
    human review, so it is named as not-run -- not quietly implied by a recall
    number.
  * In this configuration the two modes are expected to agree, because the
    supplementary round re-asks the *same* query against a *static* corpus: the
    retriever returns the same top-k, the accumulated set does not grow, and the
    loop stops on NO_NEW_EVIDENCE. That is a real finding (the bound is safe and
    cannot invent evidence) and it is reported as such, not dressed up as an
    improvement.

The holdout set stays sealed: this script only ever names the development sample.
An ordinary run does no paid calls and costs nothing.

    python scripts/compare_supplement.py
    python scripts/compare_supplement.py --out docs/evidence/issue10-supplement.json
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.eval import (NOT_RUN, TOKEN_ESTIMATE_NOTE,  # noqa: E402
                       load_cases, resolve_span)
from skra.orchestrate import MAX_SUPPLEMENTARY_ROUNDS, Orchestrator  # noqa: E402
from skra.store import SPLITTER, Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEV_CASES = ROOT / "examples/eval-dev-cases.json"
SOURCE_DB = ROOT / ".data/knowledge.sqlite3"

OFF = "supplement-off"
ON = "supplement-on"
WIDENING = "supplement-widening"
MODES = (OFF, ON, WIDENING)


def load_corpus(source_db=SOURCE_DB):
    """The real OWASP snapshots; the synthetic CC0 fixture is excluded."""
    import sqlite3
    db = sqlite3.connect(source_db)
    db.row_factory = sqlite3.Row
    docs = [dict(r) for r in db.execute(
        "SELECT title,source,license,acquired,snapshot FROM documents "
        "WHERE source LIKE 'https://%' ORDER BY source")]
    db.close()
    return docs


def materialise(docs, splitter=SPLITTER, workdir=None, tag="supplement"):
    """Build a throwaway database holding the corpus under one splitter."""
    store = Store(Path(workdir) / f"{tag}.sqlite3")
    for doc in docs:
        path = Path(workdir) / f"{tag}-{len(doc['source'])}.md"
        path.write_text(doc["snapshot"], encoding="utf-8")
        store.ingest(path, doc["title"], doc["source"], doc["license"],
                     doc["acquired"], splitter=splitter)
    return store


def _bundle_ids(store, case):
    """The active chunk ids that together cover each annotated bundle."""
    covered = []
    for span in case.evidence:
        covered.extend(c["id"] for c in resolve_span(store, span))
    return sorted(set(covered))


def run_mode(store, cases, mode, search, k=5):
    """Run every case under one mode and score retrieval on the reached evidence.

    The denominator is the annotated bundle count, unchanged between modes; what
    the mode changes is which chunks were reached. For the `on` mode the reached
    set is the orchestrator's accumulated evidence, so a supplementary round can
    only ever add ids -- never remove one the first pass already had.

    `supplement-widening` is the same loop with a retriever that returns *more*
    candidates each round (k, 2k, 3k). That is what exercises the productive
    path: real new evidence arrives, so the loop keeps going until the two-round
    cap stops it. `supplement-on` cannot show that, because re-asking the same
    query against a static corpus returns the same top-k and stops immediately
    on NO_NEW_EVIDENCE -- both are reported, and neither is dressed up.
    """
    rows = []
    started = time.perf_counter()
    for case in cases:
        case_started = time.perf_counter()
        if mode in (ON, WIDENING):
            if mode == WIDENING:
                # The orchestrator always asks with limit=k; this wrapper widens
                # the request each round, so new evidence can actually arrive and
                # the two-round cap becomes the binding stop reason.
                state = {"n": 0}

                def loop_search(query, limit, _q=case.question, _s=state):
                    _s["n"] += 1
                    return search(_q, k * _s["n"])
            else:
                loop_search = search

            def answer_once(evidence, round_no):
                return {"reached": len(evidence), "round": round_no}

            run = Orchestrator(loop_search, answer_once,
                               is_sufficient=lambda result: False,
                               deadline=None)
            outcome = run.execute(case.question, limit=k)
            reached_ids = [c["id"] for c in outcome["evidence"]]
            stop_reason = outcome["stop_reason"]
            stop_detail = outcome["stop_detail"]
            rounds = outcome["supplementary_rounds"]
            trace = outcome["trace"]
        else:
            result = search(case.question, k)
            reached_ids = [c["id"] for c in result.get("candidates", ())][:k]
            stop_reason, stop_detail, rounds, trace = None, None, 0, []

        annotated = _bundle_ids(store, case)
        hit = sorted(set(annotated) & set(reached_ids))
        rows.append({
            "case_id": case.id,
            "question": case.question,
            "expected_status": case.expected_status,
            "annotated_bundles": len(case.evidence),
            "annotated_covering_chunk_ids": annotated,
            "reached_chunk_ids": reached_ids,
            "covering_chunks_reached": hit,
            "all_bundles_reached": bool(annotated) and set(annotated) <= set(reached_ids),
            "stop_reason": stop_reason,
            "stop_detail": stop_detail,
            "supplementary_rounds": rounds,
            "trace": trace,
            "elapsed_ms": (time.perf_counter() - case_started) * 1000,
        })
    return {"mode": mode, "cases": rows, "elapsed_ms": (time.perf_counter() - started) * 1000}


def build_report(runs, cases, k, splitter, corpus_hash, docs):
    by_mode = {r["mode"]: r for r in runs}
    per_case = {}
    for case in cases:
        row = {"case_id": case.id, "question": case.question,
               "expected_status": case.expected_status,
               "annotated_bundles": len(case.evidence)}
        for mode, report in by_mode.items():
            scored = next((c for c in report["cases"] if c["case_id"] == case.id), None)
            row[mode] = None if scored is None else {
                "annotated_covering_chunk_ids": scored["annotated_covering_chunk_ids"],
                "reached_chunk_ids": scored["reached_chunk_ids"],
                "covering_chunks_reached": scored["covering_chunks_reached"],
                "all_bundles_reached": scored["all_bundles_reached"],
                "stop_reason": scored["stop_reason"],
                "supplementary_rounds": scored["supplementary_rounds"],
            }
        per_case[case.id] = row

    gained, lost, same = [], [], []
    for case in cases:
        off = per_case[case.id][OFF]
        on = per_case[case.id][ON]
        if off is None or on is None:
            continue
        off_set, on_set = set(off["reached_chunk_ids"]), set(on["reached_chunk_ids"])
        if on_set > off_set:
            gained.append(case.id)
        elif on_set < off_set:
            lost.append(case.id)
        else:
            same.append(case.id)

    wide_gained, wide_lost = [], []
    for case in cases:
        off = per_case[case.id][OFF]
        wide = per_case[case.id].get(WIDENING)
        if off is None or wide is None:
            continue
        if set(wide["reached_chunk_ids"]) > set(off["reached_chunk_ids"]):
            wide_gained.append(case.id)
        elif set(wide["reached_chunk_ids"]) < set(off["reached_chunk_ids"]):
            wide_lost.append(case.id)

    stop_counts, wide_stop_counts = {}, {}
    for scored in by_mode[ON]["cases"]:
        key = scored["stop_reason"]
        stop_counts[key] = stop_counts.get(key, 0) + 1
    for scored in by_mode[WIDENING]["cases"]:
        key = _reason(scored["stop_reason"])
        wide_stop_counts[key] = wide_stop_counts.get(key, 0) + 1
    rounds_reached = [scored["supplementary_rounds"] for scored in by_mode[ON]["cases"]]
    wide_rounds = [scored["supplementary_rounds"] for scored in by_mode[WIDENING]["cases"]]

    return {
        "kind": "supplement-comparison",
        "sample": str(DEV_CASES.relative_to(ROOT)).replace("\\", "/"),
        "sample_kind": "development",
        "holdout_loaded": False,
        "modes_compared": list(by_mode),
        "max_supplementary_rounds": MAX_SUPPLEMENTARY_ROUNDS,
        "fixed_factors": {
            "corpus": "工作库中 source 以 https:// 开头的真实资料快照（排除合成夹具）",
            "splitter": splitter,
            "k": k,
            "questions": "开发集 D01–D10，标注与 07 冻结一致",
            "generation": "未运行：本对照只测检索侧到达的证据，不产生付费回答",
            "changed_factor": ("补充检索轮数：关闭 / 初次之外最多两轮；"
                               "另含“逐轮放宽 k”的加宽臂以触发生效路径"),
        },
        "corpus_hash": corpus_hash,
        "documents": docs,
        "modes": [
            {
                "mode": r["mode"],
                "case_count": len(r["cases"]),
                "elapsed_ms": r["elapsed_ms"],
            }
            for r in runs
        ],
        "on_stop_reasons": stop_counts,
        "on_supplementary_rounds": rounds_reached,
        "widening_stop_reasons": wide_stop_counts,
        "widening_supplementary_rounds": wide_rounds,
        "delta": {
            "gained_cases": gained,
            "lost_cases": lost,
            "unchanged_cases": same,
            "note": ("补充检索只能向累积证据里增加片段，不会移除初次已有的片段；"
                     "因此 lost_cases 恒为空是结构性质，不是效果证据。"),
        },
        "widening_delta": {
            "gained_cases": wide_gained,
            "lost_cases": wide_lost,
            "note": ("加宽臂逐轮放宽 k，用于让补充轮真正带来新证据并触发两轮上限；"
                     "它验证的是停止规则与累积语义，不是检索质量提升。"),
        },
        "per_case": per_case,
        "network_called": False,
        "billed_calls": 0,
        "cost_rmb": 0,
        "complete": False,
        "not_run": list(NOT_RUN) + [
            "生成侧语义效果（补充证据是否让回答更好）：需付费调用与人工复核，本任务未运行。",
            "保留集执行：按设计封存至 Issue 12。",
        ],
        "evidence_tokens_estimate_note": TOKEN_ESTIMATE_NOTE,
        "manual_review": "pending",
    }


def print_case_table(report):
    print("\n用例        off         on       widening   on 停止原因           轮数")
    print("-" * 82)
    for cid, row in report["per_case"].items():
        off, on, wide = row.get(OFF), row.get(ON), row.get(WIDENING)
        if off is None or on is None:
            print(f"{cid:<9} n/a")
            continue
        wide_n = "-" if wide is None else len(wide["reached_chunk_ids"])
        print(f"{cid:<9} {len(off['reached_chunk_ids']):>3}"
              f"         {len(on['reached_chunk_ids']):>3}"
              f"         {str(wide_n):>3}"
              f"        {_reason(on['stop_reason']):<20} {on['supplementary_rounds']}")


def _reason(stop_reason):
    """A stop reason is a str enum; print its word, not `StopReason.X`."""
    return getattr(stop_reason, "value", stop_reason)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="在固定开发集上对照补充检索的开关")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--splitter", default=SPLITTER)
    parser.add_argument("--db", default=str(SOURCE_DB), help="提供快照的真实工作库")
    parser.add_argument("--out", default=None, help="报告输出路径")
    parser.add_argument("--json", action="store_true", help="打印完整 JSON")
    args = parser.parse_args()

    docs = load_corpus(args.db)
    if not docs:
        raise SystemExit("工作库里没有真实资料，先导入 OWASP 快照再对照。")
    cases = load_cases(DEV_CASES)
    with tempfile.TemporaryDirectory() as workdir:
        from skra.vector import Encoder, VectorSearch
        encoder = Encoder()
        store = materialise(docs, args.splitter, workdir, "supplement")
        try:
            vector = VectorSearch(store, encoder=encoder)
            vector.build()
            search = vector.search
            runs = [run_mode(store, cases, mode, search, k=args.k)
                    for mode in MODES]
            # The corpus hash is read from the materialised store, not the sample,
            # so the report ties back to the exact chunks that were searched.
            from skra.eval import freeze_sample
            frozen = freeze_sample(cases, store, encoder)
        finally:
            store.close()

    report = build_report(runs, cases, args.k, args.splitter,
                          frozen["corpus_hash"], frozen["documents"])
    print_case_table(report)
    print("\n== 停止原因分布 ==")
    print("  开启补充（同一查询、静态语料）：")
    for reason, count in sorted(report["on_stop_reasons"].items(), key=lambda kv: -kv[1]):
        print(f"    {_reason(reason):<20} {count} 例")
    print("  加宽臂（逐轮放宽 k）：")
    for reason, count in sorted(report["widening_stop_reasons"].items(),
                                 key=lambda kv: -kv[1]):
        print(f"    {reason:<20} {count} 例")
    print("\n== 相对关闭补充检索的变化 ==")
    gained = report["delta"]["gained_cases"]
    lost = report["delta"]["lost_cases"]
    print(f"  同一查询：到达证据增加 {gained or '无'}；减少 {lost or '无'}；"
          f"一致 {len(report['delta']['unchanged_cases'])} 例")
    wg = report["widening_delta"]["gained_cases"]
    wl = report["widening_delta"]["lost_cases"]
    print(f"  加宽臂：到达证据增加 {wg or '无'}；减少 {wl or '无'}")
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
