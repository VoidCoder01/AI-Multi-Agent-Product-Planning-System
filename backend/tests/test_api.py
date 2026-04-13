"""API endpoint tests using FastAPI TestClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("agents.base.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_block = MagicMock()
        mock_block.text = '["Q1?", "Q2?", "Q3?", "Q4?"]'
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        from backend.main import app

        yield TestClient(app)


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200


def test_questions_endpoint(client: TestClient):
    r = client.post("/api/questions", json={"product_idea": "A habit tracker"})
    assert r.status_code == 200
    data = r.json()
    assert "questions" in data
    assert isinstance(data["questions"], list)


def test_questions_empty_idea_rejected(client: TestClient):
    r = client.post("/api/questions", json={"product_idea": ""})
    assert r.status_code == 422
