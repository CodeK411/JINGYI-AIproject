from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Literal

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - exercised only without API extras
    raise RuntimeError("Install the API dependencies with: pip install -e '.[api]'") from exc

from .agent_tools import TOOL_SCHEMAS
from .pipeline import VeriPolicyRAG
from .schemas import QueryContext


class AskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    as_of: str
    region: str = "ALL"
    employee_type: str = "all"
    mode: Literal["dense", "hybrid", "hybrid_temporal", "full"] = "full"
    generator: Literal["extractive", "llm"] = "extractive"
    top_k: int = Field(default=5, ge=1, le=20)


class FeedbackRequest(BaseModel):
    trace_id: str
    helpful: bool
    comment: str = Field(default="", max_length=2000)


@lru_cache(maxsize=1)
def get_rag() -> VeriPolicyRAG:
    return VeriPolicyRAG.from_env()


app = FastAPI(
    title="VeriPolicy-RAG API",
    version="0.1.0",
    description="Version-, scope-, authority- and conflict-aware enterprise policy RAG.",
)


@app.get("/health")
def health() -> dict[str, Any]:
    rag = get_rag()
    return {"status": "ok", "chunks": len(rag.chunks), "corpus": str(rag.corpus_dir)}


@app.get("/v1/tools")
def tools() -> dict[str, Any]:
    return {"tools": TOOL_SCHEMAS}


@app.post("/v1/search")
def search(request: AskRequest) -> dict[str, Any]:
    try:
        context = QueryContext.create(
            request.query, request.as_of, request.region, request.employee_type
        )
        hits = get_rag().retrieve(context, mode=request.mode, top_k=request.top_k)
        return {"query": request.query, "hits": [hit.to_dict() for hit in hits]}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    try:
        context = QueryContext.create(
            request.query, request.as_of, request.region, request.employee_type
        )
        response = get_rag().ask(
            context,
            mode=request.mode,
            top_k=request.top_k,
            generator=request.generator,
        )
        return response.to_dict()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/feedback")
def feedback(request: FeedbackRequest) -> dict[str, str]:
    rag = get_rag()
    if rag.audit is None:
        raise HTTPException(status_code=503, detail="AUDIT_DB is not configured")
    rag.audit.add_feedback(request.trace_id, request.helpful, request.comment)
    return {"status": "recorded"}


def run() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "veripolicy.api:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )

