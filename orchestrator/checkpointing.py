"""LangGraph checkpoint backends for durable graph state (memory, SQLite, Postgres)."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

_ROOT = Path(__file__).resolve().parent.parent


def create_planning_checkpointer() -> tuple[object, Callable[[], None] | None]:
    """
    Build a checkpointer for ``StateGraph.compile(checkpointer=...)``.

    Env:
    - ``LANGGRAPH_CHECKPOINTER``: ``memory`` (default), ``sqlite``, or ``postgres``.
    - ``LANGGRAPH_SQLITE_PATH``: SQLite file path (default ``data/langgraph_checkpoints.sqlite``).
    - ``DATABASE_URL``: required when ``postgres`` (same DSN as session store).

    Returns:
        (checkpointer, shutdown) where ``shutdown`` closes DB resources (or None).
    """
    mode = os.getenv("LANGGRAPH_CHECKPOINTER", "memory").lower().strip()

    if mode in {"", "memory"}:
        return MemorySaver(), None

    if mode == "sqlite":
        rel = os.getenv(
            "LANGGRAPH_SQLITE_PATH",
            str(_ROOT / "data" / "langgraph_checkpoints.sqlite"),
        )
        path = Path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        from langgraph.checkpoint.sqlite import SqliteSaver

        return SqliteSaver(conn), lambda: conn.close()

    if mode == "postgres":
        dsn = os.getenv("DATABASE_URL", "").strip()
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is required when LANGGRAPH_CHECKPOINTER=postgres."
            )
        from langgraph.checkpoint.postgres import PostgresSaver

        cm = PostgresSaver.from_conn_string(dsn)
        saver = cm.__enter__()

        def shutdown() -> None:
            cm.__exit__(None, None, None)

        return saver, shutdown

    raise ValueError(
        f"Unknown LANGGRAPH_CHECKPOINTER={mode!r}; use memory, sqlite, or postgres."
    )
