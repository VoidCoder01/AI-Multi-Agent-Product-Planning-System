"""Tech Architect Agent — system design, stack, textual data flows."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json
from agents.prompt_config import AGENT_PROMPT_CONFIG
from backend.prompt_loader import prepare_rendered


class ArchitectAgent(BaseAgent):
    """Principal / Staff Engineer — architecture and feasibility framing."""

    audit_name = "ARCHITECT_AGENT"

    def create_architecture(
        self,
        prd: dict[str, Any],
        project_brief: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parts = [f"PRD:\n{json.dumps(prd, indent=2, ensure_ascii=False)}"]
        if project_brief:
            parts.append(
                f"\nProject brief (context):\n{json.dumps(project_brief, indent=2, ensure_ascii=False)}"
            )
        cfg = AGENT_PROMPT_CONFIG["architect_agent"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            "\n".join(parts),
            phase="architecture",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys},
        )
        try:
            data = parse_llm_json(text)
            if isinstance(data, dict) and data:
                return data
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
        return {"error": "parse_failed", "raw_preview": text[:1200]}

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        prd = state.get("prd") or {}
        brief = state.get("project_brief")
        return {"architecture": self.create_architecture(prd, brief if isinstance(brief, dict) else None)}
