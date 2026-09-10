"""Build real, text-based PDFs for tests and demos, with no extra dependency.

The project deliberately keeps its runtime dependency list small (pypdf is the only
PDF reader). Authoring fixtures therefore writes PDF syntax directly: a tiny
Type1/Helvetica text object per page, plus pages that intentionally carry no text at
all so the "no extractable body" path can be exercised against a genuine PDF rather
than a hand-written string.
"""
from pathlib import Path


def _escape(text):
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(lines):
    """A content stream that prints `lines`, one per text-showing operation."""
    parts = ["BT", "/F1 11 Tf", "14 TL", "72 750 Td"]
    for line in lines:
        parts.append(f"({_escape(line)}) Tj")
        parts.append("T*")
    parts.append("ET")
    return "\n".join(parts)


def build_pdf(pages):
    """Write a PDF whose pages each show the given list of text lines.

    `pages` is a list of lists; an empty list yields a page with no text at all.
    Returns the bytes, so callers can write them wherever they need.
    """
    objects = []  # 1-based object bodies, index 0 is object 1

    # Reserve: 1=Catalog, 2=Pages, 3=Font; page objects start at 4.
    page_ids = []
    next_id = 4
    for _ in pages:
        page_ids.append(next_id)
        next_id += 2  # page object + content stream object
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_id, lines in zip(page_ids, pages):
        content_id = page_id + 1
        stream = _content_stream(lines)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>")
        objects.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")

    # Serialise with a correct xref table.
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode("latin-1")
    return bytes(out)


def write_pdf(path, pages):
    """Write a generated PDF to `path` and return the Path."""
    path = Path(path)
    path.write_bytes(build_pdf(pages))
    return path


def multipage_report():
    """A five-page report: running header/footer, real sections, a title page.

    Page 1 is a title page with provenance lines; pages 2-5 carry a repeated header
    ("OWASP Agent Security Report") and footer ("Confidential — page N of 5"), with
    body sections that continue a paragraph across a page break (page 3 ends
    mid-paragraph, page 4 continues it).
    """
    header = "OWASP Agent Security Report"
    def footer(n):
        return f"Confidential - page {n} of 5"

    return [
        # Page 1: title page with boilerplate
        [header, "", "LLM Agent Security: Operator Notes", "",
         "Source: internal research digest", "License: CC BY-SA 4.0", "",
         "Prepared for internal review."],
        # Page 2
        [header, "", "## Least Privilege", "",
         "Agents should hold the narrowest permissions that still allow the task.",
         "",
         "- grant only the tools the task requires",
         "- revoke credentials when the task finishes",
         "", footer(2)],
        # Page 3: paragraph continues onto page 4
        [header, "", "## Indirect Prompt Injection", "",
         "An indirect injection arrives through content the agent reads rather than",
         "through the operator's instruction. The defence is to treat retrieved", "",
         footer(3)],
        # Page 4: continuation of page 3's paragraph + a new section
        [header, "", "content as untrusted input and to require confirmation before",
         "any action that leaves the trust boundary.", "",
         "## Tool Scoping", "",
         "Scope every tool to the smallest resource set it needs.", "", footer(4)],
        # Page 5
        [header, "", "## Audit Trails", "",
         "Log every tool invocation with the acting principal and the decision made.", "",
         footer(5)],
    ]
