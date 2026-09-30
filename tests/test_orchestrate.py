"""Bounded supplementary retrieval (Issue 10).

The orchestrator iterates retrieval at most twice beyond the first pass, and it
has to say *why* it stopped. These tests drive that behaviour through the public
interface only: a fake retriever and a fake per-round answer callback, no model,
no ledger and no network. That is deliberate -- the stop rules must be verifiable
without standing up the whole generation stack (architecture finding (3), see
docs/evidence/issue10-precheck-orchestration-20260910.md).
"""
import json
import time
import unittest

from skra.orchestrate import MAX_SUPPLEMENTARY_ROUNDS, Orchestrator, StopReason


class FakeSearch:
    """A retriever that returns scripted results per call and records queries."""

    def __init__(self, results):
        self.results = list(results)
        self.queries = []
        self.calls = 0

    def __call__(self, query, limit=5):
        self.queries.append((query, limit))
        self.calls += 1
        if self.calls <= len(self.results):
            plan = self.results[self.calls - 1]
        else:
            plan = []
        return {"mode": "fake", "query": query,
                "candidates": [{"id": c} if isinstance(c, str) else c for c in plan]}


class OrchestrateStopTest(unittest.TestCase):
    def test_the_cap_is_two_rounds_beyond_the_first(self):
        self.assertEqual(MAX_SUPPLEMENTARY_ROUNDS, 2)
        self.assertNotIn(StopReason.SUFFICIENT, set())  # enum is importable

    def test_no_new_evidence_stops_before_the_cap(self):
        # Round 1 returns the same chunk the first pass already had: nothing new,
        # so searching again would only burn budget. The required set is
        # unsatisfiable so only the "no new evidence" rule can stop the loop.
        search = FakeSearch([["a"], ["a"]])
        seen = []
        run = Orchestrator(search, lambda evidence, round_no: seen.append(round_no))
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.NO_NEW_EVIDENCE)
        self.assertEqual(search.calls, 2)  # first pass + one supplementary round
        self.assertEqual(result["supplementary_rounds"], 1)
        self.assertEqual(seen, [0], "a pass without new evidence skips generation")

    def test_sufficient_evidence_stops_immediately(self):
        search = FakeSearch([["a"]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"a"})
        self.assertEqual(result["stop_reason"], StopReason.SUFFICIENT)
        self.assertEqual(search.calls, 1)
        self.assertEqual(result["supplementary_rounds"], 0)

    def test_the_cap_stops_a_productive_loop_at_two_rounds(self):
        # Every round yields something new, so only the hard cap can stop it.
        search = FakeSearch([["a"], ["b"], ["c"], ["d"], ["e"]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"missing"})
        self.assertEqual(result["stop_reason"], StopReason.ROUND_LIMIT)
        self.assertEqual(search.calls, 3)  # first pass + exactly two rounds
        self.assertEqual(result["supplementary_rounds"], MAX_SUPPLEMENTARY_ROUNDS)


