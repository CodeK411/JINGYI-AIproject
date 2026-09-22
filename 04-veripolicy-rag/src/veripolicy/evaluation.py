from __future__ import annotations

import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from .answering import relevant_rule_keys
from .confidence import choose_threshold, retrieval_confidence
from .conflicts import detect_conflicts
from .pipeline import PipelineMode, VeriPolicyRAG
from .schemas import EvalQuery, QueryContext, SearchHit
from .scope import is_applicable


def load_eval_queries(path: str | Path) -> list[EvalQuery]:
    rows: list[EvalQuery] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(EvalQuery.from_dict(json.loads(line)))
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid evaluation row at line {line_number}: {exc}") from exc
    return rows


def _relevant(hit: SearchHit, query: EvalQuery) -> bool:
    if hit.chunk.doc_id not in query.relevant_doc_ids:
        return False
    if not query.relevant_rule_key:
        return True
    return any(str(rule.get("key")) == query.relevant_rule_key for rule in hit.chunk.rules)


def _rank_of_first_relevant(hits: list[SearchHit], query: EvalQuery) -> int | None:
    for index, hit in enumerate(hits, start=1):
        if _relevant(hit, query):
            return index
    return None


def _ndcg(hits: list[SearchHit], query: EvalQuery, k: int = 10) -> float:
    gains = [1.0 if _relevant(hit, query) else 0.0 for hit in hits[:k]]
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal_count = min(len(query.relevant_doc_ids), k)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_count))
    return dcg / idcg if idcg else 0.0


def _rule_value_correct(hits: list[SearchHit], query: EvalQuery) -> bool | None:
    if query.expected_value is None or query.relevant_rule_key is None:
        return None
    for hit in hits:
        for rule in hit.chunk.rules:
            if str(rule.get("key")) == query.relevant_rule_key:
                return str(rule.get("value")) == query.expected_value
    return False


def _answerability_score(context: QueryContext, hits: list[SearchHit]) -> float:
    conflicts, _ = detect_conflicts(hits, context)
    keys = relevant_rule_keys(context.query, hits)
    unresolved = any(
        conflict.status == "unresolved" and (not keys or conflict.rule_key in keys)
        for conflict in conflicts
    )
    return 0.0 if unresolved else retrieval_confidence(hits)


