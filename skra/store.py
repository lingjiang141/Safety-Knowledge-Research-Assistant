"""SQLite snapshots and deterministic line-based evidence retrieval."""
import hashlib
import json
import re
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path

from .pdf import extract as pdf_extract

SPLITTER = "heading-lines-v1:20"
STRUCTURED_SPLITTER = "heading-block-v2"
PROCEDURE_SPLITTER = "heading-procedure-v3"
PDF_SPLITTER = "pdf-pages-v1"
SPLITTERS = (SPLITTER, STRUCTURED_SPLITTER, PROCEDURE_SPLITTER, PDF_SPLITTER)
ALIASES = {"提示注入": "prompt injection", "工具权限": "tool permissions",
           "最小权限": "least privilege", "间接注入": "indirect injection"}

# BM25 free parameters. Standard defaults (k1 controls term-frequency saturation,
# b controls length normalisation). Recorded here, next to the shared
# tokenisation, so a reported score can always be traced to its settings.
BM25_K1 = 1.5
BM25_B = 0.75
# Reciprocal Rank Fusion constant. Rank r contributes 1/(k + r); the conventional
# value 60 damps the top ranks so one retriever's #1 cannot dominate the fusion.
RRF_K = 60
# Tokenisation is shared by the keyword prototype and BM25: one definition of
# what a "term" is, so the two cannot drift apart.
TOKEN_RE = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+")


def search_terms(query):
    """Expand a query with the Chinese→English aliases, then tokenise it.

    One tokenisation rule for every term-based retriever. Returns (tokens, expanded).
    """
    expanded = query.lower()
    for term, english in ALIASES.items():
        if term in query:
            expanded += " " + english
    return TOKEN_RE.findall(expanded), expanded


META_LINE = re.compile(
    r"^\s*(Source|Publisher|License|Retrieved|Title|Author|Date)\s*[:：]", re.IGNORECASE)
ADAPT_NOTE = re.compile(
    r"^\s*(This is a (selected )?excerpt|Formatting and|Adapted from|Note:)", re.IGNORECASE)
METADATA_SECTION = "(说明性元数据)"


def is_metadata_block(text):
    """A block that only carries provenance/licence boilerplate, not body content."""
    meaningful = [l for l in text.splitlines() if l.strip()]
    if not meaningful:
        return False
    return all(META_LINE.match(l) for l in meaningful)


def peel_metadata(lines, units):
    """Split leading provenance boilerplate away from the heading that carries it.

    A title block often bundles its H1 with Source/License lines and an "adapted
    excerpt" note. Those lines are pulled into their own unit so the boilerplate
    never shares a chunk with the title (and cannot crowd out body evidence), while
    the original text stays readable and locatable.

    `units` is a list of (section, start_line, end_line) covering `lines`; the same
    shape is returned, with a leading (METADATA_SECTION, …) unit inserted where
    boilerplate was found. Pure: it only reads `lines` and never renumbers, so both
    the guide and the procedure strategy can share one implementation (Issue 14
    follow-up: the rule had been copied verbatim into each strategy).
    """
    peeled = []
    for section, start, end in units:
        block = lines[start - 1:end]
        if is_metadata_block("\n".join(block)):
            peeled.append((section, start, end))
            continue
        head = re.match(r"^#{1,6}\s+(.+)$", block[0]) if block else None
        if not head:
            # Not a heading block: nothing to peel, it is body as it stands.
            peeled.append((section, start, end))
            continue
        body_offset = None
        for i in range(1, len(block)):
            line = block[i]
            if not line.strip() or META_LINE.match(line) or ADAPT_NOTE.match(line):
                continue
            body_offset = i
            break
        if body_offset is None:
            # Nothing but the H1 and boilerplate: the whole block is metadata, unless
            # this is a heading-only block (a section with no body yet).
            nonblank = [l for l in block[1:] if l.strip()]
            if nonblank and all(not l.strip() or META_LINE.match(l) or ADAPT_NOTE.match(l)
                                for l in block[1:]):
                peeled.append((METADATA_SECTION, start, end))
            else:
                peeled.append((section, start, end))
            continue
        region = block[1:body_offset]
        has_meta = any(META_LINE.match(l) or ADAPT_NOTE.match(l) for l in region)
        if has_meta and all(not l.strip() or META_LINE.match(l) or ADAPT_NOTE.match(l)
                            for l in region):
            peeled.append((METADATA_SECTION, start, start + body_offset - 1))
            peeled.append((section, start + body_offset, end))
        else:
            peeled.append((section, start, end))
    return peeled


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _as_row(chunk):
    """Normalise a chunk tuple to the 10-column shape chunks table expects.

    Markdown and procedure strategies build 9-tuples (no page); PDF rows append the
    page number. Padding here keeps every INSERT on one code path.
    """
    return chunk if len(chunk) == 10 else (*chunk, None)


