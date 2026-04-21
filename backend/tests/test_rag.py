"""RAG foundation tests: chunking, retrieval, and reranking."""

from __future__ import annotations

from utils.chunking import chunk_text
from utils.embeddings import build_vector_index
from utils.reranker import LexicalOverlapReranker
from utils.retriever import VectorRetriever


def test_chunk_text_creates_overlapping_segments():
    text = " ".join(f"token{i}" for i in range(1, 41))
    chunks = chunk_text(text, source="file.txt", chunk_size_tokens=10, overlap_tokens=2)
    assert len(chunks) > 1
    assert chunks[0]["chunk_id"] == "file.txt:1"
    # overlap means tail of chunk 1 appears in chunk 2
    assert "token9 token10" in chunks[1]["text"]


def test_retriever_and_reranker_return_relevant_chunks():
    chunks = [
        {"chunk_id": "a:1", "text": "payment workflow with stripe integration", "source": "a.txt"},
        {"chunk_id": "a:2", "text": "mobile onboarding and authentication flow", "source": "a.txt"},
        {"chunk_id": "a:3", "text": "sprint ceremonies and planning cadence", "source": "a.txt"},
    ]
    index = build_vector_index(chunks)
    retriever = VectorRetriever(top_k=3)
    reranker = LexicalOverlapReranker()
    candidates = retriever.retrieve("stripe payment setup", index, top_k=3)
    ranked = reranker.rerank("stripe payment setup", candidates, top_k=2)

    assert ranked
    assert ranked[0]["chunk_id"] == "a:1"
    assert ranked[0]["score"] >= ranked[-1]["score"]
