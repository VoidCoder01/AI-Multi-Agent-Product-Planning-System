"""Redis-backed caching for embeddings and LLM responses."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

import redis

logger = logging.getLogger(__name__)

class CacheLayer:
    """Wrapper for Redis caching with in-memory fallback."""
    
    def __init__(self, prefix: str = "rag_cache:") -> None:
        self.prefix = prefix
        self.redis_url = os.getenv("REDIS_URL")
        self._memory_fallback: dict[str, str] = {}
        self.client: redis.Redis | None = None
        
        if self.redis_url:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection heartbeat
                self.client.ping()
                logger.info("Connected to Redis at %s", self.redis_url)
            except Exception as e:
                logger.warning("Redis connection failed, falling back to memory layer: %s", e)
                self.client = None

    def _hash_key(self, content: str) -> str:
        """Create deterministic key from string content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_embedding(self, text: str) -> list[float] | None:
        """Fetch cached embedding vector."""
        key = f"{self.prefix}emb:{self._hash_key(text)}"
        val = self._get_raw(key)
        if val:
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                pass
        return None

    def set_embedding(self, text: str, vector: list[float], timeout_sec: int = 86400) -> None:
        """Cache embedding vector."""
        key = f"{self.prefix}emb:{self._hash_key(text)}"
        self._set_raw(key, json.dumps(vector), timeout_sec)

    def get_llm_response(self, system: str, user: str) -> str | None:
        """Fetch cached LLM response for EXACT matching prompts."""
        combo = f"sys:{system}|user:{user}"
        key = f"{self.prefix}llm:{self._hash_key(combo)}"
        return self._get_raw(key)

    def set_llm_response(self, system: str, user: str, response: str, timeout_sec: int = 3600) -> None:
        """Cache LLM generation."""
        combo = f"sys:{system}|user:{user}"
        key = f"{self.prefix}llm:{self._hash_key(combo)}"
        self._set_raw(key, response, timeout_sec)

    def get(self, key: str) -> str | None:
        return self._get_raw(key)

    def set(self, key: str, val: str, ttl: int = 3600) -> None:
        self._set_raw(key, val, ttl)

    def _get_raw(self, key: str) -> str | None:
        if self.client:
            try:
                return self.client.get(key)
            except Exception:
                return self._memory_fallback.get(key)
        return self._memory_fallback.get(key)

    def _set_raw(self, key: str, val: str, timeout_sec: int) -> None:
        if self.client:
            try:
                self.client.setex(key, timeout_sec, val)
                return
            except Exception:
                pass
        self._memory_fallback[key] = val

_global_cache = CacheLayer()

def get_cache() -> CacheLayer:
    return _global_cache
