from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .config import load_env_file
from .evaluation import run_ablation
from .pipeline import VeriPolicyRAG
from .schemas import QueryContext


def _add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--corpus", default=os.getenv("CORPUS_DIR", "data/corpus"))
    parser.add_argument("--dense-backend", choices=["lsa", "sentence-transformers"], default="lsa")
    parser.add_argument("--embedding-model", default="Qwen/Qwen3-Embedding-0.6B")
    parser.add_argument("--reranker", choices=["heuristic", "cross-encoder"], default="heuristic")
    parser.add_argument("--reranker-model", default="Qwen/Qwen3-Reranker-0.6B")
    parser.add_argument("--threshold", type=float, default=0.44)


def _build_rag(args: argparse.Namespace, audit: bool = False) -> VeriPolicyRAG:
    return VeriPolicyRAG(
        corpus_dir=args.corpus,
        dense_backend=args.dense_backend,
        embedding_model=args.embedding_model,
        reranker_backend=args.reranker,
        reranker_model=args.reranker_model,
        abstain_threshold=args.threshold,
        audit_db="artifacts/audit.db" if audit else None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="veripolicy", description="VeriPolicy-RAG CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Validate and summarize the corpus")
    _add_runtime_options(inspect_parser)

    ask_parser = subparsers.add_parser("ask", help="Ask a policy question")
    _add_runtime_options(ask_parser)
    ask_parser.add_argument("--question", required=True)
    ask_parser.add_argument("--as-of", required=True)
    ask_parser.add_argument("--region", default="ALL")
    ask_parser.add_argument("--employee-type", default="all")
    ask_parser.add_argument(
        "--mode", choices=["dense", "hybrid", "hybrid_temporal", "full"], default="full"
    )
    ask_parser.add_argument("--generator", choices=["extractive", "llm"], default="extractive")

    eval_parser = subparsers.add_parser("eval", help="Run the full ablation benchmark")
    _add_runtime_options(eval_parser)
    eval_parser.add_argument("--queries", default="data/eval/queries.jsonl")
    eval_parser.add_argument("--output", default="artifacts/eval")

    agent_parser = subparsers.add_parser("agent", help="Run the tool-calling agent")
    agent_parser.add_argument("--corpus", default=os.getenv("CORPUS_DIR", "data/corpus"))
    agent_parser.add_argument("--question", required=True)
    agent_parser.add_argument("--max-turns", type=int, default=6)

    subparsers.add_parser("serve", help="Start the FastAPI service")
    return parser


def main() -> None:
    load_env_file()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "serve":
        from .api import run

        run()
        return

    if args.command == "agent":
        from .agent import run_agent

        print(run_agent(args.question, corpus_dir=args.corpus, max_turns=args.max_turns))
        return

    rag = _build_rag(args, audit=args.command == "ask")
    if args.command == "inspect":
        families = sorted({chunk.policy_family for chunk in rag.chunks})
        documents = sorted({chunk.doc_id for chunk in rag.chunks})
        print(
            json.dumps(
                {"documents": len(documents), "chunks": len(rag.chunks), "families": families},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "ask":
        context = QueryContext.create(
            args.question, args.as_of, args.region, args.employee_type
        )
        response = rag.ask(context, mode=args.mode, generator=args.generator)
        print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))
    elif args.command == "eval":
        result = run_ablation(rag, Path(args.queries), Path(args.output))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()