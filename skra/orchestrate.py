"""Bounded supplementary retrieval with an explicit stop reason (Issue 10).

The first retrieval pass is not counted; at most ``MAX_SUPPLEMENTARY_ROUNDS``
further rounds may run. A round is only worth starting if it can plausibly add
something, so the loop stops on the first of:

  - SUFFICIENT: every required piece of evidence has been retrieved;
  - NO_NEW_EVIDENCE: the round returned nothing that was not already known;
  - ERROR: a retriever or the answer step raised;
  - BUDGET: a caller-supplied budget guard refused to continue;
  - TIMEOUT: the whole run exceeded its wall-clock allowance;
  - ROUND_LIMIT: the hard cap was reached and the loop is still productive.

This module owns iteration and stopping only. It never generates an answer: the
per-round callback receives the accumulated evidence and returns whatever the
caller wants recorded. That keeps the stop rules testable with a fake retriever
and a fake callback, with no model, ledger or network involved.
"""
import time
from enum import Enum

from .store import check_search_args

MAX_SUPPLEMENTARY_ROUNDS = 2


class StopReason(str, Enum):
    """Why the loop stopped. A str enum so it serialises as a plain word."""

    SUFFICIENT = "sufficient"
    NO_NEW_EVIDENCE = "no_new_evidence"
    ROUND_LIMIT = "round_limit"
    TIMEOUT = "timeout"
    ERROR = "error"
    BUDGET = "budget"


class _Stopped(Exception):
    """Internal signal carrying the reason a round wants to end the run."""

    def __init__(self, reason, detail=""):
        super().__init__(reason.value)
        self.reason = reason
        self.detail = detail


class Orchestrator:
    """Run the first pass plus at most two supplementary rounds.

    ``search(query, limit)`` is any retriever. ``answer_once(evidence, round_no)``
    is called once per pass with the evidence accumulated so far; it is where a
    caller would generate an answer. Its return value is handed to
    ``is_sufficient``, which decides whether another round could still help --
    that keeps this class from knowing what an "answer" is. ``budget_guard()`` is
    an optional zero-argument callable that raises to signal the budget is out.
    """

    def __init__(self, search, answer_once, is_sufficient=None,
                 budget_guard=None, deadline=None):
        self.search = search
        self.answer_once = answer_once
        self.is_sufficient = is_sufficient or (lambda result: False)
        self.budget_guard = budget_guard
        self.deadline = deadline
        # The value produced by the most recent `answer_once` call, so a caller
        # can retrieve the final answer without the orchestrator having to know
        # what an answer is.
        self.last_result = None

    @staticmethod
    def _ids(candidates):
        return [c["id"] for c in candidates]

    @staticmethod
    def _vet_candidates(candidates):
        """Reject anything a retriever must never hand back.

        Only evidence-shaped results are allowed. A candidate that asks for a
        tool, or that has no id to locate in the corpus, is a boundary violation,
        not a candidate: the retrieval side must not be able to widen the answer
        model's reach. Validated by the program, not by the prompt.
        """
        for candidate in candidates:
            if not isinstance(candidate, dict) or "id" not in candidate:
                raise _Stopped(StopReason.ERROR, "检索结果含无标识的候选，已拒绝。")
            for field in ("tool", "tool_call", "function_call", "arguments"):
                if field in candidate:
                    raise _Stopped(StopReason.ERROR,
                                   f"检索结果要求使用工具（{field}），已拒绝。")
        return candidates

    def _check_time(self):
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise _Stopped(StopReason.TIMEOUT, "总时限已到。")

    def _round(self, query, limit, known):
        """One retrieval pass: guard, search, vet, and report what is new."""
        self._check_time()
        if self.budget_guard is not None:
            try:
                self.budget_guard()
            except ValueError as exc:
                raise _Stopped(StopReason.BUDGET, str(exc)) from None
        result = self.search(query, limit)
        candidates = self._vet_candidates(result.get("candidates", ()) or ())
        fresh = [cid for cid in self._ids(candidates) if cid not in known]
        return result, candidates, fresh

    def execute(self, query, required_ids=(), limit=5):
        """Run the loop and return the accumulated evidence plus the stop reason.

        ``required_ids`` is the set of chunk ids the caller considers sufficient;
        when empty, only a hard cap or an empty round can stop the loop.
        """
        # Same guard every retriever uses: the orchestrator must not become a
        # fourth place that decides what a valid query is (Issue 08 convergence).
        check_search_args(query, limit)
        required = set(required_ids)
        known = {}
        trace = []
        stop_reason = None
        detail = ""
        round_no = 0
        started = time.monotonic()
        try:
            while True:
                self._check_time()
                result, candidates, fresh = self._round(query, limit, set(known))
                for candidate in candidates:
                    known.setdefault(candidate["id"], candidate)
                trace.append({
                    "round": round_no,
                    "query": query,
                    "returned": self._ids(candidates),
                    "new_ids": fresh,
                    "mode": result.get("mode"),
                    "run_id": result.get("run_id"),
                })
                produced = self.answer_once(list(known.values()), round_no)
                self.last_result = produced
                if self.is_sufficient(produced):
                    stop_reason, detail = StopReason.SUFFICIENT, "所需证据已齐，无需补充。"
                    break
                if required and required <= set(known):
                    stop_reason, detail = StopReason.SUFFICIENT, "所需证据已齐。"
                    break
                if round_no >= 1 and not fresh:
                    stop_reason, detail = (StopReason.NO_NEW_EVIDENCE,
                                           "本轮没有带来新证据。")
                    break
                if round_no >= MAX_SUPPLEMENTARY_ROUNDS:
                    stop_reason, detail = (StopReason.ROUND_LIMIT,
                                           "已达到最多两轮补充检索。")
                    break
                round_no += 1
        except _Stopped as exc:
            stop_reason, detail = exc.reason, exc.detail
        except Exception as exc:  # a retriever/callback failure must not vanish
            stop_reason, detail = StopReason.ERROR, f"{type(exc).__name__}: {exc}"
        elapsed_ms = (time.monotonic() - started) * 1000
        return {
            "mode": "bounded-supplementary",
            "stop_reason": stop_reason,
            "stop_detail": detail,
            "supplementary_rounds": max(0, round_no),
            "max_supplementary_rounds": MAX_SUPPLEMENTARY_ROUNDS,
            "evidence": list(known.values()),
            "trace": trace,
            "elapsed_ms": elapsed_ms,
        }
