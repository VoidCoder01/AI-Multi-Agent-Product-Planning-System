"""
FastAPI entry: orchestrator, /api/questions, /api/generate, static UI at /ui.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

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


@app.get("/")
def root():
    return {
        "message": "AI Product Planning API",
        "docs": "/docs",
        "ui": "/ui/",
    }


@app.get("/health")
def health():
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
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
    """Stream workflow progress as server-sent events."""

    async def event_stream():
        stages = [
            ("clarification", "Analyzing product idea..."),
            ("requirement", "Generating project brief..."),
            ("pm_review", "PM reviewing brief..."),
            ("prd", "Writing PRD..."),
            ("architect", "Designing architecture..."),
            ("scrum_review", "Scrum reviewing PRD..."),
            ("epics", "Creating epics and stories..."),
            ("feasibility", "Validating feasibility..."),
            ("tasks", "Breaking down tasks..."),
            ("validation", "Final validation..."),
        ]
        for stage_name, message in stages:
            payload = {"stage": stage_name, "status": "started", "message": message}
            yield f"data: {json.dumps(payload)}\n\n"

        try:
            result = await asyncio.to_thread(
                get_orchestrator().run_workflow,
                request.product_idea,
                request.answers,
                questions=request.questions,
            )
            yield f"data: {json.dumps({'stage': 'complete', 'status': 'done', 'result': result})}\n\n"
        except Exception as exc:
            payload = {
                "stage": "error",
                "status": "failed",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
