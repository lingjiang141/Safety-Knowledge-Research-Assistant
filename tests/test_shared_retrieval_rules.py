"""Shared retrieval rules must have a single home, not one copy per retriever.

Issue 08 adds BM25 and RRF on top of two existing retrievers. Before that code is
written, the rules every retriever repeats -- argument checking, active-version
filtering, run persistence -- are pulled into one place. These tests pin the
behaviour those rules must keep, and fail if a retriever starts carrying its own
copy again (which is exactly how the body-precedence rule drifted between
`store.search` and `vector.search`, see architecture review point 5).
"""
import re
import unittest
from pathlib import Path

from skra.store import Store, active_chunk_ids, check_search_args, record_run

ROOT = Path(__file__).resolve().parents[1]


def store_with(rows):
    """An in-memory store holding the given (id, text, kind) chunks."""
    store = Store(":memory:")
    with store.db:
        store.db.execute(
            "INSERT INTO documents(id,title,source,license,acquired,hash,splitter,snapshot) "
            "VALUES ('d','T','urn:x','CC0','2026-09-10','h','heading-lines-v1:20','x')")
        for cid, text, kind, active in rows:
            store.db.execute(
                "INSERT INTO chunks(id,doc_id,section,start_line,end_line,text,version,active,kind,page) "
                "VALUES (?,?,?,?,?,?,?,?,?,NULL)",
                (cid, "d", "S", 1, 1, text, "h", active, kind))
    return store


class SharedRuleTest(unittest.TestCase):
    def test_check_search_args_rejects_exactly_what_the_retrievers_reject(self):
        """One guard, one message: every retriever must reject the same inputs."""
        for bad_limit in (0, 21, -1):
            with self.subTest(limit=bad_limit):
                with self.assertRaises(ValueError):
                    check_search_args("提示注入", bad_limit)
        with self.assertRaises(ValueError):
            check_search_args("   ", 5)
        check_search_args("提示注入", 1)
        check_search_args("提示注入", 20)

    def test_active_chunk_ids_excludes_retired_versions(self):
        """A retired chunk must never be visible to any retriever (Issue 06)."""
        store = store_with([
            ("live", "prompt injection evidence", "body", 1),
            ("retired", "prompt injection old version", "body", 0),
        ])
        self.assertEqual(active_chunk_ids(store.db), {"live"})

    def test_record_run_writes_the_shared_column_signature_and_returns_an_id(self):
        store = store_with([("live", "prompt injection evidence", "body", 1)])
        result = {"mode": "test", "candidates": []}
        run_id = record_run(store.db, "提示注入", result, 1.5)
        self.assertIsInstance(run_id, int)
        row = store.db.execute(
            "SELECT query,result,elapsed_ms FROM runs WHERE id=?", (run_id,)).fetchone()
        self.assertEqual(row["query"], "提示注入")
        self.assertEqual(row["elapsed_ms"], 1.5)
        self.assertIn("test", row["result"])

    def test_no_retriever_or_adapter_keeps_a_private_copy_of_the_run_insert(self):
        """The column signature lives in one place; callers go through record_run.

        `store.py` and `boundaries.py` share `record_run`, so the raw INSERT may
        appear there. A private INSERT reappearing anywhere else is the drift this
        test exists to catch.
        """
        allowed = {"skra/store.py"}
        offenders = []
        for path in list(ROOT.glob("skra/*.py")) + list(ROOT.glob("tests/*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"INSERT\s+(OR\s+REPLACE\s+)?INTO\s+runs", text):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f"这些文件保留了 runs 插入的私有副本，应改用 record_run：{offenders}")

    def test_no_retriever_keeps_a_private_copy_of_the_limit_guard(self):
        """The 1–20 limit guard must not be re-implemented per retriever."""
        offenders = []
        for path in ROOT.glob("skra/*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if rel == "skra/store.py":
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"1\s*<=\s*limit\s*<=\s*20", text):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f"这些文件保留了 limit 校验的私有副本，应改用 check_search_args：{offenders}")


if __name__ == "__main__":
    unittest.main()
