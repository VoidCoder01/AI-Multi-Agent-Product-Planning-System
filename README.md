# AI Multi-Agent Product Planning System

Multi-agent orchestration: a user provides a product idea, the system asks clarifying questions, then **collaborating agents** produce structured artifacts — **project brief**, **PRD**, **epics**, **user stories**, **tasks**, and **subtasks**.

**Stack:** Python 3.11+, **FastAPI**, **OpenAI-compatible SDK** (native OpenAI or OpenRouter), **LangGraph** (graph workflow).

---

## Quickstart (Docker)

```bash
cp .env.example .env
# Add OPENAI_API_KEY (or OPENROUTER_API_KEY) to .env
docker compose up --build
# API Docs: http://localhost:8000/docs
```

---

## System Architecture

```text
                    ┌─────────────────────────────────────┐
                    │   Master Orchestrator (LangGraph)   │
                    │   with auto-retry on validation     │
                    └──────────────┬──────────────────────┘
                                   │
     ┌─────────────────────────────┼─────────────────────────────┐
     ▼                             ▼                             ▼
 Clarification               Requirement                    PM Agent
 Agent (questions)           Agent (brief + RAG)           (PRD + RAG)
                                   │                             │
                                   └────────────┬────────────────┘
                                                ▼
                                         Architect Agent
                                       (technical design)
                                                ▼
                                          Scrum Agent
                                    (epics + user stories)
                                                ▼
                                           Task Agent
                                       (tasks + subtasks)
                                                ▼
                   ┌────────────────────────────────────────────┐
                   │               Evaluation System            │
                   │ EvaluatorAgent scores output quality       │
                   └────────────────────────────────────────────┘

────────────────── Supporting Infrastructure ────────────────────

  Document Upload → Chunker → BagOfWordsHashEmbedding → Vector Index
                                   ↓
                     VectorRetriever (top-k cosine)
                                   ↓
                 LexicalOverlapReranker (BM25 token match)
                                   ↓
                       Context Injection into Agents

  CacheLayer (redis / in-memory fallback) mapped in BaseAgent
  JSONL LLM Audit Logger · MemoryStore (session persistence)
  True Per-Node SSE Streaming · Mermaid Workflow Diagram API
```

---

## Agent Pipeline

| Agent | Responsibility | RAG-aware | Validated Output |
|-------|----------------|-----------|------------------|
| **Clarification** | Scope, users, features, constraints | — | JSON array of questions |
| **Requirement** | Structured brief from Q&A | ✅ | JSON: name, problem, users, features |
| **PM** | Brief review + PRD | ✅ | JSON: overview, goals, personas, NFR, metrics |
| **Architect** | Technical architecture | — | JSON: services, stack, data flow, scale |
| **Scrum** | Agile backlog | — | JSON: epics → stories → AC |
| **Task** | Engineering tasks breakdown | — | JSON: tasks + subtasks |
| **Evaluator** | QA scoring post-generation | — | JSON: relevance/hallucination scores |

*Note: The LangGraph pipeline supports self-healing behavior. If a node fails validation (e.g., PM, Requirement, Architect), the system automatically routes to a retry node, injecting the error feedback into the LLM prompt. Nodes are allowed max 2 retries before halting.*

---

## Phase 1 — RAG Foundation

### Document Upload (`POST /api/upload`)
Upload a PDF/TXT/audio file (`.txt`, `.pdf`, `.mp3`, `.wav`, `.m4a`, `.webm`) to inject domain knowledge into the pipeline.
Audio uploads are auto-transcribed with Whisper first, then chunked/indexed like text documents.

### Embeddings & Retrieval
> **Design decision**: We use deterministic hash-based embeddings and lexical reranking instead of neural models (sentence-transformers, OpenAI embeddings). This is a deliberate MVP tradeoff: zero external dependencies, deterministic results, sub-millisecond latency. For production, swap in `text-embedding-3-small` and a cross-encoder reranker.

- `BagOfWordsHashEmbedding` — deterministic 256-dim hashing. Not a learned embedding; used as zero-dependency local baseline.
- `VectorRetriever` — cosine similarity top-k selection.
- `LexicalOverlapReranker` — BM25-style lexical token overlap scoring. Lightweight alternative to cross-encoders.

### Context Injection
`RequirementAgent` and `PMAgent` dynamically retrieve relevant chunks based on the product idea, injecting them directly into the agent system prompt context.

---

## Phase 2 — Production Features

- **Genuine SSE Streaming**: `/api/generate/stream` uses an asynchronous generator consuming LangGraph's native stream, yielding events per node *as they happen*.
- **Caching (`utils/cache.py`)**: `CacheLayer` is explicitly wired into `BaseAgent.call_llm()`. Identical prompts return instantly matching previous cached LLM responses. Falls back to Redis if `REDIS_URL` is set, otherwise in-memory.
- **Evaluation System (`utils/evaluator.py`)**: `EvaluatorAgent` runs as a formal final evaluation node inside the graph, scoring Briefs and PRDs for relevance and hallucination.
- **Logging (`utils/agent_logger.py`)**: Every LLM call strictly appends to `logs/agent_audit.jsonl` with precise durations and attempt counts.

---

## Known Limitations & Future Work

### Known Limitations
- RAG uses lightweight hash-based embeddings (not neural) — see Design Decisions.
- No persistent database — sessions stored as JSON files.
- Frontend not included in this submission (API-first design).

### Future Work
- Neural embeddings (OpenAI `text-embedding-3-small`).
- Cross-encoder reranking (`ms-marco-MiniLM`).
- WebSocket streaming for real-time bidirectional UI updates.
- PostgreSQL session persistence.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/questions` | Generate clarification questions |
| `POST` | `/api/generate` | Run full planning pipeline synchronously |
| `POST` | `/api/generate/stream` | Run with live SSE progress streaming |
| `POST` | `/api/upload` | Upload PDF/TXT/audio for RAG context (audio uses Whisper transcription) |
| `GET`  | `/api/sessions` | List saved sessions |
| `GET`  | `/api/sessions/{id}` | Load session artifacts |
| `GET`  | `/api/workflow/diagram` | Mermaid graph of LangGraph pipeline |
| `GET`  | `/health` | API system and provider API key status |

---

## Testing & Verification

```bash

# 1. activate virtual environment and Run local environment
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Run API server
uvicorn backend.main:app

# 3. Run Pytest Suite (tests use mocked OpenAI responses)
pytest backend/tests/ -v
```
# Frontend (Vite + React)

**Project docs:** [../README.md](../README.md) (architecture, setup, API).

## Commands

```bash
npm install
npm run dev    # http://localhost:8080/ui/ — proxies /api → FastAPI :8000
npm run build  # dist/ served by FastAPI at http://127.0.0.1:8000/ui/
```

`base` is `/ui` to match the FastAPI static mount.

---

## License
MIT — see [LICENSE](LICENSE).
