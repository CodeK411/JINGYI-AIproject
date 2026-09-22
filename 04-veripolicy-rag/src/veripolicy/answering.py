from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Sequence

from .schemas import QueryContext, SearchHit
from .text import first_sentences, token_set


CITATION_RE = re.compile(r"\[([^\[\]]+::[^\[\]]+)\]")


def relevant_rule_keys(query: str, hits: Sequence[SearchHit]) -> list[str]:
    query_tokens = token_set(query, expand=True)
    scored: list[tuple[float, str]] = []
    for hit in hits:
        for rule in hit.chunk.rules:
            key = str(rule["key"])
            label = str(rule.get("label", key))
            aliases = " ".join(str(item) for item in rule.get("aliases", []))
            rule_tokens = token_set(f"{key} {label} {aliases}", expand=True)
            overlap = len(query_tokens & rule_tokens) / max(len(query_tokens), 1)
            scored.append((overlap, key))
    scored.sort(reverse=True)
    if not scored or scored[0][0] <= 0:
        return []
    best = scored[0][0]
    return list(dict.fromkeys(key for score, key in scored if score >= best * 0.8))


class ExtractiveAnswerer:
    def answer(
        self,
        context: QueryContext,
        hits: Sequence[SearchHit],
        resolved_rules: dict[str, tuple[str, str]],
    ) -> tuple[str, list[str]]:
        if not hits:
            return "现有制度中没有找到足够证据，建议补充问题或转人工确认。", []
        keys = relevant_rule_keys(context.query, hits)
        for key in keys:
            if key not in resolved_rules:
                continue
            value, source_id = resolved_rules[key]
            for hit in hits:
                if hit.chunk.chunk_id != source_id:
                    continue
                for rule in hit.chunk.rules:
                    if str(rule["key"]) == key:
                        statement = str(rule.get("statement") or f"适用值为 {value}")
                        return f"{statement} [{source_id}]", [source_id]
        top = hits[0]
        excerpt = first_sentences(top.chunk.text, limit=2)
        return f"{excerpt} [{top.chunk.chunk_id}]", [top.chunk.chunk_id]


class OpenAICompatibleAnswerer:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "")
        self.timeout = timeout
        if not self.api_key or not self.model:
            raise ValueError("LLM_API_KEY and LLM_MODEL are required for LLM generation")

    def answer(
        self,
        context: QueryContext,
        hits: Sequence[SearchHit],
        resolved_rules: dict[str, tuple[str, str]],
    ) -> tuple[str, list[str]]:
        evidence = []
        for hit in hits:
            evidence.append(
                {
                    "citation_id": hit.chunk.chunk_id,
                    "title": hit.chunk.title,
                    "version": hit.chunk.version,
                    "effective_from": hit.chunk.effective_from.isoformat(),
                    "text": hit.chunk.text,
                }
            )
        system = (
            "你是企业制度问答助手。只能使用给定证据回答。每个事实句末尾必须添加原样引用，"
            "格式为 [citation_id]。证据不足时只回答‘证据不足，需人工确认’。不要使用常识补全。"
        )
        user = json.dumps(
            {
                "question": context.query,
                "as_of": context.as_of.isoformat(),
                "region": context.region,
                "employee_type": context.employee_type,
                "resolved_rules": resolved_rules,
                "evidence": evidence,
            },
            ensure_ascii=False,
        )
        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        answer = str(body["choices"][0]["message"]["content"]).strip()
        allowed = {hit.chunk.chunk_id for hit in hits}
        citations = [citation for citation in CITATION_RE.findall(answer) if citation in allowed]
        invalid = [citation for citation in CITATION_RE.findall(answer) if citation not in allowed]
        if invalid or not citations:
            return "生成结果未通过引用校验，需人工确认。", []
        return answer, list(dict.fromkeys(citations))

