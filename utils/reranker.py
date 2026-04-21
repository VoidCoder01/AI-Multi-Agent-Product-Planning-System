"""Lexical overlap reranker for improving retrieval precision."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _token_set(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


class LexicalOverlapReranker:
    """
    Lexical overlap reranker combining base vector score with BM25-style token matching.

    Lightweight alternative to neural cross-encoders — trades semantic precision for
    zero-latency, zero-dependency operation. For production, swap in a cross-encoder
    such as ``cross-encoder/ms-marco-MiniLM-L-6-v2``.
    """

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not query.strip() or not candidates:
            return []
        q = _token_set(query)
        rescored: list[tuple[float, dict[str, Any]]] = []
        for item in candidates:
            text = str(item.get("text") or "")
            base = float(item.get("score") or 0.0)
            tokens = _token_set(text)
            overlap = (len(q & tokens) / max(1, len(q))) if q else 0.0
            final_score = (0.65 * base) + (0.35 * overlap)
            merged = dict(item)
            merged["score"] = round(final_score, 6)
            rescored.append((final_score, merged))
        rescored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in rescored[: max(1, top_k)]]


