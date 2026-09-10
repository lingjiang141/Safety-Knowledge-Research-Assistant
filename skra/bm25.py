"""BM25 retrieval over the active chunks, with the shared retrieval rules.

Why BM25 rather than another count-based score: `Store.search` ranks a chunk by
how many query terms it contains. That ignores two things BM25 fixes -- a term
repeated ten times is not ten times as relevant, and a long chunk should not win
just for being long. Term-frequency saturation (k1) plus length normalisation (b)
make the ranking reward precision instead of size.

What it does *not* fix: BM25 matches terms, so a Chinese question that shares no
term with the English corpus retrieves nothing. That is a measured limitation, not
a defect -- four of the ten development questions are in that position
(`docs/evidence/issue08-term-mismatch-20260910.txt`). Fusion with the vector
retriever is what gives those questions a path back; BM25 alone does not.
"""
import math
import time

from .store import (BM25_B, BM25_K1, TOKEN_RE, active_chunk_ids, check_search_args,
                    record_run, search_terms)


class BM25Search:
    """Okapi BM25 over active chunks, ranked with an explicit body-precedence rule."""

    def __init__(self, store):
        self.store = store
        self.db = store.db

    def _corpus(self):
        """Active chunks with their term counts and length, ready to score."""
        docs = []
        with self.db:
            pass
        for row in self.db.execute(
                "SELECT id,text,kind FROM chunks WHERE active=1 ORDER BY id"):
            counts = {}
            for token in TOKEN_RE.findall(row["text"].lower()):
                counts[token] = counts.get(token, 0) + 1
            docs.append({"id": row["id"], "kind": row["kind"],
                         "counts": counts, "length": sum(counts.values()) or 1})
        return docs

    def search(self, query, limit=5):
        check_search_args(query, limit)
        started = time.perf_counter()
        terms, expanded = search_terms(query)
        wanted = [t for t in dict.fromkeys(terms)]
        docs = self._corpus()
        total = len(docs)
        average = (sum(d["length"] for d in docs) / total) if total else 0.0
        # Document frequency over the active corpus, so retired chunks cannot
        # skew IDF either.
        frequency = {}
        for term in wanted:
            frequency[term] = sum(1 for d in docs if term in d["counts"])

        ranked = []
        for doc in docs:
            score = 0.0
            for term in wanted:
                tf = doc["counts"].get(term, 0)
                if not tf:
                    continue
                df = frequency[term]
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                norm = 1 - BM25_B + BM25_B * (doc["length"] / (average or 1))
                score += idf * (tf * (BM25_K1 + 1)) / (tf + BM25_K1 * norm)
            if score > 0:
                # Body first, then score, then id. The body flag leads the sort key
                # on purpose: a provenance line must not take a body slot even when
                # it scores higher, which is the rule `store.search` already
                # enforces. `vector.search` does not have this rule, and the fusion
                # layer is told so rather than left to assume symmetry.
                ranked.append((doc["kind"] != "body", -score, doc["id"], score))
        ranked.sort()

        candidates = [{**self.store.read(cid), "score": round(score, 6)}
                      for _, _, cid, score in ranked[:limit]]
        elapsed = (time.perf_counter() - started) * 1000
        result = {"mode": "bm25", "query": query, "expanded_query": expanded,
                  "terms": wanted, "parameters": {"k1": BM25_K1, "b": BM25_B},
                  "corpus_size": total, "average_length": round(average, 3),
                  "body_precedence": True, "candidates": candidates,
                  "elapsed_ms": elapsed,
                  "note": "关键词匹配；中文问题若与英文原文无共同词项，将如实返回空候选。"}
        result["run_id"] = record_run(self.db, query, result, elapsed)
        return result
