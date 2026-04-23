"""
Runtime settings from environment (12-factor style).

Defaults match previous hardcoded behavior. Override per deployment without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or not str(v).strip() else str(v).strip()


def _env_int(name: str, default: int, *, min_value: int = 1) -> int:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    try:
        n = int(v.strip(), 10)
    except ValueError:
        return default
    return max(min_value, n)


def _env_float(name: str, default: float, *, min_value: float = 0.0) -> float:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    try:
        x = float(v.strip())
    except ValueError:
        return default
    return max(min_value, x)


@dataclass(frozen=True)
class LLMSettings:
    """OpenAI-compatible LLM client + retry behavior."""

    model: str
    max_retries: int
    retry_backoff_base_sec: float
    timeout_sec: float
    log_input_max_chars: int
    log_output_max_chars: int


@dataclass(frozen=True)
class TaskAgentSettings:
    max_workers: int


@lru_cache
def get_llm_settings() -> LLMSettings:
    """
    max_retries: extra attempts after the first failure (total calls = max_retries + 1).
    """
    return LLMSettings(
        model=_env_str(
            "OPENAI_MODEL",
            _env_str(
                "OPENROUTER_MODEL",
                _env_str("ANTHROPIC_MODEL", "gpt-4o-mini"),
            ),
        ),
        max_retries=max(0, _env_int("LLM_MAX_RETRIES", 2, min_value=0)),
        retry_backoff_base_sec=_env_float(
            "LLM_RETRY_BACKOFF_BASE_SEC", 0.6, min_value=0.0
        ),
        timeout_sec=_env_float(
            "LLM_TIMEOUT_SEC",
            _env_float("ANTHROPIC_TIMEOUT_SEC", 300.0, min_value=30.0),
            min_value=30.0,
        ),
        log_input_max_chars=_env_int("AGENT_LOG_INPUT_MAX_CHARS", 6000, min_value=500),
        log_output_max_chars=_env_int("AGENT_LOG_OUTPUT_MAX_CHARS", 6000, min_value=500),
    )


@lru_cache
def get_task_agent_settings() -> TaskAgentSettings:
    return TaskAgentSettings(
        max_workers=_env_int("TASK_AGENT_MAX_WORKERS", 10, min_value=1),
    )


def default_model_name() -> str:
    """Single source for README / prompt_config display."""
    return get_llm_settings().model
