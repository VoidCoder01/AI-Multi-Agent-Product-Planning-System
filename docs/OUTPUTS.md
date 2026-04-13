# Generated documentation (`docs/`)

Files in this folder are produced by `Orchestrator.save_to_files()` after a successful run (or equivalent export).

| File | Contents |
|------|----------|
| `project_brief.md` | Project brief (problem, users, features, constraints) |
| `prd.md` | Product Requirements Document |
| `epics.md` | Epics (JSON) |
| `stories.md` | User stories per epic + acceptance criteria + JSON appendix |
| `tasks.md` | Tasks and subtasks per story |

Regenerate from Python (`repository root`):

```python
from backend.orchestrator import Orchestrator
o = Orchestrator()
results = o.run_workflow(...)
o.save_to_files(results)
```

Or use the API flow and persist the JSON response locally.

The **canonical project documentation** is the root [README.md](../README.md).
