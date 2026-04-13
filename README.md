# AI Multi-Agent Product Planning System

Multi-agent orchestration (BMAD-style): a user provides a product idea, the system asks clarifying questions, then **collaborating agents** produce structured artifacts—**project brief**, **PRD**, **epics**, **user stories**, **tasks**, and **subtasks**.

**Stack:** Python 3.11+, **FastAPI**, **Anthropic Claude (Sonnet 4)**, **LangGraph** (graph workflow), **React (Vite)** UI.

---

## System architecture

```text
                    ┌─────────────────────────┐
                    │   Master orchestrator   │
                    │   (LangGraph state      │
                    │    machine)             │
                    └───────────┬─────────────┘
                                │
     ┌──────────────────────────┼──────────────────────────┐
     ▼                          ▼                          ▼
 Clarification            Requirement                 PM Agent
 Agent (questions)        Agent (brief)              (PRD)
     │                          │                          │
     └──────────────────────────┼──────────────────────────┘
                                ▼
                          Scrum Agent
                    (epics + user stories)
                                ▼
                           Task Agent
                    (tasks + subtasks)
```

- **Master orchestrator:** `backend/orchestrator.py` — builds a **LangGraph** compiled graph (`orchestrator/graph.py`) and delegates each step to the right agent class.
- **Agents:** `agents/` — each role has its own module; prompts live under `backend/prompts/`; all inherit `BaseAgent` (shared Claude client).
- **API:** `backend/main.py` — `POST /api/questions`, `POST /api/generate`; production React build served under `/ui/` (see below).
- **Outputs:** `Orchestrator.save_to_files()` writes to `docs/` (see below).

---

## Repository layout (assignment mapping)

| Assignment expectation | This repo |
|----------------------|-----------|
| `backend/` | `backend/` — FastAPI, orchestrator entrypoint, tests, requirements |
| `agents/` | `agents/` — agent implementations; `backend/prompt_loader.py` + `backend/prompts/` for prompts |
| `docs/` | `docs/` — generated `*.md` (see `docs/OUTPUTS.md`) |
| `frontend/` | `frontend/` — Vite + React + TypeScript (see `frontend/README.md`) |

**Top-level layout (single entry README: this file):**

```text
.
├── README.md                 # you are here
├── agents/                   # agent implementations (LangGraph calls these)
├── backend/                  # FastAPI, tests, requirements, prompts/*.md
├── docs/                     # generated artifacts (+ docs/OUTPUTS.md)
├── frontend/                 # React UI (Vite)
├── orchestrator/             # LangGraph graph
├── backend/prompt_loader.py  # prompt registry + templates
├── schemas/                  # PlanningState, validation
└── utils/                    # logging, memory
```

---

## Agent design

| Agent | Responsibility | Output shape |
|-------|----------------|--------------|
| **Clarification** | Scope, users, features, constraints | JSON array of question strings |
| **Requirement** | Structured brief from Q&A | JSON: name, problem, users, features, constraints |
| **PM** | PRD from brief | JSON: overview, goals, personas, functional/NFR, metrics |
| **Architect** *(bonus)* | Technical architecture from PRD + brief | JSON: services, stack, data flow, scale/security |
| **Scrum** | Agile backlog | JSON: epics → stories → acceptance criteria |
| **Task** | Engineering breakdown | JSON: per-story tasks and subtasks |

Separation is enforced by **different system prompts** and **single-purpose methods** per agent (`ask_questions`, `create_project_brief`, …).

---

## Prompt design

- Prompts live as versioned Markdown under **`backend/prompts/`** (YAML frontmatter: name, version, temperature, max_tokens). Shared text is injected via `{{shared_constraints}}`.
- **`backend/prompt_loader.py`** loads files, renders `{{variables}}` (fail-closed if any remain), and validates an OUTPUT FORMAT section before the LLM call. **`agents/prompt_config.py`** maps logical agents to prompt paths.
- User content is passed in the **user** message (idea, Q&A, prior JSON) where needed.
- **Parsing:** `agents/json_utils.py` strips optional ` ```json ` fences and recovers JSON if the model adds extra text.

---

## Workflow (LangGraph)

Nodes (simplified): `clarify` → validate Q&A → `requirement` → validate brief → `pm` (brief review + PRD) → validate PRD → `architect` → validate architecture → `scrum` → `task` (feasibility + tasks) → `final_validation`. Validation failures route to `halt`.

State (`PlanningState`) carries `product_idea`, `user_answers`, `questions`, `qa_pairs`, `project_brief`, `prd`, `architecture`, `epics_stories`, `tasks`, `task_feasibility`, `final_validation`, etc.

Implementation: `orchestrator/graph.py` (`compile_planning_graph`).

---

## Expected output files

Default directory: **`docs/`** (repository root):

```
docs/
├── OUTPUTS.md          # describes these files (not generated)
├── project_brief.md
├── prd.md
├── epics.md
├── stories.md
└── tasks.md
```

Generate via:

```python
from dotenv import load_dotenv
load_dotenv()
from backend.orchestrator import Orchestrator

o = Orchestrator()
results = o.run_workflow(
    "I want to build a marketplace for freelancers.",
    {"q1": "…", "q2": "…"},
    questions=["Who are the users?", "What is the MVP?"],  # optional
)
o.save_to_files(results)
```

---

## Setup

**Backend (Python):**

Run commands from the **repository root** (the folder that contains `backend/` and `frontend/`). If you run `uvicorn` from inside `frontend/`, you will get `ModuleNotFoundError: No module named 'backend'`.

```bash
cd /path/to/AI-Multi-Agent-Product-Planning-System
pip install -r backend/requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY (required)
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Configuration:** Optional runtime tuning is in `.env` (see `.env.example`): `ANTHROPIC_MODEL`, `ANTHROPIC_TIMEOUT_SEC`, `LLM_MAX_RETRIES`, `LLM_RETRY_BACKOFF_BASE_SEC`, `TASK_AGENT_MAX_WORKERS`, and log truncation limits. Loaded by `utils/runtime_config.py` (single source for `BaseAgent` and task parallelism).

