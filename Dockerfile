# syntax=docker/dockerfile:1
# Stage 1: build Vite/React SPA → frontend/dist
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: FastAPI serves API + static UI at /ui
FROM python:3.12-slim-bookworm
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY agents /app/agents
COPY orchestrator /app/orchestrator
COPY schemas /app/schemas
COPY utils /app/utils
COPY backend /app/backend

COPY --from=frontend-build /build/dist /app/frontend/dist

RUN mkdir -p /app/data/planning_memory /app/logs

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
