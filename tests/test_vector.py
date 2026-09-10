import tempfile
import unittest
from pathlib import Path
from skra.store import Store
from skra.vector import VectorSearch


class FixtureEncoder:
    identity = "controlled-fixture-not-real-model"
    def encode(self, texts):
        return [[1.,0.] if ("cat" in t or "猫" in t) else [0.,1.] for t in texts]


class VectorTest(unittest.TestCase):
    def test_index_search_persist_and_new_document_requires_rebuild(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            store=Store(p/'db')
            try:
                source=p/'a.md'; source.write_text('cat document')
                store.ingest(source,'cat','urn:a','CC0','2026-09-09')
                vector=VectorSearch(store,FixtureEncoder())
                with self.assertRaises(ValueError): vector.search('猫')
                vector.build()
                found=vector.search('猫')
                self.assertEqual(found['candidates'][0]['title'],'cat')
                self.assertEqual(store.run(found['run_id'])['encoder'],FixtureEncoder.identity)
                source.write_text('dog document')
                store.ingest(source,'dog','urn:b','CC0','2026-09-09')
                with self.assertRaises(ValueError): vector.search('猫')
                vector.build()
                self.assertEqual(vector.search('dog')['candidates'][0]['title'],'dog')
                changed=FixtureEncoder(); changed.identity='different-model'
                with self.assertRaises(ValueError): VectorSearch(store,changed).search('猫')
            finally: store.close()

    def test_vector_index_excludes_retired_chunks_after_update(self):
        """After a source is updated, vector search must not surface the old version."""
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            store = Store(p / 'db')
            try:
                old = p / 'a.md'; old.write_text('cat alpha guidance')
                store.ingest(old, 'doc', 'urn:x', 'CC0', '2026-09-09')
                vector = VectorSearch(store, FixtureEncoder())
                vector.build()
                self.assertTrue(vector.search('猫')['candidates'])
                new = p / 'b.md'; new.write_text('dog beta guidance')
                store.ingest(new, 'doc', 'urn:x', 'CC0', '2026-09-09')
                vector.build()
                after = vector.search('猫')['candidates']
                self.assertTrue(all('cat' not in c['text'] for c in after))
            finally:
                store.close()