Or use the helper (always uses the repo root):

```bash
chmod +x run_server.sh   # once
./run_server.sh
```

**Frontend (React + Vite)** — requires Node 18+. All UI code lives directly under **`frontend/`**.

Development (hot reload; `/api` proxied to the backend on port 8000):

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:8080/ui/** (Vite is configured with `base: /ui/`).

Production build (served by FastAPI at `/ui/`):

```bash
cd frontend
npm install
npm run build
```

Then open **http://127.0.0.1:8000/ui/** with the API running (static files from `frontend/dist/`).

- **Swagger:** http://127.0.0.1:8000/docs  

### Docker (API + UI in one command)

The repo includes a multi-stage image: build the Vite frontend, then run FastAPI with static files under `/ui`.

1. Copy and edit environment (Compose expects a `.env` file next to `docker-compose.yml`):

   ```bash
   cp .env.example .env
   # Set ANTHROPIC_API_KEY and any optional model / retry settings
   ```

2. Build and run:

   ```bash
   docker compose up --build
   ```

3. Open **http://127.0.0.1:8000/ui/** (API docs: **http://127.0.0.1:8000/docs**).

Volumes `planning_memory` and `app_logs` map to `/app/data/planning_memory` and `/app/logs` so planning artifacts and logs survive container restarts.

For hot-reload development of both services in one command:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend dev server: **http://127.0.0.1:8080/ui/**
- Backend API/docs: **http://127.0.0.1:8000/docs**

---

## Example API run

```bash
curl -s -X POST http://127.0.0.1:8000/api/questions \
  -H "Content-Type: application/json" \
  -d '{"product_idea":"A habit tracking app for teams"}'

curl -s -X POST http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_idea":"A habit tracking app for teams",
    "questions":["Who are the users?","What is the MVP?"],
    "answers":{"q1":"Team leads","q2":"Daily check-ins and streaks"}
  }'
```

---

## Validation

Check a downloaded or saved JSON for duplicate **epic**, **story**, or **task** IDs:

```bash
python backend/validate_output.py result/project_documentation.json
# or
python backend/validate_output.py project_documentation.json
```

Task IDs are **renumbered globally** after generation (`TASK-1` … `TASK-N` in story order), so duplicates from per-epic LLM calls are removed.

---

## Testing (dev)

```bash
cd backend
pip install -r requirements-dev.txt
cd ..
pytest backend/tests/ -v
```

---

## AI tooling disclosure

| Tool | Purpose |
|------|---------|
| Cursor (agent mode) | Iterative implementation support, refactors, Dockerization, UI fixes, and test scaffolding |
| Anthropic API (Claude Sonnet model via SDK) | Runtime LLM execution for all planning agents during workflow generation |
| Local pytest + Vitest tooling | Regression checks for prompt loading, task ID normalization, API behavior, and frontend components |

---

## Beyond the assignment spec

Features implemented beyond the core requirements:

- **Architect Agent** — an additional 6th agent (not required) that generates technical architecture between PRD and backlog, informing epic sequencing and task feasibility.
- **Cross-document validation** — `run_final_pipeline_validation()` checks consistency across brief, PRD, architecture, epics, and tasks (for example deferred features leaking into MVP epics or stack mismatches).
- **Agent review loops** — PM reviews the brief before writing PRD; Scrum reviews the PRD before creating epics; Task agent validates feasibility before task breakdown; review feedback is applied downstream.
- **Parallel task generation** — `TaskAgent` processes epics concurrently with configurable worker count via `TASK_AGENT_MAX_WORKERS`.
- **Versioned prompts** — prompts stored as Markdown with YAML frontmatter and loaded via `prompt_loader.py` with strict template validation.
- **Structured audit logging** — LLM calls logged to JSONL with agent name, phase, duration, prompt metadata, and truncated I/O.
- **Session memory** — `MemoryStore` persists full pipeline results as JSON per session ID, with retrieval endpoints.
- **Document versioning** — `save_to_files(version_subdir=True)` creates timestamped output directories.
- **Output validation CLI** — `python backend/validate_output.py result.json` checks duplicate epic/story/task IDs.
- **Docker support** — multi-stage Dockerfile plus production and hot-reload compose files.
- **Workflow visualization API** — `/api/workflow/diagram` exposes a Mermaid graph for the active pipeline.
- **SSE progress streaming** — `/api/generate/stream` emits stage-level workflow progress events.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Submission checklist (assignment)

- [x] Public GitHub repo + MIT license
- [x] README with architecture, agents, prompts, workflow, setup, example
- [x] `docs/` with generated artifacts + `agents/` + `backend/`
- [x] Loom video (overview, architecture, orchestration, stack, live demo)
- [x] AI tooling disclosure filled in

### Bonus features implemented

- [x] Memory system (MemoryStore - file-backed session persistence)
- [x] Document versioning (timestamped subdirectories)
- [x] Agent debugging logs (structured JSONL audit trail)
- [x] Visual workflow graph (Mermaid diagram via API)
- [x] Cross-document validation (consistency checks across all artifacts)
- [x] Architect agent (bonus 6th agent beyond spec)
- [x] Review loops (PM reviews brief, Scrum reviews PRD, Task validates feasibility)
- [x] Parallel task generation (configurable thread pool)
- [x] Docker support (multi-stage build, dev + prod compose)
- [x] SSE streaming endpoint
