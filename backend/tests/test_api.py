"""API endpoint tests using FastAPI TestClient."""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _mock_openai_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def client():
    with patch.dict(
        os.environ,
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key",
            "JWT_SECRET": "",
            "API_BEARER_TOKEN": "",
        },
        clear=False,
    ):
        with patch("agents.base.OpenAI") as mock_cls, patch("backend.main.OpenAI") as api_openai_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            api_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value = _mock_openai_response(
                '["Q1?", "Q2?", "Q3?", "Q4?"]'
            )
            mock_client.audio.transcriptions.create.return_value = MagicMock(
                text="Meeting notes about Q3 roadmap and integration dependencies."
            )

            from backend.main import app

            yield TestClient(app)


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["api_key_configured"] is True


def test_questions_endpoint(client: TestClient):
    r = client.post("/api/questions", json={"product_idea": "A habit tracker"})
    assert r.status_code == 200
    data = r.json()
    assert "questions" in data
    assert isinstance(data["questions"], list)


def test_questions_empty_idea_rejected(client: TestClient):
    r = client.post("/api/questions", json={"product_idea": ""})
    assert r.status_code == 422


def test_upload_txt_document_creates_rag_index(client: TestClient):
    encoded = base64.b64encode(b"roadmap priorities for Q3 and dependency risks").decode("ascii")
    r = client.post(
        "/api/upload",
        json={"filename": "notes.txt", "content_base64": encoded},
    )
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert body["document"]["filename"] == "notes.txt"
    assert body["document"]["chunk_count"] >= 1
    assert body["index_size"] >= 1


def test_upload_audio_document_transcribes_and_indexes(client: TestClient):
    encoded = base64.b64encode(b"fake audio bytes").decode("ascii")
    r = client.post(
        "/api/upload",
        json={"filename": "meeting.mp3", "content_base64": encoded},
    )
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert body["document"]["filename"] == "meeting.mp3"
    assert body["document"]["char_count"] > 0
    assert body["document"]["chunk_count"] >= 1
