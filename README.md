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
- **Agents:** `agents/` — each role has its own module; prompts live under `backend/prompts/`; all inherit `BaseAgent` (shared Claude client). (`backend/agents/` contains import shims for tests only.)
- **API:** `backend/main.py` — `POST /api/questions`, `POST /api/generate`; production React build served under `/ui/` (see below).
- **Outputs:** `Orchestrator.save_to_files()` writes to `docs/` (see below).

---

## Repository layout (assignment mapping)

| Assignment expectation | This repo |
|----------------------|-----------|
| `backend/` | `backend/` — FastAPI, orchestrator entrypoint, tests, requirements |
| `agents/` | `agents/` — agent implementations; `prompt_loader.py` + `backend/prompts/` for prompts |
| `docs/` | `docs/` — generated `*.md` (see `docs/OUTPUTS.md`) |
| `frontend/` | `frontend/project-code/` — Vite + React + TypeScript (see `frontend/project-code/README.md`) |

**Top-level layout (single entry README: this file):**

```text
.
├── README.md                 # you are here
├── agents/                   # agent implementations (LangGraph calls these)
├── backend/                  # FastAPI, tests, requirements, prompts/*.md
├── docs/                     # generated artifacts (+ docs/OUTPUTS.md)
├── frontend/project-code/    # React UI
├── orchestrator/             # LangGraph graph
├── prompt_loader.py          # prompt registry + templates
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
| **Scrum** | Agile backlog | JSON: epics → stories → acceptance criteria |
| **Task** | Engineering breakdown | JSON: per-story tasks and subtasks |

Separation is enforced by **different system prompts** and **single-purpose methods** per agent (`ask_questions`, `create_project_brief`, …).

---

## Prompt design

- Prompts live as versioned Markdown under **`backend/prompts/`** (YAML frontmatter: name, version, temperature, max_tokens). Shared text is injected via `{{shared_constraints}}`.
- **`prompt_loader.py`** loads files, renders `{{variables}}` (fail-closed if any remain), and validates an OUTPUT FORMAT section before the LLM call. **`agents/prompt_config.py`** maps logical agents to prompt paths.
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

**Frontend (React + Vite)** — requires Node 18+. Use **`frontend/project-code` only** (not any other folder under `frontend/`).

Development (hot reload; `/api` proxied to the backend on port 8000):

```bash
cd frontend/project-code
npm install
npm run dev
```

Open **http://127.0.0.1:8080/ui/** (Vite is configured with `base: /ui/`).

Production build (served by FastAPI at `/ui/`):

```bash
cd frontend/project-code
npm install
npm run build
```

Then open **http://127.0.0.1:8000/ui/** with the API running (static files from `frontend/project-code/dist/`).

- **Swagger:** http://127.0.0.1:8000/docs  

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

## AI tooling disclosure (fill in for submission)

| Tool | Purpose |
|------|---------|
| *e.g. Cursor / Claude / ChatGPT* | *Scaffolding, debugging, README* |
| *Anthropic API* | *Runtime LLM for all agents* |

*Replace the first row with what you actually used and how it helped.*

---

## License

MIT — see [LICENSE](LICENSE).

---

## Submission checklist (assignment)

- [ ] Public GitHub repo + MIT license  
- [ ] README with architecture, agents, prompts, workflow, setup, example  
- [ ] `docs/` + `agents/` + `backend/` + `frontend/`  
- [ ] Loom video (overview, architecture, orchestration, stack, live demo)  

**Bonus ideas (not required):** memory, versioning, RAG, debug logs UI, workflow graph visualization.
