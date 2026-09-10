"""Issue 13: structure-aware splitting for guides.

A guide's heading, definition paragraph and its qualifying list must survive
retrieval as co-located evidence, instead of being diluted by a fixed 20-line
window. Behaviors are exercised through the public Store interface.
"""
import tempfile
import unittest
from pathlib import Path

from skra.store import Store

GUIDE = """# LLM06:2025 Excessive Agency

Source: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/
Publisher: OWASP Gen AI Security Project
License: CC BY-SA 4.0
Retrieved: 2026-09-10
This is a selected excerpt, not the complete document.

## Minimize extensions

Excessive Agency is the vulnerability that enables damaging actions.

The root cause is typically one or more of:
- excessive functionality;
- excessive permissions;
- excessive autonomy.
"""


def write(directory, name, text):
    path = Path(directory) / name
    path.write_text(text, encoding="utf-8")
    return path


class StructuredGuideTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "test.sqlite3")
        self.addCleanup(self.store.close)

    def test_definition_and_its_list_stay_together(self):
        """A definition and the list it introduces must land in one retrievable chunk."""
        doc = write(self.temp.name, "guide.md", GUIDE)
        self.store.ingest(doc, "LLM06", "urn:test:guide", "CC BY-SA 4.0", "2026-09-10",
                          splitter="heading-block-v2")

        hits = self.store.search("root cause excessive functionality permissions autonomy")
        texts = [c["text"] for c in hits["candidates"]]
        joined = "\n".join(texts)
        self.assertIn("The root cause is typically", joined)
        self.assertIn("excessive functionality", joined)
        self.assertIn("excessive autonomy", joined)
        # The definition sentence and its list must not be split across chunks.
        self.assertTrue(
            any("root cause" in t and "excessive autonomy" in t for t in texts),
            "定义句与其列表项必须共存于同一片段")

    def test_metadata_does_not_crowd_out_body_evidence(self):
        """Source/License boilerplate must not occupy body search slots, but stays readable."""
        doc = write(self.temp.name, "guide.md", GUIDE)
        self.store.ingest(doc, "LLM06", "urn:test:meta", "CC BY-SA 4.0", "2026-09-10",
                          splitter="heading-block-v2")

        hits = self.store.search("license source publisher retrieved")
        # The metaline chunk may be retrievable, but must be flagged as metadata,
        # so callers can keep it out of the body candidate list.
        self.assertTrue(all(c.get("kind") == "metadata" for c in hits["candidates"]
                            if "License:" in c["text"] or "Publisher:" in c["text"]),
                        "含 License/Publisher 的片段必须标记为 metadata")

        body = self.store.search("root cause excessive functionality")
        self.assertTrue(body["candidates"], "正文定义仍必须可检索")
        # Metadata may still appear when there are fewer body hits than the limit,
        # but it must never outrank a body chunk that matches the same/at-least terms.
        self.assertEqual(body["candidates"][0].get("kind"), "body",
                         "正文证据必须排在元数据之前")

    def test_body_ranks_above_metadata_on_equal_match(self):
        """When a query matches both, body evidence must outrank provenance boilerplate."""
        doc = write(self.temp.name, "guide.md", GUIDE)
        self.store.ingest(doc, "LLM06", "urn:test:rank", "CC BY-SA 4.0", "2026-09-10",
                          splitter="heading-block-v2")
        # "License" also appears inside the metadata block; a body chunk that matches
        # the same term must come first.
        hits = self.store.search("excessive agency root cause license")
        self.assertTrue(hits["candidates"])
        self.assertEqual(hits["candidates"][0].get("kind"), "body")

    def test_heading_path_aids_retrieval_but_quote_stays_verbatim(self):
        """Heading path may join the retrieval representation, never the cited span."""
        doc = write(self.temp.name, "guide.md", GUIDE)
        self.store.ingest(doc, "LLM06", "urn:test:hpath", "CC BY-SA 4.0", "2026-09-10",
                          splitter="heading-block-v2")

        # A query that matches the heading wording should retrieve the section body.
        hits = self.store.search("Minimize extensions")
        self.assertTrue(hits["candidates"])
        top = hits["candidates"][0]
        # The heading path is exposed as metadata for the caller...
        self.assertIn("Minimize extensions", top.get("section", ""))

        # ...but the evidence text is a real, verbatim span of the source file:
        lines = Path(doc).read_text(encoding="utf-8").splitlines()
        span = "\n".join(lines[top["start_line"] - 1:top["end_line"]])
        self.assertEqual(top["text"], span, "引用必须来自真实原文跨度")

    def test_unknown_structure_falls_back_and_records_reason(self):
        """Structureless text falls back to the generic strategy, with the reason recorded."""
        blob = "\n".join(f"Plain unstructured line {i} about spraying and primitives." for i in range(1, 41))
        doc = write(self.temp.name, "blob.md", blob)

        result = self.store.ingest(doc, "Blob", "urn:test:blob", "CC BY-SA 4.0", "2026-09-10",
                                   splitter="heading-block-v2")
        # No headings → the structured splitter cannot segment it; it must say so
        # rather than pretend a confident classification.
        self.assertEqual(result["splitter"], "heading-lines-v1:20")
        self.assertIn("回退", result.get("splitter_note", ""))
        self.assertTrue(self.store.search("unstructured line spraying")["candidates"])

    def test_splitter_change_retires_old_chunk_ids(self):
        """Changing the splitter strategy makes a new version; old ids must be retired."""
        doc = write(self.temp.name, "guide.md", GUIDE)
        first = self.store.ingest(doc, "LLM06", "urn:test:switch", "CC BY-SA 4.0", "2026-09-10",
                                  splitter="heading-lines-v1:20")
        old_hits = self.store.search("root cause excessive functionality")
        old_ids = {c["id"] for c in old_hits["candidates"]}

        second = self.store.ingest(doc, "LLM06", "urn:test:switch", "CC BY-SA 4.0", "2026-09-10",
                                   splitter="heading-block-v2")
        self.assertEqual(second["status"], "updated")
        self.assertEqual(second["splitter"], "heading-block-v2")

        new_hits = self.store.search("root cause excessive functionality")
        new_ids = {c["id"] for c in new_hits["candidates"]}
        self.assertFalse(new_ids & old_ids, "策略变更后不得复用旧片段标识")
        # The old chunk can no longer be served as current evidence.
        stale = next(iter(old_ids))
        with self.assertRaises(ValueError) as ctx:
            self.store.read(stale)
        self.assertIn("失效", str(ctx.exception))

    def test_cli_accepts_splitter_flag(self):
        """The splitter strategy is an explicit, overridable CLI choice."""
        import json
        import subprocess
        import sys

        cli_db = str(Path(self.temp.name) / "cli.sqlite3")
        doc = write(self.temp.name, "cli.md", GUIDE)
        result = subprocess.run(
            [sys.executable, "-m", "skra", "--db", cli_db, "import", str(doc),
             "--title", "G", "--source", "urn:test:cli13", "--license", "CC BY-SA 4.0",
             "--splitter", "heading-block-v2"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["splitter"], "heading-block-v2")


if __name__ == "__main__":
    unittest.main()
