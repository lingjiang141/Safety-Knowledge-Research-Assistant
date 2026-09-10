"""SQLite snapshots and deterministic line-based evidence retrieval."""
import hashlib
import json
import re
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path

SPLITTER = "heading-lines-v1:20"
ALIASES = {"提示注入": "prompt injection", "工具权限": "tool permissions",
           "最小权限": "least privilege", "间接注入": "indirect injection"}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
          version TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1);
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

    def close(self):
        self.db.close()

    def _chunk(self, doc_id, content_hash, content):
        """Deterministic chunking shared by import and update."""
        chunks = []
        section = "(正文)"
        pending = []
        start = 1

        def flush():
            if pending and "\n".join(pending).strip():
                text = "\n".join(pending)
                end = start + len(pending) - 1
                cid = digest(f"{doc_id}:{content_hash}:{SPLITTER}:{start}:{end}")
                chunks.append((cid, doc_id, section, start, end, text, content_hash, 1))
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

    def ingest(self, file, title, source, license_name, acquired):
        path = Path(file)
        if path.suffix.lower() != ".md":
            raise ValueError("当前只支持 UTF-8 Markdown (.md)。")
        if not all(v.strip() for v in (title, source, license_name)):
            raise ValueError("标题、来源和许可不得为空。")
        date.fromisoformat(acquired)
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")
        if not content.strip():
            raise ValueError("资料为空，未导入。")
        content_hash = hashlib.sha256(raw).hexdigest()
        doc_id = digest(source.strip())
        existing = self.db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if existing and existing["hash"] == content_hash and existing["splitter"] == SPLITTER:
            return {"document_id": doc_id, "version": content_hash, "status": "unchanged"}
        chunks = self._chunk(doc_id, content_hash, content)
        # Publish atomically: reader-visible tables switch to the new version in one
        # transaction, and any previously active chunks for this source are retired,
        # so a half-built index can never be observed.
        with self.db:
            self.db.execute("UPDATE chunks SET active=0 WHERE doc_id=?", (doc_id,))
            if existing:
                self.db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            self.db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                            (doc_id, title.strip(), source.strip(), license_name.strip(),
                             acquired, content_hash, SPLITTER, content))
            self.db.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)", chunks)
        return {"document_id": doc_id, "version": content_hash,
                "status": "updated" if existing else "imported", "chunks": len(chunks)}

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
        if not query.strip() or not 1 <= limit <= 20:
            raise ValueError("问题不能为空；limit 必须为 1–20。")
        started = time.perf_counter()
        expanded = query.lower()
        for term, english in ALIASES.items():
            if term in query:
                expanded += " " + english
        terms = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", expanded))
        ranked = []
        for row in self.db.execute("SELECT id,text FROM chunks WHERE active=1"):
            tokens = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", row["text"].lower()))
            score = len(terms & tokens)
            if score:
                ranked.append((score, row["id"]))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        results = [{**self.read(cid), "score": score} for score, cid in ranked[:limit]]
        elapsed = (time.perf_counter() - started) * 1000
        output = {"mode": "keyword-prototype", "query": query, "expanded_query": expanded,
                  "candidates": results, "elapsed_ms": elapsed,
                  "note": "仅返回原文证据；无结果不等于资料中一定没有答案。"}
        with self.db:
            cursor = self.db.execute("INSERT INTO runs(created,query,result,elapsed_ms) VALUES (?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), query, json.dumps(output, ensure_ascii=False), elapsed))
        output["run_id"] = cursor.lastrowid
        return output

    def run(self, run_id):
        row = self.db.execute("SELECT result FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise ValueError("运行记录不存在。")
        return json.loads(row["result"])
