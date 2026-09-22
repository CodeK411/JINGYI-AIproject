from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from typing import Any


ALLOWED_TOOLS = {"search_policy", "compare_policy_versions"}
from .agent_tools import TOOL_SCHEMAS, PolicyAgentTools
from .config import load_env_file
from .pipeline import VeriPolicyRAG


SYSTEM_PROMPT = """你是企业制度问答助手。今天是 {today}。
你可以调用工具检索制度。调用 search_policy 时，如果用户没有说日期，就用今天。
只能根据工具返回的证据回答，每个结论后面必须附带 [citation_id]。
证据不足或存在未解决冲突时，直接说明需要人工确认，不要用常识补全。"""


def _call_llm(messages: list[dict], tools: list[dict]) -> dict:
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "")
    if not api_key or not model:
        raise RuntimeError("请先在 .env 里配置 LLM_API_KEY 和 LLM_MODEL")

    url = f"{base_url}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"请求地址: {url}\n模型: {model}\n返回 {exc.code}:\n{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接 {url} —— {exc}") from exc
    return body["choices"][0]["message"]


def run_agent(
    question: str,
    corpus_dir: str = "data/corpus",
    max_turns: int = 6,
    verbose: bool = True,
) -> str:
    load_env_file()
    rag = VeriPolicyRAG(corpus_dir=corpus_dir)
    toolbox = PolicyAgentTools(rag)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().isoformat())},
        {"role": "user", "content": question},
    ]

    for turn in range(1, max_turns + 1):
        reply = _call_llm(messages, TOOL_SCHEMAS)
        messages.append(reply)

        tool_calls = reply.get("tool_calls")
        if not tool_calls:
            return reply.get("content") or "(模型没有给出回答)"

        for call in tool_calls:
            name = call["function"]["name"]
            raw_arguments = call["function"]["arguments"]

            if name not in ALLOWED_TOOLS:
                result: Any = {"error": f"unknown tool: {name}"}
            else:
                try:
                    arguments = json.loads(raw_arguments)
                    result = getattr(toolbox, name)(**arguments)
                except Exception as exc:
                    result = {"error": f"{type(exc).__name__}: {exc}"}

            if verbose:
                print(f"[第{turn}轮] 调用 {name} 参数={raw_arguments}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    return "达到最大轮数仍未得到最终答案，建议转人工确认。"
