"""Prepare or run original-source (real material + retrieval) acceptance cases.

Unlike scripts/check_boundaries.py, this uses the real knowledge base and the
local vector retriever, so the answer pipeline exercises retrieval as well as
generation. Excluded fixture documents are filtered out of search results so a
synthetic demo cannot pollute a real-source question.

Without --live the script only prepares: it loads cases, builds the retriever,
runs one free preflight against the first case, and writes a report. No network
call and no charge happen unless --live is passed.
"""
import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.answer import answer, Ledger
from skra.store import Store
from skra.vector import VectorSearch

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "examples/acceptance-cases.json"


def load_spec():
    return json.loads(CASES.read_text(encoding="utf-8"))


def make_search(vector, excluded):
    """Wrap VectorSearch.search, filtering excluded doc_ids, keeping (query, limit)."""
    def selected(query, limit=5):
        # Ask for more candidates, then drop excluded docs and keep the limit.
        raw = vector.search(query, min(20, limit + len(excluded) + 3))
        kept = [c for c in raw["candidates"] if c["doc_id"] not in excluded]
        raw = {**raw, "candidates": kept[:limit],
               "excluded_doc_ids": sorted(excluded),
               "filter_note": "已从检索结果剔除合成夹具文档。" if excluded else ""}
        # Persist the filtered result so replay sees exactly what the model saw.
        with vector.db:
            row = vector.db.execute(
                "INSERT INTO runs(created,query,result,elapsed_ms) VALUES (datetime('now'),?,?,?)",
                (query, json.dumps(raw, ensure_ascii=False), raw["elapsed_ms"]))
        raw["run_id"] = row.lastrowid
        return raw
    return selected


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--config", default="examples/deepseek-flash.2026-09-09.json")
    parser.add_argument("--case", action="append", help="只运行指定 case id，可重复")
    parser.add_argument("--db", default=".data/knowledge.sqlite3")
    args = parser.parse_args()

    spec = load_spec()
    cases = spec["cases"]
    if args.case:
        unknown = set(args.case) - {c["id"] for c in cases}
        if unknown:
            parser.error("Unknown case ID: " + ", ".join(sorted(unknown)))
        cases = [c for c in cases if c["id"] in args.case]

    excluded = set(spec.get("excluded_doc_ids", []))
    store = Store(ROOT / args.db)
    ledger = Ledger(ROOT / ".data/budget.sqlite3")
    report = {
        "mode": "live" if args.live else "prepared-no-api",
        "evidence_mode": "real-material-vector-retrieval",
        "source_set": spec.get("kind"),
        "excluded_doc_ids": sorted(excluded),
        "human_review": "pending",
        "cases": [],
        "complete": False,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = ROOT / f".data/acceptance-report-{stamp}.json"
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.live else None
        vector = VectorSearch(store)
        search = make_search(vector, excluded)
        # Show what each case retrieves (free, no API).
        for case in cases:
            row = {"id": case["id"], "question": case["question"],
                   "expected_status": case["expected_status"],
                   "expected_sources": case.get("expected_sources", []),
                   "human_review": case.get("human_review", []),
                   "review_result": "pending"}
            retrieval = search(case["question"], 3)
            row["retrieval_run_id"] = retrieval["run_id"]
            row["retrieved"] = [
                {"doc_id": c["doc_id"], "section": c["section"],
                 "start_line": c["start_line"], "end_line": c["end_line"],
                 "score": round(c["score"], 4)}
                for c in retrieval["candidates"]]
            row["retrieved_count"] = len(retrieval["candidates"])
            report["cases"].append(row)

        if args.live:
            if not report["cases"]:
                raise ValueError("没有可运行的用例。")
            check = answer(store, cases[0]["question"], ledger, config,
                           preflight=True, search=search)
            if not check["budget_ready"]:
                raise ValueError("预算不足或存在未结算请求。")
            key = os.environ.get("DEEPSEEK_API_KEY")
            if not key:
                if not sys.stdin.isatty():
                    raise ValueError("请在交互终端隐藏输入密钥。")
                key = getpass.getpass("DeepSeek API key（隐藏输入、本次进程内使用）：")
            for case, row in zip(cases, report["cases"], strict=True):
                try:
                    result = answer(store, case["question"], ledger, config, key, search=search)
                    row["result"] = result
                    row["status_matches"] = result["status"] == case["expected_status"]
                except ValueError as exc:
                    row["error"] = str(exc)
                    break
        else:
            for row in report["cases"]:
                row["state"] = "prepared-not-executed"

        report["preparation_complete"] = all("retrieved_count" in r for r in report["cases"])
        report["complete"] = (args.live and len(report["cases"]) == len(cases)
                              and all("error" not in r for r in report["cases"]))
    except (OSError, ValueError) as exc:
        report["error"] = str(exc)
    finally:
        report["budget"] = ledger.summary()
        dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        store.close()
        ledger.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Report:", dest)
    return 2 if "error" in report or any("error" in r for r in report["cases"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
