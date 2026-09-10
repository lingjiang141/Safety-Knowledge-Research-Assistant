"""Issue 06: updating or deleting material must stop old evidence from new answers.

Behaviors are exercised through the public Store interface (ingest/update/delete/
search/read), not internal tables, so these tests would survive an internal refactor.
"""
import tempfile
import unittest
from pathlib import Path

from skra.store import Store

ROOT = Path(__file__).resolve().parents[1]


def write_md(directory, name, text):
    path = Path(directory) / name
    path.write_text(text, encoding="utf-8")
    return path


class VersionSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "test.sqlite3")
        self.addCleanup(self.store.close)

    def ingest(self, path, source="urn:test:doc"):
        return self.store.ingest(path, "Doc", source, "CC0-1.0", "2026-09-10")

    def test_update_replaces_old_evidence_in_search(self):
        """After updating a source, search must not return the old version's text."""
        old = write_md(self.temp.name, "old.md",
                       "# Topic\n\nThe original sentence discusses alpha protocol guidance.\n")
        first = self.ingest(old)
        old_hit = self.store.search("alpha protocol")
        self.assertEqual(len(old_hit["candidates"]), 1)
        old_id = old_hit["candidates"][0]["id"]

        new = write_md(self.temp.name, "new.md",
                       "# Topic\n\nThe revised sentence discusses beta protocol guidance.\n")
        updated = self.ingest(new)

        self.assertEqual(updated["document_id"], first["document_id"])
        self.assertNotEqual(updated["version"], first["version"])
        self.assertEqual(updated["status"], "updated")

        after = self.store.search("alpha protocol")
        hit_ids = [c["id"] for c in after["candidates"]]
        self.assertNotIn(old_id, hit_ids, "旧版本片段不得再作为证据返回")

        revised = self.store.search("beta protocol")
        self.assertEqual(len(revised["candidates"]), 1)
        self.assertIn("beta protocol", revised["candidates"][0]["text"])

    def test_delete_removes_source_from_search_and_read(self):
        """After deleting a source, its chunks must be gone from search and unreadable."""
        doc = write_md(self.temp.name, "doc.md",
                       "# Topic\n\nThis sentence discusses gamma protocol guidance.\n")
        self.ingest(doc, source="urn:test:gone")
        hit = self.store.search("gamma protocol")
        cid = hit["candidates"][0]["id"]

        removed = self.store.delete("urn:test:gone")

        self.assertEqual(removed["status"], "deleted")
        self.assertEqual(self.store.search("gamma protocol")["candidates"], [])
        self.assertEqual(self.store.documents(), [])
        with self.assertRaises(ValueError):
            self.store.read(cid)

    def test_answer_blocked_when_evidence_retired_during_generation(self):
        """If evidence is deleted while generating, the stale answer must not be returned."""
        from skra.answer import answer, Ledger

        doc = write_md(self.temp.name, "live.md",
                       "# Topic\n\nThe delta protocol requires explicit approval.\n")
        self.ingest(doc, source="urn:test:live")
        base_search = self.store.search

        def search_then_retire(query, limit=5):
            # Retrieve normally, then simulate the source being deleted in the window
            # between retrieval and answer assembly (PRD 4.3).
            result = base_search(query, limit)
            self.store.delete("urn:test:live")
            return result

        led = Ledger(Path(self.temp.name) / "budget.sqlite3")
        self.addCleanup(led.close)
        with self.assertRaises(ValueError) as ctx:
            answer(self.store, "delta protocol", led, demo=True, search=search_then_retire)
        self.assertIn("过时", str(ctx.exception))

    def test_cli_update_and_delete_are_explicit_management_commands(self):
        """Management operations go through explicit CLI subcommands, not the answer model."""
        import json
        import subprocess
        import sys

        cli_db = str(Path(self.temp.name) / "cli.sqlite3")
        doc = write_md(self.temp.name, "cli.md", "# C\n\nzeta protocol guidance.\n")

        def call(*args, ok=True):
            result = subprocess.run([sys.executable, "-m", "skra", "--db", cli_db, *args],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
            return json.loads(result.stdout) if ok else result.stderr

        call("import", str(doc), "--title", "C", "--source", "urn:test:cli", "--license", "CC0-1.0")
        new = write_md(self.temp.name, "cli2.md", "# C\n\neta protocol guidance.\n")
        updated = call("update", str(new), "--source", "urn:test:cli")
        self.assertEqual(updated["status"], "updated")
        # The old text must no longer appear among evidence candidates.
        hits = call("search", "zeta protocol")["candidates"]
        self.assertTrue(all("zeta" not in c["text"] for c in hits))
        deleted = call("delete", "urn:test:cli")
        self.assertEqual(deleted["status"], "deleted")
    def test_chunk_id_is_stable_per_version_and_never_reused(self):
        """Same version+config -> stable ids; a new version must not reuse an id."""
        doc = write_md(self.temp.name, "s.md", "# T\n\nstable theta guidance line.\n")
        self.ingest(doc, source="urn:test:stable")
        first_ids = [c["id"] for c in self.store.search("theta guidance")["candidates"]]

        # Re-importing identical content returns "unchanged" and keeps the same ids.
        self.assertEqual(self.ingest(doc, source="urn:test:stable")["status"], "unchanged")
        self.assertEqual([c["id"] for c in self.store.search("theta guidance")["candidates"]], first_ids)

        revised = write_md(self.temp.name, "s2.md", "# T\n\nstable iota guidance line.\n")
        self.ingest(revised, source="urn:test:stable")
        new_ids = [c["id"] for c in self.store.search("iota guidance")["candidates"]]
        self.assertTrue(new_ids)
        self.assertFalse(set(new_ids) & set(first_ids), "新版本不得复用旧片段标识")

    def test_history_keeps_old_version_but_marks_it_stale(self):
        """Historical runs remain readable, yet a retired chunk is flagged, not silently served."""
        doc = write_md(self.temp.name, "h.md", "# H\n\nkappa protocol guidance.\n")
        first = self.ingest(doc, source="urn:test:hist")
        old_hit = self.store.search("kappa protocol")
        old_id, old_run = old_hit["candidates"][0]["id"], old_hit["run_id"]

        revised = write_md(self.temp.name, "h2.md", "# H\n\nlambda protocol guidance.\n")
        self.ingest(revised, source="urn:test:hist")

        # The historical retrieval record is preserved and still shows the old version.
        history = self.store.run(old_run)
        self.assertEqual(history["candidates"][0]["version"], first["version"])
        # But the old chunk can no longer be served as current evidence.
        with self.assertRaises(ValueError) as ctx:
            self.store.read(old_id)
        self.assertIn("失效", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
