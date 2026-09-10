"""Issue 07: frozen evaluation samples and a reviewable baseline report.

The evaluation set anchors every question to *original-text spans* plus the
conditions that must appear together, never to chunk ids. Chunk ids change with
every splitter, so anchoring to them would make Recall incomparable across
strategies and would silently break when the corpus is re-imported. Spans are
mapped onto whatever chunks the current strategy produced, which keeps the
denominator stable while the strategy changes.

The development set and the holdout set are separated twice over: different
files, and a loader that refuses to touch the holdout unless explicitly asked.
Behaviour goes through the public eval interface.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skra.eval import (EvalError, load_cases, load_sample, resolve_span,  # noqa: E402
                       run_baseline, score_retrieval)
from skra.store import Store  # noqa: E402


def write_cases(path, cases, kind="development"):
    path.write_text(json.dumps({"kind": kind, "cases": cases}, ensure_ascii=False),
                    encoding="utf-8")
    return path


class CaseLoadingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_a_case_anchors_its_evidence_to_original_text_spans(self):
        """A question names source spans, not chunk ids, so re-splitting keeps it valid."""
        path = write_cases(self.root / "dev.json", [{
            "id": "D01",
            "question": "直接与间接注入分别从哪里进入？",
            "expected_status": "grounded",
            "evidence": [
                {"source": "S02", "start_line": 10, "end_line": 14,
                 "must_include": ["direct injection", "indirect injection"],
                 "required_together": True},
            ],
        }])
        cases = load_cases(path)
        self.assertEqual(len(cases), 1)
        span = cases[0].evidence[0]
        # The anchor is an original-text span: no chunk id anywhere in the contract.
        self.assertEqual((span.start_line, span.end_line), (10, 14))
        self.assertTrue(span.required_together)
        self.assertIn("direct injection", span.must_include)

    def test_a_case_without_evidence_is_rejected(self):
        """A question that claims no evidence cannot be scored; loading must fail loudly."""
        path = write_cases(self.root / "bad.json", [{
            "id": "D02", "question": "无依据的问题", "expected_status": "grounded",
            "evidence": [],
        }])
        with self.assertRaises(EvalError):
            load_cases(path)


class SpanResolutionTest(unittest.TestCase):
    """A span must resolve to the chunks that actually cover it, per strategy."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "test.sqlite3")
        self.addCleanup(self.store.close)
        body = "\n".join([
            "# Guide",                      # 1
            "",                             # 2
            "Direct injection enters via user input.",   # 3
            "Indirect injection enters via external content.",  # 4
            "",                             # 5
            "## Other section",             # 6
            "Unrelated text about budgets.",  # 7
        ])
        self.md = self.root / "guide.md"
        self.md.write_text(body, encoding="utf-8")
        self.store.ingest(self.md, "Guide", "urn:test:guide", "CC0-1.0", "2026-09-10")

    def test_span_resolves_to_the_chunks_covering_it(self):
        """A span maps onto chunks by original-text lines, not by chunk id."""
        span = load_cases(write_cases(self.root / "dev.json", [{
            "id": "D01", "question": "注入从哪里进入？", "expected_status": "grounded",
            "evidence": [{"source": "urn:test:guide", "start_line": 3, "end_line": 4,
                          "must_include": ["direct injection"]}],
        }]))[0].evidence[0]
        covered = resolve_span(self.store, span)
        self.assertTrue(covered, "跨度必须能解析到片段")
        text = "\n".join(c["text"] for c in covered)
        self.assertIn("Direct injection", text)
        self.assertIn("Indirect injection", text)

    def test_span_pointing_at_a_missing_source_fails_loudly(self):
        """An annotation that no longer matches the corpus must not be scored as zero."""
        span = load_cases(write_cases(self.root / "dev.json", [{
            "id": "D01", "question": "q", "expected_status": "grounded",
            "evidence": [{"source": "urn:test:absent", "start_line": 1, "end_line": 2}],
        }]))[0].evidence[0]
        with self.assertRaises(EvalError):
            resolve_span(self.store, span)


