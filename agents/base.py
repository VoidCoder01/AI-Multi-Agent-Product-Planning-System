"""OpenRouter/OpenAI client + audit logging for all agents."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from openai import OpenAI

from utils.agent_logger import log_agent_execution
from utils.cache import CacheLayer
from utils.runtime_config import get_llm_settings

logger = logging.getLogger(__name__)


class BaseAgent:
    """Shared OpenRouter client; subclasses set `audit_name`."""

    audit_name: str = "BASE_AGENT"
    _cache = CacheLayer()  # shared across agents

    def __init__(self) -> None:
        key = os.getenv("OPENROUTER_API_KEY") or os.getenv("open_router_api_key")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self._llm = get_llm_settings()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
            timeout=self._llm.timeout_sec
        )
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

        # Try cache
        import hashlib
        cache_key = hashlib.sha256(f"{self.model}:{system_prompt}:{user_message}".encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            extra = {"attempt": 0, "model": self.model}
            if prompt_audit:
                extra["prompt_audit"] = prompt_audit
            log_agent_execution(
                self.audit_name,
                phase,
                user_message[:cap_in],
                cached[:cap_out],
                status="cache_hit",
                duration_ms=0,
                extra=extra
            )
            return cached

        for attempt in range(max_retries + 1):
            last_attempt = attempt
            t0 = time.perf_counter()
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                )
                text = str(response.choices[0].message.content)
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
                self._cache.set(cache_key, text, ttl=7200)
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
