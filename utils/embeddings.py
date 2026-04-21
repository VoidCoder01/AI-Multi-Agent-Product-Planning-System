"""Lightweight bag-of-words embeddings for local semantic retrieval."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]


class BagOfWordsHashEmbedding:
    """
    Lightweight bag-of-words embedding using deterministic hashing.

    Not a learned embedding — used as a zero-dependency baseline for local
    retrieval. No GPU or external API required. For production, swap in
    ``text-embedding-3-small`` or a sentence-transformer model.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _tokens(text):
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
            bucket = int(digest[:8], 16) % self.dim
            vec[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def build_vector_index(
    chunks: list[dict[str, Any]],
    *,
    model: BagOfWordsHashEmbedding | None = None,
) -> list[dict[str, Any]]:
    model = model or BagOfWordsHashEmbedding()
    out: list[dict[str, Any]] = []
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        out.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "text": text,
                "source": chunk.get("source"),
                "embedding": model.embed(text),
            }
        )
    return out
