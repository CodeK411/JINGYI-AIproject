from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .schemas import Chunk, SearchHit
from .text import expand_query, tokenize


class BM25Index:
    def __init__(self, texts: Sequence[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents = [tokenize(text) for text in texts]
        self.lengths = np.asarray([len(tokens) for tokens in self.documents], dtype=float)
        self.avg_length = float(self.lengths.mean()) if len(self.lengths) else 1.0
        self.term_frequencies = [Counter(tokens) for tokens in self.documents]
        document_frequency: Counter[str] = Counter()
        for tokens in self.documents:
            document_frequency.update(set(tokens))
        count = len(self.documents)
        self.idf = {
            term: math.log(1.0 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def scores(self, query: str) -> np.ndarray:
        query_terms = tokenize(query, expand=True)
        scores = np.zeros(len(self.documents), dtype=float)
        if not query_terms:
            return scores
        for index, frequencies in enumerate(self.term_frequencies):
            length_norm = 1 - self.b + self.b * self.lengths[index] / max(self.avg_length, 1.0)
            total = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * length_norm
                total += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denominator
            scores[index] = total
        return scores


class LSADenseIndex:
    """Dependency-light dense baseline based on latent semantic analysis."""

    def __init__(self, texts: Sequence[str], dimensions: int = 128) -> None:
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            min_df=1,
            sublinear_tf=True,
            max_features=30000,
        )
        matrix = self.vectorizer.fit_transform(texts)
        max_components = min(matrix.shape[0] - 1, matrix.shape[1] - 1, dimensions)
        self.svd: TruncatedSVD | None = None
        if max_components >= 2:
            self.svd = TruncatedSVD(n_components=max_components, random_state=42)
            self.matrix = normalize(self.svd.fit_transform(matrix))
        else:
            self.matrix = normalize(matrix).toarray()

    def scores(self, query: str) -> np.ndarray:
        vector = self.vectorizer.transform([query])
        if self.svd is not None:
            vector = normalize(self.svd.transform(vector))
        else:
            vector = normalize(vector).toarray()
        return np.asarray(self.matrix @ vector.T).reshape(-1)


class SentenceTransformerDenseIndex:
    def __init__(self, texts: Sequence[str], model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for the neural backend; "
                "install requirements-ml.txt"
            ) from exc
        self.model = SentenceTransformer(model_name)
        self.matrix = np.asarray(
            self.model.encode(
                list(texts),
                normalize_embeddings=True,
                show_progress_bar=True,
                batch_size=16,
            )
        )

    def scores(self, query: str) -> np.ndarray:
        instruction = (
            "Instruct: Retrieve the currently applicable enterprise policy passage that answers "
            f"the employee question.\nQuery: {query}"
        )
        vector = np.asarray(
            self.model.encode([instruction], normalize_embeddings=True, show_progress_bar=False)
        )[0]
        return self.matrix @ vector


def _ranks(scores: np.ndarray, allowed: np.ndarray) -> dict[int, int]:
    order = allowed[np.argsort(-scores[allowed], kind="stable")]
    return {int(index): rank for rank, index in enumerate(order, start=1)}


class RetrievalIndex:
    def __init__(
        self,
        chunks: Sequence[Chunk],
        dense_backend: str = "lsa",
        embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
    ) -> None:
        self.chunks = list(chunks)
        texts = [chunk.retrieval_text for chunk in chunks]
        self.bm25 = BM25Index(texts)
        if dense_backend == "sentence-transformers":
            self.dense = SentenceTransformerDenseIndex(texts, embedding_model)
        elif dense_backend == "lsa":
            self.dense = LSADenseIndex(texts)
        else:
            raise ValueError(f"Unsupported dense backend: {dense_backend}")

    def search(
        self,
        query: str,
        allowed_indices: Sequence[int] | None = None,
        top_k: int = 20,
        mode: str = "hybrid",
        rrf_k: int = 60,
    ) -> list[SearchHit]:
        if allowed_indices is None:
            allowed = np.arange(len(self.chunks), dtype=int)
        else:
            allowed = np.asarray(list(allowed_indices), dtype=int)
        if not len(allowed):
            return []
        dense_scores = self.dense.scores(query)
        bm25_scores = self.bm25.scores(expand_query(query))
        dense_ranks = _ranks(dense_scores, allowed)
        bm25_ranks = _ranks(bm25_scores, allowed)
        fused = np.zeros(len(self.chunks), dtype=float)
        if mode == "dense":
            fused = dense_scores.copy()
        elif mode == "bm25":
            fused = bm25_scores.copy()
        elif mode == "hybrid":
            for index in allowed:
                fused[index] = (
                    0.55 / (rrf_k + dense_ranks[int(index)])
                    + 0.45 / (rrf_k + bm25_ranks[int(index)])
                )
        else:
            raise ValueError(f"Unsupported retrieval mode: {mode}")
        ordered = allowed[np.argsort(-fused[allowed], kind="stable")][:top_k]
        hits: list[SearchHit] = []
        for rank, index in enumerate(ordered, start=1):
            hits.append(
                SearchHit(
                    chunk=self.chunks[int(index)],
                    score=float(fused[index]),
                    rank=rank,
                    signals={
                        "dense": float(dense_scores[index]),
                        "bm25": float(bm25_scores[index]),
                        "dense_rank": float(dense_ranks[int(index)]),
                        "bm25_rank": float(bm25_ranks[int(index)]),
                        "rrf": float(fused[index]) if mode == "hybrid" else 0.0,
                    },
                )
            )
        return hits
