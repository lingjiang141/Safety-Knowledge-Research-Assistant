"""Issue 11: importing text-based PDFs and locating evidence by page.

A PDF's answer must trace back to the page it came from, with running headers and
footers kept out of the body evidence. Pages that carry no extractable text must fail
explicitly rather than import as an empty document. Behaviours go through the public
Store interface; the fixtures are real PDF files, not hand-written strings.
"""
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from make_pdf_fixtures import write_pdf, multipage_report  # noqa: E402
from skra.store import Store  # noqa: E402


class PdfImportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "test.sqlite3")
        self.addCleanup(self.store.close)
        self.pdf = write_pdf(Path(self.temp.name) / "report.pdf", multipage_report())

    def ingest(self, source="urn:test:pdf"):
        return self.store.ingest(self.pdf, "Operator Notes", source,
                                 "CC BY-SA 4.0", "2026-09-10")

    def test_pdf_body_is_imported_with_page_numbers(self):
        """Body text is retrievable and every chunk names the page it came from."""
        self.ingest()
        hits = self.store.search("indirect injection untrusted content")
        self.assertTrue(hits["candidates"], "PDF 正文必须可检索")
        self.assertTrue(any("indirect injection" in c["text"].lower()
                            for c in hits["candidates"]))
        # Evidence must be locatable to a page, not just to a line number.
        for c in hits["candidates"]:
            self.assertIsNotNone(c.get("page"), "PDF 片段必须带页码")

    def test_evidence_maps_back_to_the_real_page(self):
        """A cited span must land on the page it claims (checked against the PDF)."""
        from pypdf import PdfReader

        self.ingest()
        hits = self.store.search("audit trails tool invocation")
        self.assertTrue(hits["candidates"])
        top = hits["candidates"][0]
        self.assertIn("Audit Trails", top["text"])

        pages = PdfReader(str(self.pdf)).pages
        page_text = pages[top["page"] - 1].extract_text()
        # The quoted text must appear on the page the chunk claims.
        for line in top["text"].splitlines():
            if line.strip():
                self.assertIn(line.strip(), page_text,
                              f"引用内容必须出现在所声明页码（第 {top['page']} 页）")

    def test_running_header_and_footer_are_marked_metadata(self):
        """Repeated header/footer lines must not occupy body evidence slots."""
        self.ingest()
        hits = self.store.search("OWASP Agent Security Report Confidential page")
        boilerplate = [c for c in hits["candidates"]
                       if "OWASP Agent Security Report" in c["text"]
                       or "Confidential - page" in c["text"]]
        self.assertTrue(all(c.get("kind") == "metadata" for c in boilerplate),
                        "重复页眉页脚必须标记为 metadata")

    def test_repeated_body_text_is_not_deleted(self):
        """A line that repeats in the body must survive; only page furniture is peeled."""
        lines = ["OWASP Agent Security Report", "",
                 "## Reuse", "",
                 "Grant only the required tools.", "", "Confidential - page 1 of 2"]
        lines2 = ["OWASP Agent Security Report", "",
                  "## Reuse again", "",
                  "Grant only the required tools.", "", "Confidential - page 2 of 2"]
        pdf = write_pdf(Path(self.temp.name) / "repeat.pdf", [lines, lines2])
        self.store.ingest(pdf, "Reuse", "urn:test:pdfrepeat", "CC BY-SA 4.0", "2026-09-10")
        hits = self.store.search("grant only the required tools")
        self.assertTrue(hits["candidates"], "正文中重复出现的句子不得被误删")

    def test_paragraph_continues_across_a_page_break(self):
        """Both halves of a page-split paragraph stay retrievable, on their own pages."""
        self.ingest()
        # The paragraph is split by the page break: page 3 has its opening, page 4 the
        # continuation. Neither half may be lost just because the sentence was cut.
        first = self.store.search("defence treat retrieved")
        second = self.store.search("untrusted input confirmation trust boundary")
        self.assertTrue(first["candidates"], "跨页段落的前半必须可检索")
        self.assertTrue(second["candidates"], "跨页段落的后半必须可检索")
        self.assertTrue(any("treat retrieved" in c["text"] for c in first["candidates"]))
        self.assertTrue(any("content as untrusted input" in c["text"]
                            for c in second["candidates"]))
        # Each half reports the page it actually sits on.
        self.assertTrue(all(c["page"] == 3 for c in first["candidates"]))
        self.assertTrue(all(c["page"] == 4 for c in second["candidates"]))

    def test_scanned_pdf_without_text_fails_explicitly(self):
        """A PDF with no extractable text must fail with a reason, not import empty."""
        blank = write_pdf(Path(self.temp.name) / "blank.pdf", [[], []])
        with self.assertRaises(ValueError) as ctx:
            self.store.ingest(blank, "Blank", "urn:test:blank", "CC BY-SA 4.0", "2026-09-10")
        self.assertIn("正文", str(ctx.exception))
        # Nothing was published, so the source does not appear in the corpus.
        self.assertNotIn("urn:test:blank", {d["source"] for d in self.store.documents()})

    def test_corrupt_pdf_fails_with_reason(self):
        """A file that is not a valid PDF must fail clearly, never silently."""
        broken = Path(self.temp.name) / "broken.pdf"
        broken.write_bytes(b"%PDF-1.4\nthis is not a real pdf body\n")
        with self.assertRaises(ValueError) as ctx:
            self.store.ingest(broken, "Broken", "urn:test:broken", "CC BY-SA 4.0", "2026-09-10")
        message = str(ctx.exception)
        self.assertTrue("PDF" in message or "解析" in message or "提取" in message,
                        f"损坏文件必须给出可读原因，实际：{message}")

    def test_pdf_records_extraction_version_and_hash(self):
        """The extraction version is recorded, so a re-extract is a new version."""
        result = self.ingest()
        self.assertIn("extractor", result)
        row = self.store.documents()[0]
        self.assertTrue(row["hash"], "必须保存原文件 hash")

    def test_update_and_delete_work_for_pdf(self):
        """PDF sources follow the same update/delete contract as Markdown."""
        self.ingest()
        first = self.store.search("indirect injection")["candidates"]
        self.assertTrue(first)
        # Re-import with changed content: old page evidence must be retired.
        pdf2 = write_pdf(Path(self.temp.name) / "report2.pdf",
                         [["## Replaced", "", "The old finding is withdrawn."]])
        self.store.update(pdf2, "urn:test:pdf")
        self.assertFalse(self.store.search("indirect injection")["candidates"],
                         "更新后旧版 PDF 证据不得再返回")
        self.store.delete("urn:test:pdf")
        self.assertEqual(self.store.documents(), [])

    def test_cli_shows_page_for_pdf_evidence(self):
        """The CLI surfaces the page, so a citation can be checked by page."""
        import json
        import subprocess
        import sys as _sys

        cli_db = str(Path(self.temp.name) / "cli.sqlite3")
        imported = subprocess.run(
            [_sys.executable, "-m", "skra", "--db", cli_db, "import", str(self.pdf),
             "--title", "Operator Notes", "--source", "urn:test:pdfcli",
             "--license", "CC BY-SA 4.0"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            encoding="utf-8")
        self.assertEqual(imported.returncode, 0, imported.stderr)
        payload = json.loads(imported.stdout)
        self.assertEqual(payload["splitter"], "pdf-pages-v1")
        self.assertIn("extractor", payload)

        found = subprocess.run(
            [_sys.executable, "-m", "skra", "--db", cli_db, "search",
             "audit trails tool invocation"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            encoding="utf-8")
        self.assertEqual(found.returncode, 0, found.stderr)
        candidates = json.loads(found.stdout)["candidates"]
        self.assertTrue(candidates)
        self.assertTrue(all(c.get("page") for c in candidates),
                        "CLI 检索结果必须展示页码")

    def test_corrupt_pdf_reports_reason_through_cli(self):
        """A corrupt file must fail loudly on the CLI, not import a partial document."""
        import subprocess
        import sys as _sys

        cli_db = str(Path(self.temp.name) / "corrupt.sqlite3")
        broken = Path(self.temp.name) / "broken.pdf"
        broken.write_bytes(b"%PDF-1.4\ngarbage that is not a body\n")
        result = subprocess.run(
            [_sys.executable, "-m", "skra", "--db", cli_db, "import", str(broken),
             "--title", "Broken", "--source", "urn:test:broken-cli",
             "--license", "CC BY-SA 4.0"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            encoding="utf-8")
        self.assertNotEqual(result.returncode, 0, "损坏 PDF 不得导入成功")

    def test_vector_retrieval_keeps_body_ahead_of_page_furniture(self):
        """Body evidence must outrank running headers/footers in vector retrieval too.

        Issue 11 made this gap reachable: page furniture is now a regular metadata
        chunk, and the keyword path already prefers body, but the vector path has no
        equivalent rule (architecture finding ⑤, still open). This test pins the
        behaviour that must hold once the rule is shared, and documents the gap.
        """
        from skra.vector import VectorSearch

        self.ingest()
        vector = VectorSearch(self.store)
        vector.build()
        hits = vector.search("who must approve a tool call before it leaves the trust boundary")
        self.assertTrue(hits["candidates"])
        self.assertEqual(hits["candidates"][0]["kind"], "body",
                         "正文证据必须排在页眉页脚之前")


if __name__ == "__main__":
    unittest.main()
