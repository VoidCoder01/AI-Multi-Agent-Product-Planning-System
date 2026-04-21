"""Vector retrieval over locally stored chunk embeddings."""

from __future__ import annotations

from typing import Any

from utils.embeddings import BagOfWordsHashEmbedding, cosine_similarity


class VectorRetriever:
    def __init__(self, *, model: BagOfWordsHashEmbedding | None = None, top_k: int = 5) -> None:
        self.model = model or BagOfWordsHashEmbedding()
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        indexed_chunks: list[dict[str, Any]],
        *,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not query.strip() or not indexed_chunks:
            return []

        q_vec = self.model.embed(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in indexed_chunks:
            emb = item.get("embedding")
            if not isinstance(emb, list):
                continue
            score = cosine_similarity(q_vec, emb)
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)

        out: list[dict[str, Any]] = []
        for score, item in scored[: max(1, top_k or self.top_k)]:
            out.append(
                {
                    "chunk_id": item.get("chunk_id"),
                    "text": item.get("text"),
                    "source": item.get("source"),
                    "score": round(float(score), 6),
                }
            )
        return out
