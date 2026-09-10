"""Issue 14: procedures with prerequisites, code fences and warnings.

Querying one step of an operational guide must return that step together with its
prerequisite, its fenced code and the adjacent warning, as locatable evidence.
Code is analysed, never executed. Behaviors go through the public Store interface.
"""
import tempfile
import unittest
from pathlib import Path

from skra.store import Store

PROCEDURE = """# Rotating an API key safely

## Prerequisites

- You must have the owner role.
- The service must be in maintenance mode.

## Steps

1. Revoke the old key in the console.
2. Issue a new key.
3. Deploy the new key to the runtime.

Warning: never paste the key into a shared document.

## Example automation

Run the following after the prerequisites are met:

```bash
# this comment is not a heading
export OLD_KEY=$(cat old.key)
curl -H "Authorization: Bearer $NEW_KEY" https://example.invalid/rotate
```
"""


def write(directory, name, text):
    path = Path(directory) / name
    path.write_text(text, encoding="utf-8")
    return path


class ProcedureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "test.sqlite3")
        self.addCleanup(self.store.close)

    def ingest(self, text, splitter="heading-procedure-v3", source="urn:test:proc"):
        doc = write(self.temp.name, "proc.md", text)
        return doc, self.store.ingest(doc, "Proc", source, "CC0-1.0", "2026-09-10",
                                      splitter=splitter)

    def test_step_keeps_its_prerequisite_and_neighbouring_warning(self):
        """A step block must carry its prerequisite and the warning that guards it."""
        self.ingest(PROCEDURE)
        hits = self.store.search("revoke the old key prerequisites warning")
        self.assertTrue(hits["candidates"])
        joined = "\n".join(c["text"] for c in hits["candidates"])
        self.assertIn("Revoke the old key", joined)
        # The prerequisite and the warning must be retrievable alongside the step,
        # not orphaned in far-away chunks.
        self.assertTrue(any("owner role" in c["text"] or "maintenance mode" in c["text"]
                            for c in hits["candidates"]),
                        "前置条件必须与步骤一起可检索")
        self.assertTrue(any("never paste the key" in c["text"] for c in hits["candidates"]),
                        "相邻警告必须与步骤一起可检索")

    def test_code_fence_is_one_piece_and_hash_is_not_a_heading(self):
        """A fenced block is atomic: a '#' inside it is a comment, never a section."""
        self.ingest(PROCEDURE)
        hits = self.store.search("curl authorization bearer rotate")
        self.assertTrue(hits["candidates"])
        top = hits["candidates"][0]
        # The whole fence — opener, body and closer — must live in a single chunk...
        self.assertIn("```bash", top["text"])
        self.assertIn("export OLD_KEY", top["text"])
        self.assertIn("example.invalid/rotate", top["text"])
        self.assertTrue(top["text"].rstrip().endswith("```"), "代码块必须完整包含结束围栏")
        # ...and the shell comment must not have been mistaken for a heading.
        self.assertNotIn("this comment is not a heading", top["section"])
        # The sentence that introduces the code remains retrievable next to it
        # (its own chunk just before), so the fence is never context-free.
        nearby = self.store.search("Run the following prerequisites met")
        self.assertTrue(any("Run the following" in c["text"] for c in nearby["candidates"]),
                        "引入代码的说明句必须与代码一起可检索")

    def test_warning_stays_with_the_steps_it_guards(self):
        """A warning written straight under the steps belongs to that section."""
        _, result = self.ingest(PROCEDURE)
        self.assertEqual(result["splitter"], "heading-procedure-v3")
        rows = list(self.store.db.execute(
            "SELECT section,text FROM chunks WHERE active=1 ORDER BY start_line"))
        warning = next(r for r in rows if "never paste the key" in r["text"])
        self.assertEqual(warning["section"], "Steps",
                         "紧随步骤的警告必须归属该步骤所在小节")

    def test_unknown_structure_falls_back_and_records_reason(self):
        """A structureless blob cannot be segmented by the procedure strategy."""
        blob = "\n".join(f"Plain operation line {i} about rotating keys." for i in range(1, 41))
        doc = write(self.temp.name, "blob.md", blob)
        result = self.store.ingest(doc, "Blob", "urn:test:procblob", "CC0-1.0", "2026-09-10",
                                   splitter="heading-procedure-v3")
        self.assertEqual(result["splitter"], "heading-lines-v1:20")
        self.assertIn("回退", result.get("splitter_note", ""))
        self.assertTrue(self.store.search("rotating keys operation line")["candidates"])

    def test_evidence_span_is_verbatim(self):
        """Every procedure chunk must map back to a real span of the source file."""
        doc, _ = self.ingest(PROCEDURE)
        lines = Path(doc).read_text(encoding="utf-8").splitlines()
        for row in self.store.db.execute(
                "SELECT start_line,end_line,text FROM chunks WHERE active=1"):
            span = "\n".join(lines[row["start_line"] - 1:row["end_line"]])
            self.assertEqual(row["text"], span, "引用必须来自真实原文跨度")

    def test_body_following_a_peeled_title_block_is_not_called_metadata(self):
        """Prose after a peeled provenance block is body, not more provenance.

        A title block bundles its H1 with Source/License lines. Peeling those off
        leaves the rest of that first section unheaded, so it must not inherit the
        metadata label from the block above it — otherwise a whole section of real
        content is filed as boilerplate and loses its body search slot.
        """
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
        doc = write(self.temp.name, "titled.md", TITLED)
        self.store.ingest(doc, "Titled", "urn:test:titled", "CC0-1.0", "2026-09-10",
                          splitter="heading-procedure-v3")
        lines = TITLED.splitlines()
        rows = [dict(r) for r in self.store.db.execute(
            "SELECT start_line,end_line,kind,text FROM chunks WHERE active=1 "
            "ORDER BY start_line")]
        body_line = next(i for i, l in enumerate(lines, 1) if "alter behaviour" in l)
        covering = [r for r in rows if r["start_line"] <= body_line <= r["end_line"]]
        self.assertTrue(covering, "正文必须至少被一个片段覆盖")
        self.assertTrue(all(r["kind"] == "body" for r in covering),
                        f"第 {body_line} 行是正文，不能标成 metadata：{covering}")
        # The provenance lines must still be metadata, or the fix has just moved the bug.
        lic_line = next(i for i, l in enumerate(lines, 1) if l.startswith("License:"))
        meta = [r for r in rows if r["start_line"] <= lic_line <= r["end_line"]]
        self.assertTrue(meta and all(r["kind"] == "metadata" for r in meta),
                        "许可行必须仍标为 metadata")
        # And the body must actually be reachable by a body query.
        hits = self.store.search("prompt injection external content")
        self.assertTrue(any("alter behaviour" in c["text"] for c in hits["candidates"]),
                        "正文必须仍能被检索到，而不是被元数据标签排除")

    def test_cli_accepts_procedure_splitter(self):
        """The procedure strategy is an explicit, overridable CLI choice."""
        import json
        import subprocess
        import sys

        cli_db = str(Path(self.temp.name) / "cli.sqlite3")
        doc = write(self.temp.name, "cli.md", PROCEDURE)
        result = subprocess.run(
            [sys.executable, "-m", "skra", "--db", cli_db, "import", str(doc),
             "--title", "P", "--source", "urn:test:cli14", "--license", "CC0-1.0",
             "--splitter", "heading-procedure-v3"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["splitter"], "heading-procedure-v3")


if __name__ == "__main__":
    unittest.main()
