"""Reciprocal Rank Fusion over several retrievers.

Cosine similarity is in [0,1]; BM25 is unbounded. To add them you would have to
calibrate one scale against the other, and on a corpus of three documents there is
nothing to calibrate with -- any weight would be fitted to ten questions. RRF
avoids the question entirely by reading only the rank each retriever assigned:

    score(chunk) = sum over retrievers of  weight_r / (K + rank_r(chunk))

A chunk that two retrievers both rank highly climbs; a chunk only one retriever
likes still appears, just lower. Nothing is discarded, and the report says which
retriever contributed which rank, so the fusion can be audited.

Deliberately *not* done here: normalising the retrievers' scores, learning weights,
or dropping weak retrievers. Each is a change that would need its own evidence, and
this task is scoped to whether fusion helps at all.
"""
import time

from .store import RRF_K, active_chunk_ids, check_search_args, record_run


class RRFSearch:
    """Fuse any retrievers that expose `search(query, limit) -> {candidates: [...]}`."""

    def __init__(self, store, retrievers):
        """`retrievers` is a list of (name, callable, weight) in priority order."""
        self.store = store
        self.retrievers = [(name, fn, float(weight)) for name, fn, weight in retrievers]

    def search(self, query, limit=5, pool=None):
        check_search_args(query, limit)
        started = time.perf_counter()
        # Each retriever is asked for a pool at least as deep as the final cut, so
        # a chunk ranked just outside the top `limit` by one retriever can still be
        # promoted by agreement across the others.
        depth = pool or max(limit, 10)
        active = active_chunk_ids(self.store.db)

        scores = {}
        contributions = {}
        modes = {}
        for name, retrieve, weight in self.retrievers:
            result = retrieve(query, depth)
            modes[name] = result.get("mode", "unknown")
            for rank, candidate in enumerate(result["candidates"], start=1):
                cid = candidate["id"]
                if cid not in active:
                    # A retriever should never hand back a retired chunk; refuse to
                    # fuse one rather than let fusion resurrect it (Issue 06).
                    raise ValueError(
                        f"{name} 返回了已失效片段 {cid}；融合拒绝使用无效版本。")
                scores[cid] = scores.get(cid, 0.0) + weight / (RRF_K + rank)
                contributions.setdefault(cid, {})[name] = rank

        ranking = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        candidates = []
        for cid, score in ranking[:limit]:
            candidates.append({**self.store.read(cid), "score": round(score, 9),
                               "contributions": contributions[cid]})
        elapsed = (time.perf_counter() - started) * 1000
        result = {
            "mode": "hybrid-rrf", "query": query, "limit": limit, "pool": depth,
            "parameters": {"k": RRF_K,
                           "weights": {name: weight for name, _, weight in self.retrievers},
                           "sources": {name: modes[name] for name, _, _ in self.retrievers}},
            "candidates": candidates, "elapsed_ms": elapsed,
            "note": ("按排名融合，不合并不同尺度的分数；候选卡片的 contributions 显示每路给出的名次。"
                     "未做分数归一化或权重学习——那需要各自的证据。"),
        }
        result["run_id"] = record_run(self.store.db, query, result, elapsed)
        return result
