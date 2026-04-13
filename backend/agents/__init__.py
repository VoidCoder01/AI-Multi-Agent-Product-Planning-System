"""Shim: re-exports root `agents` package for backward compatibility."""

from agents import (  # noqa: F401
    ClarificationAgent,
    PMAgent,
    RequirementAgent,
    ScrumAgent,
    TaskAgent,
    renumber_task_ids_globally,
)
from agents.base import BaseAgent

__all__ = [
    "BaseAgent",
    "ClarificationAgent",
    "RequirementAgent",
    "PMAgent",
    "ScrumAgent",
    "TaskAgent",
    "renumber_task_ids_globally",
]
