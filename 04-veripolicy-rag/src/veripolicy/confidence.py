from __future__ import annotations

import math
from collections.abc import Sequence

from .schemas import SearchHit


def retrieval_confidence(hits: Sequence[SearchHit]) -> float:
    if not hits:
        return 0.0
    top = hits[0]
    coverage = float(top.signals.get("coverage", 0.0))
    rule_coverage = float(top.signals.get("rule_coverage", 0.0))
    phrase_bonus = float(top.signals.get("rule_phrase_bonus", 0.0))
    dense = float(top.signals.get("dense", 0.0))
    dense = max(0.0, min(1.0, (dense + 1.0) / 2.0))
    bm25 = float(top.signals.get("bm25", 0.0))
    bm25_strength = 1.0 - math.exp(-max(bm25, 0.0) / 5.0)
    if len(hits) > 1:
        top_score = float(top.score)
        second_score = float(hits[1].score)
        margin = max(0.0, top_score - second_score)
        margin_strength = 1.0 - math.exp(-6.0 * margin)
    else:
        margin_strength = 0.5
    rule_bonus = 1.0 if top.chunk.rules else 0.0
    confidence = (
        0.22 * coverage
        + 0.12 * dense
        + 0.12 * bm25_strength
        + 0.18 * rule_coverage
        + 0.20 * phrase_bonus
        + 0.08 * margin_strength
        + 0.08 * rule_bonus
    )
    return max(0.0, min(1.0, confidence))


def choose_threshold(rows: Sequence[tuple[float, bool]]) -> dict[str, float]:
    """Calibrate on dev only by maximizing balanced accuracy."""
    if not rows:
        return {"threshold": 0.46, "balanced_accuracy": 0.0}
    positives = sum(1 for _, label in rows if label)
    negatives = len(rows) - positives
    best = {"threshold": 0.46, "balanced_accuracy": -1.0}
    candidates = sorted({0.0, 1.0, *(round(i / 100, 2) for i in range(1, 100))})
    for threshold in candidates:
        tp = sum(1 for score, label in rows if label and score >= threshold)
        tn = sum(1 for score, label in rows if not label and score < threshold)
        tpr = tp / positives if positives else 1.0
        tnr = tn / negatives if negatives else 1.0
        balanced = (tpr + tnr) / 2.0
        if balanced > best["balanced_accuracy"]:
            best = {"threshold": threshold, "balanced_accuracy": balanced}
    return best
