"""
LangGraph: clarify → … → requirement → PM (brief review + PRD) → architect → scrum (PRD review + epics) → task (feasibility + tasks) → final validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from langgraph.graph import END, START, StateGraph

from schemas.state import PlanningState
from schemas.validation import (
    apply_feasibility_feedback_to_story_and_tasks,
    apply_pm_review_feedback_to_brief,
    run_final_pipeline_validation,
    validate_architecture,
    validate_project_brief,
    validate_prd,
    validate_qa_context,
)

if TYPE_CHECKING:
    from backend.orchestrator import Orchestrator


def compile_planning_graph(orch: Orchestrator):
    """Build compiled LangGraph with validation gates and halt on failure."""

    def node_clarify(state: PlanningState) -> dict:
        idea = state["product_idea"]
        ua = state.get("user_answers") or {}
        qs = state.get("questions")
        if not qs:
            qs = orch.clarification_agent.ask_questions(idea)
        qa_pairs = [
            (qs[i], str(ua.get(f"q{i + 1}", "")))
            for i in range(len(qs))
        ]
        return {
            "questions": qs,
            "qa_pairs": qa_pairs,
            "clarifications": qs,
            "halt_reason": None,
            "validation_errors": [],
        }

    def node_validate_qa(state: PlanningState) -> dict:
        ok, errs = validate_qa_context(state.get("qa_pairs") or [])
        if not ok:
            return {
                "halt_reason": "qa_validation: " + "; ".join(errs),
                "validation_errors": errs,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_requirement(state: PlanningState) -> dict:
        brief = orch.requirement_agent.create_project_brief(
            state["product_idea"],
            state["qa_pairs"] or [],
        )
        return {"project_brief": brief}

    def node_validate_brief(state: PlanningState) -> dict:
        brief = state.get("project_brief") or {}
        if brief.get("error"):
            msg = "requirement_agent returned unparsed output"
            return {
                "halt_reason": "brief_validation: " + msg,
                "validation_errors": [msg],
            }
        ok, errs = validate_project_brief(brief)
        if not ok:
            return {
                "halt_reason": "brief_validation: " + "; ".join(errs),
                "validation_errors": errs,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_pm(state: PlanningState) -> dict:
        brief = state["project_brief"]
        review = orch.pm_agent.review_project_brief(brief)
        patched_brief = apply_pm_review_feedback_to_brief(brief, review)
        prd = orch.pm_agent.create_prd(patched_brief, brief_review=review)
        return {
            "project_brief": patched_brief,
            "prd": prd,
            "pm_brief_review": review,
        }

    def node_validate_prd(state: PlanningState) -> dict:
        prd = state.get("prd") or {}
        if prd.get("error"):
            msg = "pm_agent returned unparsed output"
            return {
                "halt_reason": "prd_validation: " + msg,
                "validation_errors": [msg],
            }
        ok, errs = validate_prd(prd)
        if not ok:
            return {
                "halt_reason": "prd_validation: " + "; ".join(errs),
                "validation_errors": errs,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_architect(state: PlanningState) -> dict:
        arch = orch.architect_agent.create_architecture(
            state["prd"],
            state.get("project_brief"),
        )
        return {"architecture": arch}

    def node_validate_architecture(state: PlanningState) -> dict:
        arch = state.get("architecture") or {}
        if arch.get("error"):
            msg = "architect_agent returned unparsed output"
            return {
                "halt_reason": "architecture_validation: " + msg,
                "validation_errors": [msg],
            }
        ok, errs = validate_architecture(arch)
        if not ok:
            return {
                "halt_reason": "architecture_validation: " + "; ".join(errs),
                "validation_errors": errs,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_scrum(state: PlanningState) -> dict:
        prd = state["prd"]
        prd_review = orch.scrum_agent.review_prd(prd)
        es = orch.scrum_agent.create_epics_and_stories(
            prd,
            architecture=state.get("architecture"),
            prd_review=prd_review,
        )
        epics = es.get("epics", []) if isinstance(es, dict) else []
        return {
            "epics_stories": es,
            "epics": epics,
            "scrum_prd_review": prd_review,
        }

    def node_task(state: PlanningState) -> dict:
        epics = (state.get("epics_stories") or {}).get("epics", [])
        if not epics:
            return {
                "tasks": {"tasks": []},
                "task_feasibility": {"error": "no_epics", "overall_feasible": False},
            }
        feas = orch.task_agent.validate_feasibility(
            epics,
            state.get("prd"),
            state.get("architecture"),
        )
        tasks = orch.task_agent.create_tasks(epics, feasibility_review=feas)
        patched_es, tasks = apply_feasibility_feedback_to_story_and_tasks(
            state.get("epics_stories") or {},
            tasks,
            feas,
        )
        return {
            "epics_stories": patched_es,
            "tasks": tasks,
            "task_feasibility": feas,
        }

    def node_final_validation(state: PlanningState) -> dict:
        report = run_final_pipeline_validation(state)
        return {"final_validation": report}

    def node_halt(state: PlanningState) -> dict:
        reason = state.get("halt_reason") or "unknown"
        return {"pipeline_error": reason}

    def route_ok(state: PlanningState) -> Literal["next", "halt"]:
        if state.get("halt_reason"):
            return "halt"
        return "next"

    g = StateGraph(PlanningState)
    g.add_node("clarify", node_clarify)
    g.add_node("validate_qa", node_validate_qa)
    g.add_node("requirement", node_requirement)
    g.add_node("validate_brief", node_validate_brief)
    g.add_node("pm", node_pm)
    g.add_node("validate_prd", node_validate_prd)
    g.add_node("architect", node_architect)
    g.add_node("validate_architecture", node_validate_architecture)
    g.add_node("scrum", node_scrum)
    g.add_node("task", node_task)
    g.add_node("final_validation", node_final_validation)
    g.add_node("halt", node_halt)

    g.add_edge(START, "clarify")
    g.add_edge("clarify", "validate_qa")
    g.add_conditional_edges(
        "validate_qa",
        route_ok,
        {"next": "requirement", "halt": "halt"},
    )
    g.add_edge("requirement", "validate_brief")
    g.add_conditional_edges(
        "validate_brief",
        route_ok,
        {"next": "pm", "halt": "halt"},
    )
    g.add_edge("pm", "validate_prd")
    g.add_conditional_edges(
        "validate_prd",
        route_ok,
        {"next": "architect", "halt": "halt"},
    )
    g.add_edge("architect", "validate_architecture")
    g.add_conditional_edges(
        "validate_architecture",
        route_ok,
        {"next": "scrum", "halt": "halt"},
    )
    g.add_edge("scrum", "task")
    g.add_edge("task", "final_validation")
    g.add_edge("final_validation", END)
    g.add_edge("halt", END)

    return g.compile()
