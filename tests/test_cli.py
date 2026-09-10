import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CLITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / "test.sqlite3")

    def call(self, *args, ok=True):
        result = subprocess.run([sys.executable, "-m", "skra", "--db", self.db, *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
        return json.loads(result.stdout) if ok else result.stderr

    def ingest(self, path=None, ok=True):
        return self.call("import", str(path or ROOT / "examples/security-demo.md"),
            "--title", "Demo", "--source", "urn:test:demo", "--license", "CC0-1.0", ok=ok)

    def test_end_to_end_and_idempotency(self):
        first = self.ingest()
        found = self.call("search", "提示注入")
        self.assertTrue(found["candidates"])
        evidence = found["candidates"][0]
        self.assertEqual(evidence["section"], "Prompt injection")
        lines = (ROOT / "examples/security-demo.md").read_text().splitlines()
        self.assertEqual(evidence["text"], "\n".join(lines[evidence["start_line"]-1:evidence["end_line"]]))
        self.assertEqual(self.call("read", evidence["id"])["version"], first["version"])
        self.assertEqual(self.ingest()["status"], "unchanged")
        self.assertEqual(len(self.call("docs")), 1)
        self.assertEqual(self.call("search", "提示注入")["candidates"], found["candidates"])
        self.assertEqual(self.call("run", str(found["run_id"]))["candidates"], found["candidates"])

    def test_errors_and_no_matches(self):
        empty = Path(self.temp.name) / "empty.md"
        empty.write_text("  ")
        self.ingest(empty, ok=False)
        self.assertEqual(self.call("docs"), [])
        self.ingest()
        self.assertEqual(self.call("search", "unfindableword")["candidates"], [])
        self.call("search", " ", ok=False)
        self.call("search", "test", "--limit", "0", ok=False)
        self.call("read", "missing", ok=False)
        changed = Path(self.temp.name) / "changed.md"
        changed.write_text("changed")
        self.ingest(changed, ok=False)
        self.assertEqual(len(self.call("docs")), 1)


if __name__ == "__main__":
    unittest.main()
