"""Local multilingual embeddings and exact cosine search for a small corpus."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .store import active_chunk_ids, check_search_args, digest, record_run

MODEL_DIR = Path(__file__).resolve().parents[1] / ".data/models/minilm"


class Encoder:
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ValueError("请使用已安装向量依赖的 .venv Python。") from None
        if not (MODEL_DIR / "provenance.json").exists():
            raise ValueError("本地模型未准备好；先运行 scripts/setup_vector.py。")
        self.manifest = json.loads((MODEL_DIR / "provenance.json").read_text())
        self.identity = json.dumps(self.manifest, sort_keys=True)
        # transformers 4.57.6 misidentifies re-saved non-Mistral configs as Mistral.
        # This is BERT/MiniLM; do not apply a Mistral-specific tokenizer mutation.
        self.model = SentenceTransformer(str(MODEL_DIR), device="cpu", local_files_only=True,
                                         tokenizer_kwargs={"fix_mistral_regex": False})

    def encode(self, texts):
        import numpy as np
        result = []
        for text in texts:
            ids = self.model.tokenizer.encode(text, add_special_tokens=False)
            # Avoid silently truncating the original 20-line chunks at 128 tokens.
            windows = [self.model.tokenizer.decode(ids[i:i+100]) for i in range(0, len(ids), 100)] or [""]
            vectors = self.model.encode(windows, normalize_embeddings=True, show_progress_bar=False)
            pooled = np.mean(vectors, axis=0)
            pooled /= max(float(np.linalg.norm(pooled)), 1e-12)
            result.append(pooled.tolist())
        return result


class VectorSearch:
    def __init__(self, store, encoder=None):
        self.store = store
        self.encoder = encoder or Encoder()
        self.db = store.db
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS vector_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, embedding TEXT);
        ''')

    def corpus(self):
        # Only the current, active version of each source is indexed; retired chunks
        # must never re-enter an answer (Issue 06).
        rows = self.db.execute("SELECT id,text FROM chunks WHERE active=1 ORDER BY id").fetchall()
        fingerprint = digest(json.dumps([(r["id"], digest(r["text"])) for r in rows]))
        return rows, fingerprint

    def build(self):
        started = time.perf_counter()
        rows, fingerprint = self.corpus()
        if not rows:
            raise ValueError("资料库为空，先导入资料。")
        vectors = self.encoder.encode([r["text"] for r in rows])
        with self.db:
            self.db.execute("DELETE FROM vectors")
            self.db.executemany("INSERT INTO vectors VALUES (?,?)",
                [(r["id"], json.dumps(v)) for r, v in zip(rows, vectors, strict=True)])
            self.db.executemany("INSERT OR REPLACE INTO vector_meta VALUES (?,?)",
                [("corpus", fingerprint), ("encoder", self.encoder.identity)])
        return {"chunks": len(rows), "corpus": fingerprint, "encoder": self.encoder.identity,
                "elapsed_ms": (time.perf_counter()-started)*1000}

    def search(self, query, limit=5):
        check_search_args(query, limit)
        started = time.perf_counter()
        _, fingerprint = self.corpus()
        meta = dict(self.db.execute("SELECT key,value FROM vector_meta").fetchall())
        if meta.get("corpus") != fingerprint or meta.get("encoder") != self.encoder.identity:
            raise ValueError("向量索引缺失或资料/模型已变化，请先运行 index 重建。")
        q = self.encoder.encode([query])[0]
        active = active_chunk_ids(self.db)
        ranking = []
        for r in self.db.execute("SELECT id,embedding FROM vectors"):
            if r["id"] not in active:
                continue
            score = sum(a*b for a,b in zip(q,json.loads(r["embedding"]),strict=True))
            ranking.append((score,r["id"]))
        ranking.sort(key=lambda r: (-r[0],r[1]))
        result = {"mode": "vector", "query": query, "corpus": fingerprint,
                  "encoder": self.encoder.identity, "metric": "cosine", "limit": limit,
                  "candidates": [{**self.store.read(cid), "score": score} for score,cid in ranking[:limit]],
                  "elapsed_ms": (time.perf_counter()-started)*1000,
                  "note": "纯向量基线，无关键词扩展；相似度不等于答案有依据。"}
        result["run_id"] = record_run(self.db, query, result, result["elapsed_ms"])
        return result
