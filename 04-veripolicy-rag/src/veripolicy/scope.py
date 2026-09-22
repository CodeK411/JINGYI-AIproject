from __future__ import annotations

from .schemas import Chunk, QueryContext


def is_temporally_active(chunk: Chunk, context: QueryContext) -> bool:
    if context.as_of < chunk.effective_from:
        return False
    return chunk.effective_to is None or context.as_of <= chunk.effective_to


def region_matches(chunk: Chunk, context: QueryContext) -> bool:
    if context.region == "ALL":
        return "ALL" in chunk.regions
    return "ALL" in chunk.regions or context.region in chunk.regions


def employee_type_matches(chunk: Chunk, context: QueryContext) -> bool:
    if context.employee_type == "all":
        return "all" in chunk.employee_types
    return "all" in chunk.employee_types or context.employee_type in chunk.employee_types


def is_applicable(chunk: Chunk, context: QueryContext) -> bool:
    return (
        is_temporally_active(chunk, context)
        and region_matches(chunk, context)
        and employee_type_matches(chunk, context)
    )


def scope_specificity(chunk: Chunk, context: QueryContext) -> float:
    region = 0.0
    if context.region != "ALL" and context.region in chunk.regions:
        region = 1.0
    elif "ALL" in chunk.regions:
        region = 0.35
    employee = 0.0
    if context.employee_type != "all" and context.employee_type in chunk.employee_types:
        employee = 1.0
    elif "all" in chunk.employee_types:
        employee = 0.35
    return (region + employee) / 2.0


def precedence_key(chunk: Chunk, context: QueryContext) -> tuple[float, int, int]:
    return (
        scope_specificity(chunk, context),
        chunk.authority,
        chunk.effective_from.toordinal(),
    )

