from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .schemas import Chunk, PolicyDocument
from .text import slugify


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)
RULE_RE = re.compile(r"<!--\s*rule:\s*(\{.*?\})\s*-->", re.DOTALL)


class DocumentFormatError(ValueError):
    pass


def _parse_date(value: Any, field_name: str) -> date | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise DocumentFormatError(f"{field_name} must use YYYY-MM-DD, got {value!r}") from exc


def _as_tuple(value: Any, default: str) -> tuple[str, ...]:
    if value is None:
        return (default,)
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def parse_document(path: str | Path) -> PolicyDocument:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise DocumentFormatError(f"{path}: missing YAML front matter")
    metadata = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    required = ["doc_id", "title", "policy_family", "version", "effective_from"]
    missing = [field for field in required if metadata.get(field) in (None, "")]
    if missing:
        raise DocumentFormatError(f"{path}: missing fields {', '.join(missing)}")
    return PolicyDocument(
        doc_id=str(metadata["doc_id"]),
        title=str(metadata["title"]),
        policy_family=str(metadata["policy_family"]),
        version=str(metadata["version"]),
        effective_from=_parse_date(metadata["effective_from"], "effective_from"),  # type: ignore[arg-type]
        effective_to=_parse_date(metadata.get("effective_to"), "effective_to"),
        regions=tuple(item.upper() for item in _as_tuple(metadata.get("regions"), "ALL")),
        employee_types=tuple(
            item.lower() for item in _as_tuple(metadata.get("employee_types"), "all")
        ),
        authority=int(metadata.get("authority", 50)),
        source_path=str(path),
        body=body,
    )


def _extract_rules(text: str) -> tuple[dict[str, Any], ...]:
    rules: list[dict[str, Any]] = []
    for raw_rule in RULE_RE.findall(text):
        try:
            rule = json.loads(raw_rule)
        except json.JSONDecodeError as exc:
            raise DocumentFormatError(f"Invalid rule JSON: {raw_rule}") from exc
        if "key" not in rule or "value" not in rule:
            raise DocumentFormatError(f"Rule requires key and value: {raw_rule}")
        rule["value"] = str(rule["value"])
        rules.append(rule)
    return tuple(rules)


def _strip_rules(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", RULE_RE.sub("", text)).strip()


def _sections(body: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        return [("正文", body)]
    sections: list[tuple[str, str]] = []
    heading_stack: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, title))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if content:
            path = " > ".join(item[1] for item in heading_stack)
            sections.append((path, content))
    return sections


def _split_long_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current.strip())
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = (tail + "\n\n" + paragraph).strip()
        else:
            current = (current + "\n\n" + paragraph).strip()
    if current:
        chunks.append(current)
    return chunks


def chunk_document(
    document: PolicyDocument,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen_ids: set[str] = set()
    for heading, raw_content in _sections(document.body):
        rules = _extract_rules(raw_content)
        content = _strip_rules(raw_content)
        for part_number, part in enumerate(_split_long_text(content, max_chars, overlap_chars), start=1):
            base_id = f"{document.doc_id}::{slugify(heading)}"
            chunk_id = base_id if part_number == 1 else f"{base_id}::p{part_number}"
            if chunk_id in seen_ids:
                chunk_id = f"{chunk_id}-{len(seen_ids)}"
            seen_ids.add(chunk_id)
            rule_terms = " ".join(
                " ".join(
                    [
                        str(rule.get("key", "")),
                        str(rule.get("label", "")),
                        str(rule.get("statement", "")),
                        " ".join(str(alias) for alias in rule.get("aliases", [])),
                    ]
                )
                for rule in rules
            )
            retrieval_text = (
                f"{document.title}\n章节：{heading}\n适用地区：{' '.join(document.regions)}\n"
                f"适用人员：{' '.join(document.employee_types)}\n规则术语：{rule_terms}\n{part}"
            )
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=document.doc_id,
                    title=document.title,
                    heading=heading,
                    text=part,
                    retrieval_text=retrieval_text,
                    policy_family=document.policy_family,
                    version=document.version,
                    effective_from=document.effective_from,
                    effective_to=document.effective_to,
                    regions=document.regions,
                    employee_types=document.employee_types,
                    authority=document.authority,
                    rules=rules,
                )
            )
    return chunks


def load_corpus(
    corpus_dir: str | Path,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[Chunk]:
    corpus_dir = Path(corpus_dir)
    paths = sorted([*corpus_dir.rglob("*.md"), *corpus_dir.rglob("*.markdown")])
    if not paths:
        raise FileNotFoundError(f"No Markdown policy files found under {corpus_dir}")
    chunks: list[Chunk] = []
    doc_ids: set[str] = set()
    for path in paths:
        document = parse_document(path)
        if document.doc_id in doc_ids:
            raise DocumentFormatError(f"Duplicate doc_id: {document.doc_id}")
        doc_ids.add(document.doc_id)
        chunks.extend(chunk_document(document, max_chars=max_chars, overlap_chars=overlap_chars))
    return chunks