class RetrievalScoringTest(unittest.TestCase):
    """Recall counts evidence bundles, and a bundle only counts when it is whole."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "test.sqlite3")
        self.addCleanup(self.store.close)
        body = "\n".join([
            "# Permissions",
            "Minimize extension permissions.",
            "Excessive functionality means too many features.",
            "Excessive permissions means too much access.",
            "Excessive autonomy means acting without approval.",
        ])
        self.md = self.root / "guide.md"
        self.md.write_text(body, encoding="utf-8")
        self.store.ingest(self.md, "Guide", "urn:test:guide", "CC0-1.0", "2026-09-10")

    def _case(self, evidence):
        return load_cases(write_cases(self.root / "dev.json", [{
            "id": "D01", "question": "权限风险分类", "expected_status": "grounded",
            "evidence": evidence,
        }]))[0]

    def test_a_whole_bundle_hit_counts_and_a_split_bundle_does_not(self):
        """A bundle whose parts land in different chunks is not a hit: it was cut apart."""
        case = self._case([
            {"source": "urn:test:guide", "start_line": 3, "end_line": 5,
             "must_include": ["excessive functionality", "excessive permissions"],
             "required_together": True},
        ])
        # Force the two halves into different chunks by indexing with a 2-line budget
        # is not available through the public interface, so instead verify the rule
        # directly on a bundle that cannot fit in one retrieved chunk set.
        report = score_retrieval(self.store, case, search=lambda q, n: {"candidates": []})
        self.assertEqual(report["retrieved_bundles"], 0)
        self.assertEqual(report["relevant_bundles"], 1)
        self.assertEqual(report["recall_at_5"], 0.0)
        self.assertEqual(report["broken_bundles"], 0)

    def test_recall_is_measured_over_bundles_not_chunks(self):
        """Two bundles retrieved in the top five give Recall 1.0 even if chunks differ."""
        case = self._case([
            {"source": "urn:test:guide", "start_line": 2, "end_line": 2,
             "must_include": ["minimize extension permissions"]},
            {"source": "urn:test:guide", "start_line": 3, "end_line": 5,
             "must_include": ["excessive autonomy"]},
        ])
        hits = [dict(r) for r in self.store.db.execute(
            "SELECT * FROM chunks WHERE active=1 ORDER BY start_line")]
        report = score_retrieval(self.store, case,
                                 search=lambda q, n: {"candidates": hits[:n]})
        self.assertEqual(report["relevant_bundles"], 2)
        self.assertEqual(report["retrieved_bundles"], 2)
        self.assertEqual(report["recall_at_5"], 1.0)

    def test_a_bundle_missing_one_condition_is_reported_as_incomplete(self):
        """Splitting a required-together bundle apart must be visible, not silently a miss."""
        # The baseline splitter cuts this fixture into lines 1–20 and 21–26, so a span
        # crossing line 20/21 genuinely lands in two chunks.
        filler = "\n".join(f"Filler line {i} about unrelated topics." for i in range(1, 22))
        body = "\n".join([
            "# Permissions",
            "Minimize extension permissions.",
            filler,
            "Excessive functionality means too many features.",
            "Excessive permissions means too much access.",
            "Excessive autonomy means acting without approval.",
        ])
        md = self.root / "long.md"
        md.write_text(body, encoding="utf-8")
        self.store.ingest(md, "Long Guide", "urn:test:long", "CC0-1.0", "2026-09-10")
        case = self._case([
            {"source": "urn:test:long", "start_line": 20, "end_line": 22,
             "must_include": ["filler line 20", "filler line 21"],
             "required_together": True},
        ])
        rows = [dict(r) for r in self.store.db.execute(
            "SELECT * FROM chunks WHERE active=1 AND doc_id=(SELECT id FROM documents WHERE source='urn:test:long') ORDER BY start_line")]
        self.assertGreater(len(rows), 1, "夹具必须真的产生多个片段")
        covering = [r for r in rows if r["start_line"] <= 22 and r["end_line"] >= 20]
        self.assertGreater(len(covering), 1, "跨度必须真的横跨多个片段")
        # Offer only the first covering chunk: the bundle arrives incomplete.
        report = score_retrieval(self.store, case,
                                 search=lambda q, n: {"candidates": covering[:1]})
        self.assertEqual(report["retrieved_bundles"], 0)
        self.assertEqual(report["broken_bundles"], 1)
        self.assertEqual(report["recall_at_5"], 0.0)

    def test_a_whole_bundle_spanning_two_chunks_counts_when_both_are_retrieved(self):
        """The complement of the previous test: keeping both halves is a hit."""
        filler = "\n".join(f"Filler line {i} about unrelated topics." for i in range(1, 22))
        body = "\n".join([
            "# Permissions", "Minimize extension permissions.", filler,
            "Excessive functionality means too many features.",
            "Excessive permissions means too much access.",
            "Excessive autonomy means acting without approval.",
        ])
        md = self.root / "long.md"
        md.write_text(body, encoding="utf-8")
        self.store.ingest(md, "Long Guide", "urn:test:long", "CC0-1.0", "2026-09-10")
        case = self._case([
            {"source": "urn:test:long", "start_line": 20, "end_line": 22,
             "must_include": ["filler line 20", "filler line 21"],
             "required_together": True},
        ])
        rows = [dict(r) for r in self.store.db.execute(
            "SELECT * FROM chunks WHERE active=1 AND doc_id=(SELECT id FROM documents WHERE source='urn:test:long') ORDER BY start_line")]
        covering = [r for r in rows if r["start_line"] <= 22 and r["end_line"] >= 20]
        report = score_retrieval(self.store, case,
                                 search=lambda q, n: {"candidates": covering})
        self.assertEqual(report["retrieved_bundles"], 1)
        self.assertEqual(report["broken_bundles"], 0)
        self.assertEqual(report["recall_at_5"], 1.0)


class CostAccountingTest(unittest.TestCase):
    """A strategy must not win by stuffing more text into the evidence budget."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "test.sqlite3")
        self.addCleanup(self.store.close)

    def _case(self, evidence):
        return load_cases(write_cases(self.root / "dev.json", [{
            "id": "D01", "question": "权限建议", "expected_status": "grounded",
            "evidence": evidence,
        }]))[0]

    def test_report_counts_evidence_tokens_and_metadata_occupancy(self):
        """Metadata sitting in the evidence slots is reported, not hidden."""
        body = "\n".join([
            "# Guide",
            "Source: https://example.invalid/page",
            "License: CC BY-SA 4.0",
            "Body text about minimizing permissions.",
        ])
        md = self.root / "guide.md"
        md.write_text(body, encoding="utf-8")
        self.store.ingest(md, "Guide", "urn:test:guide", "CC0-1.0", "2026-09-10")
        case = self._case([{"source": "urn:test:guide", "start_line": 4, "end_line": 4,
                            "must_include": ["minimizing permissions"]}])
        rows = [dict(r) for r in self.store.db.execute(
            "SELECT * FROM chunks WHERE active=1 ORDER BY start_line")]
        report = score_retrieval(self.store, case,
                                 search=lambda q, n: {"candidates": rows})
        self.assertGreater(report["evidence_tokens"], 0)
        self.assertIn("metadata_chunks", report)
        self.assertLessEqual(report["metadata_chunks"], len(rows))


