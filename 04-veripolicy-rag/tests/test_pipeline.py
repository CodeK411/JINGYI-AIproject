from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from veripolicy.agent_tools import PolicyAgentTools
from veripolicy.pipeline import VeriPolicyRAG
from veripolicy.schemas import QueryContext
from veripolicy.scope import is_applicable


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rag = VeriPolicyRAG(ROOT / "data" / "corpus", abstain_threshold=0.0)

    def test_temporal_filter_selects_old_and_new_versions(self) -> None:
        old_context = QueryContext.create("国内出差饭补多少", "2024-06-01", "CN", "full_time")
        new_context = QueryContext.create("国内出差饭补多少", "2025-06-01", "CN", "full_time")
        old_hits = self.rag.retrieve(old_context, mode="full", top_k=3)
        new_hits = self.rag.retrieve(new_context, mode="full", top_k=3)
        self.assertEqual(old_hits[0].chunk.doc_id, "travel_cn_2024")
        self.assertEqual(new_hits[0].chunk.doc_id, "travel_cn_2025")
        self.assertTrue(all(is_applicable(hit.chunk, old_context) for hit in old_hits))
        self.assertTrue(all(is_applicable(hit.chunk, new_context) for hit in new_hits))

    def test_scope_filter_selects_intern_policy(self) -> None:
        context = QueryContext.create("实习生学习预算多少", "2025-06-01", "CN", "intern")
        hits = self.rag.retrieve(context, mode="full", top_k=3)
        self.assertEqual(hits[0].chunk.doc_id, "learning_intern_cn_2025")

    def test_extractive_answer_has_valid_citation(self) -> None:
        context = QueryContext.create("2025 年 P1 多久确认", "2025-04-01", "CN", "full_time")
        response = self.rag.ask(context, generator="extractive", log=False)
        self.assertTrue(response.answerable)
        self.assertTrue(response.citations)
        self.assertIn(response.citations[0], response.answer)
        self.assertIn("10 分钟", response.answer)

    def test_equal_precedence_conflict_forces_abstention(self) -> None:
        context = QueryContext.create("客户礼品上限是多少", "2025-06-01", "CN", "full_time")
        response = self.rag.ask(context, top_k=10, log=False)
        self.assertFalse(response.answerable)
        self.assertTrue(any(item.status == "unresolved" for item in response.conflicts))
        self.assertEqual(response.citations, [])

    def test_version_comparison_tool(self) -> None:
        result = PolicyAgentTools(self.rag).compare_policy_versions(
            "P1 事件确认时限", "2024-06-01", "2025-06-01", "CN", "full_time"
        )
        self.assertIn("incident.p1_ack_minutes", result["changed_rules"])

    def test_audit_log_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rag = VeriPolicyRAG(
                ROOT / "data" / "corpus",
                abstain_threshold=0.0,
                audit_db=Path(directory) / "audit.db",
            )
            context = QueryContext.create("2025 年报销期限", "2025-03-01", "CN", "full_time")
            response = rag.ask(context)
            self.assertTrue(response.trace_id)
            self.assertTrue((Path(directory) / "audit.db").exists())


if __name__ == "__main__":
    unittest.main()

