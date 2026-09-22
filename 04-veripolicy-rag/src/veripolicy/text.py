from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


ALIASES: dict[str, tuple[str, ...]] = {
    "年假": ("带薪休假", "annual leave", "休假天数"),
    "带薪休假": ("年假", "annual leave"),
    "饭补": ("餐补", "伙食费", "餐饮报销", "meal allowance"),
    "餐补": ("饭补", "伙食费", "餐饮报销", "meal allowance"),
    "酒店": ("住宿", "旅馆", "hotel"),
    "住宿": ("酒店", "旅馆", "hotel"),
    "打车": ("出租车", "网约车", "交通费", "taxi"),
    "报销": ("费用", "expense", "发票"),
    "远程办公": ("居家办公", "在家办公", "remote work", "WFH"),
    "事故": ("故障", "事件", "incident"),
    "响应": ("确认", "acknowledge", "ack"),
    "聊天记录": ("客户对话", "会话数据", "conversation data"),
    "学习经费": ("培训预算", "课程报销", "learning budget"),
    "离职": ("账号回收", "权限撤销", "offboarding"),
    "实习生": ("intern", "实习员工"),
    "正式员工": ("全职员工", "full time", "full-time"),
    "英国": ("GB", "UK", "United Kingdom"),
    "中国": ("CN", "China"),
}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def expand_query(text: str) -> str:
    normalized = normalize_text(text)
    additions: list[str] = []
    for phrase, aliases in ALIASES.items():
        if normalize_text(phrase) in normalized:
            additions.extend(aliases)
    if not additions:
        return normalized
    return normalized + " " + " ".join(dict.fromkeys(additions))


def tokenize(text: str, expand: bool = False) -> list[str]:
    text = expand_query(text) if expand else normalize_text(text)
    latin = re.findall(r"[a-z]+(?:[-_][a-z]+)*|\d+(?:\.\d+)?", text)
    chinese_runs = re.findall(r"[\u3400-\u9fff]+", text)
    chinese: list[str] = []
    for run in chinese_runs:
        chinese.extend(run)
        chinese.extend(run[i : i + 2] for i in range(len(run) - 1))
        if len(run) <= 8:
            chinese.append(run)
    return latin + chinese


def token_set(text: str, expand: bool = False) -> set[str]:
    return {
        token
        for token in tokenize(text, expand=expand)
        if len(token.strip()) > 1 or token.isdigit()
    }


def overlap_features(query: str, document: str) -> tuple[float, float]:
    query_tokens = token_set(query, expand=True)
    doc_tokens = token_set(document)
    if not query_tokens:
        return 0.0, 0.0
    shared = query_tokens & doc_tokens
    coverage = len(shared) / len(query_tokens)
    union = query_tokens | doc_tokens
    jaccard = len(shared) / len(union) if union else 0.0
    return coverage, jaccard


def first_sentences(text: str, limit: int = 2) -> str:
    sentences = [piece.strip() for piece in re.split(r"(?<=[。！？.!?])\s*", text) if piece.strip()]
    return "".join(sentences[:limit]) if sentences else text.strip()


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u3400-\u9fff]+", "-", text.strip().lower()).strip("-")
    return cleaned[:48] or "section"


def minmax(values: Iterable[float]) -> list[float]:
    values = [float(value) for value in values]
    if not values:
        return []
    low, high = min(values), max(values)
    if high - low < 1e-12:
        return [1.0 if high > 0 else 0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]
