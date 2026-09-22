from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .schemas import QueryContext, SearchHit
from .scope import scope_specificity
from .text import minmax, normalize_text, overlap_features


class FeatureReranker:
    """Transparent reranker used in the reproducible CPU profile."""

    def rerank(
        self,
        context: QueryContext,
        hits: Sequence[SearchHit],
        top_k: int,
    ) -> list[SearchHit]:
        if not hits:
            return []
        dense = minmax(hit.signals.get("dense", 0.0) for hit in hits)
        sparse = minmax(hit.signals.get("bm25", 0.0) for hit in hits)
        scored: list[SearchHit] = []
        for index, hit in enumerate(hits):
            coverage, jaccard = overlap_features(context.query, hit.chunk.retrieval_text)
            heading_coverage, _ = overlap_features(context.query, hit.chunk.heading)
            rule_coverage = 0.0
            rule_phrase_bonus = 0.0
            normalized_query = normalize_text(context.query)
            for rule in hit.chunk.rules:
                rule_text = " ".join(
                    [
                        str(rule.get("key", "")),
                        str(rule.get("label", "")),
                        str(rule.get("statement", "")),
                        " ".join(str(alias) for alias in rule.get("aliases", [])),
                    ]
                )
                current, _ = overlap_features(context.query, rule_text)
                rule_coverage = max(rule_coverage, current)
                phrases = [str(rule.get("label", "")), *[str(x) for x in rule.get("aliases", [])]]
                if any(
                    len(normalize_text(phrase)) >= 2 and normalize_text(phrase) in normalized_query
                    for phrase in phrases
                ):
                    rule_phrase_bonus = 1.0
            specificity = scope_specificity(hit.chunk, context)
            authority = min(max(hit.chunk.authority / 100.0, 0.0), 1.0)
            base_rank = 1.0 / max(hit.rank, 1)
            score = (
                0.20 * dense[index]
                + 0.16 * sparse[index]
                + 0.12 * coverage
                + 0.03 * jaccard
                + 0.06 * heading_coverage
                + 0.15 * rule_coverage
                + 0.15 * rule_phrase_bonus
                + 0.05 * specificity
                + 0.02 * authority
                + 0.06 * base_rank
            )
            signals = dict(hit.signals)
            signals.update(
                {
                    "coverage": coverage,
                    "jaccard": jaccard,
                    "heading_coverage": heading_coverage,
                    "rule_coverage": rule_coverage,
                    "rule_phrase_bonus": rule_phrase_bonus,
                    "scope_specificity": specificity,
                    "authority": authority,
                    "base_rank": base_rank,
                    "rerank": score,
                }
            )
            scored.append(SearchHit(chunk=hit.chunk, score=score, signals=signals))
        scored.sort(key=lambda item: item.score, reverse=True)
        for rank, hit in enumerate(scored[:top_k], start=1):
            hit.rank = rank
        return scored[:top_k]


class CrossEncoderReranker:
    def __init__(self, model_name: str = "Qwen/Qwen3-Reranker-0.6B") -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for the neural reranker; "
                "install requirements-ml.txt"
            ) from exc
        self.model = CrossEncoder(
            model_name,
            prompts={
                "policy": (
                    "Judge whether the document contains the applicable enterprise policy rule "
                    "needed to answer the query."
                )
            },
            default_prompt_name="policy",
        )

    def rerank(
        self,
        context: QueryContext,
        hits: Sequence[SearchHit],
        top_k: int,
    ) -> list[SearchHit]:
        if not hits:
            return []
        pairs = [(context.query, hit.chunk.retrieval_text) for hit in hits]
        scores = np.asarray(self.model.predict(pairs), dtype=float)
        order = np.argsort(-scores, kind="stable")[:top_k]
        result: list[SearchHit] = []
        for rank, index in enumerate(order, start=1):
            hit = hits[int(index)]
            signals = dict(hit.signals)
            signals["cross_encoder"] = float(scores[index])
            result.append(
                SearchHit(
                    chunk=hit.chunk,
                    score=float(scores[index]),
                    rank=rank,
                    signals=signals,
                )
            )
        return result
