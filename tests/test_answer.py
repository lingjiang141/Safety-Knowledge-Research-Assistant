import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from datetime import date

from skra.answer import Ledger, answer, validate
from skra.store import Store

ROOT = Path(__file__).resolve().parents[1]


class AnswerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.store = Store(self.path / "knowledge.db")
        self.ledger = Ledger(self.path / "budget.db")
        self.addCleanup(self.store.close)
        self.addCleanup(self.ledger.close)
        self.store.ingest(ROOT / "examples/security-demo.md", "demo", "urn:demo", "CC0", "2026-09-09")
        self.config = {"model": "test-model", "verified": True, "verified_at": date.today().isoformat(),
            "input_bound_strategy": "context-window", "context_token_upper_bound": 1048576,
            "input_rmb_per_million": 1, "output_rmb_per_million": 2}

    def response(self, payload, key, timeout):
        e = json.loads(payload["messages"][1]["content"])["evidence"][0]
        body = {"status": "grounded", "claims": [{"text": "这是受控测试结论。", "citations": [e["id"]]}],
                "citations": [{"id": e["id"], "quote": e["text"], "translation": "受控测试释义"}], "missing": "",
                "coverage": [{"question_id": "q1", "claims": [0], "missing": ""}]}
        return {"usage": {"prompt_tokens": 100, "completion_tokens": 50},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(body),
                 "reasoning_content": "DO_NOT_LOG_INTERNAL_REASONING"}}]}

    def ask(self, send, **kwargs):
        return answer(self.store, "提示注入", self.ledger, self.config, "TEST_SECRET", send=send, **kwargs)

    def test_success_accounting_and_no_secret_logging(self):
        sent = Mock(side_effect=self.response)
        result = self.ask(sent)
        self.assertEqual(result["status"], "grounded")
        self.assertEqual(sent.call_count, 1)
        self.assertEqual(result["budget"]["spent_rmb"], .0002)
        reopened = Ledger(self.path / "budget.db")
        self.assertEqual(reopened.summary()["spent_rmb"], .0002)
        reopened.close()
        logs = " ".join(str(tuple(r)) for r in self.store.db.execute("SELECT * FROM runs"))
        logs += " ".join(str(tuple(r)) for r in self.ledger.db.execute("SELECT * FROM calls"))
        self.assertNotIn("TEST_SECRET", logs)
        self.assertNotIn("DO_NOT_LOG_INTERNAL_REASONING", logs)

    def test_missing_config_key_and_insufficient_budget_never_send(self):
        sent = Mock()
        with self.assertRaises(ValueError):
            answer(self.store, "提示注入", self.ledger, send=sent)
        with self.assertRaises(ValueError):
            answer(self.store, "提示注入", self.ledger, {**self.config, "verified": False}, "key", send=sent)
        cid = self.ledger.reserve(10_000_000, {})
        self.ledger.settle(cid, 10_000_000, {})
        with self.assertRaises(ValueError):
            self.ask(sent)
        sent.assert_not_called()

    def test_timeout_blocks_restart_and_no_retry(self):
        sent = Mock(side_effect=TimeoutError("TEST_SECRET"))
        with self.assertRaisesRegex(ValueError, "费用未知"):
            self.ask(sent)
        self.assertEqual(sent.call_count, 1)
        other = Ledger(self.path / "budget.db")
        try:
            self.assertTrue(other.summary()["blocked"])
            self.assertGreater(other.summary()["reserved_rmb"], 0)
            with self.assertRaises(ValueError):
                other.reserve(1, {})
        finally:
            other.close()
        with self.assertRaises(ValueError):
            self.ask(sent)
        self.assertEqual(sent.call_count, 1)

    def test_bad_quote_charged_but_not_displayed(self):
        def corrupt(*args):
            response = self.response(*args)
            content = json.loads(response["choices"][0]["message"]["content"])
            content["citations"][0]["quote"] = "invented evidence"
            response["choices"][0]["message"]["content"] = json.dumps(content)
            return response
        with self.assertRaisesRegex(ValueError, "引用校验失败"):
            self.ask(corrupt)
        self.assertGreater(self.ledger.summary()["spent_rmb"], 0)
        self.assertFalse(self.ledger.summary()["blocked"])

    def test_invalid_quote_reports_reason_and_records_replay_without_secrets(self):
        def corrupt(*args):
            response = self.response(*args)
            content = json.loads(response["choices"][0]["message"]["content"])
            content["citations"][0]["quote"] = "invented evidence TEST_SECRET"
            response["choices"][0]["message"]["content"] = json.dumps(content)
            return response
        with self.assertRaisesRegex(ValueError, "引用原文与资料不符"):
            self.ask(corrupt)
        last = self.store.db.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()[0]
        saved = self.store.run(last)
        self.assertEqual(saved["diagnostic"]["stage"], "citation_validation")
        self.assertIn("model_output", saved)
        self.assertNotIn("TEST_SECRET", saved["model_output"])
        self.assertGreater(self.ledger.summary()["spent_rmb"], 0)

    def test_missing_usage_holds_reservation(self):
        with self.assertRaises(ValueError):
            self.ask(lambda *args: {"choices": []})
        self.assertTrue(self.ledger.summary()["blocked"])

    def test_unknown_citation_and_uncited_claim_rejected(self):
        evidence = self.store.search("提示注入")["candidates"]
        bad = {"status": "grounded", "claims": [{"text": "bad", "citations": ["fake"]}],
               "citations": [{"id": "fake", "quote": "bad", "translation": "bad"}], "missing": ""}
        with self.assertRaises(ValueError):
            validate(bad, evidence)
        bad["citations"] = []
        with self.assertRaises(ValueError):
            validate(bad, evidence)

    def test_demo_and_no_evidence_free(self):
        sent = Mock()
        self.assertEqual(self.ask(sent, demo=True)["mode"], "demo")
        result = answer(self.store, "no_matching_word", self.ledger, send=sent)
        self.assertEqual(result["status"], "insufficient")
        sent.assert_not_called()
        self.assertEqual(self.ledger.summary()["spent_rmb"], 0)

    def test_atomic_reservation_excludes_second_connection(self):
        self.ledger.reserve(1, {})
        other = Ledger(self.path / "budget.db")
        try:
            with self.assertRaises(ValueError):
                other.reserve(1, {})
        finally:
            other.close()

    def test_invalid_prices_and_large_input_never_send(self):
        sent = Mock()
        for value in (None, "NaN", -1, 0):
            config = {**self.config, "input_rmb_per_million": value}
            with self.assertRaises(ValueError):
                answer(self.store, "提示注入", self.ledger, config, "key", send=sent)
        with self.assertRaises(ValueError):
            answer(self.store, "x"*2001, self.ledger, self.config, "key", send=sent)
        sent.assert_not_called()

    def test_preflight_without_key_reports_bound_without_reserving(self):
        sent = Mock()
        result = answer(self.store, "提示注入", self.ledger, self.config, send=sent, preflight=True)
        # 1048576 input tokens @1/M = 1.048576 + 1500 output tokens @2/M = 0.003.
        self.assertEqual(result["max_reservation_rmb"], 1.051576)
        self.assertFalse(result["key_configured"])
        self.assertTrue(result["budget_ready"])
        self.assertEqual(result["budget"]["reserved_rmb"], 0)
        sent.assert_not_called()

    def test_tool_call_in_response_is_rejected_even_with_valid_answer(self):
        def unexpected_tool(*args):
            response = self.response(*args)
            response["choices"][0]["message"]["tool_calls"] = [
                {"type": "function", "function": {"name": "delete_files", "arguments": "{}"}}]
            return response
        with self.assertRaisesRegex(ValueError, "工具调用"):
            self.ask(unexpected_tool)


if __name__ == "__main__":
    unittest.main()
