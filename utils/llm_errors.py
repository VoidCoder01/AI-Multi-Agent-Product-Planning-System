"""Classify raw LLM provider exceptions into clean, user-facing error objects."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class LLMError:
    code: str          # machine-readable slug
    title: str         # short heading shown in the UI
    message: str       # human explanation
    action: str        # what the user should do
    retryable: bool    # whether a retry makes sense


_CREDIT_PATTERNS = [
    "credit balance is too low",
    "insufficient credits",
    "billing",
    "payment required",
    "quota exceeded",
]

_AUTH_PATTERNS = [
    "invalid api key",
    "incorrect api key",
    "authentication",
    "unauthorized",
    "401",
]

_MODEL_PATTERNS = [
    "model:",
    "model not found",
    "no such model",
    "does not exist",
]

_RATE_PATTERNS = [
    "rate limit",
    "too many requests",
    "429",
    "requests per",
]

_OVERLOAD_PATTERNS = [
    "overloaded",
    "capacity",
    "service unavailable",
    "503",
    "529",
]

_CONTEXT_PATTERNS = [
    "context window",
    "maximum context",
    "too long",
    "token limit",
]


def _contains(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(p in lower for p in patterns)


def classify(exc: Exception) -> LLMError:
    """Return a structured LLMError from any provider exception."""
    raw = str(exc)
    low = raw.lower()

    # ── Credit / billing ──────────────────────────────────────────────
    if _contains(raw, _CREDIT_PATTERNS):
        return LLMError(
            code="insufficient_credits",
            title="API credit balance exhausted",
            message="Your API account has run out of credits.",
            action="Top up your balance in the provider's billing dashboard, or switch to a free provider (OpenRouter / Gemini) in the provider selector.",
            retryable=False,
        )

    # ── Authentication ─────────────────────────────────────────────────
    if _contains(raw, _AUTH_PATTERNS):
        provider = _detect_provider(raw)
        key_var = _key_env_var(provider)
        return LLMError(
            code="invalid_api_key",
            title="Invalid API key",
            message=f"The {provider} API key was rejected.",
            action=f"Check that {key_var} in your .env file is correct and has not expired.",
            retryable=False,
        )

    # ── Model not found ────────────────────────────────────────────────
    if _contains(raw, _MODEL_PATTERNS):
        model_match = re.search(r"model[:\s]+([^\s'\"},]+)", raw, re.IGNORECASE)
        model_name = model_match.group(1) if model_match else "configured model"
        return LLMError(
            code="model_not_found",
            title="Model not found",
            message=f"The model '{model_name}' does not exist or is not accessible with your API key.",
            action="Update the *_MODEL variable in your .env file to a valid model ID and restart the backend.",
            retryable=False,
        )

    # ── Rate limit ─────────────────────────────────────────────────────
    if _contains(raw, _RATE_PATTERNS):
        return LLMError(
            code="rate_limit",
            title="Rate limit reached",
            message="Too many requests were sent to the AI provider.",
            action="Wait a moment and try again. Consider upgrading your plan for higher throughput.",
            retryable=True,
        )

    # ── Overloaded / 5xx ───────────────────────────────────────────────
    if _contains(raw, _OVERLOAD_PATTERNS):
        return LLMError(
            code="provider_overloaded",
            title="AI provider overloaded",
            message="The AI provider is experiencing high traffic.",
            action="Retry in a few seconds. If the issue persists, switch to a different provider.",
            retryable=True,
        )

    # ── Context window ─────────────────────────────────────────────────
    if _contains(raw, _CONTEXT_PATTERNS):
        return LLMError(
            code="context_too_long",
            title="Input too long",
            message="The combined prompt exceeded the model's context window.",
            action="Shorten your product idea or reduce the size of uploaded documents.",
            retryable=False,
        )

    # ── Connection errors ──────────────────────────────────────────────
    if any(t in low for t in ("connection", "timeout", "network", "resolve", "unreachable")):
        return LLMError(
            code="connection_error",
            title="Cannot reach AI provider",
            message="A network error occurred while contacting the AI provider.",
            action="Check your internet connection and that the provider's API is reachable.",
            retryable=True,
        )

    # ── Fallback ───────────────────────────────────────────────────────
    return LLMError(
        code="unknown_error",
        title="AI request failed",
        message=raw[:300] if len(raw) <= 300 else raw[:297] + "…",
        action="Check the backend logs for details. You may need to restart the server.",
        retryable=True,
    )


def _detect_provider(text: str) -> str:
    low = text.lower()
    if "anthropic" in low:
        return "Anthropic"
    if "openai" in low:
        return "OpenAI"
    if "openrouter" in low:
        return "OpenRouter"
    if "gemini" in low or "google" in low:
        return "Gemini"
    return "AI provider"


def _key_env_var(provider: str) -> str:
    return {
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
        "Gemini": "GEMINI_API_KEY",
    }.get(provider, "*_API_KEY")


def to_dict(exc: Exception) -> dict:
    """Serialise a classified LLMError for JSON / SSE transport."""
    err = classify(exc)
    return {
        "code": err.code,
        "title": err.title,
        "message": err.message,
        "action": err.action,
        "retryable": err.retryable,
    }