class OrchestrateBoundaryTest(unittest.TestCase):
    def test_budget_guard_stops_before_any_search(self):
        search = FakeSearch([["a"]])
        run = Orchestrator(search, lambda evidence, round_no: None,
                           budget_guard=lambda: (_ for _ in ()).throw(ValueError("预算不足")))
        result = run.execute("q", required_ids={"a"})
        self.assertEqual(result["stop_reason"], StopReason.BUDGET)
        self.assertEqual(search.calls, 0, "a refused budget must not reach the retriever")

    def test_budget_guard_stops_mid_loop(self):
        # Enough budget for the first pass, then refused: the run must stop there
        # and still report the evidence it did obtain.
        search = FakeSearch([["a"], ["b"]])
        calls = {"n": 0}

        def guard():
            calls["n"] += 1
            if calls["n"] > 1:
                raise ValueError("预算不足")

        run = Orchestrator(search, lambda evidence, round_no: None, budget_guard=guard)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.BUDGET)
        self.assertEqual(len(result["evidence"]), 1)

    def test_a_retriever_error_stops_and_is_recorded(self):
        def failing(query, limit=5):
            raise RuntimeError("boom in retriever")

        run = Orchestrator(failing, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"a"})
        self.assertEqual(result["stop_reason"], StopReason.ERROR)
        self.assertIn("boom in retriever", result["stop_detail"])

    def test_an_answer_callback_error_stops_and_is_recorded(self):
        search = FakeSearch([["a"]])

        def failing_answer(evidence, round_no):
            raise ValueError("answer step failed")

        run = Orchestrator(search, failing_answer)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.ERROR)
        self.assertIn("answer step failed", result["stop_detail"])

    def test_a_deadline_stops_a_run_that_overran(self):
        # A deadline already in the past must stop the loop before any search.
        search = FakeSearch([["a"]])
        run = Orchestrator(search, lambda evidence, round_no: None,
                           deadline=time.monotonic() - 1)
        result = run.execute("q", required_ids={"a"})
        self.assertEqual(result["stop_reason"], StopReason.TIMEOUT)
        self.assertEqual(search.calls, 0)

    def test_invalid_query_and_limit_are_refused_by_the_program(self):
        search = FakeSearch([["a"]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        with self.assertRaises(ValueError):
            run.execute("   ", required_ids=set())
        with self.assertRaises(ValueError):
            run.execute("q", required_ids=set(), limit=0)
        with self.assertRaises(ValueError):
            run.execute("q", required_ids=set(), limit=21)
        self.assertEqual(search.calls, 0, "an invalid call must never reach the retriever")


class OrchestrateTraceTest(unittest.TestCase):
    def test_the_trace_is_auditable_and_carries_no_chain_of_thought(self):
        search = FakeSearch([["a"], ["b"], []])
        run = Orchestrator(search, lambda evidence, round_no: {"reasoning": "SECRET_THOUGHT"})
        result = run.execute("q", required_ids={"never"})
        # The trace records what happened, not what anyone was thinking.
        rounds = result["trace"]
        self.assertEqual([r["round"] for r in rounds], [0, 1, 2])
        self.assertEqual(rounds[0]["query"], "q")
        self.assertEqual(rounds[0]["returned"], ["a"])
        self.assertEqual(rounds[0]["new_ids"], ["a"])
        self.assertEqual(rounds[1]["new_ids"], ["b"])
        self.assertEqual(rounds[2]["new_ids"], [])
        self.assertEqual(result["stop_reason"], StopReason.NO_NEW_EVIDENCE)
        # The callback's return value is never spliced into the trace.
        self.assertNotIn("reasoning", json.dumps(result))
        self.assertNotIn("SECRET_THOUGHT", json.dumps(result))

    def test_the_trace_records_the_external_state_per_round(self):
        search = FakeSearch([[{"id": "a", "version": "v1"}], [{"id": "b", "version": "v2"}]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["trace"][0]["mode"], "fake")
        self.assertIn("run_id", result["trace"][0])
        versions = {(e["id"], e["version"]) for e in result["evidence"]}
        self.assertEqual(versions, {("a", "v1"), ("b", "v2")})

    def test_a_retrieved_id_never_duplicates_in_the_final_evidence(self):
        search = FakeSearch([["a", "b"], ["b", "c"]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        ids = [e["id"] for e in result["evidence"]]
        self.assertEqual(ids, sorted(set(ids), key=ids.index))
        self.assertEqual(len(ids), len(set(ids)))


class OrchestrateControlTest(unittest.TestCase):
    """The on/off control the Issue 10 card requires, as a fixed-shape guard.

    Two arms of the same loop, differing only in whether the retriever can widen:
    a static re-ask must stop on NO_NEW_EVIDENCE, and a widening retriever must
    stop on the two-round cap. Both must only ever *add* evidence. The full
    development-set run is `scripts/compare_supplement.py`; this keeps the shape
    true without needing the corpus.
    """

    def test_a_static_reask_never_grows_the_evidence(self):
        search = FakeSearch([["a", "b"], ["a", "b"], ["a", "b"], ["a", "b"]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.NO_NEW_EVIDENCE)
        self.assertEqual(result["supplementary_rounds"], 1)
        self.assertEqual([e["id"] for e in result["evidence"]], ["a", "b"])

    def test_a_widening_retriever_stops_on_the_cap_not_the_growth(self):
        growing = [["a"], ["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d"]]
        search = FakeSearch(growing)
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.ROUND_LIMIT)
        self.assertEqual(result["supplementary_rounds"], MAX_SUPPLEMENTARY_ROUNDS)
        self.assertEqual(search.calls, MAX_SUPPLEMENTARY_ROUNDS + 1)

    def test_the_reached_evidence_only_ever_grows_across_rounds(self):
        # Nothing the first pass reached may fall out of the accumulated set: a
        # supplementary round widens the window, it does not replace it.
        search = FakeSearch([["a", "b"], ["c"], ["d"]])
        run = Orchestrator(search, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual([e["id"] for e in result["evidence"]], ["a", "b", "c", "d"])
        self.assertEqual(result["trace"][0]["returned"], ["a", "b"])
        self.assertEqual(result["trace"][1]["new_ids"], ["c"])


class OrchestrateToolBoundaryTest(unittest.TestCase):
    """Only search-and-read are permitted, and they are permitted by the program.

    The answer model must not be able to widen its own reach: a candidate that
    claims to be a tool call, or names a chunk the retriever never returned, is
    refused here rather than passed along (PRD 4.2 / 4.5, Issue 10 card).
    """

    def test_a_candidate_that_requests_a_tool_is_refused(self):
        def rogue(query, limit=5):
            return {"mode": "fake", "query": query, "candidates": [
                {"id": "a", "tool": "write_file", "arguments": {"path": "/etc/passwd"}}]}

        run = Orchestrator(rogue, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.ERROR)
        self.assertIn("工具", result["stop_detail"])
        self.assertEqual(result["evidence"], [])

    def test_a_candidate_without_an_id_is_refused(self):
        def nameless(query, limit=5):
            return {"mode": "fake", "query": query, "candidates": [{"text": "no id here"}]}

        run = Orchestrator(nameless, lambda evidence, round_no: None)
        result = run.execute("q", required_ids={"never"})
        self.assertEqual(result["stop_reason"], StopReason.ERROR)
        self.assertIn("无标识", result["stop_detail"])
        self.assertEqual(result["evidence"], [])

    def test_the_orchestrator_cannot_be_asked_to_write_or_fetch(self):
        # There is no parameter that turns on network access or writes; passing an
        # unsupported keyword must fail loudly rather than be silently ignored.
        search = FakeSearch([["a"]])
        with self.assertRaises(TypeError):
            Orchestrator(search, lambda evidence, round_no: None, allow_network=True)
        with self.assertRaises(TypeError):
            Orchestrator(search, lambda evidence, round_no: None, write_files=True)


if __name__ == "__main__":
    unittest.main()
