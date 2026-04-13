"""Shared LangGraph state (TypedDict for reducer-less merge)."""

from __future__ import annotations

from typing import TypedDict


class PlanningState(TypedDict, total=False):
    """Full planning state flowing through the graph."""

    user_input: str
    product_idea: str
    user_answers: dict
    questions: list[str] | None
    qa_pairs: list[tuple[str, str]]
    clarifications: list[str]
    project_brief: dict
    pm_brief_review: dict
    prd: dict
    architecture: dict
    epics_stories: dict
    epics: list  # alias convenience
    scrum_prd_review: dict
    task_feasibility: dict
    tasks: dict
    final_validation: dict
    validation_errors: list[str]
    clarify_round: int
    max_clarify_rounds: int
    pipeline_error: str | None
    needs_retry_clarify: bool
    halt_reason: str | None
    session_id: str | None
