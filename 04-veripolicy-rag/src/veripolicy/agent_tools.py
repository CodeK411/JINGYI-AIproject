from __future__ import annotations

from collections import defaultdict
from typing import Any

from .pipeline import VeriPolicyRAG
from .schemas import QueryContext


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "按日期、地区和员工类型检索当时有效的企业制度，返回带引用的证据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户的原始问题，保持完整自然语言，不要拆成关键词罗列。"},
                    "as_of": {"type": "string", "description": "查询基准日期 YYYY-MM-DD。用户问某一年时用该年年中，例如问 2025 年就传 2025-06-01。"},
                    "region": {"type": "string", "enum": ["CN", "GB", "ALL"], "description": "提问者所在地区。CN=中国，GB=英国。注意 ALL 不是不限地区，它表示只检索全球通用制度、排除所有地区专属条款。中文提问且用户未说明地区时传 CN。"},
                    "employee_type": {"type": "string", "enum": ["full_time", "intern", "contractor", "secure_role", "all"], "description": "提问者的员工类型，必须使用英文枚举值，禁止传中文。full_time=正式员工，intern=实习生，contractor=外包合同工，secure_role=涉密岗位。注意 all 不是不限人群，它表示只检索标注为全员适用的制度、排除所有针对特定人群的条款。用户未说明身份时传 full_time。"},
                },
                "required": ["query", "as_of", "region", "employee_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_policy_versions",
            "description": "比较同一制度在两个不同日期的有效规则差异，用于回答制度有什么变化这类问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户的原始问题，保持完整自然语言。"},
                    "date_a": {"type": "string", "description": "较早的基准日期 YYYY-MM-DD。"},
                    "date_b": {"type": "string", "description": "较晚的基准日期 YYYY-MM-DD。"},
                    "region": {"type": "string", "enum": ["CN", "GB", "ALL"], "description": "提问者所在地区。CN=中国，GB=英国。注意 ALL 不是不限地区，它表示只检索全球通用制度。中文提问且用户未说明地区时传 CN。"},
                    "employee_type": {"type": "string", "enum": ["full_time", "intern", "contractor", "secure_role", "all"], "description": "提问者的员工类型，必须使用英文枚举值，禁止传中文。注意 all 不是不限人群。用户未说明身份时传 full_time。"},
                },
                "required": ["query", "date_a", "date_b", "region", "employee_type"],
            },
        },
    },
]


class PolicyAgentTools:
    def __init__(self, rag: VeriPolicyRAG) -> None:
        self.rag = rag

    def search_policy(self, query, as_of, region="ALL", employee_type="all"):
        context = QueryContext.create(query, as_of, region, employee_type)
        response = self.rag.ask(context, mode="full")
        result = response.to_dict()
        # 把结构化规则补回证据里，供大模型引用具体数值
        for hit_dict, hit in zip(result["hits"], response.hits):
            hit_dict["rules"] = [dict(rule) for rule in hit.chunk.rules]
        return result

    def compare_policy_versions(
        self,
        query: str,
        date_a: str,
        date_b: str,
        region: str = "ALL",
        employee_type: str = "all",
    ) -> dict[str, Any]:
        before = self.rag.retrieve(
            QueryContext.create(query, date_a, region, employee_type), mode="full", top_k=5
        )
        after = self.rag.retrieve(
            QueryContext.create(query, date_b, region, employee_type), mode="full", top_k=5
        )

        def collect(hits: list[Any]) -> dict[str, list[dict[str, str]]]:
            rules: dict[str, list[dict[str, str]]] = defaultdict(list)
            for hit in hits:
                for rule in hit.chunk.rules:
                    rules[str(rule["key"])].append(
                        {
                            "value": str(rule["value"]),
                            "citation_id": hit.chunk.chunk_id,
                            "statement": str(rule.get("statement", "")),
                        }
                    )
            return dict(rules)

        rules_a, rules_b = collect(before), collect(after)
        changed = {
            key: {"before": rules_a.get(key, []), "after": rules_b.get(key, [])}
            for key in sorted(set(rules_a) | set(rules_b))
            if rules_a.get(key) != rules_b.get(key)
        }
        return {
            "query": query,
            "date_a": date_a,
            "date_b": date_b,
            "changed_rules": changed,
            "evidence_a": [hit.to_dict() for hit in before],
            "evidence_b": [hit.to_dict() for hit in after],
        }

