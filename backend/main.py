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
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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
logger = logging.getLogger(__name__)

from backend.orchestrator import Orchestrator
from backend.security import (
    AuthContext,
    authenticate_request,
    get_configured_auth_mode,
    require_roles,
)
from schemas.models import GenerateBody, ProductIdeaBody
from utils.chunking import chunk_text
from utils.embeddings import build_vector_index

_orchestrator: Orchestrator | None = None
_auth_mode_override: str | None = None


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


def _parse_allowed_origins() -> tuple[list[str], bool]:
    """
    Build CORS origins from ALLOWED_ORIGINS env.

    Defaults to localhost origins for safer local development behavior.
    """
    raw = os.getenv("ALLOWED_ORIGINS")
    if raw:
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    else:
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    wildcard_enabled = "*" in origins
    return origins, wildcard_enabled

_allowed_origins, _wildcard_cors = _parse_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=not _wildcard_cors,
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
    request_id: str | None = None


class UploadDocumentBody(BaseModel):
    filename: str
    content_base64: str
    session_id: str | None = None


class AuthModeBody(BaseModel):
    mode: str = Field(pattern="^(none|enforced)$")


def _auth_from_request(request: Request) -> AuthContext | None:
    auth = getattr(request.state, "auth", None)
    if isinstance(auth, AuthContext):
        return auth
    return None


def _auth_toggle_enabled() -> bool:
    return os.getenv("AUTH_MODE_TOGGLE_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _effective_auth_mode() -> str:
    if _auth_mode_override in {"none", "enforced"}:
        return _auth_mode_override
    configured = get_configured_auth_mode()
    if configured == "none":
        return "none"
    return "enforced"


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
    if ext in {".mp3", ".wav", ".m4a", ".webm"}:
        return _transcribe_audio_with_whisper(filename, content)
    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Upload .txt, .pdf, .mp3, .wav, .m4a, or .webm files only.",
    )


def _transcribe_audio_with_whisper(filename: str, content: bytes) -> str:
    """Transcribe uploaded audio using Whisper via OpenAI-compatible SDK."""
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
    openrouter_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("open_router_api_key")
    api_key = openai_key or openrouter_key
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY or OPENROUTER_API_KEY is required for audio transcription.",
        )
    model = os.getenv("WHISPER_MODEL", "whisper-1")
    client_kwargs = {
        "api_key": api_key,
        "timeout": float(os.getenv("WHISPER_TIMEOUT_SEC", "120")),
    }
    if openrouter_key and not openai_key:
        client_kwargs["base_url"] = "https://openrouter.ai/api/v1"
        model = os.getenv("WHISPER_MODEL", "openai/whisper-1")
    client = OpenAI(**client_kwargs)
    audio_file = io.BytesIO(content)
    audio_file.name = filename
    try:
        transcription = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Audio transcription failed: {type(exc).__name__}: {exc}",
        ) from exc
    text = str(getattr(transcription, "text", "") or "").strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Transcription returned empty text. Please upload clearer audio.",
        )
    return text


@app.get("/")
def root():
    return {
        "message": "AI Product Planning API",
        "docs": "/docs",
        "ui": "/ui/",
    }


@app.get("/health")
def health():
    has_key = bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("openai_api_key")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("open_router_api_key")
    )
    return {"status": "ok" if has_key else "degraded", "api_key_configured": has_key}


@app.get("/api/health")
def api_health():
    return health()


@app.middleware("http")
async def api_security_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        if _effective_auth_mode() == "enforced":
            try:
                request.state.auth = authenticate_request(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"error": "unauthorized", "detail": str(exc.detail)},
                )
        else:
            request.state.auth = None
    return await call_next(request)


@app.get("/api/admin/auth-mode")
def get_auth_mode(http_request: Request):
    auth = _auth_from_request(http_request)
    if _effective_auth_mode() == "enforced":
        require_roles(auth, {"admin"})
    return {
        "mode": _effective_auth_mode(),
        "configured_mode": get_configured_auth_mode(),
        "toggle_enabled": _auth_toggle_enabled(),
    }


