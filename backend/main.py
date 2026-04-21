"""
FastAPI entry: orchestrator, /api/questions, /api/generate, static UI at /ui.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env from repo root and backend/
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
load_dotenv(_ROOT / ".env")
load_dotenv(_BACKEND / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from backend.orchestrator import Orchestrator
from schemas.models import GenerateBody, ProductIdeaBody
from utils.chunking import chunk_text
from utils.embeddings import build_vector_index

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


app = FastAPI(
    title="AI Multi-Agent Product Planning API",
    description="Brief → PRD → epics/stories → tasks.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# React production build (npm run build in frontend/) — served under /ui
_UI_DIST = _ROOT / "frontend" / "dist"
if _UI_DIST.is_dir():
    app.mount(
        "/ui",
        StaticFiles(directory=str(_UI_DIST), html=True),
        name="ui",
    )


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    stage: str | None = None


class UploadDocumentBody(BaseModel):
    filename: str
    content_base64: str
    session_id: str | None = None


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract PDF text via pdfplumber (phase-1 RAG ingestion)."""
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise HTTPException(
            status_code=500,
            detail="PDF upload requires `pdfplumber` to be installed.",
        ) from exc

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def _extract_document_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        return content.decode("utf-8", errors="ignore").strip()
    if ext == ".pdf":
        return _extract_text_from_pdf(content)
    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Upload .txt or .pdf files only.",
    )


@app.get("/")
def root():
    return {
        "message": "AI Product Planning API",
        "docs": "/docs",
        "ui": "/ui/",
    }


@app.get("/health")
def health():
    has_key = bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("open_router_api_key"))
    return {"status": "ok" if has_key else "degraded", "api_key_configured": has_key}


@app.get("/api/health")
def api_health():
    return health()


@app.exception_handler(Exception)
async def global_exception_handler(_request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


@app.post("/api/questions", responses={500: {"model": ErrorResponse}})
def get_questions(request: ProductIdeaBody):
    try:
        questions = get_orchestrator().clarification_agent.ask_questions(
            request.product_idea
        )
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(e).__name__,
                "message": str(e),
                "stage": "clarification",
            },
        ) from e


@app.post("/api/generate", responses={500: {"model": ErrorResponse}})
def generate_documentation(request: GenerateBody):
    try:
        return get_orchestrator().run_workflow(
            request.product_idea,
            request.answers,
            questions=request.questions,
            session_id=request.session_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": type(e).__name__,
                "message": str(e),
                "stage": "workflow_generation",
            },
        ) from e


@app.post("/api/generate/stream")
async def generate_stream(request: GenerateBody):
    """Stream real per-node workflow progress as server-sent events."""

    async def event_stream():
        import queue
        import threading

        q: queue.Queue = queue.Queue()
        SENTINEL = object()

        def run_in_thread():
            try:
                orch = get_orchestrator()
                for node_name, message, node_output in orch.run_workflow_streaming(
                    request.product_idea,
                    request.answers,
                    questions=request.questions,
                    session_id=request.session_id,
                ):
                    if node_name == "complete":
                        q.put({"stage": "complete", "status": "done", "result": node_output})
                    else:
                        q.put({"stage": node_name, "status": "completed", "message": message})
            except Exception as exc:
                q.put({
                    "stage": "error",
                    "status": "failed",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                })
            finally:
                q.put(SENTINEL)

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

        loop = asyncio.get_event_loop()
        while True:
            item = await loop.run_in_executor(None, q.get)
            if item is SENTINEL:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/upload", responses={500: {"model": ErrorResponse}})
async def upload_document(request: UploadDocumentBody):
    """
    Upload a TXT/PDF document, chunk it, embed it, and store in session memory.
    """
    if not request.filename:
        raise HTTPException(status_code=400, detail="Missing filename in upload request.")

    try:
        content = base64.b64decode(request.content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid base64 content. Encode your file bytes using base64 before upload.",
        ) from exc

    text = _extract_document_text(request.filename, content)
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from document. Please upload a text-based PDF/TXT.",
        )

    source = request.filename
    chunks = chunk_text(text, source=source, chunk_size_tokens=800, overlap_tokens=100)
    indexed = build_vector_index(chunks)

    orch = get_orchestrator()
    payload = orch._memory.load(request.session_id) if request.session_id else None
    if not isinstance(payload, dict):
        payload = {}
    rag = payload.get("rag")
    if not isinstance(rag, dict):
        rag = {}

    documents = rag.get("documents")
    if not isinstance(documents, list):
        documents = []
    index = rag.get("index")
    if not isinstance(index, list):
        index = []
    raw_documents = rag.get("raw_documents")
    if not isinstance(raw_documents, dict):
        raw_documents = {}

    doc_id = str(uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    documents.append(
        {
            "doc_id": doc_id,
            "filename": source,
            "uploaded_at": uploaded_at,
            "char_count": len(text),
            "chunk_count": len(chunks),
        }
    )
    raw_documents[doc_id] = text
    index.extend(indexed)

    rag["documents"] = documents
    rag["raw_documents"] = raw_documents
    rag["index"] = index
    payload["rag"] = rag

    sid = orch._memory.save(payload, session_id=request.session_id)
    return {
        "session_id": sid,
        "document": {
            "doc_id": doc_id,
            "filename": source,
            "char_count": len(text),
            "chunk_count": len(chunks),
        },
        "index_size": len(index),
    }


@app.get("/api/workflow/diagram")
def workflow_diagram():
    """Return a Mermaid diagram for the current workflow graph."""
    return {"mermaid": get_orchestrator().mermaid_diagram()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    data = get_orchestrator()._memory.load(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.get("/api/sessions")
def list_sessions():
    return {"sessions": get_orchestrator()._memory.list_sessions()}
