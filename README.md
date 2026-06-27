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

- **Autonomous PR reviews** — triggered automatically on `opened`, `reopened`, and `synchronize` events (push new commits → auto re-review)
- **Multi-LLM support** — Groq (free tier), OpenAI-compatible (xAI Grok), Anthropic Claude, Ollama (local)
- **Line-by-line comments** — precise, actionable feedback on specific code lines with severity (`BLOCKING`, `WARNING`, `SUGGESTION`)
- **Quality scoring** — every PR gets a 0–100 quality score and a human-readable summary
- **RAG-powered learning** — stores review patterns in ChromaDB, retrieves similar past reviews for context-aware analysis
- **User feedback loop** — rate reviews (1–5), categorize feedback, improve future results
- **MCP server** — Model Context Protocol interface for integration with LLM-powered IDEs and tools
- **Dual database** — PostgreSQL in production, SQLite for local development (no external deps needed)
- **Background processing** — reviews run as async background tasks (eager mode) or via Celery workers with Redis

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
                                            │  3. analyze_rag      │
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

The server starts with SQLite + eager mode (reviews run as background tasks on the same event loop).

### 4. Repos register automatically

The agent **auto-registers** any repo that sends a webhook — no manual setup needed. You can also register or list repos via the API:

```bash
# List registered repos
curl http://localhost:8000/api/repos

# Register manually
curl -X POST http://localhost:8000/api/repos/register \
  -H "Content-Type: application/json" \
  -d '{"full_name": "your-org/your-repo", "github_repo_id": 12345}'
```

### 5. Set up GitHub webhook

Open your repo on GitHub → **Settings** → **Webhooks** → **Add webhook**:

| Field | Value | Why |
|---|---|---|
| **Payload URL** | `https://your-server.com/webhook/github` | Agent listens on this endpoint. For local dev, use [smee.io](https://smee.io) or ngrok to expose `http://localhost:8000/webhook/github` |
| **Content type** | `application/json` | Must be JSON (NOT `x-www-form-urlencoded`) |
| **Secret** | Same as `GITHUB_WEBHOOK_SECRET` in `.env` | Used for HMAC-SHA256 signature verification — must match **exactly**, or all requests get 401 |
| **Events** | **Let me select individual events** → check **Pull requests** | This triggers on `opened`, `reopened`, AND `synchronize` (new commits pushed to an existing PR) |
| **Active** | ✅ checked | |

Click **Add webhook**. That's it.

**What happens next:**
1. Open or push to a PR on that repo → GitHub sends a POST to `/webhook/github`
2. Agent verifies the HMAC signature using your secret
3. Agent auto-registers the repo in its database (no manual setup needed)
4. Agent runs the 6-node LangGraph pipeline
5. Within seconds, inline review comments + a summary appear on your PR

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

### `GET /api/repos`
List registered repos.

### `POST /api/repos/register`
Register a repo manually (auto-registers on first webhook otherwise).

```json
// Request
{"full_name": "owner/repo", "github_repo_id": 12345}
// Response
{"status": "registered", "repo_id": "uuid"}
```

---

## Production Deployment

### Docker Compose (local)

```bash
docker compose up -d
```

Starts 5 services: `api`, `worker`, `postgres`, `redis`, `chromadb`. Set `DATABASE_URL=postgresql+asyncpg://...` in `.env`.

### Render (cloud — free tier)

Deploy via blueprint (`render.yaml`):

1. Push to GitHub — Render auto-deploys via Blueprint
2. Create a PostgreSQL instance on Render Dashboard
3. Set env vars: `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `APP_SECRET_KEY`, `GROQ_API_KEY`, `DATABASE_URL`
4. Set GitHub webhook → `https://your-app.onrender.com/webhook/github`

The app runs with eager mode (no Celery/Redis needed on free tier).

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
| `analyze_rag` | Sends each file to LLM for analysis with RAG context from ChromaDB |
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
├── unit/           # Unit tests (51 total across 8 files)
├── integration/    # API integration tests (7 tests)
└── e2e_dryrun.py   # End-to-end pipeline test with real LLM

docker-compose.yml  # Production-ready multi-service setup
Dockerfile          # Python 3.12-slim container
render.yaml         # Render Blueprint deployment
```

---

## Testing

```bash
pytest tests/ -v
# 58 passed
```

End-to-end dry run with a real LLM:

```bash
GROQ_API_KEY=gsk_... python tests/e2e_dryrun.py
```

---

## License

MIT
