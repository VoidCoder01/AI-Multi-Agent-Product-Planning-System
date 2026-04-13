# Frontend (Vite + React)

**Project docs:** [../README.md](../README.md) (architecture, setup, API).

## Commands

```bash
npm install
npm run dev    # http://localhost:8080/ui/ — proxies /api → FastAPI :8000
npm run build  # dist/ served by FastAPI at http://127.0.0.1:8000/ui/
```

`base` is `/ui` to match the FastAPI static mount.
