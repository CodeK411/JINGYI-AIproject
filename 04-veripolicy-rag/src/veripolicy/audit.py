from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schemas import QueryContext, RAGResponse


class AuditStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS query_audit (
                    trace_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    query TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    region TEXT NOT NULL,
                    employee_type TEXT NOT NULL,
                    answerable INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    citations_json TEXT NOT NULL,
                    conflict_json TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    mode TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    label INTEGER NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def log(self, context: QueryContext, response: RAGResponse) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO query_audit (
                    trace_id, query, as_of, region, employee_type, answerable,
                    confidence, citations_json, conflict_json, latency_ms, mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response.trace_id,
                    context.query,
                    context.as_of.isoformat(),
                    context.region,
                    context.employee_type,
                    int(response.answerable),
                    response.confidence,
                    json.dumps(response.citations, ensure_ascii=False),
                    json.dumps([conflict.__dict__ for conflict in response.conflicts], ensure_ascii=False),
                    response.latency_ms,
                    response.mode,
                ),
            )

    def add_feedback(self, trace_id: str, label: bool, comment: str = "") -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO feedback (trace_id, label, comment) VALUES (?, ?, ?)",
                (trace_id, int(label), comment),
            )

