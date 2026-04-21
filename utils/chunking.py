"""Token-based text chunking for RAG ingestion."""

from __future__ import annotations

from typing import Any


def chunk_text(
    text: str,
    *,
    source: str,
    chunk_size_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[dict[str, Any]]:
    """
    Split text into overlapping token chunks.

    Output shape:
    {
      "chunk_id": "source:1",
      "text": "...",
      "source": "file.pdf"
    }
    """
    raw_tokens = (text or "").split()
    if not raw_tokens:
        return []

    chunk_size = max(1, int(chunk_size_tokens))
    overlap = max(0, min(int(overlap_tokens), chunk_size - 1))
    step = max(1, chunk_size - overlap)

    chunks: list[dict[str, Any]] = []
    i = 0
    idx = 1
    while i < len(raw_tokens):
        piece = raw_tokens[i : i + chunk_size]
        if not piece:
            break
        chunks.append(
            {
                "chunk_id": f"{source}:{idx}",
                "text": " ".join(piece),
                "source": source,
            }
        )
        idx += 1
        i += step
    return chunks
