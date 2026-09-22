from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Literal

from .answering import ExtractiveAnswerer, OpenAICompatibleAnswerer, relevant_rule_keys
from .audit import AuditStore
from .config import load_env_file
from .confidence import retrieval_confidence
from .conflicts import detect_conflicts
from .ingest import load_corpus
from .rerank import CrossEncoderReranker, FeatureReranker
from .retrieval import RetrievalIndex
from .schemas import QueryContext, RAGResponse, SearchHit
from .scope import is_applicable


PipelineMode = Literal["dense", "hybrid", "hybrid_temporal", "full"]


class VeriPolicyRAG:
    def __init__(
        self,
        corpus_dir: str | Path,
        dense_backend: str = "lsa",
        embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
        reranker_backend: str = "heuristic",
        reranker_model: str = "Qwen/Qwen3-Reranker-0.6B",
        abstain_threshold: float = 0.46,
        audit_db: str | Path | None = None,
    ) -> None:
        self.corpus_dir = Path(corpus_dir)
        self.chunks = load_corpus(self.corpus_dir)
        self.index = RetrievalIndex(
            self.chunks,
            dense_backend=dense_backend,
            embedding_model=embedding_model,
        )
        if reranker_backend == "cross-encoder":
            self.reranker = CrossEncoderReranker(reranker_model)
        elif reranker_backend == "heuristic":
            self.reranker = FeatureReranker()
        else:
            raise ValueError(f"Unsupported reranker backend: {reranker_backend}")
        self.abstain_threshold = float(abstain_threshold)
        self.audit = AuditStore(audit_db) if audit_db else None

    @classmethod
    def from_env(cls) -> "VeriPolicyRAG":
        load_env_file()
        return cls(
            corpus_dir=os.getenv("CORPUS_DIR", "data/corpus"),
            dense_backend=os.getenv("DENSE_BACKEND", "lsa"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B"),
            reranker_backend=os.getenv("RERANKER_BACKEND", "heuristic"),
            reranker_model=os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-0.6B"),
            abstain_threshold=float(os.getenv("ABSTAIN_THRESHOLD", "0.44")),
            audit_db=os.getenv("AUDIT_DB") or None,
        )

    def retrieve(
        self,
        context: QueryContext,
        mode: PipelineMode = "full",
        top_k: int = 5,
        candidate_k: int = 25,
    ) -> list[SearchHit]:
        use_filter = mode in {"hybrid_temporal", "full"}
        allowed = (
            [index for index, chunk in enumerate(self.chunks) if is_applicable(chunk, context)]
            if use_filter
            else None
        )
        retrieval_mode = "dense" if mode == "dense" else "hybrid"
        hits = self.index.search(
            context.query,
            allowed_indices=allowed,
            top_k=max(top_k, candidate_k if mode == "full" else top_k),
            mode=retrieval_mode,
        )
        if mode == "full":
            hits = self.reranker.rerank(context, hits, top_k=top_k)
        else:
            hits = hits[:top_k]
            for rank, hit in enumerate(hits, start=1):
                hit.rank = rank
        return hits

    def ask(
        self,
        context: QueryContext,
        mode: PipelineMode = "full",
        top_k: int = 5,
        generator: str = "extractive",
        log: bool = True,
    ) -> RAGResponse:
        started = time.perf_counter()
        trace_id = uuid.uuid4().hex
        hits = self.retrieve(context=context, mode=mode, top_k=top_k)
        conflicts, resolved = detect_conflicts(hits, context)
        confidence = retrieval_confidence(hits)
        relevant_keys = relevant_rule_keys(context.query, hits)
        unresolved_for_query = any(
            conflict.status == "unresolved"
            and (not relevant_keys or conflict.rule_key in relevant_keys)
            for conflict in conflicts
        )
        answerable = bool(hits) and confidence >= self.abstain_threshold and not unresolved_for_query
        if not answerable:
            if unresolved_for_query:
                answer = "检测到同等优先级的有效制度存在冲突，系统已停止作答并建议人工确认。"
            else:
                answer = "现有制度中没有找到置信度足够的证据，建议补充问题或转人工确认。"
            citations: list[str] = []
        else:
            if generator == "llm":
                answerer = OpenAICompatibleAnswerer()
            elif generator == "extractive":
                answerer = ExtractiveAnswerer()
            else:
                raise ValueError("generator must be 'extractive' or 'llm'")
            answer, citations = answerer.answer(context, hits, resolved)
            if not citations:
                answerable = False
        latency_ms = (time.perf_counter() - started) * 1000
        response = RAGResponse(
            query=context.query,
            answer=answer,
            answerable=answerable,
            confidence=confidence,
            citations=citations,
            hits=hits,
            conflicts=conflicts,
            latency_ms=latency_ms,
            mode=mode,
            trace_id=trace_id,
        )
        if self.audit and log:
            self.audit.log(context, response)
        return response
