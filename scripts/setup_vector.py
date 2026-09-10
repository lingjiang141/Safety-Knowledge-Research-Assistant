"""Download a revision-pinned model once; all subsequent retrieval is offline."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from huggingface_hub import HfApi
from sentence_transformers import SentenceTransformer
from skra.vector import MODEL_DIR

name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
revision = HfApi().model_info(name).sha
model = SentenceTransformer(name, revision=revision, device="cpu",
                            cache_folder=str(MODEL_DIR.parent / "cache"), trust_remote_code=False)
model.save(str(MODEL_DIR))
(MODEL_DIR / "provenance.json").write_text(json.dumps({"model":name,"revision":revision,
    "pooling":"mean-of-normalized-100-token-windows-v1", "dimension":384,
    "license":"Apache-2.0"},indent=2),encoding="utf-8")
print("Saved", MODEL_DIR, revision)
