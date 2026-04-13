# System Architecture

## Overview

This system implements a multi-agent orchestration pipeline using LangGraph as the workflow engine and Anthropic Claude as the LLM backbone. The architecture follows a directed acyclic graph (DAG) pattern where each agent is a node with validation gates between stages.

## Agent Pipeline

```text
User Input -> Clarification Agent -> QA Validation Gate
  -> Requirement Agent -> Brief Validation Gate
  -> PM Agent (Brief Review + PRD) -> PRD Validation Gate
  -> Architect Agent -> Architecture Validation Gate
  -> Scrum Agent (PRD Review + Epics/Stories)
  -> Task Agent (Feasibility + Task Breakdown)
  -> Final Cross-Document Validation -> Output
```

Any validation gate failure routes to a `halt` node that stops the pipeline with a diagnostic error, preventing garbage-in-garbage-out propagation.

## Key Design Decisions

1. **LangGraph over simple sequential calls** - conditional routing enables validation gates, retry loops, and halt-on-failure, which a flat function chain cannot express.
2. **One agent class per role** - each agent has a single responsibility with its own prompt, parse logic, and audit name.
3. **Prompts as versioned files** - prompts live as Markdown with YAML frontmatter under `backend/prompts/`, separating prompt iteration from code logic changes.
4. **Review-then-generate pattern** - PM reviews the brief before writing PRD; Scrum reviews the PRD before creating epics; review feedback is programmatically applied downstream.
5. **Parallel epic processing** - TaskAgent processes each epic in a separate thread (configurable via `TASK_AGENT_MAX_WORKERS`), then globally renumbers task IDs.
6. **Cross-document validation** - final validation checks consistency across all artifacts (stack references, MVP scope leaks, metric contradictions, story-to-task traceability).

## Data Flow

```text
PlanningState (TypedDict)
├── product_idea: str
├── user_answers: dict
├── questions: list[str]
├── qa_pairs: list[tuple]
├── project_brief: dict        <- RequirementAgent
├── pm_brief_review: dict      <- PMAgent.review_project_brief()
├── prd: dict                  <- PMAgent.create_prd()
├── architecture: dict         <- ArchitectAgent
├── scrum_prd_review: dict     <- ScrumAgent.review_prd()
├── epics_stories: dict        <- ScrumAgent.create_epics_and_stories()
├── task_feasibility: dict     <- TaskAgent.validate_feasibility()
├── tasks: dict                <- TaskAgent.create_tasks()
└── final_validation: dict     <- run_final_pipeline_validation()
```

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM | Anthropic Claude (Sonnet 4) | Strong structured output and context window |
| Orchestration | LangGraph | Native state machine with conditional edges |
| API | FastAPI | Async-capable, auto-generated OpenAPI docs, Pydantic validation |
| Prompts | Markdown + YAML frontmatter | Version-controlled, human-readable, template-friendly |
| Memory | File-based JSON per session | Simple, debuggable, no external DB dependency for MVP |
| Logging | JSONL append | Structured, grep-friendly, no infrastructure overhead |
