"""Controlled evidence tests isolate generation from retrieval quality."""
import json
from pathlib import Path
from datetime import datetime, timezone
from skra.answer import question_parts

CASES = Path(__file__).resolve().parents[1] / "examples/boundary-cases.json"


def load_cases():
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def prepare(store, directory, case):
    """Return an explicitly labelled oracle-evidence adapter, not a retriever."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    evidence = []
    for index, source in enumerate(case["sources"]):
        file = directory / f"{case['id']}-{index}.md"
        file.write_text(source, encoding="utf-8")
        doc = store.ingest(file, f"Synthetic {case['id']} / {index}",
                           f"urn:skra:boundary:v1:{case['id']}:{index}", "CC0-1.0", "2026-09-09")
        for row in store.db.execute("SELECT id FROM chunks WHERE doc_id=?", (doc["document_id"],)):
            evidence.append(store.read(row[0]))

    def selected(query, limit):
        result = {"mode": "controlled-evidence-not-retrieval", "query": query,
                  "candidates": evidence, "case_id": case["id"], "elapsed_ms": 0}
        with store.db:
            row = store.db.execute("INSERT INTO runs(created,query,result,elapsed_ms) VALUES (?,?,?,0)",
                (datetime.now(timezone.utc).isoformat(), query, json.dumps(result, ensure_ascii=False)))
        result["run_id"] = row.lastrowid
        return result
    return evidence, selected


def contract_response(case, evidence):
    """Hand-authored response fixture; not an LLM prediction or quality metric."""
    cited = evidence if case["expected_status"] != "insufficient" else []
    return {"status": case["expected_status"],
            "claims": [{"text": case["contract_text"], "citations": [e["id"] for e in cited]}] if cited else [],
            "citations": [{"id": e["id"], "quote": e["text"],
                           "translation": "受控测试释义占位，不作为翻译质量证据。"} for e in cited],
            "missing": case["contract_missing"],
            "coverage": [{"question_id": q["id"],
                          "claims": [0] if cited and not (case["id"] == "partial" and i == 1) else [],
                          "missing": case["contract_missing"] if not cited or (case["id"] == "partial" and i == 1) else ""}
                         for i, q in enumerate(question_parts(case["question"]))]}