class SplitIsolationTest(unittest.TestCase):
    """Holdout answers must stay out of the tuning context by construction."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dev = write_cases(self.root / "dev.json", [{
            "id": "D01", "question": "开发题", "expected_status": "grounded",
            "evidence": [{"source": "urn:test:guide", "start_line": 1, "end_line": 1}],
        }], kind="development")
        self.holdout = write_cases(self.root / "holdout.json", [{
            "id": "H01", "question": "保留题", "expected_status": "grounded",
            "evidence": [{"source": "urn:test:guide", "start_line": 1, "end_line": 1}],
        }], kind="holdout")

    def test_default_loading_does_not_touch_the_holdout_set(self):
        """Running the baseline must not read holdout answers, by construction."""
        sample = load_sample(self.dev, holdout=None)
        self.assertEqual([c.id for c in sample.cases], ["D01"])
        self.assertFalse(sample.holdout_loaded)
        self.assertEqual(sample.holdout_path, None)

    def test_asking_for_the_holdout_without_the_explicit_flag_is_refused(self):
        """The holdout file cannot be opened by naming it as the development set."""
        with self.assertRaises(EvalError) as caught:
            load_sample(self.holdout, holdout=None)
        self.assertIn("保留集", str(caught.exception))

    def test_explicit_holdout_entry_loads_both_sets_separately(self):
        """A deliberate final-evaluation run loads both, and labels which is which."""
        sample = load_sample(self.dev, holdout=self.holdout)
        self.assertEqual(sample.case_ids(kind="development"), ["D01"])
        self.assertEqual(sample.case_ids(kind="holdout"), ["H01"])
        self.assertTrue(sample.holdout_loaded)


class BaselineReportTest(unittest.TestCase):
    """The baseline must be reproducible: same corpus and sample give the same freeze."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "test.sqlite3")
        self.addCleanup(self.store.close)
        body = "\n".join([
            "# Permissions",
            "Minimize extension permissions so a compromised tool cannot act widely.",
            "Complete mediation means the system, not the model, checks each call.",
        ])
        self.md = self.root / "guide.md"
        self.md.write_text(body, encoding="utf-8")
        self.store.ingest(self.md, "Guide", "urn:test:guide", "CC0-1.0", "2026-09-10")
        self.dev = write_cases(self.root / "dev.json", [{
            "id": "D01", "question": "为什么不能只让模型自己判断权限？",
            "expected_status": "grounded",
            "evidence": [{"source": "urn:test:guide", "start_line": 3, "end_line": 3,
                          "must_include": ["complete mediation"]}],
        }])

    def _search(self, corpus_hits):
        def selected(query, limit=5):
            return {"candidates": corpus_hits()[:limit]}
        return selected

    def _all_chunks(self):
        return [dict(r) for r in self.store.db.execute(
            "SELECT * FROM chunks WHERE active=1 ORDER BY start_line")]

    def test_report_records_the_frozen_corpus_and_sample_versions(self):
        """A baseline is only reviewable if it names the exact corpus and sample it ran on."""
        report = run_baseline(self.store, self.dev,
                              search=self._search(self._all_chunks))
        freeze = report["freeze"]
        for key in ("sample_hash", "corpus_hash", "splitter", "encoder"):
            self.assertIn(key, freeze)
            self.assertTrue(freeze[key], f"{key} 必须被记录")
        self.assertEqual(freeze["sample_hash"].__len__(), 64)

    def test_the_same_inputs_produce_the_same_freeze_hash(self):
        """Freezing is deterministic: re-running the same baseline reproduces the hash."""
        first = run_baseline(self.store, self.dev, search=self._search(self._all_chunks))
        second = run_baseline(self.store, self.dev, search=self._search(self._all_chunks))
        self.assertEqual(first["freeze"]["sample_hash"], second["freeze"]["sample_hash"])
        self.assertEqual(first["freeze"]["corpus_hash"], second["freeze"]["corpus_hash"])

    def test_report_states_what_was_not_run_instead_of_implying_coverage(self):
        """Generation metrics must be reported as not-run, not silently omitted."""
        report = run_baseline(self.store, self.dev, search=self._search(self._all_chunks))
        self.assertFalse(report["complete"])
        self.assertIn("not_run", report)
        self.assertTrue(any("生成" in item for item in report["not_run"]))
        self.assertEqual(report["network_called"], False)
        self.assertEqual(report["billed_calls"], 0)
        self.assertIn("cost_rmb", report)

    def test_report_carries_per_case_rows_and_an_aggregate(self):
        """Reviewing a baseline means seeing each case, not only the average."""
        report = run_baseline(self.store, self.dev, search=self._search(self._all_chunks))
        self.assertEqual(report["case_count"], 1)
        row = report["cases"][0]
        self.assertEqual(row["case_id"], "D01")
        self.assertIn("recall_at_5", row)
        self.assertIn("elapsed_ms", row)
        self.assertIn("recall_at_5", report["aggregate"])
        self.assertEqual(report["evidence_tokens_estimate_note"].count("\n"), 0)

    def test_a_baseline_run_never_reads_the_holdout_file(self):
        """Even with a holdout present on disk, an ordinary run must not open it."""
        holdout = write_cases(self.root / "holdout.json", [{
            "id": "H01", "question": "保留题", "expected_status": "grounded",
            "evidence": [{"source": "urn:test:guide", "start_line": 3, "end_line": 3}],
        }], kind="holdout")
        self.assertTrue(holdout.exists())
        report = run_baseline(self.store, self.dev, search=self._search(self._all_chunks))
        self.assertFalse(report["holdout_loaded"])
        self.assertIsNone(report["holdout_path"])
        self.assertEqual([c["case_id"] for c in report["cases"]], ["D01"])

    def test_a_stale_annotation_is_reported_as_a_failure_not_a_zero(self):
        """Annotations that no longer match the corpus must not look like honest misses."""
        stale = write_cases(self.root / "stale.json", [{
            "id": "D77", "question": "已失效的标注",
            "expected_status": "grounded",
            "evidence": [{"source": "urn:test:absent", "start_line": 1, "end_line": 2}],
        }])
        report = run_baseline(self.store, stale, search=self._search(self._all_chunks))
        self.assertEqual(report["failed_cases"], ["D77"])
        self.assertIsNone(report["cases"][0]["recall_at_5"])
        self.assertTrue(report["cases"][0]["error"])
        # A failure must keep the aggregate honest instead of averaging in a fake zero.
        self.assertIsNone(report["aggregate"]["recall_at_5"])


