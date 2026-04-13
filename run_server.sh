#!/usr/bin/env bash
# Run FastAPI from repository root so `import backend` works from any shell cwd.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
exec uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
