"""
LangGraph: clarify → … → requirement → PM (brief review + PRD) → architect → scrum (PRD review + epics) → task (feasibility + tasks) → final validation → evaluate.

Validation gates support up to 2 auto-retries before halting.
"""

from __future__ import annotations

import json
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


def compile_planning_graph(orch: Orchestrator, *, checkpointer: object):
    """Build compiled LangGraph with validation gates, retry loops, and evaluation.

    ``checkpointer`` enables LangGraph persistence at step boundaries (memory, SQLite, or Postgres).
    """

    def _unique_errors(errs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for err in errs:
            msg = str(err).strip()
            if not msg or msg in seen:
                continue
            seen.add(msg)
            out.append(msg)
        return out

    # ──────────────────────────────────────────────────────────────
    # Pipeline nodes
    # ──────────────────────────────────────────────────────────────

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
            clean = _unique_errors(errs)
            return {
                "halt_reason": clean[0] if clean else "Please add a bit more context before generating docs.",
                "validation_errors": clean,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_requirement(state: PlanningState) -> dict:
        rag_context = orch.retrieve_context(
            state["product_idea"],
            session_id=state.get("session_id"),
            top_k=4,
        )
        brief = orch.requirement_agent.create_project_brief(
            state["product_idea"],
            state["qa_pairs"] or [],
            context_chunks=rag_context,
        )
        return {"project_brief": brief, "rag_context": rag_context}

    def node_validate_brief(state: PlanningState) -> dict:
        brief = state.get("project_brief") or {}
        if brief.get("error"):
            msg = "We couldn't generate a valid project brief from the current inputs. Please refine your answers and try again."
            return {"halt_reason": msg, "validation_errors": [msg]}
        ok, errs = validate_project_brief(brief)
        if not ok:
            clean = _unique_errors(errs)
            return {
                "halt_reason": "The generated project brief is incomplete. Please try again.",
                "validation_errors": clean,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_retry_requirement(state: PlanningState) -> dict:
        """Re-run requirement agent with validation errors injected as context."""
        errors = state.get("validation_errors") or []
        error_context = "\n".join(f"- {e}" for e in errors)
        rag_context = orch.retrieve_context(
            state["product_idea"],
            session_id=state.get("session_id"),
            top_k=4,
        )
        enhanced_idea = (
            f"{state['product_idea']}\n\n"
            f"IMPORTANT: Your previous output had these validation errors — fix them:\n{error_context}"
        )
        brief = orch.requirement_agent.create_project_brief(
            enhanced_idea,
            state.get("qa_pairs") or [],
            context_chunks=rag_context,
        )
        return {
            "project_brief": brief,
            "rag_context": rag_context,
            "clarify_round": (state.get("clarify_round") or 0) + 1,
            "halt_reason": None,
            "validation_errors": [],
        }

    def node_pm(state: PlanningState) -> dict:
        brief = state["project_brief"]
        rag_context = state.get("rag_context") if isinstance(state.get("rag_context"), list) else None
        review = orch.pm_agent.review_project_brief(brief)
        patched_brief = apply_pm_review_feedback_to_brief(brief, review)
        prd = orch.pm_agent.create_prd(
            patched_brief,
            brief_review=review,
            context_chunks=rag_context,
        )
        return {
            "project_brief": patched_brief,
            "prd": prd,
            "pm_brief_review": review,
        }

    def node_validate_prd(state: PlanningState) -> dict:
        prd = state.get("prd") or {}
        if prd.get("error"):
            msg = "We couldn't generate a valid PRD right now. Please try again in a moment."
            return {"halt_reason": msg, "validation_errors": [msg]}
        ok, errs = validate_prd(prd)
        if not ok:
            clean = _unique_errors(errs)
            return {
                "halt_reason": "The generated PRD is missing required sections. Please retry generation.",
                "validation_errors": clean,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_retry_pm(state: PlanningState) -> dict:
        """Re-run PM agent with validation errors injected as context."""
        errors = state.get("validation_errors") or []
        error_context = "\n".join(f"- {e}" for e in errors)
        brief = state.get("project_brief") or {}
        rag = state.get("rag_context") if isinstance(state.get("rag_context"), list) else None
        review = orch.pm_agent.review_project_brief(brief)
        patched = apply_pm_review_feedback_to_brief(brief, review)
        prd = orch.pm_agent.create_prd(
            patched,
            brief_review={
                **review,
                "validation_feedback": f"Fix these PRD errors:\n{error_context}",
            },
            context_chunks=rag,
        )
        return {
            "prd": prd,
            "pm_brief_review": review,
            "clarify_round": (state.get("clarify_round") or 0) + 1,
            "halt_reason": None,
            "validation_errors": [],
        }

    def node_architect(state: PlanningState) -> dict:
        arch = orch.architect_agent.create_architecture(
            state["prd"],
            state.get("project_brief"),
        )
        return {"architecture": arch}

    def node_validate_architecture(state: PlanningState) -> dict:
        arch = state.get("architecture") or {}
        if arch.get("error"):
            msg = "We couldn't generate a valid architecture draft. Please try again."
            return {"halt_reason": msg, "validation_errors": [msg]}
        ok, errs = validate_architecture(arch)
        if not ok:
            clean = _unique_errors(errs)
            return {
                "halt_reason": "The architecture draft is incomplete. Please retry generation.",
                "validation_errors": clean,
            }
        return {"halt_reason": None, "validation_errors": []}

    def node_retry_architect(state: PlanningState) -> dict:
        """Re-run architect agent with validation errors injected."""
        errors = state.get("validation_errors") or []
        error_context = "\n".join(f"- {e}" for e in errors)
        prd = dict(state.get("prd") or {})
        prd["_arch_validation_feedback"] = f"Fix these architecture errors:\n{error_context}"
        arch = orch.architect_agent.create_architecture(
            prd,
            state.get("project_brief"),
        )
        return {
            "architecture": arch,
            "clarify_round": (state.get("clarify_round") or 0) + 1,
            "halt_reason": None,
            "validation_errors": [],
        }

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

    def node_evaluate(state: PlanningState) -> dict:
        """Post-pipeline quality scoring via EvaluatorAgent."""
        from utils.evaluator import EvaluatorAgent
        evaluator = EvaluatorAgent()
        idea = state.get("product_idea", "")
        results = {}
        brief = state.get("project_brief") or {}
        if brief and not brief.get("error"):
            try:
                results["brief_eval"] = evaluator.evaluate_output(
                    idea, json.dumps(brief)[:3000]
                )
            except Exception:
                pass
        prd = state.get("prd") or {}
        if prd and not prd.get("error"):
            try:
                results["prd_eval"] = evaluator.evaluate_output(
                    idea, json.dumps(prd)[:3000]
                )
            except Exception:
                pass
        return {"evaluation_scores": results}

    def node_halt(state: PlanningState) -> dict:
        reason = state.get("halt_reason") or "unknown"
        return {"pipeline_error": reason}

    # ──────────────────────────────────────────────────────────────
    # Routing functions
    # ──────────────────────────────────────────────────────────────

    def route_ok(state: PlanningState) -> Literal["next", "halt"]:
        if state.get("halt_reason"):
            return "halt"
        return "next"

    def route_brief_validation(state: PlanningState) -> Literal["next", "retry", "halt"]:
        if not state.get("halt_reason"):
            return "next"
        if (state.get("clarify_round") or 0) < (state.get("max_clarify_rounds") or 2):
            return "retry"
        return "halt"

    def route_prd_validation(state: PlanningState) -> Literal["next", "retry", "halt"]:
        if not state.get("halt_reason"):
            return "next"
        if (state.get("clarify_round") or 0) < (state.get("max_clarify_rounds") or 2):
            return "retry"
        return "halt"

    def route_arch_validation(state: PlanningState) -> Literal["next", "retry", "halt"]:
        if not state.get("halt_reason"):
            return "next"
        if (state.get("clarify_round") or 0) < (state.get("max_clarify_rounds") or 2):
            return "retry"
        return "halt"

    # ──────────────────────────────────────────────────────────────
    # Build graph
    # ──────────────────────────────────────────────────────────────

    g = StateGraph(PlanningState)

    # Register nodes
    g.add_node("clarify", node_clarify)
    g.add_node("validate_qa", node_validate_qa)
    g.add_node("requirement", node_requirement)
    g.add_node("validate_brief", node_validate_brief)
    g.add_node("retry_requirement", node_retry_requirement)
    g.add_node("pm", node_pm)
    g.add_node("validate_prd", node_validate_prd)
    g.add_node("retry_pm", node_retry_pm)
    g.add_node("architect", node_architect)
    g.add_node("validate_architecture", node_validate_architecture)
    g.add_node("retry_architect", node_retry_architect)
    g.add_node("scrum", node_scrum)
    g.add_node("task", node_task)
    g.add_node("final_validation", node_final_validation)
    g.add_node("evaluate", node_evaluate)
    g.add_node("halt", node_halt)

    # Wire edges
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
        route_brief_validation,
        {"next": "pm", "retry": "retry_requirement", "halt": "halt"},
    )
    g.add_edge("retry_requirement", "validate_brief")

    g.add_edge("pm", "validate_prd")
    g.add_conditional_edges(
        "validate_prd",
        route_prd_validation,
        {"next": "architect", "retry": "retry_pm", "halt": "halt"},
    )
    g.add_edge("retry_pm", "validate_prd")

    g.add_edge("architect", "validate_architecture")
    g.add_conditional_edges(
        "validate_architecture",
        route_arch_validation,
        {"next": "scrum", "retry": "retry_architect", "halt": "halt"},
    )
    g.add_edge("retry_architect", "validate_architecture")

    g.add_edge("scrum", "task")
    g.add_edge("task", "final_validation")
    g.add_edge("final_validation", "evaluate")
    g.add_edge("evaluate", END)
    g.add_edge("halt", END)

    return g.compile(checkpointer=checkpointer)
