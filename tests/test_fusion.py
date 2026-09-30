"""RRF fusion: combine retrievers by rank, since their scores are not comparable.

Cosine similarity lives in [-1,1]; BM25 is unbounded and corpus-dependent. Adding
them (or weighting them) requires a calibration nobody can justify on a small
corpus. Reciprocal Rank Fusion sidesteps that: it reads only the *rank* each
retriever assigned, so a chunk both retrievers agree on rises even though their
scores were never on the same scale.

The development set makes this concrete. BM25 finds nothing for four of ten
questions (no shared term with the English corpus); the vector retriever finds
evidence for all of them. Fusion has to keep the vector hits while letting agree-
on chunks climb -- not average the two into a blend that is worse than either.
"""
import unittest

from skra.fusion import RRFSearch, RRF_K
from skra.store import Store


def store_with(rows):
    store = Store(":memory:")
    with store.db:
        store.db.execute(
            "INSERT INTO documents(id,title,source,license,acquired,hash,splitter,snapshot) "
            "VALUES ('d','T','urn:x','CC0','2026-09-10','h','heading-lines-v1:20','x')")
        for cid, text, kind in rows:
            store.db.execute(
                "INSERT INTO chunks(id,doc_id,section,start_line,end_line,text,version,active,kind,page) "
                "VALUES (?,?,?,?,?,?,?,1,?,NULL)",
                (cid, "d", "S", 1, 1, text, "h", kind))
    return store


def fixed(candidates):
    """A stand-in retriever returning a fixed ranking, purely by rank order."""
    def search(query, limit):
        return {"mode": "fixed", "query": query,
                "candidates": candidates[:limit], "elapsed_ms": 0}
    return search


class RRFFusionTest(unittest.TestCase):
    def make_store(self, rows):
        store = store_with(rows)
        self.addCleanup(store.close)
        return store

    def test_a_chunk_both_retrievers_rank_high_wins(self):
        """The point of RRF: agreement between retrievers outranks one strong vote."""
        store = self.make_store([("shared", "x", "body"), ("only_a", "x", "body"),
                            ("only_b", "x", "body")])
        a = fixed([{"id": "only_a"}, {"id": "shared"}])
        b = fixed([{"id": "only_b"}, {"id": "shared"}])
        result = RRFSearch(store, [("a", a, 1.0), ("b", b, 1.0)]).search("q", limit=5)
        self.assertEqual(result["candidates"][0]["id"], "shared",
                         "两路都排第 2 的片段应胜过只被一路排第 1 的片段")

    def test_scores_from_different_scales_never_get_added(self):
        """A huge BM25 score must not outweigh a small cosine score by magnitude.

        The two retrievers below put different chunks first with wildly different
        score magnitudes. If fusion summed scores, 'big' would dominate; by rank it
        is a tie and the deterministic id tiebreak decides.
        """
        store = self.make_store([("big", "x", "body"), ("small", "x", "body")])
        a = fixed([{"id": "big", "score": 99999.0}])
        b = fixed([{"id": "small", "score": 0.01}])
        result = RRFSearch(store, [("a", a, 1.0), ("b", b, 1.0)]).search("q", limit=5)
        ids = [c["id"] for c in result["candidates"]]
        self.assertEqual(set(ids), {"big", "small"})
        # Equal rank-1 contributions -> the tie is broken by id, not by magnitude.
        self.assertEqual(ids, sorted(ids), f"同分应由 id 决定顺序，而非分数大小：{ids}")

    def test_weights_are_recorded_and_actually_applied(self):
        store = self.make_store([("from_a", "x", "body"), ("from_b", "x", "body")])
        a = fixed([{"id": "from_a"}])
        b = fixed([{"id": "from_b"}])
        result = RRFSearch(store, [("a", a, 3.0), ("b", b, 1.0)]).search("q", limit=5)
        self.assertEqual(result["candidates"][0]["id"], "from_a")
        self.assertEqual(result["parameters"]["k"], RRF_K)
        self.assertEqual(result["parameters"]["weights"], {"a": 3.0, "b": 1.0})

    def test_a_retriever_that_finds_nothing_does_not_block_the_other(self):
        """Four of ten dev questions are BM25-empty; the vector hits must survive."""
        store = self.make_store([("vec_only", "x", "body")])
        empty = fixed([])
        vec = fixed([{"id": "vec_only"}])
        result = RRFSearch(store, [("bm25", empty, 1.0), ("vector", vec, 1.0)]).search("q", limit=5)
        self.assertEqual([c["id"] for c in result["candidates"]], ["vec_only"])

    def test_per_retriever_contributions_are_reported(self):
        """The fusion has to be reviewable: which retriever ranked what, at what rank."""
        store = self.make_store([("x1", "x", "body")])
        a = fixed([{"id": "x1"}])
        b = fixed([{"id": "x1"}])
        result = RRFSearch(store, [("a", a, 1.0), ("b", b, 1.0)]).search("q", limit=5)
        card = result["candidates"][0]
        self.assertEqual(card["contributions"], {"a": 1, "b": 1})
        self.assertAlmostEqual(card["score"], 2 * 1.0 / (RRF_K + 1), places=9)

    def test_retired_versions_never_survive_fusion(self):
        """Fusion must not resurrect a chunk a retriever should not have returned."""
        store = self.make_store([("gone", "x", "body")])
        with store.db:
            store.db.execute("UPDATE chunks SET active=0 WHERE id='gone'")
        a = fixed([{"id": "gone"}])
        with self.assertRaises(ValueError):
            RRFSearch(store, [("a", a, 1.0)]).search("q", limit=5)

    def test_the_shared_argument_guard_applies(self):
        store = self.make_store([("a", "x", "body")])
        with self.assertRaises(ValueError):
            RRFSearch(store, [("a", fixed([{"id": "a"}]), 1.0)]).search("q", 0)

    def test_the_fused_run_is_persisted_like_any_other_search(self):
        store = self.make_store([("x1", "x", "body")])
        a = fixed([{"id": "x1"}])
        result = RRFSearch(store, [("a", a, 1.0)]).search("q", limit=5)
        self.assertEqual(result["mode"], "hybrid-rrf")
        self.assertIsInstance(result["run_id"], int)
        self.assertEqual(store.run(result["run_id"])["mode"], "hybrid-rrf")


if __name__ == "__main__":
    unittest.main()
