"""Simple file-backed memory for last session artifacts (debug / resume)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class MemoryStore:
    """JSON file per session id under data/planning_memory/."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or Path(__file__).resolve().parent.parent / "data" / "planning_memory"
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, payload: dict[str, Any], session_id: str | None = None) -> str:
        sid = session_id or str(uuid4())
        path = self._base / f"{sid}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return sid

    def load(self, session_id: str) -> dict[str, Any] | None:
        path = self._base / f"{session_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_sessions(self) -> list[str]:
        """Return all session IDs."""
        return [p.stem for p in self._base.glob("*.json")]

    def __len__(self) -> int:
        return len(list(self._base.glob("*.json")))
