from __future__ import annotations

import unittest
from pathlib import Path

from veripolicy.evaluation import load_eval_queries
from veripolicy.pipeline import VeriPolicyRAG
from veripolicy.schemas import QueryContext


ROOT = Path(__file__).resolve().parents[1]


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rag = VeriPolicyRAG(ROOT / "data" / "corpus")

    def test_eval_set_has_dev_test_and_hard_negatives(self) -> None:
        queries = load_eval_queries(ROOT / "data" / "eval" / "queries.jsonl")
        self.assertEqual(len(queries), 108)
        self.assertEqual({query.split for query in queries}, {"dev", "test"})
        self.assertTrue(any(not query.answerable for query in queries))
        self.assertTrue(any("temporal" in query.tags for query in queries))
        self.assertTrue(any("scope" in query.tags for query in queries))

    def test_full_pipeline_removes_stale_version(self) -> None:
        context = QueryContext.create("客户聊天记录保存多久", "2025-05-01", "CN", "full_time")
        baseline = self.rag.retrieve(context, mode="dense", top_k=10)
        full = self.rag.retrieve(context, mode="full", top_k=10)
        self.assertTrue(any(hit.chunk.doc_id == "retention_2024" for hit in baseline))
        self.assertTrue(all(hit.chunk.doc_id != "retention_2024" for hit in full))


if __name__ == "__main__":
    unittest.main()
