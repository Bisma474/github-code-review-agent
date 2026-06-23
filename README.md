# GitHub Code Review Agent

> Autonomous AI-powered code review for every pull request. Deploy once, review forever.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-1C3C3C?logo=langgraph&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

**GitHub Code Review Agent** listens for GitHub pull request webhooks, intelligently analyzes every changed file using your choice of LLM (Groq, OpenAI, Anthropic, Ollama), and posts structured, line-by-line review comments directly on the PR — with severity ratings, quality scores, and a summary.

It learns from past reviews via ChromaDB-based RAG (Retrieval Augmented Generation), supports user feedback to improve future reviews, and runs as a production-grade FastAPI service with Celery workers.

---

## Features

- **Autonomous PR reviews** — triggered automatically on `opened`, `reopened`, and `synchronize` events
- **Multi-LLM support** — Groq (free tier), OpenAI-compatible (xAI Grok), Anthropic Claude, Ollama (local)
- **Line-by-line comments** — precise, actionable feedback on specific code lines with severity (`BLOCKING`, `WARNING`, `SUGGESTION`)
- **Quality scoring** — every PR gets a 0–100 quality score and a human-readable summary
- **RAG-powered learning** — stores review patterns in ChromaDB, retrieves similar past reviews for context-aware analysis
- **User feedback loop** — rate reviews (1–5), categorize feedback, improve future results
- **MCP server** — Model Context Protocol interface for integration with LLM-powered IDEs and tools
- **Dual database** — PostgreSQL in production, SQLite for local development (no external deps needed)
- **Celery async workers** — review tasks run in the background, queue with retry logic

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   GitHub    │────▶│  FastAPI Webhook  │────▶│  Celery Worker    │
│  Webhook    │     │  POST /webhook/   │     │  review_pr task   │
└─────────────┘     └──────────────────┘     └───────────────────┘
                                                     │
                                                     ▼
                                           ┌───────────────────┐
                                           │  LangGraph Pipeline │
                                           │  (6 nodes)          │
                                           │                     │
                                           │  1. fetch_diff      │
                                           │  2. parse_files      │
                                           │  3. analyze_llm      │
                                           │  4. format_comments   │
                                           │  5. post_comments     │
                                           │  6. generate_summary  │
                                           └───────────────────┘
                                               │           │
                                               ▼           ▼
                                        ┌──────────┐ ┌──────────┐
                                        │PostgreSQL │ │ ChromaDB │
                                        │ (Reviews) │ │ (Patterns)│
                                        └──────────┘ └──────────┘
                                               │
                                               ▼
                                        ┌──────────┐
                                        │  Redis    │
                                        │ (Broker)  │
                                        └──────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- A [Groq API key](https://console.groq.com) (free tier — 30 req/min)

### 1. Clone and setup

```bash
git clone https://github.com/Bisma474/github-code-review-agent.git
cd github-code-review-agent

uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:

```ini
GITHUB_TOKEN=ghp_your_github_pat
GITHUB_WEBHOOK_SECRET=your_webhook_secret
APP_SECRET_KEY=your_random_secret
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_key
```

### 3. Run (dev mode — no Docker needed)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server starts with SQLite + Celery eager mode (tasks run inline).

### 4. Register a repository

```python
import asyncio
from app.db.session import get_async_session
from app.db.crud.repository import create_repo

async def main():
    async with get_async_session() as db:
        repo = await create_repo(
            db,
            github_repo_id=12345,
            owner="your-org",
            name="your-repo",
            full_name="your-org/your-repo",
            webhook_secret="your_webhook_secret",
        )
        print(f"Registered: {repo.id}")

asyncio.run(main())
```

### 5. Set up GitHub webhook

Go to your repo → **Settings** → **Webhooks** → **Add webhook**:

| Field | Value |
|---|---|
| Payload URL | `http://your-server:8000/webhook/github` |
| Content type | `application/json` |
| Secret | `your_webhook_secret` (match `.env`) |
| Events | **Pull requests** |
| Active | ✅ |

That's it. Open a PR on the repo — the agent reviews it automatically.

---

## API Reference

### `GET /health`
Health check with database status.

```json
{"status": "ok", "db": "ok", "version": "1.0.0", "timestamp": "..."}
```

### `POST /webhook/github`
GitHub webhook receiver (validated via HMAC-SHA256).

**Headers:** `X-Hub-Signature-256`, `X-GitHub-Event`, `Content-Type`

```json
{"status": "queued", "pr_number": 42}
```

### `POST /feedback`
Submit review feedback.

```json
// Request
{"review_id": "uuid", "rating": 4, "category": "accuracy", "notes": "Great catch on line 23"}

// Response
{"id": "uuid", "review_id": "uuid", "rating": 4, "category": "accuracy", "notes": "..."}
```

### `GET /feedback/{review_id}`
Get all feedback for a review.

---

## Production Deployment (Docker)

```bash
docker compose up -d
```

This starts 5 services: `api`, `worker`, `postgres`, `redis`, `chromadb`. Set `DATABASE_URL=postgresql+asyncpg://...` in `.env`.

---

## LLM Providers

| Provider | Config | Cost |
|---|---|---|
| **Groq** 🏆 | `LLM_PROVIDER=groq` + `GROQ_API_KEY` | Free tier |
| **xAI Grok** | `LLM_PROVIDER=grok` + `GROK_API_KEY` | Pay-per-use |
| **Anthropic Claude** | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` | Pay-per-use |
| **Ollama** (local) | `LLM_PROVIDER=ollama` | Free |

---

## Pipeline Nodes

| Node | Description |
|---|---|
| `fetch_diff` | Retrieves raw unified diff from GitHub API |
| `parse_files` | Parses diff into per-file structured hunks |
| `analyze_llm` | Sends each file to LLM for analysis with RAG context |
| `format_comments` | Structures LLM output into review comments with severity |
| `post_comments` | Posts inline comments on the PR |
| `generate_summary` | Generates a PR-level quality score and summary |

---

## Project Structure

```
app/
├── agent/          # LangGraph pipeline (graph, state, LLM client, 6 nodes)
├── api/            # FastAPI routes (health, webhook, feedback)
├── core/           # Config (pydantic-settings), exceptions, structured logging
├── db/             # SQLAlchemy models, CRUD, session management, Alembic migrations
├── github/         # GitHub API client, webhook signature validation
├── mcp/            # Model Context Protocol server + 5 tools
├── rag/            # ChromaDB client, pattern repository, store/retrieve
└── tasks/          # Celery task definitions

tests/
├── unit/           # Unit tests (57 total across 7 files)
├── integration/    # API integration tests (7 tests)
└── e2e_dryrun.py   # End-to-end pipeline test with real LLM

docker-compose.yml  # Production-ready multi-service setup
Dockerfile          # Python 3.12-slim container
```

---

## Testing

```bash
pytest tests/ -v
# 57 passed
```

End-to-end dry run with a real LLM:

```bash
GROQ_API_KEY=gsk_... python tests/e2e_dryrun.py
```

---

## License

MIT
