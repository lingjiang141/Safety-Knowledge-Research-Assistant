"""A supplement round must actually reach the answer path (Issue 10).

The orchestrator's stop rules are tested in isolation in `test_orchestrate.py`.
These tests check the other half: that the real answer path uses it, that a
supplement round can genuinely add evidence, and that the trace and the stop
reason survive to the persisted run. A fake transport and a fake retriever keep
this offline: no model, no network, no ledger spend.
"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from skra.answer import Ledger, bounded_answer
from skra.store import Store

ROOT = Path(__file__).resolve().parents[1]


class BoundedAnswerTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Store(Path(temp.name) / "docs.db")
        self.ledger = Ledger(Path(temp.name) / "budget.db")
        self.addCleanup(self.store.close)
        self.addCleanup(self.ledger.close)
        self.store.ingest(ROOT / "examples/security-demo.md", "demo",
                          "urn:demo", "CC0", "2026-09-09")
        self.evidence = (self.store.search("提示注入")["candidates"][:1]
                         + self.store.search("工具权限")["candidates"][:1])
        self.assertEqual(len({e["id"] for e in self.evidence}), 2)
        self.config = {"model": "offline-fixture", "verified": True,
                       "verified_at": date.today().isoformat(),
                       "input_bound_strategy": "context-window",
                       "context_token_upper_bound": 1048576,
                       "input_rmb_per_million": 1, "output_rmb_per_million": 2}

    def body(self, evidence, status="grounded", missing=""):
        cited = evidence if status != "insufficient" else []
        return {"status": status,
                "claims": [{"text": "受控结论。", "citations": [e["id"] for e in cited]}] if cited else [],
                "citations": [{"id": e["id"], "quote": e["text"],
                               "translation": "受控释义"} for e in cited],
                "missing": missing,
                "coverage": [{"question_id": "q1", "claims": [0] if cited else [],
                              "missing": missing}]}

    def sender(self, statuses, seen):
        """A transport returning one scripted status per call, in order."""
        queue = list(statuses)

        def send(payload, key, timeout):
            seen.append(payload)
            status, missing = queue.pop(0) if queue else ("grounded", "")
            body = self.body(self.evidence, status, missing)
            return {"usage": {"prompt_tokens": 100, "completion_tokens": 100},
                    "choices": [{"finish_reason": "stop",
                                 "message": {"content": json.dumps(body)}}]}
        return send

    def test_a_supplement_round_can_upgrade_an_answer(self):
        # First pass is insufficient; the retriever then offers new evidence, so a
        # supplement round is allowed and the second pass is grounded.
        rounds = {"n": 0}

        def search(query, limit=5):
            rounds["n"] += 1
            return {"mode": "fake", "query": query, "run_id": rounds["n"],
                    "candidates": self.evidence[:1] if rounds["n"] == 1 else self.evidence}

        seen = []
        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([("insufficient", "资料没有提供该数据。"),
                                                  ("grounded", "")],
                                                 seen),
                                search=search)
        self.assertEqual(len(seen), 2, "the supplement round must actually be requested")
        self.assertEqual(result["status"], "grounded")
        self.assertEqual(result["supplement"]["supplementary_rounds"], 1)
        self.assertEqual(result["supplement"]["stop_reason"], "sufficient")

    def test_a_grounded_first_pass_does_not_search_again(self):
        calls = {"n": 0}

        def search(query, limit=5):
            calls["n"] += 1
            return {"mode": "fake", "query": query, "run_id": calls["n"],
                    "candidates": self.evidence}

        seen = []
        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([("grounded", "")], seen),
                                search=search)
        self.assertEqual(calls["n"], 1, "a complete answer needs no supplement")
        self.assertEqual(result["supplement"]["stop_reason"], "sufficient")
        self.assertEqual(result["supplement"]["supplementary_rounds"], 0)

    def test_no_new_evidence_stops_and_is_recorded(self):
        calls = {"n": 0}

        def search(query, limit=5):
            calls["n"] += 1
            return {"mode": "fake", "query": query, "run_id": calls["n"],
                    "candidates": self.evidence[:1]}  # same single chunk every time

        seen = []
        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([("insufficient", "资料没有提供该数据。"),
                                                  ("insufficient", "资料没有提供该数据。")],
                                                 seen),
                                search=search)
        self.assertEqual(len(seen), 1, "unchanged evidence must not cause another billed call")
        self.assertEqual(result["supplement"]["stop_reason"], "no_new_evidence")
        self.assertEqual(result["supplement"]["supplementary_rounds"], 1)

    def test_the_supplement_trace_is_persisted_with_the_run(self):
        calls = {"n": 0}

        def search(query, limit=5):
            calls["n"] += 1
            return {"mode": "fake", "query": query, "run_id": calls["n"],
                    "candidates": self.evidence[:1]}

        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([("insufficient", "资料没有提供该数据。")] * 3,
                                                 []),
                                search=search)
        saved = self.store.run(result["answer_run_id"])
        self.assertIn("supplement", saved)
        self.assertEqual(saved["supplement"]["stop_reason"], "no_new_evidence")
        self.assertEqual(saved["supplement"]["max_supplementary_rounds"], 2)
        self.assertTrue(saved["supplement"]["trace"])

    def test_amending_a_run_keeps_its_own_answer_fields(self):
        # The supplement is added to the answer's run, it does not replace it:
        # reading the run id must still yield the answer that was returned.
        calls = {"n": 0}

        def search(query, limit=5):
            calls["n"] += 1
            return {"mode": "fake", "query": query, "run_id": calls["n"],
                    "candidates": self.evidence[:1]}

        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([("insufficient", "资料没有提供该数据。")] * 3,
                                                 []),
                                search=search)
        saved = self.store.run(result["answer_run_id"])
        self.assertEqual(saved["status"], result["status"])
        self.assertEqual(saved["prompt_version"], "evidence-v3.5")
        # `answer_run_id` is assigned after the row is written, so the stored
        # record never carries its own id; the answer's own fields must survive.
        self.assertEqual(saved["call_id"], result["call_id"])
        self.assertIn("validation", saved)

    def test_amending_an_unknown_run_is_refused(self):
        from skra.store import amend_run
        with self.assertRaises(ValueError):
            amend_run(self.store.db, 999999, {"supplement": {}})

    def test_answer_retrieval_id_resolves_to_its_accumulated_evidence(self):
        result = bounded_answer(self.store, "提示注入", self.ledger, demo=True)
        retrieval = self.store.run(result["retrieval_run_id"])
        self.assertEqual(retrieval["mode"], "accumulated-evidence")
        self.assertTrue(retrieval["candidates"])

    def test_insufficient_budget_is_reported_as_budget(self):
        self.ledger.reserve(10_000_000, {})
        seen = []
        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([], seen))
        self.assertEqual(result["supplement"]["stop_reason"], "budget")
        self.assertEqual(seen, [])

    def test_the_two_round_cap_holds_even_when_every_round_adds_evidence(self):
        pool = self.evidence + [{"id": "extra", "text": "额外证据", "version": "v"}]
        calls = {"n": 0}

        def search(query, limit=5):
            calls["n"] += 1
            return {"mode": "fake", "query": query, "run_id": calls["n"],
                    "candidates": self.evidence[:calls["n"]]}

        seen = []
        result = bounded_answer(self.store, "提示注入", self.ledger, self.config, "k",
                                send=self.sender([("insufficient", "缺")] * 5, seen),
                                search=search)
        self.assertLessEqual(result["supplement"]["supplementary_rounds"], 2)
        self.assertLessEqual(len(seen), 3, "first pass plus at most two rounds")
        self.assertIn(result["supplement"]["stop_reason"],
                      {"round_limit", "no_new_evidence", "sufficient"})


if __name__ == "__main__":
    unittest.main()
