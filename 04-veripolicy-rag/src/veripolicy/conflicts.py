from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .schemas import Conflict, QueryContext, SearchHit
from .scope import precedence_key


def detect_conflicts(
    hits: Sequence[SearchHit],
    context: QueryContext,
) -> tuple[list[Conflict], dict[str, tuple[str, str]]]:
    grouped: dict[str, list[tuple[SearchHit, dict[str, object]]]] = defaultdict(list)
    for hit in hits:
        for rule in hit.chunk.rules:
            grouped[str(rule["key"])].append((hit, rule))

    conflicts: list[Conflict] = []
    resolved: dict[str, tuple[str, str]] = {}
    for key, candidates in grouped.items():
        values = {str(rule["value"]) for _, rule in candidates}
        ordered = sorted(
            candidates,
            key=lambda item: precedence_key(item[0].chunk, context),
            reverse=True,
        )
        winner_hit, winner_rule = ordered[0]
        winner_value = str(winner_rule["value"])
        resolved[key] = (winner_value, winner_hit.chunk.chunk_id)
        if len(values) <= 1:
            continue
        top_key = precedence_key(winner_hit.chunk, context)
        tied_values = {
            str(rule["value"])
            for hit, rule in ordered
            if precedence_key(hit.chunk, context) == top_key
        }
        unresolved = len(tied_values) > 1
        conflicts.append(
            Conflict(
                rule_key=key,
                status="unresolved" if unresolved else "resolved_by_precedence",
                values=tuple(sorted(values)),
                source_ids=tuple(hit.chunk.chunk_id for hit, _ in ordered),
                selected_source_id=None if unresolved else winner_hit.chunk.chunk_id,
                reason=(
                    "Equal-precedence active sources disagree; human review required."
                    if unresolved
                    else "Selected by scope specificity, authority, then effective date."
                ),
            )
        )
        if unresolved:
            resolved.pop(key, None)
    return conflicts, resolved
