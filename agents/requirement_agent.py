"""Requirement Agent — structured project brief."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json
from agents.prompt_config import AGENT_PROMPT_CONFIG
from backend.prompt_loader import prepare_rendered


class RequirementAgent(BaseAgent):
    """Principal Requirements Engineer — brief must be complete and concise."""

    audit_name = "REQUIREMENT_AGENT"

    def create_project_brief(
        self, product_idea: str, qa_pairs: list[tuple[str, str]]
    ) -> dict[str, Any]:
        qa_text = "\n".join(f"Q: {q}\nA: {a}" for q, a in qa_pairs)
        user_message = f"Product idea:\n{product_idea}\n\nQ&A:\n{qa_text}"
        cfg = AGENT_PROMPT_CONFIG["requirement_agent"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            user_message,
            phase="project_brief",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys},
        )
        try:
            data = parse_llm_json(text)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
        return {"error": "parse_failed", "raw_preview": text[:1200]}

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        idea = state.get("product_idea") or ""
        qa = state.get("qa_pairs") or []
        brief = self.create_project_brief(idea, qa)
        return {"project_brief": brief}
