"""Task Agent — developer-ready atomic tasks and subtasks per story."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from agents.base import BaseAgent
from agents.json_utils import parse_llm_json
from agents.prompt_config import AGENT_PROMPT_CONFIG
from backend.prompt_loader import prepare_rendered
from utils.runtime_config import get_task_agent_settings

logger = logging.getLogger(__name__)


def renumber_task_ids_globally(payload: dict) -> dict:
    """
    Assign globally unique ids TASK-1 … TASK-N in stable order:
    order of entries in payload['tasks'], then order of tasks within each story group.
    Mutates task dicts in place.
    """
    groups = payload.get("tasks")
    if not isinstance(groups, list):
        return payload
    n = 1
    for story_group in groups:
        if not isinstance(story_group, dict):
            continue
        for task in story_group.get("tasks") or []:
            if isinstance(task, dict):
                task["id"] = f"TASK-{n}"
                n += 1
    return payload


class TaskAgent(BaseAgent):
    """
    Principal Engineer / Tech Lead — feasibility check, then break stories into shippable work.
    Processes one epic per LLM call (bounded tokens), epics in parallel.
    """

    audit_name = "TASK_AGENT"

    def validate_feasibility(
        self,
        epics: list,
        prd: dict[str, Any] | None = None,
        architecture: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "epics": epics,
            "prd": prd or {},
            "architecture": architecture or {},
        }
        cfg = AGENT_PROMPT_CONFIG["task_agent"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            json.dumps(payload, indent=2, ensure_ascii=False),
            phase="task_feasibility",
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

    def _process_single_epic(
        self,
        idx: int,
        epic: dict,
        feasibility_context: str = "",
    ) -> tuple[int, list, dict | None]:
        story_count = len(epic.get("stories") or [])
        logger.info(
            "TaskAgent: epic %s (%s) — %s stories (worker)",
            idx,
            epic.get("id"),
            story_count,
        )
        epic_blob = {"epic": epic}
        if feasibility_context:
            epic_blob["feasibility_review_excerpt"] = feasibility_context[:3500]
        payload = json.dumps(epic_blob, indent=2, ensure_ascii=False)
        cfg = AGENT_PROMPT_CONFIG["task_epic"]
        system, loaded_sys, meta_sys = prepare_rendered(str(cfg["prompt"]), {})
        text = self.call_llm(
            system,
            payload,
            phase=f"epic_{idx}",
            max_tokens=loaded_sys.max_tokens,
            prompt_audit={"system": meta_sys},
        )
        try:
            data = parse_llm_json(text)
            if not isinstance(data, dict):
                raise ValueError("root is not an object")
            part = data.get("tasks")
            if not isinstance(part, list):
                raise ValueError("missing tasks array")
            return idx, part, None
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return idx, [], {
                "epic_index": idx,
                "epic_id": epic.get("id"),
                "error": str(e),
                "raw_preview": (text or "")[:1200],
            }

    def create_tasks(
        self,
        epics: list,
        *,
        feasibility_review: dict[str, Any] | None = None,
    ) -> dict:
        if not epics:
            return {"tasks": []}

        feasibility_context = ""
        if feasibility_review and not feasibility_review.get("error"):
            feasibility_context = json.dumps(feasibility_review, ensure_ascii=False)

        n_epics = len(epics)
        workers = min(
            max(1, get_task_agent_settings().max_workers),
            n_epics,
        )
        logger.info(
            "TaskAgent: %s epic(s), parallel workers=%s",
            n_epics,
            workers,
        )

        ordered_parts: list[list] = [[] for _ in range(n_epics)]
        failures: list = []

        if workers == 1:
            for idx, epic in enumerate(epics):
                _i, part, fail = self._process_single_epic(
                    idx, epic, feasibility_context
                )
                ordered_parts[_i] = part
                if fail:
                    failures.append(fail)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {
                    pool.submit(
                        self._process_single_epic, idx, epic, feasibility_context
                    ): idx
                    for idx, epic in enumerate(epics)
                }
                for fut in as_completed(futs):
                    idx, part, fail = fut.result()
                    ordered_parts[idx] = part
                    if fail:
                        failures.append(fail)

        merged: list = []
        for part in ordered_parts:
            merged.extend(part)

        out: dict = {"tasks": merged}
        renumber_task_ids_globally(out)

        total = sum(
            len(sg.get("tasks", []))
            for sg in merged
            if isinstance(sg, dict)
        )
        logger.info("TaskAgent: %s tasks after global renumber", total)

        if failures:
            out["task_generation_warnings"] = failures
        return out

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        epics = (state.get("epics_stories") or {}).get("epics", [])
        if not epics and state.get("epics"):
            epics = state["epics"]
        return {"tasks": self.create_tasks(epics)}