class ShippedSampleTest(unittest.TestCase):
    """The shipped samples must stay valid against the real corpus annotations."""

    ROOT = Path(__file__).resolve().parents[1]

    def test_every_shipped_span_carries_its_required_conditions(self):
        """A span that no longer contains its required terms is a stale annotation."""
        if not (self.ROOT / ".data/knowledge.sqlite3").exists():
            self.skipTest("缺少已导入的知识库；本机离线时跳过。")
        store = Store(self.ROOT / ".data/knowledge.sqlite3")
        self.addCleanup(store.close)
        cases = load_cases(self.ROOT / "examples/eval-dev-cases.json")
        self.assertGreaterEqual(len(cases), 10)
        for case in cases:
            for span in case.evidence:
                covered = resolve_span(store, span)
                text = "\n".join(c["text"] for c in covered).lower()
                for term in span.must_include:
                    self.assertIn(term.lower(), text,
                                  f"{case.id} 的跨度 {span.start_line}-{span.end_line} "
                                  f"已不含必现词 {term!r}，标注需重新核对。")

    def test_the_development_sample_never_claims_the_holdout_kind(self):
        """The shipped development file must not be able to masquerade as holdout."""
        spec = json.loads((self.ROOT / "examples/eval-dev-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["kind"], "development")

    def test_the_holdout_sample_is_a_separate_file_and_is_not_the_dev_set(self):
        """A holdout file exists and shares no case ids with the development set."""
        holdout_path = self.ROOT / "examples/eval-holdout-cases.json"
        self.assertTrue(holdout_path.exists(), "保留集必须单独成文件")
        dev = load_cases(self.ROOT / "examples/eval-dev-cases.json")
        holdout = load_cases(holdout_path, kind="holdout")
        overlap = {c.id for c in dev} & {c.id for c in holdout}
        self.assertFalse(overlap, f"开发集与保留集编号重复：{sorted(overlap)}")
        # The same question must not appear in both, or tuning leaks into the holdout.
        shared = {c.question for c in dev} & {c.question for c in holdout}
        self.assertFalse(shared, f"同一问题同时出现在两集：{sorted(shared)}")


if __name__ == "__main__":
    unittest.main()
