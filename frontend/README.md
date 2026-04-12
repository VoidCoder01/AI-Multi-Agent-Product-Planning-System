# Frontend

The only UI for this project lives in **`project-code/`** (Vite + React + TypeScript).

**Option A — from `frontend/` (delegates to `project-code/`):**

```bash
cd frontend
npm install          # installs deps inside project-code/
npm run dev          # http://localhost:8080/ui/
npm run build
```

**Option B — from `project-code/` directly:**

```bash
cd frontend/project-code
npm install
npm run dev
npm run build        # → dist/ served by FastAPI at /ui/
```

See the repository root `README.md` for full stack setup.
