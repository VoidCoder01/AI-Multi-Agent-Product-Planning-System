"""Clarification Agent — adaptive questions before requirements."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json
from agents.prompt_config import AGENT_PROMPT_CONFIG
from backend.prompt_loader import prepare_rendered


class ClarificationAgent(BaseAgent):
    """Senior Business Analyst: surface gaps in scope, users, value, constraints."""

    audit_name = "CLARIFICATION_AGENT"

    def ask_questions(self, product_idea: str) -> list[str]:
        cfg = AGENT_PROMPT_CONFIG["clarification_agent"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            f"Product idea:\n{product_idea.strip()}",
            phase="ask_questions",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys},
        )
        return self._parse_question_list(text)

    def refine_questions(
        self,
        product_idea: str,
        validation_errors: list[str],
        prior_questions: list[str] | None,
    ) -> list[str]:
        cfg = AGENT_PROMPT_CONFIG["clarification_refine"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        payload = {
            "product_idea": product_idea,
            "validation_errors": validation_errors,
            "prior_questions": prior_questions or [],
        }
        text = self.call_llm(
            system,
            json.dumps(payload, indent=2),
            phase="refine_questions",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys},
        )
        out = self._parse_question_list(text)
        return out[:3] if len(out) > 3 else out

    def _parse_question_list(self, text: str) -> list[str]:
        try:
            data = parse_llm_json(text)
            if isinstance(data, list):
                out = [str(q).strip() for q in data if str(q).strip()]
                if out:
                    return out
        except (ValueError, TypeError, KeyError):
            pass
        return [
            "What is the primary user segment and their top pain?",
            "What is in scope for the first release vs later?",
            "What regulatory, security, or platform constraints apply?",
        ]

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node helper: emit clarifications list for memory."""
        idea = state.get("product_idea") or state.get("user_input") or ""
        qs = self.ask_questions(idea)
        return {"clarifications": qs, "questions": qs}
