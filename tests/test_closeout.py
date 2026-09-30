"""Delivery regressions: evidence belongs to its source, redundant calls stop."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import compare_splitters, demo
from scripts.prepare_demo import prepare
from skra.eval import Case, EvidenceSpan
from skra.orchestrate import Orchestrator
from skra.store import Store, SPLITTER


class CloseoutTest(unittest.TestCase):
    def docs(self):
        return [dict(title=name, source=f"https://example.test/{name}",
                     license="CC0", acquired="2026-09-10",
                     snapshot=f"# {name}\n\n{name} only evidence\n")
                for name in ("alpha", "beta")]

    def test_preview_never_attributes_another_documents_text(self):
        with tempfile.TemporaryDirectory() as directory:
            store = compare_splitters.materialise(self.docs(), SPLITTER, directory, "source")
            store.close()
            result = compare_splitters.preview((SPLITTER,), Path(directory) / "source.sqlite3")
        for doc in result["strategies"][SPLITTER]:
            self.assertEqual(len(doc["chunks"]), 1)
            self.assertIn(doc["title"] + " only evidence", doc["chunks"][0]["text"])

    def test_demo_does_not_count_same_lines_from_another_source(self):
        class WrongSourceVector:
            def __init__(self, store, encoder=None):
                self.store = store

            def build(self):
                pass

            def search(self, query, limit):
                return self.store.search("beta", limit)

        case = Case(demo.SHOWCASE, "alpha", "grounded",
                    (EvidenceSpan(self.docs()[0]["source"], 3, 3),))
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with patch("skra.vector.VectorSearch", WrongSourceVector), patch("skra.vector.Encoder"):
                with contextlib.redirect_stdout(output):
                    demo.step_before_after(self.docs(), directory, [case])
        self.assertNotIn("✅", output.getvalue())
        self.assertEqual(output.getvalue().count("未进前 5"), 3)

    def test_no_new_evidence_does_not_generate_another_answer(self):
        calls = []
        run = Orchestrator(lambda q, k: {"candidates": [{"id": "same"}]},
                           lambda evidence, round_no: calls.append(round_no))
        result = run.execute("query")
        self.assertEqual(result["stop_reason"], "no_new_evidence")
        self.assertEqual(calls, [0])

    def test_preparation_uses_committed_corpus_and_refuses_existing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fresh.sqlite3"
            result = prepare(target)
            self.assertEqual(result["documents"], 3)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare(target)
            self.assertEqual(target.read_bytes(), before)

    def test_expired_pricing_does_not_break_offline_demo(self):
        import json
        from skra.answer import Ledger
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "docs.sqlite3")
            ledger = Ledger(Path(directory) / "budget.sqlite3")
            self.addCleanup(store.close)
            self.addCleanup(ledger.close)
            store.ingest(demo.ROOT / "examples/security-demo.md", "demo", "urn:demo",
                         "CC0", "2026-09-10")
            config = json.loads((demo.ROOT / "examples/deepseek-flash.2026-09-09.json").read_text(encoding="utf-8"))
            config["verified_at"] = "2000-01-01"
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    demo.step_generation(store, ledger, False, path)
                self.assertIn("预检不可用", output.getvalue())
                self.assertEqual(ledger.summary()["spent_rmb"], 0)
            finally:
                store.close()
                ledger.close()


if __name__ == "__main__":
    unittest.main()
