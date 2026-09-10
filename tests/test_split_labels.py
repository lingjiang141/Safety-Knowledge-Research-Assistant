"""Issue 15: no body section may be filed as provenance by the splitter.

Found while comparing strategies: the procedure strategy labelled real prose as
`metadata` whenever it followed a peeled title block, because the unheaded
continuation inherited the label of the block above it. That cost the content its
body search slot, so a whole section became invisible to body queries.

These tests pin the invariant at the chunk level, for both structure-aware
strategies, so the same class of mistake cannot come back through either one.
"""
import tempfile
import unittest
from pathlib import Path

from skra.store import PROCEDURE_SPLITTER, STRUCTURED_SPLITTER, Store

# A title block that bundles its H1 with provenance, then body prose that is *not*
# itself provenance. This is the shape of every real OWASP snapshot.
TITLED = """# Prompt Injection

Source: https://example.invalid/llm01
Publisher: Example Publisher
License: CC BY-SA 4.0
Retrieved: 2026-09-10
This is a selected excerpt of the official page, not the complete document.

A prompt injection vulnerability occurs when user prompts alter behaviour.
Indirect injection arrives through external content such as files.

## Prevention

Limit the extensions an agent may call to the minimum necessary.
"""

PROVENANCE_LINES = ("Source:", "Publisher:", "License:", "Retrieved:")


class BodyNeverLabelledAsProvenanceTest(unittest.TestCase):
    """Each strategy gets its own store, so one cannot mask the other's failure."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "titled.md"
        self.path.write_text(TITLED, encoding="utf-8")
        self.lines = TITLED.splitlines()
        self.stores = {}

    def store_for(self, splitter):
        """One store per splitter, ingested once and reused across a test."""
        if splitter not in self.stores:
            store = Store(Path(self.temp.name) / f"{splitter}.sqlite3")
            self.addCleanup(store.close)
            result = store.ingest(self.path, "Titled", f"urn:test:{splitter}",
                                  "CC0-1.0", "2026-09-10", splitter=splitter)
            self.assertEqual(result["splitter"], splitter,
                             "夹具必须真的用该策略切分，否则断言没有意义")
            self.stores[splitter] = store
        return self.stores[splitter]

    def _rows(self, store):
        return [dict(r) for r in store.db.execute(
            "SELECT start_line,end_line,kind,text FROM chunks WHERE active=1 "
            "ORDER BY start_line")]

    def _covering(self, rows, line_no):
        return [r for r in rows if r["start_line"] <= line_no <= r["end_line"]]

    def _line_of(self, fragment):
        return next(i for i, l in enumerate(self.lines, 1) if fragment in l)

    def test_prose_after_a_title_block_is_body_in_both_strategies(self):
        """Body prose must never inherit the provenance label from the block above."""
        for splitter in (STRUCTURED_SPLITTER, PROCEDURE_SPLITTER):
            with self.subTest(splitter=splitter):
                rows = self._rows(self.store_for(splitter))
                for fragment in ("alter behaviour", "arrives through external content",
                                 "Limit the extensions"):
                    line = self._line_of(fragment)
                    covering = self._covering(rows, line)
                    self.assertTrue(covering, f"{splitter}：第 {line} 行必须被覆盖")
                    self.assertTrue(
                        all(r["kind"] == "body" for r in covering),
                        f"{splitter}：第 {line} 行（{fragment!r}）是正文，"
                        f"不能标成 metadata：{covering}")

    def test_the_provenance_lines_still_are_metadata(self):
        """The fix must not move the bug: real boilerplate keeps its label."""
        for splitter in (STRUCTURED_SPLITTER, PROCEDURE_SPLITTER):
            with self.subTest(splitter=splitter):
                rows = self._rows(self.store_for(splitter))
                for fragment in PROVENANCE_LINES:
                    line = self._line_of(fragment)
                    covering = self._covering(rows, line)
                    self.assertTrue(covering, f"{splitter}：第 {line} 行必须被覆盖")
                    self.assertTrue(
                        all(r["kind"] == "metadata" for r in covering),
                        f"{splitter}：第 {line} 行（{fragment!r}）是出处信息，"
                        f"应当标为 metadata：{covering}")

    def test_body_remains_reachable_by_a_body_query(self):
        """Labelling is not cosmetic: misfiled body loses its body search slot."""
        for splitter in (STRUCTURED_SPLITTER, PROCEDURE_SPLITTER):
            with self.subTest(splitter=splitter):
                store = self.store_for(splitter)
                hits = store.search("prompt injection external content")
                self.assertTrue(
                    any("alter behaviour" in c["text"] for c in hits["candidates"]),
                    f"{splitter}：正文必须仍能被检索到，而不是被元数据标签排除")

    def test_metadata_does_not_shadow_a_body_hit(self):
        """A boilerplate line must not outrank real body evidence for a body query."""
        for splitter in (STRUCTURED_SPLITTER, PROCEDURE_SPLITTER):
            with self.subTest(splitter=splitter):
                store = self.store_for(splitter)
                hits = store.search("prompt injection external content")
                self.assertTrue(hits["candidates"])
                self.assertEqual(hits["candidates"][0]["kind"], "body",
                                 f"{splitter}：首位应为正文，而不是出处信息")


if __name__ == "__main__":
    unittest.main()
