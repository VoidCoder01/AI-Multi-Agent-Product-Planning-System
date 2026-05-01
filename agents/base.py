"""Provider-aware LLM client + audit logging for all agents."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Any

# Thread-local slot for a streaming chunk callback.
# The SSE endpoint sets this before running the graph so every agent call
# inside that thread can forward tokens back to the queue.
_stream_cb: threading.local = threading.local()

from anthropic import Anthropic
from openai import OpenAI

from utils.agent_logger import log_agent_execution
from utils.cache import CacheLayer
from utils.runtime_config import get_llm_settings

logger = logging.getLogger(__name__)


class BaseAgent:
    """Shared provider client; subclasses set `audit_name`."""

    audit_name: str = "BASE_AGENT"
    _cache = CacheLayer()  # shared across agents

    def __init__(self) -> None:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key")
        openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
        openrouter_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("open_router_api_key")
        # Tests patch env vars per test; clear cached settings so provider/model follow current env.
        get_llm_settings.cache_clear()
        self._llm = get_llm_settings()
        provider = self._llm.provider
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("gemini_api_key")
        if provider == "auto":
            if anthropic_key:
                provider = "anthropic"
            elif gemini_key:
                provider = "gemini"
            elif openrouter_key:
                provider = "openrouter"
            elif openai_key:
                provider = "openai"
            else:
                provider = "openrouter"  # fall back to OpenRouter free tier
        self.provider = provider
        resolved_model = self._llm.model
        if self.provider == "anthropic":
            if not anthropic_key:
                raise ValueError("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY")
            self.client = Anthropic(api_key=anthropic_key, timeout=self._llm.timeout_sec)
        elif self.provider == "openrouter":
            if not openrouter_key:
                raise ValueError("LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY")
            self.client = OpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=self._llm.timeout_sec,
            )
        elif self.provider == "openai":
            if not openai_key:
                raise ValueError("LLM_PROVIDER=openai requires OPENAI_API_KEY")
            if not os.getenv("OPENAI_MODEL") and ("/" in resolved_model or ":" in resolved_model):
                raise ValueError(
                    "OPENAI_MODEL must be a native OpenAI model when LLM_PROVIDER=openai."
                )
            self.client = OpenAI(api_key=openai_key, timeout=self._llm.timeout_sec)
        elif self.provider == "gemini":
            if not gemini_key:
                raise ValueError("LLM_PROVIDER=gemini requires GEMINI_API_KEY")
            self.client = OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=self._llm.timeout_sec,
            )
        else:
            raise ValueError("LLM_PROVIDER must be one of: anthropic, openrouter, openai, gemini, auto")
        self.model = resolved_model

    def _create_completion(
        self,
        *,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """Non-streaming or streaming completion depending on `on_chunk`."""
        if self.provider in {"openai", "openrouter", "gemini"}:
            if on_chunk:
                full = ""
                stream = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    stream=True,
                )
                for chunk in stream:
                    delta = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                    if delta:
                        full += delta
                        on_chunk(delta)
                return full
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return str(response.choices[0].message.content)

        # Anthropic
        if on_chunk:
            full = ""
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    full += text
                    on_chunk(text)
            return full
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text_parts = [
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ]
        return "\n".join(text_parts).strip()

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

        # Pick up any streaming callback registered by the SSE thread.
        on_chunk: Callable[[str], None] | None = getattr(_stream_cb, "fn", None)

        for attempt in range(max_retries + 1):
            last_attempt = attempt
            t0 = time.perf_counter()
            try:
                text = self._create_completion(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    max_tokens=max_tokens,
                    on_chunk=on_chunk,
                )
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
