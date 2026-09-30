"""BM25 retrieval: term-frequency saturation and length normalisation.

The keyword prototype scores a chunk by how many query terms it contains, so a
long chunk repeating one term can outrank a short, precise one. BM25 fixes both
halves of that: term frequency saturates (the 10th occurrence adds little) and
length normalisation stops long chunks from winning on size alone.

The rules every retriever shares -- argument guard, active-version filter, run
persistence -- come from skra.store, not from a copy kept here.
"""
import unittest

from skra.store import Store, BM25_K1, BM25_B
from skra.bm25 import BM25Search


def store_with(rows):
    """An in-memory store holding (id, text, kind) body/metadata chunks."""
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


class BM25SearchTest(unittest.TestCase):
    def make_store(self, rows):
        store = store_with(rows)
        self.addCleanup(store.close)
        return store

    def test_term_frequency_saturates_instead_of_scaling_linearly(self):
        """The 10th repeat must add far less than the 1st; a count-based score would not.

        Both chunks carry the query terms, but one repeats them. Under BM25 the
        padded chunk's gain over a 1-occurrence chunk is small (saturation), while
        a linear count would make it ten times as large. The assertion pins that
        *ratio*, not a winner: with only two chunks in the corpus IDF is near zero
        for both terms, so which chunk wins is not the point -- how much the
        repeats are worth is.
        """
        store = self.make_store([
            ("once", "least privilege", "body"),
            ("ten", "least privilege " * 10, "body"),
        ])
        result = BM25Search(store).search("least privilege", limit=5)
        scores = {c["id"]: c["score"] for c in result["candidates"]}
        once, ten = scores["once"], scores["ten"]
        self.assertGreater(once, 0)
        # Linear scoring would give ten == 10 * once. Saturation keeps it well under.
        self.assertLess(ten, 10 * once,
                        f"词频未饱和：once={once} ten={ten}")
        self.assertLess(ten / once, 3,
                        f"重复词的边际收益过高，接近线性：{ten / once:.2f}×")

    def test_a_short_precise_chunk_beats_a_long_diluted_one_at_the_same_frequency(self):
        """Length normalisation: equal term frequency, but the long chunk is diluted.

        Same terms in both, same counts -- the difference is how much unrelated
        text surrounds them. BM25's b term must rank the focused chunk first.
        """
        store = self.make_store([
            ("diluted", "least privilege " + "filler " * 60, "body"),
            ("focused", "least privilege limits what an agent may do.", "body"),
        ])
        result = BM25Search(store).search("least privilege", limit=5)
        ids = [c["id"] for c in result["candidates"]]
        self.assertEqual(ids[0], "focused", f"长而稀释的块不该排第一：{ids}")

    def test_retired_versions_are_never_returned(self):
        """The active filter is shared with every other retriever (Issue 06)."""
        store = self.make_store([("old", "prompt injection retired copy", "body")])
        with store.db:
            store.db.execute("UPDATE chunks SET active=0 WHERE id='old'")
        result = BM25Search(store).search("prompt injection", limit=5)
        self.assertEqual(result["candidates"], [])

    def test_the_shared_argument_guard_applies(self):
        store = self.make_store([("a", "prompt injection", "body")])
        for bad in (0, 21):
            with self.subTest(limit=bad):
                with self.assertRaises(ValueError):
                    BM25Search(store).search("prompt injection", bad)
        with self.assertRaises(ValueError):
            BM25Search(store).search("   ", 5)

    def test_the_result_is_reviewable_and_persisted_like_the_other_retrievers(self):
        """Fusion needs one candidate shape across retrievers, and a stored run."""
        store = self.make_store([("a", "prompt injection is a real risk", "body")])
        result = BM25Search(store).search("prompt injection", limit=5)
        self.assertEqual(result["mode"], "bm25")
        self.assertEqual(result["parameters"]["k1"], BM25_K1)
        self.assertEqual(result["parameters"]["b"], BM25_B)
        self.assertIn("prompt", result["terms"])
        self.assertIsInstance(result["run_id"], int)
        stored = store.run(result["run_id"])
        self.assertEqual(stored["mode"], "bm25")

    def test_body_evidence_is_not_displaced_by_metadata(self):
        """BM25 states its own precedence rule rather than inheriting one silently.

        `vector.search` ranks purely by score; `store.search` prefers body chunks.
        BM25 follows the keyword path (body first) and says so in the report, so a
        fusion layer can see the difference instead of guessing.
        """
        store = self.make_store([
            ("meta", "Least Privilege License: least privilege least privilege", "metadata"),
            ("body", "least privilege limits what an agent may do.", "body"),
        ])
        result = BM25Search(store).search("least privilege", limit=5)
        ids = [c["id"] for c in result["candidates"]]
        self.assertEqual(ids[0], "body", f"正文片段不该被出处样板挤掉：{ids}")
        self.assertTrue(result["body_precedence"])

    def test_a_query_with_no_shared_term_returns_nothing_rather_than_noise(self):
        """A Chinese query with no English term and no alias must not fabricate hits.

        Four of ten development questions are in this position (see
        docs/evidence/issue08-term-mismatch-20260910.txt); BM25 has to report the
        miss honestly instead of returning arbitrary chunks.
        """
        store = self.make_store([("a", "least privilege limits what an agent may do.", "body")])
        result = BM25Search(store).search("为什么不能只让模型自己判断？", limit=5)
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
