"""Build a separate, reproducible demo database from committed OWASP excerpts."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skra.store import Store


def prepare(target):
    manifest = json.loads((ROOT / "examples/corpus/manifest.json").read_text(encoding="utf-8"))
    # Validate every file before publishing any document. Never overwrite an
    # existing database: preparation is for a fresh, independently reviewable run.
    for doc in manifest:
        path = ROOT / "examples/corpus" / doc["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != doc["sha256"]:
            raise ValueError(f"Corpus hash mismatch: {doc['file']}")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb"):
        pass
    store = Store(target)
    try:
        for doc in manifest:
            store.ingest(ROOT / "examples/corpus" / doc["file"], doc["title"],
                         doc["source"], doc["license"], doc["acquired"])
        return {"database": str(target.resolve()), "documents": len(store.documents()),
                "network_called": False, "billed_calls": 0}
    finally:
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / ".data/demo.sqlite3"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.db), ensure_ascii=False, indent=2))
