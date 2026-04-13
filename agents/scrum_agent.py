"""Scrum Agent — reviews PRD, then epics/stories with MVP tagging and priorities."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json
from agents.prompt_config import AGENT_PROMPT_CONFIG
from backend.prompt_loader import prepare_rendered


class ScrumAgent(BaseAgent):
    """Certified Scrum Master — validates PRD fit, then backlog with MVP discipline."""

    audit_name = "SCRUM_AGENT"

    def review_prd(self, prd: dict[str, Any]) -> dict[str, Any]:
        cfg = AGENT_PROMPT_CONFIG["scrum_agent"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            f"PRD:\n{json.dumps(prd, indent=2, ensure_ascii=False)}",
            phase="scrum_review_prd",
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

    def create_epics_and_stories(
        self,
        prd: dict[str, Any],
        *,
        architecture: dict[str, Any] | None = None,
        prd_review: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parts = [f"PRD:\n{json.dumps(prd, indent=2, ensure_ascii=False)}"]
        if architecture and not architecture.get("error"):
            parts.append(
                "\nArchitecture (for dependency ordering):\n"
                f"{json.dumps(architecture, indent=2, ensure_ascii=False)}"
            )
        if prd_review and not prd_review.get("error"):
            parts.append(
                "\nYour prior PRD review (address concerns in epic order and MVP tagging):\n"
                f"{json.dumps(prd_review, indent=2, ensure_ascii=False)}"
            )
        cfg = AGENT_PROMPT_CONFIG["scrum_epics"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            "\n".join(parts),
            phase="epics_stories",
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
        prd = state.get("prd") or {}
        arch = state.get("architecture")
        review = self.review_prd(prd)
        es = self.create_epics_and_stories(
            prd,
            architecture=arch if isinstance(arch, dict) else None,
            prd_review=review,
        )
        epics = es.get("epics", []) if isinstance(es, dict) else []
        return {"epics_stories": es, "epics": epics, "scrum_prd_review": review}
