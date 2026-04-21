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
        self,
        product_idea: str,
        qa_pairs: list[tuple[str, str]],
        *,
        context_chunks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        qa_text = "\n".join(f"Q: {q}\nA: {a}" for q, a in qa_pairs)
        context_text = ""
        if context_chunks:
            trimmed = context_chunks[:4]
            context_lines = []
            for c in trimmed:
                src = str(c.get("source") or "context")
                txt = str(c.get("text") or "").strip()
                if txt:
                    context_lines.append(f"- [{src}] {txt[:600]}")
            if context_lines:
                context_text = "\n\nRetrieved context:\n" + "\n".join(context_lines)

        user_message = f"Product idea:\n{product_idea}\n\nQ&A:\n{qa_text}{context_text}"
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
        ctx = state.get("rag_context") if isinstance(state.get("rag_context"), list) else None
        brief = self.create_project_brief(idea, qa, context_chunks=ctx)
        return {"project_brief": brief}
