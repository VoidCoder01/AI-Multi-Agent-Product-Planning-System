"""PM Agent — senior PRD: MVP phases, risks, tradeoffs; reviews brief before PRD."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json
from agents.prompt_config import AGENT_PROMPT_CONFIG
from backend.prompt_loader import prepare_rendered


class PMAgent(BaseAgent):
    """Staff Product Manager — opinionated PRD with MVP discipline and explicit decisions."""

    audit_name = "PM_AGENT"

    def review_project_brief(self, project_brief: dict[str, Any]) -> dict[str, Any]:
        cfg = AGENT_PROMPT_CONFIG["pm_review_brief"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        user, _, meta_user = prepare_rendered(
            str(cfg["user_prompt"]),
            {"project_brief_json": json.dumps(project_brief, indent=2, ensure_ascii=False)},
            validate_output_format=False,
        )
        text = self.call_llm(
            system,
            user,
            phase="pm_review_brief",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys, "user": meta_user},
        )
        try:
            data = parse_llm_json(text)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
        return {"error": "parse_failed", "raw_preview": text[:1200]}

    def create_prd(
        self,
        project_brief: dict[str, Any],
        brief_review: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cfg = AGENT_PROMPT_CONFIG["prd_agent"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        brief_section = ""
        if brief_review and not brief_review.get("error"):
            brief_section = (
                "\n\nYour prior review of this brief (must address gaps and recommendations):\n"
                f"{json.dumps(brief_review, indent=2, ensure_ascii=False)}"
            )
        user, _, meta_user = prepare_rendered(
            str(cfg["user_prompt"]),
            {
                "project_brief_json": json.dumps(
                    project_brief, indent=2, ensure_ascii=False
                ),
                "brief_review_section": brief_section,
            },
            validate_output_format=False,
        )
        text = self.call_llm(
            system,
            user,
            phase="prd",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys, "user": meta_user},
        )
        try:
            data = parse_llm_json(text)
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
        return {"error": "parse_failed", "raw_preview": text[:1200]}

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief = state.get("project_brief") or {}
        review = self.review_project_brief(brief)
        prd = self.create_prd(brief, brief_review=review)
        return {"prd": prd, "pm_brief_review": review}