def evaluate_mode(
    rag: VeriPolicyRAG,
    queries: list[EvalQuery],
    mode: PipelineMode,
    top_k: int = 10,
    threshold: float | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    threshold = rag.abstain_threshold if threshold is None else threshold
    answerable_queries = [query for query in queries if query.answerable]
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    hit1 = hit3 = hit5 = 0
    stale_or_wrong_scope = 0
    answerability_correct = 0
    value_correct: list[bool] = []
    latencies: list[float] = []
    details: list[dict[str, Any]] = []
    tag_results: dict[str, list[float]] = defaultdict(list)

    for query in queries:
        context = QueryContext.create(
            query=query.query,
            as_of=query.as_of,
            region=query.region,
            employee_type=query.employee_type,
        )
        started = time.perf_counter()
        hits = rag.retrieve(context, mode=mode, top_k=top_k)
        elapsed = (time.perf_counter() - started) * 1000
        latencies.append(elapsed)
        confidence = _answerability_score(context, hits)
        predicted_answerable = bool(hits) and confidence >= threshold
        answerability_correct += int(predicted_answerable == query.answerable)
        rank = _rank_of_first_relevant(hits, query) if query.answerable else None
        if query.answerable:
            hit1 += int(rank is not None and rank <= 1)
            hit3 += int(rank is not None and rank <= 3)
            hit5 += int(rank is not None and rank <= 5)
            reciprocal_ranks.append(1.0 / rank if rank else 0.0)
            ndcgs.append(_ndcg(hits, query, k=10))
            if hits and not is_applicable(hits[0].chunk, context):
                stale_or_wrong_scope += 1
            correct = _rule_value_correct(hits, query)
            if correct is not None:
                value_correct.append(correct)
            for tag in query.tags:
                tag_results[tag].append(1.0 if rank is not None and rank <= 3 else 0.0)
        details.append(
            {
                "query_id": query.query_id,
                "query": query.query,
                "mode": mode,
                "answerable": query.answerable,
                "predicted_answerable": predicted_answerable,
                "confidence": round(confidence, 6),
                "first_relevant_rank": rank,
                "top_chunk_id": hits[0].chunk.chunk_id if hits else None,
                "top_doc_id": hits[0].chunk.doc_id if hits else None,
                "latency_ms": round(elapsed, 3),
            }
        )

    denominator = max(len(answerable_queries), 1)
    metrics: dict[str, Any] = {
        "mode": mode,
        "queries": len(queries),
        "answerable_queries": len(answerable_queries),
        "hit@1": hit1 / denominator,
        "hit@3": hit3 / denominator,
        "hit@5": hit5 / denominator,
        "mrr@10": statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "ndcg@10": statistics.mean(ndcgs) if ndcgs else 0.0,
        "stale_or_wrong_scope@1": stale_or_wrong_scope / denominator,
        "rule_value_accuracy": statistics.mean(value_correct) if value_correct else None,
        "answerability_accuracy": answerability_correct / max(len(queries), 1),
        "latency_p50_ms": statistics.median(latencies) if latencies else 0.0,
        "threshold": threshold,
        "hit@3_by_tag": {
            tag: statistics.mean(values) for tag, values in sorted(tag_results.items())
        },
    }
    return metrics, details


def calibrate_on_dev(
    rag: VeriPolicyRAG,
    queries: list[EvalQuery],
    mode: PipelineMode = "full",
) -> dict[str, float]:
    rows: list[tuple[float, bool]] = []
    for query in queries:
        context = QueryContext.create(
            query.query,
            as_of=query.as_of,
            region=query.region,
            employee_type=query.employee_type,
        )
        hits = rag.retrieve(context, mode=mode, top_k=5)
        rows.append((_answerability_score(context, hits), query.answerable))
    return choose_threshold(rows)


def run_ablation(
    rag: VeriPolicyRAG,
    eval_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    queries = load_eval_queries(eval_path)
    dev = [query for query in queries if query.split == "dev"]
    test = [query for query in queries if query.split == "test"]
    modes: list[PipelineMode] = ["dense", "hybrid", "hybrid_temporal", "full"]
    results: list[dict[str, Any]] = []
    all_details: list[dict[str, Any]] = []
    calibrations: dict[str, dict[str, float]] = {}
    for mode in modes:
        calibration = calibrate_on_dev(rag, dev, mode=mode)
        calibrations[mode] = calibration
        threshold = calibration["threshold"]
        metrics, details = evaluate_mode(rag, test, mode=mode, threshold=threshold)
        results.append(metrics)
        all_details.extend(details)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset": str(eval_path),
        "dev_queries": len(dev),
        "test_queries": len(test),
        "calibration": calibrations,
        "results": results,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output_dir / "per_query.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_details:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output_dir / "report.md").write_text(_markdown_report(payload), encoding="utf-8")
    return payload


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# VeriPolicy-RAG 消融实验",
        "",
        f"开发集：{payload['dev_queries']} 条；测试集：{payload['test_queries']} 条。",
        "每条 pipeline 的拒答阈值均只在开发集校准，测试集没有参与选阈值。",
        "",
        "| Pipeline | Hit@1 | Hit@3 | MRR@10 | nDCG@10 | 错版本/错范围@1 | 拒答准确率 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["results"]:
        lines.append(
            "| {mode} | {hit1:.3f} | {hit3:.3f} | {mrr:.3f} | {ndcg:.3f} | {stale:.3f} | {answer:.3f} |".format(
                mode=row["mode"],
                hit1=row["hit@1"],
                hit3=row["hit@3"],
                mrr=row["mrr@10"],
                ndcg=row["ndcg@10"],
                stale=row["stale_or_wrong_scope@1"],
                answer=row["answerability_accuracy"],
            )
        )
    lines.extend(
        [
            "",
            "## 解释",
            "",
            "- `dense`：不做时间/人群过滤的向量基线。",
            "- `hybrid`：Dense + BM25，经 Reciprocal Rank Fusion 合并。",
            "- `hybrid_temporal`：增加生效日期、地区和员工类型过滤。",
            "- `full`：再加入可解释特征重排；生产配置可切换 Qwen3 Cross-Encoder。",
            "",
            "所有数字由同一测试集实跑生成，未手填。",
        ]
    )
    return "\n".join(lines) + "\n"
