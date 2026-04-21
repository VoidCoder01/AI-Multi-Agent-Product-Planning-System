# System Architecture

## Overview

The system is an API-first multi-agent planning pipeline orchestrated with LangGraph.
LLM calls use the OpenAI Python SDK pointed at OpenRouter (`base_url=https://openrouter.ai/api/v1`).
Each graph node performs one role-specific transformation and writes partial state into a shared `PlanningState`.

## Pipeline Graph

```text
User Input
  -> clarify
  -> validate_qa
  -> requirement
  -> validate_brief
      -> retry_requirement (max 2) | pm
  -> validate_prd
      -> retry_pm (max 2) | architect
  -> validate_architecture
      -> retry_architect (max 2) | scrum
  -> task
  -> final_validation
  -> evaluate
  -> END

On unrecoverable validation failures -> halt -> END
```

Retry nodes inject validation errors back into the agent prompt context, enabling self-healing behavior before hard halt.

## Data Flow

```text
PlanningState (TypedDict)
├── product_idea / user_answers / questions / qa_pairs
├── project_brief / pm_brief_review / prd
├── architecture / scrum_prd_review / epics_stories
├── task_feasibility / tasks / final_validation
├── evaluation_scores
├── validation_errors / halt_reason / pipeline_error
├── clarify_round / max_clarify_rounds
└── session_id / rag_context
```

## RAG Design

- `BagOfWordsHashEmbedding`: deterministic hash-based vectorization baseline.
- `VectorRetriever`: cosine similarity candidate retrieval from session index.
- `LexicalOverlapReranker`: lexical overlap rescoring for final top-k context.

This is an intentional zero-dependency MVP tradeoff (deterministic, fast, no external embedding API).

## Runtime and Observability

- `CacheLayer` is wired into `BaseAgent.call_llm()` for prompt-level response caching.
- `agent_logger` records each LLM call to JSONL audit logs with timing and attempt metadata.
- `/api/generate/stream` emits SSE updates after each node actually finishes, then emits one final result event.

## Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM SDK | OpenAI client + OpenRouter | Provider-agnostic routing with one SDK |
| Orchestration | LangGraph | State machine + conditional routing + retries |
| API | FastAPI | Validation, OpenAPI docs, async-compatible server |
| Memory | File-based JSON sessions | Simple persistence with low setup overhead |
| Caching | Redis or in-memory fallback | Lower latency/repeated prompt cost |
| Retrieval | Hash embeddings + lexical reranker | Lightweight local RAG baseline |