def check_search_args(query, limit):
    """The one argument guard every retriever shares.

    Each retriever had grown its own copy of this check; adding BM25 and a fusion
    layer would have made it four. It lives here so the two retrievers (and any
    later one) cannot disagree about what a valid query is.
    """
    if not query.strip() or not 1 <= limit <= 20:
        raise ValueError("问题不能为空；limit 必须为 1–20。")


def active_chunk_ids(db):
    """The ids of chunks that may be returned; retired versions are excluded.

    A retired chunk must never re-enter an answer (Issue 06), and every retriever
    has to apply that same rule -- so it is applied in one place.
    """
    return {r["id"] for r in db.execute("SELECT id FROM chunks WHERE active=1")}


def record_run(db, query, result, elapsed_ms, created=None, sqlite_clock=False):
    """Persist one retrieved result under the shared runs column signature.

    This is the single writer for the `runs` table: changing its columns used to
    require edits in four places with no guard. `created` is injectable so
    offline/controlled runs can stamp a fixed value; `sqlite_clock` keeps the
    answer path's original `datetime('now')` stamp without a second INSERT.
    """
    if created is not None:
        stamp_sql, params = "?,?,?,?", (created, query,
                                        json.dumps(result, ensure_ascii=False), elapsed_ms)
    elif sqlite_clock:
        stamp_sql, params = "datetime('now'),?,?,?", (query,
                                        json.dumps(result, ensure_ascii=False), elapsed_ms)
    else:
        stamp_sql, params = "?,?,?,?", (datetime.now(timezone.utc).isoformat(), query,
                                        json.dumps(result, ensure_ascii=False), elapsed_ms)
    with db:
        cursor = db.execute(
            f"INSERT INTO runs(created,query,result,elapsed_ms) VALUES ({stamp_sql})", params)
    return cursor.lastrowid


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
          license TEXT NOT NULL, acquired TEXT NOT NULL, hash TEXT NOT NULL,
          splitter TEXT NOT NULL, snapshot TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, section TEXT NOT NULL,
          start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, text TEXT NOT NULL,
          version TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
          kind TEXT NOT NULL DEFAULT 'body', page INTEGER);
        CREATE TABLE IF NOT EXISTS runs (
          id INTEGER PRIMARY KEY, created TEXT, query TEXT, result TEXT, elapsed_ms REAL);
        """)
        # Migrate pre-Issue-06 databases: chunks gained version/active columns.
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(chunks)")}
        if "version" not in columns:
            self.db.execute("ALTER TABLE chunks ADD COLUMN version TEXT NOT NULL DEFAULT ''")
            self.db.execute("UPDATE chunks SET version=(SELECT hash FROM documents d WHERE d.id=chunks.doc_id)")
        if "active" not in columns:
            self.db.execute("ALTER TABLE chunks ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        if "kind" not in columns:
            self.db.execute("ALTER TABLE chunks ADD COLUMN kind TEXT NOT NULL DEFAULT 'body'")
        if "page" not in columns:
            # Issue 11: PDF chunks carry the page they came from. Markdown rows keep
            # NULL, so "no page" stays distinguishable from "page 0".
            self.db.execute("ALTER TABLE chunks ADD COLUMN page INTEGER")

    def close(self):
        self.db.close()

    def _chunk(self, doc_id, content_hash, content, splitter=SPLITTER):
        """Deterministic chunking shared by import and update."""
        if splitter == PDF_SPLITTER:
            # PDF content is the extracted line list, not a Markdown string.
            return self._chunk_pdf(doc_id, content_hash, content)
        if splitter == STRUCTURED_SPLITTER:
            return self._chunk_structured(doc_id, content_hash, content)
        if splitter == PROCEDURE_SPLITTER:
            return self._chunk_procedure(doc_id, content_hash, content)
        if splitter != SPLITTER:
            raise ValueError(f"未知切分策略：{splitter}")
        chunks = []
        section = "(正文)"
        pending = []
        start = 1

        def flush():
            if pending and "\n".join(pending).strip():
                text = "\n".join(pending)
                end = start + len(pending) - 1
                cid = digest(f"{doc_id}:{content_hash}:{splitter}:{start}:{end}")
                chunks.append((cid, doc_id, section, start, end, text, content_hash, 1, "body"))
            pending.clear()

        fenced = False
        for number, line in enumerate(content.splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
            heading = re.match(r"^#{1,6}\s+(.+)$", line) if not fenced else None
            if heading:
                flush()
                section = heading.group(1)
            if not pending:
                start = number
            pending.append(line)
            if len(pending) >= 20:
                flush()
        flush()
        return chunks

    def _chunk_structured(self, doc_id, content_hash, content):
        """Structure-aware splitting for guides.

        A block = a heading plus its body up to the next heading of the same or
        higher level. Within a block, a definition paragraph is kept together with
        the list it introduces, so a qualifier is never separated from its items.
        Oversized blocks are split only at blank-line boundaries and keep their
        section label, never mid-sentence.
        """
        lines = content.splitlines()
        blocks = []  # (section, start_line, end_line)
        current_section = "(正文)"
        block_start = 1
        for number, line in enumerate(lines, 1):
            heading = re.match(r"^#{1,6}\s+(.+)$", line)
            if heading:
                if number > block_start and any(l.strip() for l in lines[block_start - 1:number - 1]):
                    blocks.append((current_section, block_start, number - 1))
                current_section = heading.group(1)
                block_start = number
        if block_start <= len(lines) and any(l.strip() for l in lines[block_start - 1:]):
            blocks.append((current_section, block_start, len(lines)))

        # A leading title block often bundles the H1 with provenance boilerplate and
        # an "adapted excerpt" note; peel those off so the boilerplate cannot crowd
        # out body evidence. Shared with the procedure strategy (single rule, shared).
        blocks = peel_metadata(lines, blocks)

        chunks = []
        for section, start, end in blocks:
            text = "\n".join(lines[start - 1:end])
            if not text.strip():
                continue
            # Keep a definition paragraph with the list that follows it: split only
            # at blank lines, and never between an introducing colon line and its
            # list items.
            pieces = self._split_block(lines[start - 1:end], start)
            for piece_start, piece_end, piece_text in pieces:
                kind = "metadata" if (section == METADATA_SECTION
                                      or is_metadata_block(piece_text)) else "body"
                cid = digest(f"{doc_id}:{content_hash}:{STRUCTURED_SPLITTER}:{piece_start}:{piece_end}")
                chunks.append((cid, doc_id, section, piece_start, piece_end,
                               piece_text, content_hash, 1, kind))
        return chunks

    def _chunk_procedure(self, doc_id, content_hash, content):
        """Splitting for operational procedures (Issue 14).

        A procedure unit = a heading plus its body up to the next heading of the
        same or higher level. Units are labelled:
          - a headed unit keeps its section name, so a step still names the
            prerequisite section it depends on;
          - a fenced-code unit gets a derived label ("代码（…）"), and the line that
            introduces the fence stays inside it, so code is never orphaned;
          - an unheaded unit written straight after a headed one inherits that
            section, so a warning sitting under the steps is still locatable there.

        The leading H1 block that also carries provenance boilerplate is peeled off
        as metadata, exactly as for structured guides. Code is analysed, never run.
        """
        lines = content.splitlines()
        # Fenced regions are tracked first: a "# …" inside a code fence is a comment,
        # not a heading, so scanning must not treat it as a section boundary.
        fenced = set()
        inside = False
        for number, line in enumerate(lines, 1):
            if line.lstrip().startswith(("```", "~~~")):
                fenced.add(number)
                inside = not inside
            elif inside:
                fenced.add(number)
        units = []  # (section, start_line, end_line)
        current = "(正文)"
        start = 1
        for number, line in enumerate(lines, 1):
            heading = re.match(r"^#{1,6}\s+(.+)$", line) if number not in fenced else None
            if heading:
                if number > start and any(l.strip() for l in lines[start - 1:number - 1]):
                    units.append((current, start, number - 1))
                current = heading.group(1)
                start = number
        if start <= len(lines) and any(l.strip() for l in lines[start - 1:]):
            units.append((current, start, len(lines)))

        # Peel provenance boilerplate off the leading title block — the same shared
        # rule the guide strategy uses, so both can never drift apart.
        units = peel_metadata(lines, units)

        # Each unit takes the label of its own heading, except an unheaded
        # continuation, which is tagged from the section that precedes it, so a
        # warning written straight under the steps is still locatable there.
        # The one label that must never be inherited is the metadata label: peeling a
        # provenance block off a title leaves the rest of that section unheaded, and
        # inheriting would file a whole section of real content as boilerplate. Such a
        # continuation keeps the real heading it followed, which peel_metadata left on
        # the unit it split from.
        labelled = []
        for index, (section, unit_start, unit_end) in enumerate(units):
            block = lines[unit_start - 1:unit_end]
            unheaded = not re.match(r"^#{1,6}\s+", block[0]) if block else True
            if unheaded and index > 0:
                previous = labelled[-1][0]
                if section == METADATA_SECTION:
                    # Keep the metadata label only when this really is more provenance.
                    pass
                elif previous == METADATA_SECTION:
                    section = next((s for s, _, _ in reversed(labelled)
                                    if s != METADATA_SECTION), section)
                else:
                    section = previous
            labelled.append((section, unit_start, unit_end))

        # A heading introduces the body that follows, so it is folded into that body
        # instead of becoming a chunk of its own. A heading is only merged into the
        # previous unit when that unit had no heading of its own (its body continues
        # past a blank line); a headed unit always starts a new section.
        # The heading is dropped here; it is re-attached to the first piece of each
        # unit below, so the label never becomes a chunk on its own and always sits
        # at the head of the paragraph it announces.
        merged = []
        for section, start, end in labelled:
            block = lines[start - 1:end]
            headed = bool(re.match(r"^#{1,6}\s+", block[0])) if block else False
            if headed:
                if len(block) == 1:
                    continue  # a heading immediately superseded by the next one
                merged.append((section, start, end))
            elif merged and merged[-1][0] != METADATA_SECTION:
                merged[-1] = (merged[-1][0], merged[-1][1], end)
            else:
                # An unheaded continuation is normally absorbed into the section above
                # it, but never into a provenance block: that would file real body
                # content as boilerplate and cost it its body search slot. After a
                # peeled title the section that follows keeps its own name instead.
                merged.append((section, start, end))
        labelled = merged

        # A code fence is atomic: the fence keeps only the piece that actually opens
        # it, so a fence never swallows neighbouring prose, while the derived
        # "代码（…）" label still ties the fence to the procedure it belongs to. A
        # headed unit is cut from the line after its heading, which is re-attached to
        # the opening piece.
        chunks = []
        for section, start, end in labelled:
            headed = bool(re.match(r"^#{1,6}\s+", lines[start - 1])) if start <= len(lines) else False
            body_start = start + 1 if headed else start
            pieces = self._procedure_pieces(body_start, end, lines)
            if headed and pieces:
                first_start, _, first_text = pieces[0]
                pieces[0] = (start, first_start + first_text.count("\n"),
                             lines[start - 1] + "\n" + first_text)
            for piece_start, piece_end, piece_text in pieces:
                if not piece_text.strip():
                    continue
                # Only the piece that opens the fence carries the derived label; a
                # heading is re-attached above without appearing twice in the text.
                section_label = section
                if section not in (METADATA_SECTION, "(正文)") and any(
                        l.lstrip().startswith(("```", "~~~")) for l in piece_text.splitlines()):
                    section_label = f"代码（{section}）"
                kind = ("metadata" if section_label == METADATA_SECTION else "body")
                cid = digest(f"{doc_id}:{content_hash}:{PROCEDURE_SPLITTER}:"
                             f"{piece_start}:{piece_end}")
                chunks.append((cid, doc_id, section_label, piece_start, piece_end,
                               piece_text, content_hash, 1, kind))
        return chunks

    def _chunk_pdf(self, doc_id, content_hash, content):
        """Page-aware splitting for text-based PDFs (Issue 11).

        `content` is a list of (page_number, line) pairs from the extractor. The
        leading and trailing lines of a page that repeat across pages are running
        headers/footers: they are kept as metadata rather than deleted, so the
        original page furniture stays reviewable without occupying body evidence
        slots. A paragraph interrupted by a page break keeps both halves retrievable,
        because chunking never crosses a page boundary.
        """
        pairs = list(content)
        if not pairs:
            return []

        furniture = self._page_furniture(pairs)
        lines = [text for _, text in pairs]

        # Section labels come from headings in the extracted text, exactly as for
        # Markdown guides: a PDF's content structure, not its file extension,
        # decides the split.
        chunks = []
        section = "(正文)"
        pending, pending_page = [], None
        at = 1
        fenced = False

        def flush():
            nonlocal pending, pending_page
            text = "\n".join(pending)
            if text.strip():
                # `at` is a 1-based line number; furniture indices are 0-based.
                kind = "metadata" if all(
                    not l.strip() or (at + i - 1) in furniture
                    for i, l in enumerate(pending)) else "body"
                cid = digest(f"{doc_id}:{content_hash}:{PDF_SPLITTER}:"
                             f"{pending_page}:{at}:{at + len(pending) - 1}")
                chunks.append((cid, doc_id, section, at, at + len(pending) - 1,
                               text, content_hash, 1, kind, pending_page))
            pending, pending_page = [], None

        for index, (page, line) in enumerate(pairs):
            number = index + 1
            heading = (re.match(r"^#{1,6}\s+(.+)$", line)
                       if not fenced and line.lstrip().startswith("#") else None)
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
            # Page furniture is its own unit: a running header must not be glued to
            # the body paragraph that follows it, or the body would inherit the
            # metadata label and drop out of the body evidence slots.
            if index in furniture:
                flush()
                at, pending_page = number, page
                pending.append(line)
                flush()
                continue
            # A page break always starts a new chunk: a continuous paragraph is
            # still locatable on both pages, never merged into one fake span.
            if pending and (pending_page != page or heading):
                flush()
            if heading:
                section = heading.group(1)
            if not pending:
                at = number
            if pending_page is None:
                pending_page = page
            pending.append(line)
        flush()

        # A PDF's title page carries the same Source/License boilerplate a Markdown
        # guide does, so the shared peeling rule applies unchanged — the format
        # decides extraction, the content decides splitting and boilerplate handling.
        chunks = self._peel_pdf_provenance(chunks, pairs, furniture)
        return chunks

    @staticmethod
    def _peel_pdf_provenance(chunks, pairs, furniture):
        """Mark a title block's provenance lines as metadata, reusing peel_metadata.

        The rule is shared with Markdown, so a PDF title page cannot drift from a
        Markdown one. Only page 1 is inspected: later pages have no title block.
        """
        lines = [text for _, text in pairs]
        rebuilt = []
        for chunk in chunks:
            start, end = chunk[3], chunk[4]
            if chunk[8] != "metadata" and start <= end:
                units = [(chunk[2], start, end)]
                peeled = peel_metadata(lines, units)
                # Only accept the split when it actually isolated boilerplate; a
                # single unit means there was nothing to peel.
                if len(peeled) > 1:
                    for section, sub_start, sub_end in peeled:
                        text = "\n".join(lines[sub_start - 1:sub_end])
                        if not text.strip():
                            continue
                        kind = "metadata" if section == METADATA_SECTION else "body"
                        cid = digest(f"{chunk[1]}:{chunk[6]}:{PDF_SPLITTER}:"
                                     f"{chunk[9]}:{sub_start}:{sub_end}")
                        rebuilt.append((cid, chunk[1], section, sub_start, sub_end,
                                        text, chunk[6], 1, kind, chunk[9]))
                    continue
            rebuilt.append(chunk)
        return rebuilt


    @staticmethod
    def _page_furniture(pairs):
        """Line indices that look like running headers/footers.

        Only the first and last non-blank line of each page are candidates, and only
        when the same text (ignoring a changing page number) repeats on most pages.
        That keeps a sentence that merely happens to repeat inside the body intact.
        """
        pages = {}
        for index, (page, line) in enumerate(pairs):
            pages.setdefault(page, []).append(index)
        page_numbers = sorted(pages)
        if len(page_numbers) < 2:
            return set()

        def normalise(text):
            # Drop digits so "page 2 of 5" and "page 3 of 5" compare equal.
            return re.sub(r"\d+", "#", text.strip())

        total = len(page_numbers)
        candidates = {"top": {}, "bottom": {}}
        for page in page_numbers:
            indices = pages[page]
            nonblank = [i for i in indices if pairs[i][1].strip()]
            if not nonblank:
                continue
            for edge, index in (("top", nonblank[0]), ("bottom", nonblank[-1])):
                key = normalise(pairs[index][1])
                candidates[edge].setdefault(key, []).append(index)

        furniture = set()
        # "Most pages" = at least half (a two-page file needs both pages to agree).
        threshold = max(2, (total + 1) // 2)
        for edge in ("top", "bottom"):
            for key, indices in candidates[edge].items():
                if len(indices) >= threshold:
                    furniture.update(indices)
        return furniture

    @staticmethod
    def _procedure_pieces(start, end, lines, budget=20):
        """Cut one unit into pieces, keeping fences and their introducer together.

        A fenced block (plus the sentence that announces it) is atomic — never split
        — and a blank line starts a new piece, so a step's paragraph, its code and a
        following warning each stay locatable.
        """
        block = lines[start - 1:end]
        pieces, pending, at = [], [], start
        cursor, fenced = 0, False
        while cursor < len(block):
            line = block[cursor]
            # A fence may arrive right after an empty line ("Run …:\n\n```bash", and
            # even across the blank line the introducing sentence is part of it). The
            # pending prose is handed over wholesale, so the introducer is never
            # emitted twice and never counted as a chunk of its own.
            if not fenced and line.lstrip().startswith(("```", "~~~")):
                fence = cursor + 1
                while fence < len(block) and not block[fence].lstrip().startswith(("```", "~~~")):
                    fence += 1
                fence = min(fence + 1, len(block))
                lead = list(pending)
                pending = []
                pieces.append((at, start + fence - 1, "\n".join(lead + block[cursor:fence])))
                cursor = fence
                continue
            if not fenced and not line.strip() and pending:
                pieces.append((at, start + cursor - 1, "\n".join(pending)))
                pending, at = [], start + cursor + 1
            else:
                if not pending:
                    at = start + cursor
                pending.append(line)
                if not fenced and len(pending) >= budget:
                    pieces.append((at, start + cursor, "\n".join(pending)))
                    pending, at = [], start + cursor + 1
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
            cursor += 1
        if pending:
            pieces.append((at, start + len(block) - 1, "\n".join(pending)))
        return [(s, e, t) for s, e, t in pieces if t.strip()]

    @staticmethod
    def _split_block(block_lines, offset, budget=20):
        """Split a block at blank lines, keeping a list with its introducing line."""
        pieces = []
        pending, start = [], offset
        i = 0
        while i < len(block_lines):
            line = block_lines[i]
            if not pending:
                start = offset + i
            pending.append(line)
            # Detect "…:" line followed by list items → keep them together.
            joined = "\n".join(pending)
            introduces_list = joined.rstrip().endswith(":") or joined.rstrip().endswith("：")
            next_is_item = (i + 1 < len(block_lines)
                            and re.match(r"^\s*([-*+]|\d+[.)])\s+", block_lines[i + 1] or ""))
            keep = introduces_list and next_is_item
            if len(pending) >= budget and not keep:
                text = "\n".join(pending)
                if text.strip():
                    pieces.append((start, start + len(pending) - 1, text))
                pending = []
            i += 1
        if pending and "\n".join(pending).strip():
            pieces.append((start, start + len(pending) - 1, "\n".join(pending)))
        return pieces

    def ingest(self, file, title, source, license_name, acquired, splitter=None):
        path = Path(file)
        suffix = path.suffix.lower()
        if suffix not in (".md", ".pdf"):
            raise ValueError("当前只支持 UTF-8 Markdown (.md) 与文本型 PDF (.pdf)。")
        if not all(v.strip() for v in (title, source, license_name)):
            raise ValueError("标题、来源和许可不得为空。")
        date.fromisoformat(acquired)

        # The file format decides how content is extracted; the content structure
        # decides how it is split. A PDF must not be forced through Markdown rules.
        extractor = ""
        if suffix == ".pdf":
            if splitter is None:
                splitter = PDF_SPLITTER
            elif splitter != PDF_SPLITTER:
                raise ValueError(
                    f"PDF 需用 {PDF_SPLITTER} 提取；文件格式决定提取方式，"
                    "内容结构才决定切分策略。")
            raw = path.read_bytes()
            pairs, page_texts, extractor = pdf_extract(path)
            content = json.dumps(page_texts, ensure_ascii=False)
            chunk_source = pairs
        else:
            if splitter is None:
                splitter = SPLITTER
            if splitter == PDF_SPLITTER:
                raise ValueError(f"{PDF_SPLITTER} 只能用于 PDF 文件。")
            raw = path.read_bytes()
            content = raw.decode("utf-8-sig")
            if not content.strip():
                raise ValueError("资料为空，未导入。")
            chunk_source = content

        if splitter not in SPLITTERS:
            raise ValueError(f"未知切分策略：{splitter}")
        content_hash = hashlib.sha256(raw).hexdigest()
        doc_id = digest(source.strip())
        existing = self.db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if existing and existing["hash"] == content_hash and existing["splitter"] == splitter:
            return {"document_id": doc_id, "version": content_hash, "status": "unchanged"}

        splitter_note = ""
        if suffix == ".md" and splitter in (STRUCTURED_SPLITTER, PROCEDURE_SPLITTER) \
                and not any(re.match(r"^#{1,6}\s+.+$", line) for line in content.splitlines()):
            # No headings at all: the structure-aware strategies cannot segment this
            # document, so fall back to the fixed baseline instead of guessing a
            # confident classification (Issue 13/14).
            splitter = SPLITTER
            splitter_note = "结构不明：未发现标题，已回退通用固定行切分策略。"

        chunks = self._chunk(doc_id, content_hash, chunk_source, splitter)
        # Publish atomically: reader-visible tables switch to the new version in one
        # transaction, and any previously active chunks for this source are retired,
        # so a half-built index can never be observed. A change of splitter strategy
        # is a new version, so old chunk ids are retired, not reused.
        with self.db:
            self.db.execute("UPDATE chunks SET active=0 WHERE doc_id=?", (doc_id,))
            if existing:
                self.db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            self.db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                            (doc_id, title.strip(), source.strip(), license_name.strip(),
                             acquired, content_hash, splitter, content))
            self.db.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?)",
                               [_as_row(c) for c in chunks])
        return {"document_id": doc_id, "version": content_hash, "splitter": splitter,
                **({"splitter_note": splitter_note} if splitter_note else {}),
                **({"extractor": extractor} if extractor else {}),
                "status": "updated" if existing else "imported", "chunks": len(chunks)}

    def update(self, file, source, title=None, license_name=None, acquired=None, splitter=None):
        """Re-import a source with new content, reusing its recorded metadata."""
        existing = self.db.execute(
            "SELECT * FROM documents WHERE id=?", (digest(source.strip()),)).fetchone()
        if not existing:
            raise ValueError("该来源不存在，无法更新。")
        return self.ingest(file, title or existing["title"], source,
                           license_name or existing["license"],
                           acquired or existing["acquired"],
                           splitter or existing["splitter"])

    def documents(self):
        return [dict(r) for r in self.db.execute(
            "SELECT id,title,source,license,acquired,hash,splitter FROM documents ORDER BY id")]

    def delete(self, source):
        """Retire a source: remove its document and deactivate all its chunks."""
        if not source or not source.strip():
            raise ValueError("来源不得为空。")
        doc_id = digest(source.strip())
        existing = self.db.execute("SELECT id FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not existing:
            raise ValueError("该来源不存在，无法删除。")
        with self.db:
            self.db.execute("UPDATE chunks SET active=0 WHERE doc_id=?", (doc_id,))
            self.db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        return {"document_id": doc_id, "status": "deleted"}

    def read(self, cid):
        row = self.db.execute("""SELECT c.*, d.title,d.source,d.license,d.acquired,
          d.hash AS version,d.splitter FROM chunks c JOIN documents d ON c.doc_id=d.id
          WHERE c.id=? AND c.active=1""", (cid,)).fetchone()
        if not row:
            retired = self.db.execute("SELECT active FROM chunks WHERE id=?", (cid,)).fetchone()
            if retired:
                raise ValueError("片段属于已失效的历史版本，不再作为当前证据。")
            raise ValueError("片段不存在。")
        return dict(row)

    def search(self, query, limit=5):
        check_search_args(query, limit)
        started = time.perf_counter()
        expanded = query.lower()
        for term, english in ALIASES.items():
            if term in query:
                expanded += " " + english
        terms = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", expanded))
        ranked = []
        for row in self.db.execute("SELECT id,text,kind FROM chunks WHERE active=1"):
            tokens = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", row["text"].lower()))
            score = len(terms & tokens)
            if score:
                # Body evidence takes precedence over provenance boilerplate, so
                # a licence/source line cannot occupy a body search slot (Issue 13).
                ranked.append((-score, row["kind"] != "body", row["id"]))
        ranked.sort()
        results = [{**self.read(cid), "score": -score} for score, _, cid in ranked[:limit]]
        elapsed = (time.perf_counter() - started) * 1000
        output = {"mode": "keyword-prototype", "query": query, "expanded_query": expanded,
                  "candidates": results, "elapsed_ms": elapsed,
                  "note": "仅返回原文证据；无结果不等于资料中一定没有答案。"}
        output["run_id"] = record_run(self.db, query, output, elapsed)
        return output

    def run(self, run_id):
        row = self.db.execute("SELECT result FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise ValueError("运行记录不存在。")
        return json.loads(row["result"])
