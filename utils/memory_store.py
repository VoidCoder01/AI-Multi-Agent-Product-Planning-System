"""Session persistence abstraction with file + PostgreSQL implementations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


class SessionStore(Protocol):
    """Contract for storing and retrieving workflow sessions."""

    def save(
        self,
        payload: dict[str, Any],
        session_id: str | None = None,
        *,
        owner_id: str | None = None,
    ) -> str: ...
    def load(
        self,
        session_id: str,
        *,
        owner_id: str | None = None,
    ) -> dict[str, Any] | None: ...
    def list_sessions(self, *, owner_id: str | None = None) -> list[str]: ...


class FileMemoryStore:
    """JSON file per session id under data/planning_memory/."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or Path(__file__).resolve().parent.parent / "data" / "planning_memory"
        self._base.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        payload: dict[str, Any],
        session_id: str | None = None,
        *,
        owner_id: str | None = None,
    ) -> str:
        sid = session_id or str(uuid4())
        path = self._base / f"{sid}.json"
        persisted = dict(payload)
        if owner_id:
            persisted["_owner_id"] = owner_id
        path.write_text(json.dumps(persisted, indent=2, ensure_ascii=False), encoding="utf-8")
        return sid

    def load(self, session_id: str, *, owner_id: str | None = None) -> dict[str, Any] | None:
        path = self._base / f"{session_id}.json"
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if owner_id:
            stored_owner = payload.get("_owner_id")
            if stored_owner and stored_owner != owner_id:
                return None
        return payload

    def list_sessions(self, *, owner_id: str | None = None) -> list[str]:
        """Return all session IDs."""
        sessions: list[str] = []
        for path in self._base.glob("*.json"):
            if not owner_id:
                sessions.append(path.stem)
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if payload.get("_owner_id") == owner_id:
                sessions.append(path.stem)
        return sessions

    def __len__(self) -> int:
        return len(list(self._base.glob("*.json")))


class PostgresMemoryStore:
    """PostgreSQL-backed session store for multi-user deployments."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._ensure_schema()

    def _connect(self):
        try:
            import psycopg
        except Exception as exc:  # pragma: no cover - dependency/environment specific
            raise RuntimeError("psycopg is required for PostgreSQL session storage.") from exc
        return psycopg.connect(self._dsn)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS planning_sessions (
                        session_id TEXT PRIMARY KEY,
                        owner_id TEXT NULL,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_planning_sessions_owner
                    ON planning_sessions (owner_id);
                    """
                )
            conn.commit()

    def save(
        self,
        payload: dict[str, Any],
        session_id: str | None = None,
        *,
        owner_id: str | None = None,
    ) -> str:
        sid = session_id or str(uuid4())
        persisted = dict(payload)
        if owner_id:
            persisted["_owner_id"] = owner_id
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO planning_sessions (session_id, owner_id, payload, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW())
                    ON CONFLICT (session_id) DO UPDATE SET
                        owner_id = EXCLUDED.owner_id,
                        payload = EXCLUDED.payload,
                        updated_at = NOW();
                    """,
                    (sid, owner_id, json.dumps(persisted, ensure_ascii=False)),
                )
            conn.commit()
        return sid

    def load(self, session_id: str, *, owner_id: str | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if owner_id:
                    cur.execute(
                        """
                        SELECT payload
                        FROM planning_sessions
                        WHERE session_id = %s AND (owner_id = %s OR owner_id IS NULL)
                        LIMIT 1;
                        """,
                        (session_id, owner_id),
                    )
                else:
                    cur.execute(
                        """
                        SELECT payload
                        FROM planning_sessions
                        WHERE session_id = %s
                        LIMIT 1;
                        """,
                        (session_id,),
                    )
                row = cur.fetchone()
        if not row:
            return None
        payload = row[0]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def list_sessions(self, *, owner_id: str | None = None) -> list[str]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if owner_id:
                    cur.execute(
                        """
                        SELECT session_id
                        FROM planning_sessions
                        WHERE owner_id = %s
                        ORDER BY updated_at DESC;
                        """,
                        (owner_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT session_id
                        FROM planning_sessions
                        ORDER BY updated_at DESC;
                        """
                    )
                rows = cur.fetchall()
        return [row[0] for row in rows]


def create_session_store() -> SessionStore:
    """Create store from environment; defaults to local file store."""
    backend = os.getenv("SESSION_STORE_BACKEND", "").strip().lower()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if backend == "postgres" or (not backend and database_url):
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when SESSION_STORE_BACKEND=postgres.")
        return PostgresMemoryStore(database_url)
    return FileMemoryStore()


# Backward-compatible alias
MemoryStore = FileMemoryStore
