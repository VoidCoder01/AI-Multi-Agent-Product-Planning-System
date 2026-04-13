"""Extract JSON from Claude replies (may include markdown fences or extra text)."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_llm_json(text: str) -> Any:
    """Parse a JSON object or array from model output."""
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", raw)
    if fence:
        raw = fence.group(1).strip()
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start_obj, start_arr = raw.find("{"), raw.find("[")
        if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
            end = raw.rfind("]")
            if end > start_arr:
                return json.loads(raw[start_arr : end + 1])
        if start_obj != -1:
            end = raw.rfind("}")
            if end > start_obj:
                return json.loads(raw[start_obj : end + 1])
        raise
