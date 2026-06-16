# Technical Architecture Document
## Autonomous GitHub Code Review Agent

---

## Table of Contents

1. [Tech Stack & Reasoning](#1-tech-stack--reasoning)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [File & Folder Structure](#3-file--folder-structure)
4. [Database Schema](#4-database-schema)
5. [Environment Variables & Configuration](#5-environment-variables--configuration)

---

## 1. Tech Stack & Reasoning

### Core AI & Orchestration

| Technology | Role | Why This |
|---|---|---|
| **Ollama + local LLM** (free) or **Anthropic API** (pay-per-use) | Code analysis brain | Ollama runs local models like DeepSeek Coder, Qwen2.5-Coder, or CodeLlama entirely free with no API costs. For better quality, fall back to Anthropic API (pay-per-use). |
| **LangGraph** | Agent workflow orchestration | Gives you stateful, graph-based agent pipelines with built-in support for retries, conditional branching, and human-in-the-loop. LangChain alone is too linear for this — you need graph flows. |
| **MCP (Model Context Protocol)** | GitHub tool interface | Standard protocol for giving an AI agent access to external tools. Building a custom MCP server here is cleaner than raw function calling and more composable as you scale. |

### Backend & API

| Technology | Role | Why This |
|---|---|---|
| **Python 3.12+** | Primary language | The entire AI/ML ecosystem lives here. LangGraph, LangChain, ChromaDB, PyGithub — all Python-first. |
| **FastAPI** | Webhook listener + REST API | Async-native, fast, auto-generates OpenAPI docs. Perfect for a webhook receiver that needs to handle bursts of PR events without blocking. Flask would work but FastAPI's async support is better here. |
| **Uvicorn** | ASGI server | The standard production server for FastAPI. |
| **PyGithub** | GitHub API client | Clean Python wrapper around the GitHub REST API. Handles auth, pagination, and rate limiting for you. |

### Storage

| Technology | Role | Why This |
|---|---|---|
| **PostgreSQL** | Primary database | Stores repos, PRs, reviews, comments, and feedback. Relational data with clear relationships — Postgres is the right tool. SQLite works for local dev but won't scale. |
| **ChromaDB** | Vector store for RAG | Stores embeddings of your codebase for pattern matching. Lightweight, runs locally or as a server, Python-native. Pinecone is an option if you go cloud-first but ChromaDB avoids external dependencies for v1. |
| **Redis** | Job queue + caching | Webhook events go into a Redis queue so FastAPI returns 200 immediately and the review runs async. Also caches GitHub API responses to avoid rate limit hits. |

### Infrastructure

| Technology | Role | Why This |
|---|---|---|
| **Docker + Docker Compose** | Local dev + deployment | Keeps Postgres, Redis, ChromaDB, and the app consistent across environments. One `docker-compose up` and everything runs. |
| **Celery** | Async task worker | Pulls jobs from Redis and runs the LangGraph review pipeline in the background. Keeps the webhook endpoint fast and non-blocking. |
| **Alembic** | Database migrations | Pairs with SQLAlchemy for versioned, reversible schema migrations. Never edit your DB manually. |
| **SQLAlchemy** | ORM | Clean Python models for all DB tables. Handles connections, sessions, and query building. |

---

## 2. System Architecture Overview

```
GitHub PR Opened
       │
       ▼
┌─────────────────┐
│  GitHub Webhook  │  POST /webhook/github
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI App     │  Validates signature, returns 200 immediately
└────────┬────────┘
         │  Enqueues job
         ▼
┌─────────────────┐
│  Redis Queue     │  review:jobs
└────────┬────────┘
         │  Celery picks up job
         ▼
┌──────────────────────────────────────────┐
│           LangGraph Review Pipeline       │
│                                          │
│  [1] Fetch PR Diff (via MCP → GitHub)   │
│          │                               │
│  [2] Chunk & Parse Diff                 │
│          │                               │
│  [3] RAG Lookup (ChromaDB)              │
│          │                               │
│  [4] Claude Analysis                    │
│          │                               │
│  [5] Format Comments                    │
│          │                               │
│  [6] Post to GitHub (via MCP)           │
│          │                               │
│  [7] Post Summary Comment               │
└──────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL     │  Stores PR, review, comments, feedback
└─────────────────┘
```

---

## 3. File & Folder Structure

```
github-review-agent/
│
├── app/                          # Main application package
│   │
│   ├── api/                      # FastAPI routes
│   │   ├── __init__.py
│   │   ├── webhook.py            # POST /webhook/github — receives PR events
│   │   └── health.py             # GET /health — liveness check
│   │
│   ├── agent/                    # LangGraph agent pipeline
│   │   ├── __init__.py
│   │   ├── graph.py              # Defines the LangGraph state machine (nodes + edges)
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── fetch_diff.py     # Node 1: Fetches PR diff via MCP
│   │   │   ├── parse_diff.py     # Node 2: Chunks and structures the diff
│   │   │   ├── rag_lookup.py     # Node 3: Queries ChromaDB for codebase patterns
│   │   │   ├── analyze.py        # Node 4: Sends to Claude for review
│   │   │   ├── format_comments.py # Node 5: Formats line-by-line comments
│   │   │   ├── post_comments.py  # Node 6: Posts comments via MCP → GitHub
│   │   │   └── post_summary.py   # Node 7: Posts overall summary comment
│   │   └── state.py              # LangGraph state schema (TypedDict)
│   │
│   ├── mcp/                      # Custom MCP server
│   │   ├── __init__.py
│   │   ├── server.py             # MCP server entry point
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── get_pr_diff.py    # Tool: fetch diff for a PR
│   │       ├── get_pr_files.py   # Tool: list files changed in PR
│   │       ├── post_comment.py   # Tool: post inline review comment
│   │       └── post_summary.py   # Tool: post PR-level summary comment
│   │
│   ├── tasks/                    # Celery async tasks
│   │   ├── __init__.py
│   │   └── review.py             # review_pr() task — runs the LangGraph pipeline
│   │
│   ├── db/                       # Database layer
│   │   ├── __init__.py
│   │   ├── session.py            # SQLAlchemy engine + session factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── repository.py     # Repository model
│   │   │   ├── pull_request.py   # PullRequest model
│   │   │   ├── review.py         # Review model
│   │   │   ├── comment.py        # ReviewComment model
│   │   │   └── feedback.py       # Feedback model
│   │   └── crud/
│   │       ├── __init__.py
│   │       ├── repository.py     # DB operations for repos
│   │       ├── pull_request.py   # DB operations for PRs
│   │       ├── review.py         # DB operations for reviews
│   │       └── comment.py        # DB operations for comments
│   │
│   ├── rag/                      # RAG / vector store layer
│   │   ├── __init__.py
│   │   ├── indexer.py            # Indexes codebase files into ChromaDB
│   │   ├── retriever.py          # Queries ChromaDB for relevant patterns
│   │   └── embeddings.py         # Embedding model config (HuggingFace / OpenAI)
│   │
│   ├── github/                   # GitHub API client helpers
│   │   ├── __init__.py
│   │   ├── client.py             # PyGithub client factory
│   │   └── webhook.py            # Webhook signature validation
│   │
│   ├── core/                     # App-wide config and utilities
│   │   ├── __init__.py
│   │   ├── config.py             # Loads env vars via pydantic-settings
│   │   ├── logging.py            # Structured logging setup
│   │   └── exceptions.py         # Custom exception classes
│   │
│   ├── celery_app.py             # Celery app instance + config
│   └── main.py                   # FastAPI app factory + router registration
│
├── migrations/                   # Alembic migration files
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
│
├── tests/
│   ├── unit/
│   │   ├── test_parse_diff.py
│   │   ├── test_format_comments.py
│   │   └── test_rag_retriever.py
│   ├── integration/
│   │   ├── test_webhook.py
│   │   └── test_review_pipeline.py
│   └── conftest.py
│
├── scripts/
│   ├── index_repo.py             # One-time script to index a codebase into ChromaDB
│   └── test_webhook.py           # Sends a fake PR webhook event for local testing
│
├── docker/
│   ├── Dockerfile                # App container
│   └── Dockerfile.worker         # Celery worker container
│
├── docker-compose.yml            # Local dev: app + postgres + redis + chromadb
├── alembic.ini                   # Alembic config
├── pyproject.toml                # Dependencies (use uv or poetry)
├── .env.example                  # Template for env vars
├── .env                          # Your actual secrets (never commit this)
└── README.md
```

---

## 4. Database Schema

### Overview

Five tables. They follow a simple chain: a **Repository** has many **PullRequests**, each PullRequest gets one **Review**, each Review has many **ReviewComments**, and engineers can leave **Feedback** on any comment.

---

### Table 1: `repositories`

Stores each GitHub repo that the agent is connected to.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Internal unique ID |
| `github_repo_id` | INTEGER (unique) | GitHub's numeric ID for the repo |
| `owner` | VARCHAR | GitHub username or org (e.g. `acme-corp`) |
| `name` | VARCHAR | Repo name (e.g. `backend-api`) |
| `full_name` | VARCHAR (unique) | `owner/name` combined (e.g. `acme-corp/backend-api`) |
| `is_active` | BOOLEAN | Whether the agent is currently enabled for this repo |
| `webhook_secret` | VARCHAR | The secret used to validate incoming webhooks from this repo |
| `created_at` | TIMESTAMP | When this repo was registered |
| `updated_at` | TIMESTAMP | Last updated |

**Relationships:** One repository → many pull requests.

---

### Table 2: `pull_requests`

One record per PR event received. Tracks the PR's state through the review lifecycle.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Internal unique ID |
| `repository_id` | UUID (FK → repositories.id) | Which repo this PR belongs to |
| `github_pr_id` | INTEGER | GitHub's numeric PR ID |
| `github_pr_number` | INTEGER | The PR number shown in GitHub UI (e.g. #42) |
| `title` | VARCHAR | PR title |
| `author` | VARCHAR | GitHub username of the PR author |
| `base_branch` | VARCHAR | Branch being merged into (e.g. `main`) |
| `head_branch` | VARCHAR | Branch with changes (e.g. `feat/login`) |
| `status` | ENUM | `pending`, `reviewing`, `completed`, `failed` |
| `github_pr_url` | VARCHAR | Direct URL to the PR on GitHub |
| `diff_fetched_at` | TIMESTAMP | When the diff was successfully fetched |
| `created_at` | TIMESTAMP | When the webhook was received |
| `updated_at` | TIMESTAMP | Last updated |

**Relationships:** Many pull requests → one repository. One pull request → one review.

**Unique constraint:** `(repository_id, github_pr_number)` — prevents duplicate reviews for the same PR.

---

### Table 3: `reviews`

One record per completed agent review. Stores the overall verdict and metadata.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Internal unique ID |
| `pull_request_id` | UUID (FK → pull_requests.id, unique) | Which PR this review belongs to |
| `quality_score` | INTEGER | Overall code quality score (0–100) |
| `summary` | TEXT | The summary comment posted to GitHub |
| `top_concerns` | JSONB | Array of top 3 concern strings posted in summary |
| `files_reviewed` | INTEGER | How many files were analyzed |
| `total_comments` | INTEGER | Total number of inline comments posted |
| `model_used` | VARCHAR | Which Claude model was used (e.g. `claude-sonnet-4-6`) |
| `tokens_used` | INTEGER | Total tokens consumed for cost tracking |
| `duration_seconds` | FLOAT | How long the full review pipeline took |
| `completed_at` | TIMESTAMP | When the review finished |
| `created_at` | TIMESTAMP | When the review started |

**Relationships:** One review → one pull request. One review → many review comments.

---

### Table 4: `review_comments`

Each individual inline comment posted on a specific line of a file in the PR.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Internal unique ID |
| `review_id` | UUID (FK → reviews.id) | Which review this comment belongs to |
| `github_comment_id` | BIGINT | GitHub's ID for the posted comment (for updates/deletes) |
| `file_path` | VARCHAR | Path of the file being commented on (e.g. `src/auth/login.py`) |
| `line_number` | INTEGER | Line number in the diff |
| `category` | ENUM | `bug`, `security`, `performance`, `style`, `suggestion` |
| `severity` | ENUM | `blocking`, `warning`, `suggestion` |
| `body` | TEXT | The full comment text posted to GitHub |
| `code_snippet` | TEXT | The specific code snippet being referenced |
| `suggestion` | TEXT | Claude's suggested fix (if any) |
| `was_dismissed` | BOOLEAN | Whether the engineer dismissed this comment |
| `was_resolved` | BOOLEAN | Whether the engineer marked it resolved |
| `created_at` | TIMESTAMP | When the comment was posted |

**Relationships:** Many review comments → one review.

---

### Table 5: `feedback`

Captures engineer feedback on individual comments — used to improve future reviews.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Internal unique ID |
| `comment_id` | UUID (FK → review_comments.id) | Which comment the feedback is about |
| `action` | ENUM | `dismissed`, `resolved`, `thumbs_up`, `thumbs_down` |
| `engineer` | VARCHAR | GitHub username of the engineer who gave feedback |
| `reason` | TEXT | Optional note explaining why something was dismissed |
| `created_at` | TIMESTAMP | When the feedback was submitted |

**Relationships:** Many feedback records → one review comment.

---

### Entity Relationship Summary

```
repositories
    │
    └── pull_requests (many)
            │
            └── reviews (one)
                    │
                    └── review_comments (many)
                                │
                                └── feedback (many)
```

---

## 5. Environment Variables & Configuration

Copy `.env.example` to `.env` and fill in all values before running anything.

### GitHub

```env
# Your GitHub App or Personal Access Token
# Needs: pull_requests (read/write), contents (read), issues (write)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Secret you set when registering the webhook on GitHub
# Used to validate that incoming webhook requests are actually from GitHub
GITHUB_WEBHOOK_SECRET=your_random_secret_string

# Optional: GitHub App credentials (if using GitHub App instead of PAT)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY_PATH=./keys/github-app.pem
```

### Anthropic

```env
# Ollama (free, local) — set the model you pulled (e.g. deepseek-coder, qwen2.5-coder)
# No API key needed. Run: ollama pull deepseek-coder
OLLAMA_MODEL=deepseek-coder
OLLAMA_BASE_URL=http://localhost:11434

# Optional: Anthropic API (pay-per-use, better quality)
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
# ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_MAX_TOKENS=4096
```

### Database (PostgreSQL)

```env
# Full connection string
DATABASE_URL=postgresql://postgres:password@localhost:5432/code_review_agent

# Individual parts (used by Docker Compose)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=code_review_agent
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### Redis

```env
# Redis connection for Celery queue + caching
REDIS_URL=redis://localhost:6379/0

# Separate DB index for caching (optional but clean)
REDIS_CACHE_URL=redis://localhost:6379/1
```

### ChromaDB (RAG)

```env
# Where ChromaDB stores its data locally
CHROMA_PERSIST_DIR=./chroma_data

# If running ChromaDB as a server instead
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Collection name for your codebase embeddings
CHROMA_COLLECTION_NAME=codebase_patterns
```

### Embeddings

```env
# Which embedding model to use for RAG
# Uses HuggingFace sentence-transformers — free, local, no API key needed
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### App Config

```env
# Environment — affects logging, error detail, etc.
APP_ENV=development   # development | production

# FastAPI server
APP_HOST=0.0.0.0
APP_PORT=8000

# Secret key for any internal signing (generate with: openssl rand -hex 32)
APP_SECRET_KEY=your_random_secret_here

# Log level
LOG_LEVEL=INFO   # DEBUG | INFO | WARNING | ERROR
```

### Celery Worker

```env
# Celery reads REDIS_URL above — no separate config needed
# But you can tune concurrency here
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_TIMEOUT=300   # seconds before a review task is killed
```

### MCP Server

```env
# Port the custom MCP server runs on
MCP_SERVER_PORT=9000

# The LLM model the agent uses internally
# Use "ollama/deepseek-coder" for free local or "claude-sonnet-4-6" for Anthropic API
LLM_PROVIDER=ollama
LLM_MODEL=deepseek-coder
```

---

### Quick Start Checklist

Before writing a single line of app code, make sure these are done:

- [ ] Create a GitHub Personal Access Token (or GitHub App) with the right scopes
- [ ] Register a webhook on your test repo pointing to your local tunnel (use `cloudflared` — free, no account needed)
- [ ] Copy `.env.example` → `.env` and fill in all values
- [ ] Run `docker-compose up -d` to start Postgres, Redis, and ChromaDB
- [ ] Run `alembic upgrade head` to create all tables
- [ ] Run `scripts/index_repo.py` to index your codebase into ChromaDB
- [ ] Run `scripts/test_webhook.py` to fire a fake PR event and verify the pipeline end-to-end
