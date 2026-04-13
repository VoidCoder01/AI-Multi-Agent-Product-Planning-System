"""Config-driven mapping of agents to prompt files (under backend/prompts) and default models."""

from __future__ import annotations

from typing import Any

from utils.runtime_config import default_model_name

# Mirrors ANTHROPIC_MODEL / BaseAgent — documentation for prompts; runtime uses BaseAgent.model.
_DEFAULT_MODEL = default_model_name()

AGENT_PROMPT_CONFIG: dict[str, dict[str, Any]] = {
    "prd_agent": {
        "model": _DEFAULT_MODEL,
        "prompt": "prd/v1.md",
        "user_prompt": "pm/prd_user_v1.md",
    },
    "pm_review_brief": {
        "model": _DEFAULT_MODEL,
        "prompt": "pm/review_brief_v1.md",
        "user_prompt": "pm/review_brief_user_v1.md",
    },
    "clarification_agent": {
        "model": _DEFAULT_MODEL,
        "prompt": "clarification/ask_v2.md",
    },
    "clarification_refine": {
        "model": _DEFAULT_MODEL,
        "prompt": "clarification/refine_v1.md",
    },
    "requirement_agent": {
        "model": _DEFAULT_MODEL,
        "prompt": "requirement/brief_v2.md",
    },
    "architect_agent": {
        "model": _DEFAULT_MODEL,
        "prompt": "architect/v1.md",
    },
    "scrum_agent": {
        "model": _DEFAULT_MODEL,
        "prompt": "scrum/review_prd_v1.md",
    },
    "scrum_epics": {
        "model": _DEFAULT_MODEL,
        "prompt": "scrum/epics_stories_v1.md",
    },
    "task_agent": {
        "model": _DEFAULT_MODEL,
        "prompt": "task/feasibility_v1.md",
    },
    "task_epic": {
        "model": _DEFAULT_MODEL,
        "prompt": "task/epic_tasks_v1.md",
    },
}
