from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class PolicyDocument:
    doc_id: str
    title: str
    policy_family: str
    version: str
    effective_from: date
    effective_to: date | None
    regions: tuple[str, ...]
    employee_types: tuple[str, ...]
    authority: int
    source_path: str
    body: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    heading: str
    text: str
    retrieval_text: str
    policy_family: str
    version: str
    effective_from: date
    effective_to: date | None
    regions: tuple[str, ...]
    employee_types: tuple[str, ...]
    authority: int
    rules: tuple[dict[str, Any], ...] = ()

    def citation_id(self) -> str:
        return self.chunk_id


@dataclass(frozen=True)
class QueryContext:
    query: str
    as_of: date
    region: str = "ALL"
    employee_type: str = "all"

    @classmethod
    def create(
        cls,
        query: str,
        as_of: str | date | None = None,
        region: str = "ALL",
        employee_type: str = "all",
    ) -> "QueryContext":
        parsed = date.today() if as_of is None else (
            date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
        )
        return cls(
            query=query.strip(),
            as_of=parsed,
            region=region.upper().strip() or "ALL",
            employee_type=employee_type.lower().strip() or "all",
        )


@dataclass
class SearchHit:
    chunk: Chunk
    score: float
    rank: int = 0
    signals: dict[str, float] = field(default_factory=dict)

    def to_dict(self, include_text: bool = True) -> dict[str, Any]:
        result = {
            "rank": self.rank,
            "score": round(float(self.score), 6),
            "chunk_id": self.chunk.chunk_id,
            "doc_id": self.chunk.doc_id,
            "title": self.chunk.title,
            "heading": self.chunk.heading,
            "version": self.chunk.version,
            "effective_from": self.chunk.effective_from.isoformat(),
            "effective_to": (
                self.chunk.effective_to.isoformat() if self.chunk.effective_to else None
            ),
            "regions": list(self.chunk.regions),
            "employee_types": list(self.chunk.employee_types),
            "signals": {k: round(float(v), 6) for k, v in self.signals.items()},
        }
        if include_text:
            result["text"] = self.chunk.text
        return result


@dataclass(frozen=True)
class Conflict:
    rule_key: str
    status: str
    values: tuple[str, ...]
    source_ids: tuple[str, ...]
    selected_source_id: str | None = None
    reason: str = ""


@dataclass
class RAGResponse:
    query: str
    answer: str
    answerable: bool
    confidence: float
    citations: list[str]
    hits: list[SearchHit]
    conflicts: list[Conflict] = field(default_factory=list)
    latency_ms: float = 0.0
    mode: str = "full"
    trace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "answerable": self.answerable,
            "confidence": round(float(self.confidence), 6),
            "citations": self.citations,
            "hits": [hit.to_dict() for hit in self.hits],
            "conflicts": [asdict(conflict) for conflict in self.conflicts],
            "latency_ms": round(float(self.latency_ms), 2),
            "mode": self.mode,
            "trace_id": self.trace_id,
        }


@dataclass(frozen=True)
class EvalQuery:
    query_id: str
    split: str
    query: str
    as_of: date
    region: str
    employee_type: str
    answerable: bool
    relevant_doc_ids: tuple[str, ...]
    relevant_rule_key: str | None
    expected_value: str | None
    tags: tuple[str, ...]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "EvalQuery":
        return cls(
            query_id=row["query_id"],
            split=row.get("split", "test"),
            query=row["query"],
            as_of=date.fromisoformat(row["as_of"]),
            region=row.get("region", "ALL").upper(),
            employee_type=row.get("employee_type", "all").lower(),
            answerable=bool(row.get("answerable", True)),
            relevant_doc_ids=tuple(row.get("relevant_doc_ids", [])),
            relevant_rule_key=row.get("relevant_rule_key"),
            expected_value=(str(row["expected_value"]) if row.get("expected_value") is not None else None),
            tags=tuple(row.get("tags", [])),
        )

