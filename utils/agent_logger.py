"""Structured JSONL logging for agent runs (evaluation / debugging)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("agent_audit")

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT_LOG = _REPO / "logs" / "agent_executions.jsonl"


def _truncate(s: str, max_len: int = 4000) -> str:
    s = s or ""
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def _flatten_prompt_audit(record: dict[str, Any], extra: dict[str, Any] | None) -> None:
    """Promote prompt metadata for easier grep in JSONL."""
    if not extra:
        return
    pa = extra.get("prompt_audit")
    if not isinstance(pa, dict):
        return
    for key in ("system", "user"):
        block = pa.get(key)
        if isinstance(block, dict):
            if block.get("prompt_name"):
                record[f"prompt_{key}_name"] = block["prompt_name"]
            if block.get("prompt_version"):
                record[f"prompt_{key}_version"] = block["prompt_version"]
            if block.get("prompt_path"):
                record[f"prompt_{key}_path"] = block["prompt_path"]
            vk = block.get("variable_keys")
            if isinstance(vk, list):
                record[f"prompt_{key}_vars"] = vk


def log_agent_execution(
    agent: str,
    phase: str,
    input_summary: str,
    output_summary: str,
    *,
    status: str = "ok",
    duration_ms: float | None = None,
    extra: dict[str, Any] | None = None,
    log_path: Path | None = None,
) -> None:
    """Append one JSON line per agent transition."""
    path = log_path or _DEFAULT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "phase": phase,
        "status": status,
        "input": _truncate(input_summary),
        "output": _truncate(output_summary),
    }
    if duration_ms is not None:
        record["duration_ms"] = round(duration_ms, 2)
    if extra:
        record["extra"] = extra
        _flatten_prompt_audit(record, extra)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path.open("a", encoding="utf-8").write(line)
    _logger.info("%s | %s | %s", agent, phase, status)


def log_agent_parse_fallback(
    agent: str,
    phase: str,
    reason: str,
    *,
    raw_preview: str | None = None,
    fallback_detail: str | None = None,
    extra: dict[str, Any] | None = None,
    log_path: Path | None = None,
) -> None:
    """Log when deterministic fallback replaces unparseable LLM output."""
    path = log_path or _DEFAULT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "llm_parse_fallback",
        "agent": agent,
        "phase": phase,
        "status": "fallback",
        "reason": reason,
        "raw_preview": _truncate(raw_preview or "", 1500),
    }
    if fallback_detail:
        record["fallback_detail"] = _truncate(fallback_detail, 2000)
    if extra:
        record["extra"] = extra
        _flatten_prompt_audit(record, extra)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path.open("a", encoding="utf-8").write(line)
    _logger.warning("%s | %s | parse_fallback: %s", agent, phase, reason)
