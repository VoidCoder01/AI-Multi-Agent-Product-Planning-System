"""Anthropic client + audit logging for all agents."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from anthropic import Anthropic

from utils.agent_logger import log_agent_execution
from utils.runtime_config import get_llm_settings

logger = logging.getLogger(__name__)


class BaseAgent:
    """Shared Claude client; subclasses set `audit_name`."""

    audit_name: str = "BASE_AGENT"

    def __init__(self) -> None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self._llm = get_llm_settings()
        self.client = Anthropic(api_key=key, timeout=self._llm.timeout_sec)
        self.model = self._llm.model

    def call_llm(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        phase: str = "completion",
        prompt_audit: dict[str, Any] | None = None,
    ) -> str:
        last_err: Exception | None = None
        last_attempt = 0
        last_fail_duration_ms: float | None = None
        cap_in = self._llm.log_input_max_chars
        cap_out = self._llm.log_output_max_chars
        max_retries = self._llm.max_retries

        for attempt in range(max_retries + 1):
            last_attempt = attempt
            t0 = time.perf_counter()
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                block = response.content[0]
                text = block.text if hasattr(block, "text") else str(block)
                duration_ms = (time.perf_counter() - t0) * 1000.0
                extra: dict[str, Any] = {"attempt": attempt, "model": self.model}
                if prompt_audit:
                    extra["prompt_audit"] = prompt_audit
                log_agent_execution(
                    self.audit_name,
                    phase,
                    user_message[:cap_in],
                    text[:cap_out],
                    status="ok",
                    duration_ms=duration_ms,
                    extra=extra,
                )
                return text
            except Exception as e:
                last_fail_duration_ms = (time.perf_counter() - t0) * 1000.0
                last_err = e
                logger.warning(
                    "%s %s failed attempt %s: %s",
                    self.audit_name,
                    phase,
                    attempt + 1,
                    e,
                )
                if attempt < max_retries:
                    time.sleep(self._llm.retry_backoff_base_sec * (attempt + 1))
        assert last_err is not None
        fail_extra: dict[str, Any] = {
            "attempt": last_attempt,
            "model": self.model,
            "error_type": type(last_err).__name__,
        }
        if prompt_audit:
            fail_extra["prompt_audit"] = prompt_audit
        log_agent_execution(
            self.audit_name,
            phase,
            user_message[:cap_in],
            repr(last_err)[:cap_out],
            status="llm_error",
            duration_ms=last_fail_duration_ms,
            extra=fail_extra,
        )
        raise last_err
