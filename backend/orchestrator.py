"""Master orchestrator: LangGraph workflow + file export + memory."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agents import (
    ArchitectAgent,
    ClarificationAgent,
    PMAgent,
    RequirementAgent,
    ScrumAgent,
    TaskAgent,
)
from orchestrator.checkpointing import create_planning_checkpointer
from orchestrator.graph import compile_planning_graph
from utils.memory_store import SessionStore, create_session_store
from utils.reranker import LexicalOverlapReranker
from utils.retriever import VectorRetriever

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Master orchestrator: specialized agents + LangGraph
    (clarify → … → requirement → PM review+PRD → architect → scrum review+epics → feasibility+tasks → validation).
    """

    def __init__(self) -> None:
        self.clarification_agent = ClarificationAgent()
        self.requirement_agent = RequirementAgent()
        self.pm_agent = PMAgent()
        self.architect_agent = ArchitectAgent()
        self.scrum_agent = ScrumAgent()
        self.task_agent = TaskAgent()
        self._memory: SessionStore = create_session_store()
        self._retriever = VectorRetriever(top_k=6)
        self._reranker = LexicalOverlapReranker()
        self._checkpointer, self._checkpoint_shutdown = create_planning_checkpointer()
        self._graph = compile_planning_graph(self, checkpointer=self._checkpointer)

    def shutdown_checkpointing(self) -> None:
        """Release DB connections used by the LangGraph checkpointer (e.g. Postgres)."""
        if self._checkpoint_shutdown is not None:
            self._checkpoint_shutdown()
            self._checkpoint_shutdown = None

    @staticmethod
    def _run_config(thread_id: str) -> dict:
        """RunnableConfig for LangGraph: one checkpoint thread per pipeline run."""
        return {"configurable": {"thread_id": thread_id}}

    def mermaid_diagram(self) -> str:
        """LangGraph structure as Mermaid (for documentation / debugging)."""
        return self._graph.get_graph().draw_mermaid()

    def run_workflow(
        self,
        product_idea: str,
        user_answers: dict,
        questions: list[str] | None = None,
        *,
        session_id: str | None = None,
        owner_id: str | None = None,
    ) -> dict:
        """
        Run the LangGraph pipeline. Pass the same `questions` as /api/questions
        so answers align with prompts (q1, q2, …).
        """
        thread_id = str(uuid4())
        initial: dict = {
            "product_idea": product_idea,
            "user_answers": user_answers,
            "questions": questions,
            "user_input": product_idea,
            "session_id": session_id,
            "owner_id": owner_id,
            "clarify_round": 0,
            "max_clarify_rounds": 2,
        }
        logger.info(
            "Starting planning graph for idea length=%s thread_id=%s",
            len(product_idea),
            thread_id,
        )
        final = self._graph.invoke(initial, config=self._run_config(thread_id))
        return self._finalize_result(
            product_idea,
            final,
            session_id=session_id,
            owner_id=owner_id,
            langgraph_thread_id=thread_id,
        )

    def _finalize_result(
        self,
        product_idea: str,
        final: dict,
        *,
        session_id: str | None = None,
        owner_id: str | None = None,
        langgraph_thread_id: str | None = None,
    ) -> dict:
        """Persist final graph state and shape consistent API response payload."""
        err = final.get("pipeline_error") or final.get("halt_reason")
        payload_for_memory = {
            "product_idea": product_idea,
            "questions": final.get("questions") or [],
            "project_brief": final.get("project_brief"),
            "pm_brief_review": final.get("pm_brief_review"),
            "prd": final.get("prd"),
            "architecture": final.get("architecture"),
            "scrum_prd_review": final.get("scrum_prd_review"),
            "epics_stories": final.get("epics_stories"),
            "task_feasibility": final.get("task_feasibility"),
            "tasks": final.get("tasks"),
            "final_validation": final.get("final_validation"),
            "halt_reason": final.get("halt_reason"),
            "pipeline_error": final.get("pipeline_error"),
            "validation_errors": final.get("validation_errors"),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        sid = self._memory.save(payload_for_memory, session_id=session_id, owner_id=owner_id)

        return {
            "session_id": sid,
            "langgraph_thread_id": langgraph_thread_id,
            "questions": final.get("questions") or [],
            "project_brief": final.get("project_brief") or {},
            "pm_brief_review": final.get("pm_brief_review") or {},
            "prd": final.get("prd") or {},
            "architecture": final.get("architecture") or {},
            "scrum_prd_review": final.get("scrum_prd_review") or {},
            "epics_stories": final.get("epics_stories") or {},
            "task_feasibility": final.get("task_feasibility") or {},
            "tasks": final.get("tasks") or {},
            "final_validation": final.get("final_validation") or {},
            "evaluation_scores": final.get("evaluation_scores") or {},
            "rag_context": final.get("rag_context") or [],
            "error": err,
            "halt_reason": final.get("halt_reason"),
            "validation_errors": final.get("validation_errors") or [],
        }

    def retrieve_context(
        self,
        query: str,
        *,
        session_id: str | None,
        owner_id: str | None = None,
        top_k: int = 4,
    ) -> list[dict]:
        """Retrieve and rerank chunks from session-level RAG index."""
        if not session_id or not query.strip():
            return []
        payload = self._memory.load(session_id, owner_id=owner_id) or {}
        rag = payload.get("rag") if isinstance(payload, dict) else None
        if not isinstance(rag, dict):
            return []
        index = rag.get("index")
        if not isinstance(index, list) or not index:
            return []
        candidates = self._retriever.retrieve(query, index, top_k=max(top_k * 2, 6))
        reranked = self._reranker.rerank(query, candidates, top_k=top_k)
        return reranked

    # ------------------------------------------------------------------
    # Human-in-the-loop streaming: start → (interrupt) → resume
    # ------------------------------------------------------------------

    _STAGE_MESSAGES: dict[str, str] = {
        "clarify": "Analyzing product idea…",
        "validate_qa": "Validating Q&A context…",
        "requirement": "Generating project brief…",
        "validate_brief": "Validating brief…",
        "pm": "PM reviewing brief & writing PRD…",
        "validate_prd": "Validating PRD…",
        "architect": "Designing technical architecture…",
        "validate_architecture": "Validating architecture…",
        "scrum": "Creating epics and user stories…",
        "task": "Breaking down tasks and subtasks…",
        "final_validation": "Running final validation…",
        "evaluate": "Scoring output quality…",
        "retry_requirement": "Retrying brief generation…",
        "retry_pm": "Retrying PRD generation…",
        "halt": "Pipeline halted — validation failed.",
    }

    def start_workflow_stream(
        self,
        product_idea: str,
        *,
        session_id: str | None = None,
        owner_id: str | None = None,
        on_chunk: object = None,
    ):
        """Start the graph, stream clarify-node events, then yield an interrupt
        event containing the generated questions and the thread_id needed to resume."""
        from agents.base import _stream_cb  # noqa: PLC0415
        if on_chunk is not None:
            _stream_cb.fn = on_chunk
        else:
            _stream_cb.fn = None  # type: ignore[assignment]

        thread_id = str(uuid4())
        initial: dict = {
            "product_idea": product_idea,
            "user_answers": {},
            "questions": None,
            "user_input": product_idea,
            "session_id": session_id,
            "owner_id": owner_id,
            "clarify_round": 0,
            "max_clarify_rounds": 2,
        }
        run_cfg = self._run_config(thread_id)
        for event in self._graph.stream(initial, config=run_cfg, stream_mode="updates"):
            for node_name, node_output in event.items():
                msg = self._STAGE_MESSAGES.get(node_name, f"Processing {node_name}…")
                yield (node_name, msg, node_output)

        # Graph paused at interrupt — read the questions from the checkpoint.
        state = self._graph.get_state(run_cfg)
        questions = (state.values or {}).get("questions") or []
        yield ("interrupt", "Clarification needed.", {"thread_id": thread_id, "questions": questions})

    def resume_workflow_stream(
        self,
        thread_id: str,
        user_answers: dict,
        questions: list[str],
        *,
        session_id: str | None = None,
        owner_id: str | None = None,
        on_chunk: object = None,
        product_idea: str = "",
    ):
        """Resume the graph after the user has answered the clarification questions."""
        from agents.base import _stream_cb  # noqa: PLC0415
        if on_chunk is not None:
            _stream_cb.fn = on_chunk
        else:
            _stream_cb.fn = None  # type: ignore[assignment]

        run_cfg = self._run_config(thread_id)
        # Recompute qa_pairs with the real answers — node_clarify already ran with
        # empty user_answers (before the interrupt), so its qa_pairs is stale.
        qa_pairs = [
            (questions[i], str(user_answers.get(f"q{i + 1}", "")))
            for i in range(len(questions))
        ]
        self._graph.update_state(
            run_cfg,
            {"user_answers": user_answers, "questions": questions, "qa_pairs": qa_pairs},
        )

        final_state: dict = {}
        for event in self._graph.stream(None, config=run_cfg, stream_mode="updates"):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    final_state.update(node_output)
                msg = self._STAGE_MESSAGES.get(node_name, f"Processing {node_name}…")
                yield (node_name, msg, node_output)

        # Read full final state from checkpoint for _finalize_result.
        state = self._graph.get_state(run_cfg)
        merged = dict(state.values or {})
        merged.update(final_state)
        if not product_idea:
            product_idea = merged.get("product_idea", "")
        yield (
            "complete",
            "Workflow complete.",
            self._finalize_result(
                product_idea,
                merged,
                session_id=session_id,
                owner_id=owner_id,
                langgraph_thread_id=thread_id,
            ),
        )

    def run_workflow_streaming(
        self,
        product_idea: str,
        user_answers: dict,
        questions: list[str] | None = None,
        *,
        session_id: str | None = None,
        owner_id: str | None = None,
    ):
        """Yield per-node updates and final API payload from one graph execution."""
        stage_messages = {
            "clarify": "Analyzing product idea…",
            "validate_qa": "Validating Q&A context…",
            "requirement": "Generating project brief…",
            "validate_brief": "Validating brief…",
            "pm": "PM reviewing brief & writing PRD…",
            "validate_prd": "Validating PRD…",
            "architect": "Designing technical architecture…",
            "validate_architecture": "Validating architecture…",
            "scrum": "Creating epics and user stories…",
            "task": "Breaking down tasks and subtasks…",
            "final_validation": "Running final validation…",
            "evaluate": "Scoring output quality…",
            "retry_requirement": "Retrying brief generation…",
            "retry_pm": "Retrying PRD generation…",
            "halt": "Pipeline halted — validation failed.",
        }
        thread_id = str(uuid4())
        initial: dict = {
            "product_idea": product_idea,
            "user_answers": user_answers,
            "questions": questions,
            "user_input": product_idea,
            "session_id": session_id,
            "owner_id": owner_id,
            "clarify_round": 0,
            "max_clarify_rounds": 2,
        }
        final_state = dict(initial)
        run_cfg = self._run_config(thread_id)
        for event in self._graph.stream(initial, config=run_cfg, stream_mode="updates"):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    final_state.update(node_output)
                msg = stage_messages.get(node_name, f"Processing {node_name}…")
                yield (node_name, msg, node_output)
        yield (
            "complete",
            "Workflow complete.",
            self._finalize_result(
                product_idea,
                final_state,
                session_id=session_id,
                owner_id=owner_id,
                langgraph_thread_id=thread_id,
            ),
        )

    def save_to_files(
        self,
        results: dict,
        output_dir: str | Path | None = None,
        *,
        version_subdir: bool = False,
    ) -> Path:
        """
        Write artifacts under `docs/` by default. Set `version_subdir=True` for
        timestamped subfolders (simple doc versioning).
        """
        repo_root = Path(__file__).resolve().parent.parent
        base = Path(output_dir) if output_dir is not None else repo_root / "docs"
        if version_subdir:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out = base / f"v_{stamp}"
        else:
            out = base
        out.mkdir(parents=True, exist_ok=True)

        def write_json_md(filename: str, title: str, payload: object) -> None:
            body = json.dumps(payload, indent=2, ensure_ascii=False)
            (out / filename).write_text(
                f"# {title}\n\n```json\n{body}\n```\n",
                encoding="utf-8",
            )

        write_json_md(
            "project_brief.md",
            "Project Brief",
            results.get("project_brief") or {},
        )
        write_json_md("prd.md", "Product Requirements Document", results.get("prd") or {})
        write_json_md(
            "architecture.md",
            "Technical architecture",
            results.get("architecture") or {},
        )
        write_json_md(
            "pm_brief_review.md",
            "PM review of brief",
            results.get("pm_brief_review") or {},
        )
        write_json_md(
            "scrum_prd_review.md",
            "Scrum review of PRD",
            results.get("scrum_prd_review") or {},
        )
        write_json_md(
            "task_feasibility.md",
            "Task feasibility review",
            results.get("task_feasibility") or {},
        )
        write_json_md(
            "final_validation.md",
            "Output validation",
            results.get("final_validation") or {},
        )

        es = results.get("epics_stories") or {}
        epics = es.get("epics", [])
        write_json_md("epics.md", "Epics", {"epics": epics})

        stories_md = _format_stories_markdown(epics)
        (out / "stories.md").write_text(stories_md, encoding="utf-8")

        write_json_md(
            "tasks.md",
            "Tasks and Subtasks",
            results.get("tasks") or {},
        )

        logger.info("Wrote documentation to %s", out)
        return out


def _format_stories_markdown(epics: list) -> str:
    """Human-readable epic / story / AC outline (plus JSON appendix)."""
    lines = ["# User Stories", ""]
    for epic in epics:
        eid = epic.get("id", "")
        etitle = epic.get("title", "Epic")
        lines.append(f"## {eid} {etitle}".strip())
        lines.append("")
        desc = epic.get("description")
        if desc:
            lines.append(f"{desc}\n")
        sc = epic.get("success_criteria")
        if sc:
            lines.append(f"**Success criteria:** {sc}\n")
        for story in epic.get("stories") or []:
            sid = story.get("id", "")
            stitle = story.get("title", "")
            lines.append(f"### {sid} {stitle}".strip())
            lines.append("")
            for ac in story.get("acceptance_criteria") or []:
                lines.append(f"- {ac}")
            lines.append("")
    lines.append("---\n")
    lines.append("```json\n")
    lines.append(json.dumps({"epics": epics}, indent=2, ensure_ascii=False))
    lines.append("\n```\n")
    return "\n".join(lines)
