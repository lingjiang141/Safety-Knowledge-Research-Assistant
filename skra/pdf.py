"""Text-layer PDF extraction: pages -> locatable lines (Issue 11).

This module only reads a PDF's text layer; it never runs OCR and never executes
anything embedded in the file. It returns a flat list of (page, text) lines plus the
per-page text, so the Store can build chunks that still know which page they came
from. Anything it cannot extract reliably is reported, never guessed.
"""
import logging
from pathlib import Path

EXTRACTOR = "pdf-text-v1"


class PdfError(ValueError):
    """A PDF problem the operator must see, phrased so it can act on it."""


def extract(path):
    """Return (lines, pages, extractor) for a text-based PDF.

    `lines` is a list of (page_number, text); `pages` is the per-page raw text.
    A PDF with no extractable text raises PdfError rather than yielding an empty
    document, because a scanned file must fail loudly (PRD 4.4).
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise PdfError("缺少 PDF 解析依赖 pypdf，无法提取 PDF。") from exc

    try:
        # pypdf logs recoverable-parse chatter straight to stderr; the caller gets a
        # single explicit PdfError instead, so library noise stays out of the CLI.
        logging.getLogger("pypdf").setLevel(logging.CRITICAL)
        reader = PdfReader(str(path))
        page_texts = []
        for page in reader.pages:
            page_texts.append(page.extract_text() or "")
    except PdfError:
        raise
    except Exception as exc:
        raise PdfError(f"PDF 解析失败，文件可能已损坏或加密：{exc}") from exc

    if not page_texts:
        raise PdfError("PDF 不含任何页面，无法提取正文。")

    lines = []
    for number, text in enumerate(page_texts, 1):
        for line in text.splitlines():
            lines.append((number, line))

    if not any(text.strip() for _, text in lines):
        raise PdfError(
            "PDF 未提取到可读正文：该文件可能是扫描件或纯图片，本轮不支持 OCR，"
            "不会伪装成功。")

    suspect = _suspect_reading_order(lines)
    if suspect is not None:
        # PRD 4.4: tell the operator we cannot reconstruct this layout reliably
        # rather than importing text whose order we cannot vouch for.
        raise PdfError(
            f"PDF 阅读顺序疑似混乱（{suspect}），本轮不支持双栏/任意排版重建，"
            "未导入以避免产生错误页码定位。")

    return lines, page_texts, EXTRACTOR


def _suspect_reading_order(lines):
    """Return a reason if the extracted order looks structurally implausible.

    A deliberately conservative check: it only flags a page whose text is dominated
    by very short fragmented lines (the usual signature of text drawn in many
    disconnected fragments, such as columns interleaved by a broken extractor).
    Normal prose and lists never trigger it.
    """
    by_page = {}
    for page, text in lines:
        if text.strip():
            by_page.setdefault(page, []).append(text.strip())
    for page, texts in by_page.items():
        if len(texts) < 12:
            continue  # too little text on this page to judge
        short = sum(1 for t in texts if len(t) <= 3)
        if short / len(texts) > 0.6:
            return f"第 {page} 页出现大量碎片化短行（{short}/{len(texts)}）"
    return None