@app.post("/api/admin/auth-mode")
def set_auth_mode(body: AuthModeBody, http_request: Request):
    if not _auth_toggle_enabled():
        raise HTTPException(status_code=403, detail="Auth mode toggle is disabled.")

    auth = _auth_from_request(http_request)
    if _effective_auth_mode() == "enforced":
        require_roles(auth, {"admin"})

    global _auth_mode_override
    _auth_mode_override = body.mode
    logger.warning("Auth mode override set to %s", body.mode)
    return {
        "mode": _effective_auth_mode(),
        "configured_mode": get_configured_auth_mode(),
        "toggle_enabled": _auth_toggle_enabled(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid4())
    logger.exception(
        "Unhandled server exception request_id=%s path=%s",
        request_id,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )


@app.post("/api/questions", responses={500: {"model": ErrorResponse}})
def get_questions(request: ProductIdeaBody, http_request: Request):
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:generate", "planner:readwrite"})
    try:
        questions = get_orchestrator().clarification_agent.ask_questions(
            request.product_idea
        )
        return {"questions": questions}
    except Exception as exc:
        logger.exception("Question generation failed", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate clarification questions.",
        ) from exc


@app.post("/api/generate", responses={500: {"model": ErrorResponse}})
def generate_documentation(request: GenerateBody, http_request: Request):
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:generate", "planner:readwrite"})
    try:
        owner_id = auth.subject if auth and not auth.is_admin else None
        return get_orchestrator().run_workflow(
            request.product_idea,
            request.answers,
            questions=request.questions,
            session_id=request.session_id,
            owner_id=owner_id,
        )
    except Exception as exc:
        logger.exception("Workflow generation failed", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate planning artifacts.",
        ) from exc


@app.post("/api/generate/stream")
async def generate_stream(request: GenerateBody, http_request: Request):
    """Stream real per-node workflow progress as server-sent events."""
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:generate", "planner:readwrite"})
    owner_id = auth.subject if auth and not auth.is_admin else None

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
                    owner_id=owner_id,
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
async def upload_document(request: UploadDocumentBody, http_request: Request):
    """
    Upload TXT/PDF/audio, chunk it, embed it, and store in session memory.
    """
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:generate", "planner:readwrite"})
    owner_id = auth.subject if auth and not auth.is_admin else None

    if not request.filename:
        raise HTTPException(status_code=400, detail="Missing filename in upload request.")

    try:
        content = base64.b64decode(request.content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid base64 content. Encode your file bytes using base64 before upload.",
        ) from exc

    max_upload_bytes = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    if len(content) > max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds MAX_UPLOAD_BYTES ({max_upload_bytes}).",
        )

    text = _extract_document_text(request.filename, content)
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from document. Please upload a supported text/PDF/audio file.",
        )
    max_document_chars = int(os.getenv("MAX_DOCUMENT_CHARS", "250000"))
    if len(text) > max_document_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Extracted text exceeds MAX_DOCUMENT_CHARS ({max_document_chars}).",
        )

    source = request.filename
    chunks = chunk_text(text, source=source, chunk_size_tokens=800, overlap_tokens=100)
    indexed = build_vector_index(chunks)

    orch = get_orchestrator()
    payload = (
        orch._memory.load(request.session_id, owner_id=owner_id)
        if request.session_id
        else None
    )
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

    max_index_items = int(os.getenv("MAX_SESSION_INDEX_ITEMS", "4000"))
    if len(index) > max_index_items:
        raise HTTPException(
            status_code=413,
            detail=f"Session index size exceeds MAX_SESSION_INDEX_ITEMS ({max_index_items}).",
        )

    rag["documents"] = documents
    rag["raw_documents"] = raw_documents
    rag["index"] = index
    payload["rag"] = rag

    sid = orch._memory.save(payload, session_id=request.session_id, owner_id=owner_id)
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
def workflow_diagram(http_request: Request):
    """Return a Mermaid diagram for the current workflow graph."""
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:read", "planner:readwrite"})
    return {"mermaid": get_orchestrator().mermaid_diagram()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, http_request: Request):
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:read", "planner:readwrite"})
    owner_id = None if auth and auth.is_admin else (auth.subject if auth else None)
    data = get_orchestrator()._memory.load(session_id, owner_id=owner_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.get("/api/sessions")
def list_sessions(http_request: Request):
    auth = _auth_from_request(http_request)
    require_roles(auth, {"planner:read", "planner:readwrite"})
    owner_id = None if auth and auth.is_admin else (auth.subject if auth else None)
    return {"sessions": get_orchestrator()._memory.list_sessions(owner_id=owner_id)}
