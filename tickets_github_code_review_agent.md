# Feature Ticket List
## Autonomous GitHub Code Review Agent

**Build order:** Tickets are listed in dependency order. Start at T-001 and work forward. Phase 0 has no dependencies — all three tickets can run in parallel.

**Priority labels:**
- **P0 (Must-Have)** — v1 launch. Without these, the app does nothing useful.
- **P1 (Should-Have)** — Important for production readiness. Defer only if blocked.
- **P2 (Nice-to-Have)** — v2 features. Build after all P0 and P1 are complete.

---

## Phase 0: Project Foundation

### T-001: Project Scaffolding & Dependencies

**Priority:** P0  
**Dependencies:** None  
**File(s):** `pyproject.toml`, `.env.example`, `.gitignore`

**Description:**
Set up the Python project skeleton. Initialize `pyproject.toml` using `uv` (recommended) or `poetry` with all required dependencies. Create `.env.example` with every env var documented with a comment explaining what it does. Create `.gitignore` that excludes `.env`, `__pycache__/`, `.venv/`, `*.pyc`, `.pem` keys, and `chroma_data/`.

**Dependencies to include:**
- `fastapi`, `uvicorn[standard]`
- `pygithub`
- `langgraph`, `langchain-core`
- `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
- `celery`, `redis`
- `httpx` (for Ollama HTTP calls)
- `pydantic-settings`
- `python-dotenv`
- `chromadb`, `sentence-transformers` (v2, but include now to avoid conflicts later)
- Dev: `pytest`, `pytest-asyncio`, `httpx` (for test client)

**Acceptance Criteria:**
1. Running `uv sync` or `poetry install` installs all dependencies without errors
2. `.env.example` contains ALL env vars from the architecture doc (GitHub, Anthropic, DB, Redis, ChromaDB, embeddings, app config, Celery, MCP)
3. `.gitignore` covers at minimum: `.env`, `__pycache__/`, `.venv/`, `*.pyc`, `chroma_data/`, `.pem`
4. Running `python --version` returns 3.12+

---

### T-002: Config & Environment Loading

**Priority:** P0  
**Dependencies:** T-001  
**File(s):** `app/__init__.py`, `app/core/__init__.py`, `app/core/config.py`, `app/core/exceptions.py`

**Description:**
Create the application configuration module. Use `pydantic-settings` to load all env vars from `.env` and validate them at startup. Define a `Settings` class with typed fields for every environment variable grouped by section (GitHub, Anthropic, Database, Redis, ChromaDB, Embeddings, App, Celery, MCP). Also create custom exception classes: `AppException`, `WebhookValidationError`, `GitHubAPIError`, `LLMError`, `ReviewError`.

**Acceptance Criteria:**
1. `Settings` loads all env vars from `.env` on instantiation
2. Missing required env vars raise a `ValidationError` at startup with the variable name
3. Optional env vars fall back to documented defaults (e.g. `APP_PORT=8000`, `LOG_LEVEL=INFO`)
4. `Settings` exposes a singleton via `get_settings()` with caching
5. `AppException` and subclasses exist with proper `__init__` taking a message and optional error code
6. All exception classes inherit from `AppException` which inherits from `Exception`

---

### T-003: Structured Logging Setup

**Priority:** P1  
**Dependencies:** T-002  
**File(s):** `app/core/logging.py`

**Description:**
Create a structured logging module that provides a configured logger. Logs should be JSON-formatted in production and human-readable in development. Include the module name, timestamp, log level, and message. Add a `get_logger(name)` factory function that returns a logger with consistent formatting. Log level is controlled by `LOG_LEVEL` env var.

**Acceptance Criteria:**
1. `get_logger("app.webhook")` returns a configured logger
2. In `APP_ENV=development`, logs are human-readable with color (use standard logging)
3. In `APP_ENV=production`, logs are JSON lines (one JSON object per line)
4. Logs include: `timestamp`, `level`, `module`, `message`
5. Extra fields can be passed via `logger.info("msg", extra={"key": "val"})`

---

## Phase 1: Database Layer

### T-004: Database Session & Engine

**Priority:** P0  
**Dependencies:** T-002  
**File(s):** `app/db/__init__.py`, `app/db/session.py`

**Description:**
Create the SQLAlchemy database layer. Set up an async engine using `DATABASE_URL` from config, create a session factory, and provide a `get_db()` async context manager that yields a session and handles commit/rollback. For local dev, support both PostgreSQL and SQLite (switched via `DATABASE_URL`). Create the declarative `Base` class that all models will inherit from.

**Acceptance Criteria:**
1. `engine` is created from `DATABASE_URL` on module init
2. `async_session` is a configured `async_sessionmaker`
3. `get_db()` yields an async session, commits on success, rolls back on exception
4. `Base` is a proper `declarative_base()` instance
5. Works with both `postgresql+asyncpg://...` and `sqlite+aiosqlite://` URLs

---

### T-005: Database Models (All 5 Tables)

**Priority:** P0  
**Dependencies:** T-004  
**File(s):** `app/db/models/__init__.py`, `app/db/models/repository.py`, `app/db/models/pull_request.py`, `app/db/models/review.py`, `app/db/models/comment.py`, `app/db/models/feedback.py`

**Description:**
Create all 5 SQLAlchemy ORM models matching the architecture doc's database schema exactly.

**`Repository` table:**
- `id` (UUID, PK), `github_repo_id` (INT, unique), `owner` (VARCHAR), `name` (VARCHAR), `full_name` (VARCHAR, unique), `is_active` (BOOLEAN, default True), `webhook_secret` (VARCHAR), `created_at`, `updated_at`
- Relationship: `pull_requests`

**`PullRequest` table:**
- `id` (UUID, PK), `repository_id` (UUID, FK), `github_pr_id` (INT), `github_pr_number` (INT), `title` (VARCHAR), `author` (VARCHAR), `base_branch` (VARCHAR), `head_branch` (VARCHAR), `status` (ENUM: pending/reviewing/completed/failed), `github_pr_url` (VARCHAR), `diff_fetched_at` (TIMESTAMP, nullable), `created_at`, `updated_at`
- Unique constraint: `(repository_id, github_pr_number)`
- Relationship: `repository`, `review`

**`Review` table:**
- `id` (UUID, PK), `pull_request_id` (UUID, FK, unique), `quality_score` (INT), `summary` (TEXT), `top_concerns` (JSON), `files_reviewed` (INT), `total_comments` (INT), `model_used` (VARCHAR), `tokens_used` (INT), `duration_seconds` (FLOAT), `completed_at` (TIMESTAMP, nullable), `created_at`
- Relationship: `pull_request`, `review_comments`

**`ReviewComment` table:**
- `id` (UUID, PK), `review_id` (UUID, FK), `github_comment_id` (BIGINT, nullable), `file_path` (VARCHAR), `line_number` (INT), `category` (ENUM: bug/security/performance/style/suggestion), `severity` (ENUM: blocking/warning/suggestion), `body` (TEXT), `code_snippet` (TEXT, nullable), `suggestion` (TEXT, nullable), `was_dismissed` (BOOLEAN, default False), `was_resolved` (BOOLEAN, default False), `created_at`
- Relationship: `review`, `feedback_records`

**`Feedback` table:**
- `id` (UUID, PK), `comment_id` (UUID, FK), `action` (ENUM: dismissed/resolved/thumbs_up/thumbs_down), `engineer` (VARCHAR), `reason` (TEXT, nullable), `created_at`

**Acceptance Criteria:**
1. All 5 models are defined with correct columns, types, and nullability
2. All foreign keys and relationships are properly declared
3. Enums use SQLAlchemy `Enum` type with native enum support
4. `PullRequest` has unique constraint on `(repository_id, github_pr_number)`
5. Running `Base.metadata.create_all(engine)` creates all 5 tables
6. All models have `__tablename__` set correctly (plural, snake_case)

---

### T-006: Alembic Migration Setup

**Priority:** P1  
**Dependencies:** T-005  
**File(s):** `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/001_initial_schema.py`

**Description:**
Initialize Alembic for database migrations. Configure it to use the async SQLAlchemy engine and auto-detect model changes from `app/db/models`. Generate the initial migration that creates all 5 tables.

**Acceptance Criteria:**
1. `alembic init` produces the correct directory structure under `migrations/`
2. `alembic.ini` points to the correct migration directory
3. `migrations/env.py` is configured for async SQLAlchemy and imports all models
4. Running `alembic upgrade head` creates all 5 tables in the database
5. Running `alembic downgrade -1` drops the last migration cleanly
6. Running `alembic history` shows the migration chain

---

### T-007: CRUD Operations

**Priority:** P0  
**Dependencies:** T-005  
**File(s):** `app/db/crud/__init__.py`, `app/db/crud/repository.py`, `app/db/crud/pull_request.py`, `app/db/crud/review.py`, `app/db/crud/comment.py`

**Description:**
Create CRUD helper functions for each model. All functions take an async session as the first parameter. Each module covers the operations needed by the rest of the app.

**`repository.py`:** `create_repo`, `get_repo_by_full_name`, `get_repo_by_id`, `get_active_repos`, `set_repo_active_status`

**`pull_request.py`:** `create_pr`, `get_pr_by_id`, `get_pr_by_github_number`, `update_pr_status`, `get_pending_prs`

**`review.py`:** `create_review`, `get_review_by_pr_id`, `update_review`

**`comment.py`:** `create_comment`, `get_comments_by_review_id`, `update_comment_github_id`, `get_dismissed_patterns` (for v2)

**Acceptance Criteria:**
1. Every CRUD function accepts `db: AsyncSession` as the first argument
2. Create functions return the created model instance with generated UUIDs
3. Get functions return `None` when the record is not found (no exceptions)
4. Update functions accept a dict of field: value pairs and apply only those fields
5. All functions are async and use `await db.execute(...)` / `await db.commit()`
6. Type hints are present on all function parameters and return types

---

## Phase 2: GitHub Integration

### T-008: GitHub Client Factory

**Priority:** P0  
**Dependencies:** T-002  
**File(s):** `app/github/__init__.py`, `app/github/client.py`

**Description:**
Create a GitHub API client factory that wraps PyGithub. Initialize a `Github` instance using `GITHUB_TOKEN` from settings. Provide helper methods: `get_repo(full_name)`, `get_pull_request(repo, number)`, `get_pr_diff(repo, number)`, `get_pr_files(repo, number)`, `post_review_comment(repo, pr_number, body, path, line, commit_id)`, `post_pr_comment(repo, pr_number, body)`. Handle rate limiting by catching `RateLimitExceededException` and logging a warning.

**Acceptance Criteria:**
1. `get_github_client()` returns a configured PyGithub `Github` instance
2. `get_pr_diff` returns the raw diff string from the PR
3. `get_pr_files` returns a list of file dicts with filename, status, additions, deletions
4. `post_review_comment` posts an inline comment and returns the comment ID
5. `post_pr_comment` posts a PR-level comment and returns the comment ID
6. All methods raise `GitHubAPIError` on non-200 responses with the status code and message
7. Rate limit exceeded is caught and logged before re-raising

---

### T-009: Webhook Signature Validation

**Priority:** P0  
**Dependencies:** T-002  
**File(s):** `app/github/webhook.py`

**Description:**
Implement webhook payload signature validation. Create a function `validate_webhook_signature(payload_body: bytes, signature_header: str, secret: str) -> bool` that computes HMAC-SHA256 of the body using the secret and compares it to the signature header using a constant-time comparison. If the header is missing or the comparison fails, raise `WebhookValidationError`.

**Acceptance Criteria:**
1. `validate_webhook_signature` returns `True` when the signature matches
2. `validate_webhook_signature` returns `False` when the signature does not match
3. Uses `hmac.compare_digest` for constant-time comparison (no timing attack)
4. Raises `WebhookValidationError` if the signature header is missing
5. Works with both `sha256=` prefixed and raw hex signatures
6. Test with a known payload + secret to verify HMAC calculation

---

### T-010: MCP Server — Server Entry Point

**Priority:** P0  
**Dependencies:** T-008  
**File(s):** `app/mcp/__init__.py`, `app/mcp/server.py`

**Description:**
Build the custom MCP (Model Context Protocol) server. This is a FastAPI-based server (or stdio-based) that exposes the MCP tools as callable endpoints. The server registers four tools: `get_pr_diff`, `get_pr_files`, `post_comment`, `post_summary`. Each tool reads the current configuration from `app/core/config.py` and delegates to the corresponding GitHub client method. The MCP server listens on `MCP_SERVER_PORT` from settings.

**Implementation approach for v1:**
- Use the MCP Python SDK (`mcp` package) to define a server with tools
- Each tool is registered with `@server.tool()` decorator
- Tools accept parameters and return structured JSON responses
- The server runs as a subprocess or separate service alongside FastAPI

**Acceptance Criteria:**
1. MCP server starts on the configured port
2. Server registers tools: `get_pr_diff`, `get_pr_files`, `post_comment`, `post_summary`
3. Each tool delegates to the corresponding function from `app/github/client.py`
4. Tools return structured JSON responses
5. Server can be started independently: `python -m app.mcp.server`

---

### T-011: MCP Tool — Get PR Diff

**Priority:** P0  
**Dependencies:** T-010  
**File(s):** `app/mcp/tools/__init__.py`, `app/mcp/tools/get_pr_diff.py`

**Description:**
Implement the MCP tool that fetches a pull request's diff. The tool accepts `owner`, `repo`, and `pr_number` as parameters. It calls the GitHub client's `get_pr_diff`, returns the raw diff text. On failure, returns a structured error with the error code and message. The result includes: `{ "success": true, "diff": "...raw diff...", "files_count": 5, "total_changes": 120 }` or `{ "success": false, "error": "PR not found", "error_code": "NOT_FOUND" }`.

**Acceptance Criteria:**
1. Tool is registered as `get_pr_diff` on the MCP server
2. Accepts `owner: str`, `repo: str`, `pr_number: int`
3. Returns raw diff text with metadata (file count, change count)
4. Returns error object on failure (404, 403, rate limit)
5. Includes a `success: bool` field in every response

---

### T-012: MCP Tool — Get PR Files

**Priority:** P0  
**Dependencies:** T-010  
**File(s):** `app/mcp/tools/get_pr_files.py`

**Description:**
Implement the MCP tool that lists all files changed in a PR. Accepts `owner`, `repo`, `pr_number`. Returns a list of file objects with filename, status (added/modified/removed), additions, deletions, and changes. Used by the review pipeline to filter binary files and count files.

**Acceptance Criteria:**
1. Tool is registered as `get_pr_files` on the MCP server
2. Accepts `owner: str`, `repo: str`, `pr_number: int`
3. Returns `{ "success": true, "files": [...] }` with each file having filename, status, additions, deletions
4. Handles 404 and 403 errors gracefully with error objects

---

### T-013: MCP Tool — Post Review Comment

**Priority:** P0  
**Dependencies:** T-010  
**File(s):** `app/mcp/tools/post_comment.py`

**Description:**
Implement the MCP tool that posts an inline review comment on a specific line of a file in a PR. Accepts `owner`, `repo`, `pr_number`, `body` (markdown comment text), `path` (file path), `line` (line number). Uses the GitHub client's `post_review_comment`. Returns the created comment ID and URL on success.

**Acceptance Criteria:**
1. Tool is registered as `post_comment` on the MCP server
2. Accepts `owner`, `repo`, `pr_number`, `body`, `path`, `line`, `commit_id`
3. Posts comment to the correct file and line
4. Returns `{ "success": true, "comment_id": 123456789, "html_url": "..." }`
5. Returns error on invalid line numbers or missing permissions

---

### T-014: MCP Tool — Post Summary Comment

**Priority:** P0  
**Dependencies:** T-010  
**File(s):** `app/mcp/tools/post_summary.py`

**Description:**
Implement the MCP tool that posts a PR-level summary comment. Accepts `owner`, `repo`, `pr_number`, `body` (full markdown summary). Uses the GitHub Issues API (PR-level comments go through the issues endpoint). Returns the comment ID and URL.

**Acceptance Criteria:**
1. Tool is registered as `post_summary` on the MCP server
2. Accepts `owner`, `repo`, `pr_number`, `body`
3. Posts to the PR conversation timeline (not inline)
4. Returns `{ "success": true, "comment_id": ..., "html_url": "..." }`
5. Handles 403 (missing write permission) with a clear error

---

## Phase 3: API Layer

### T-015: FastAPI App Factory & Health Endpoint

**Priority:** P0  
**Dependencies:** T-002, T-003  
**File(s):** `app/main.py`, `app/api/__init__.py`, `app/api/health.py`

**Description:**
Create the FastAPI application using an app factory pattern. `create_app()` initializes the FastAPI instance, loads config, sets up CORS (allow GitHub webhook origin), registers all routers, and configures startup/shutdown events. Add a `GET /health` endpoint that returns `{ "status": "ok", "timestamp": "...", "version": "1.0.0" }`. The health check should verify the database connection is alive.

**Acceptance Criteria:**
1. `create_app()` returns a configured FastAPI instance
2. `GET /health` returns 200 with status, timestamp, and version
3. Health check pings the database and returns `db: "ok"` or `db: "error"`
4. Startup event initializes the database engine
5. Shutdown event disposes the database engine
6. App runs on `APP_HOST`:`APP_PORT` from settings

---

### T-016: Webhook Endpoint — Receive & Validate

**Priority:** P0  
**Dependencies:** T-009, T-015  
**File(s):** `app/api/webhook.py`

**Description:**
Implement the `POST /webhook/github` endpoint. On each request:
1. Extract `X-Hub-Signature-256` header
2. Read the raw request body
3. Call `validate_webhook_signature` — return `401` if invalid
4. Parse JSON payload
5. Validate required fields: `action`, `pull_request.number`, `repository.full_name`
6. If `action != "opened"`, return `202` and ignore
7. If repo is not active in the database, return `202` and log
8. Create a `PullRequest` record in the DB with `status = pending`
9. Enqueue a Celery task to run the review
10. Return `202 Accepted` with `{ "status": "queued", "pr_number": 42 }`

**Acceptance Criteria:**
1. `POST /webhook/github` with invalid signature returns `401` with no detail
2. `POST /webhook/github` with valid signature and valid payload returns `202`
3. Missing required fields returns `422 Unprocessable Entity`
4. Non-`opened` actions return `202` and do NOT create a DB record
5. Valid request creates a `PullRequest` record with `status = pending`
6. Celery task is enqueued with the correct PR ID
7. Endpoint responds in under 500ms (it should only validate + enqueue)

---

### T-017: Celery App Configuration

**Priority:** P1  
**Dependencies:** T-002, T-016  
**File(s):** `app/celery_app.py`

**Description:**
Create the Celery application instance. Configure it to use Redis as the broker (`REDIS_URL`). Set task serialization to JSON. Configure task routes so review tasks go to a `review` queue. Set `task_acks_late = True` so tasks are re-delivered if a worker crashes. Set `worker_prefetch_multiplier = 1` for fair task distribution.

**Acceptance Criteria:**
1. `celery_app.py` creates a `Celery` instance with broker from `REDIS_URL`
2. Task routes are configured: `review.*` → `review` queue
3. `task_acks_late = True` is set
4. Running `celery -A app.celery_app worker -l info` starts a worker successfully

---

### T-018: Async Review Task

**Priority:** P0  
**Dependencies:** T-017  
**File(s):** `app/tasks/__init__.py`, `app/tasks/review.py`

**Description:**
Create the Celery task `review_pr(pull_request_id: str)` that orchestrates the full review. The task:
1. Retrieves the `PullRequest` record from the DB
2. Updates status to `reviewing`
3. Creates a `Review` record with `status = started`
4. Calls the LangGraph pipeline (imported from `app.agent.graph`)
5. On success: updates review status to `completed`, PR status to `completed`
6. On failure: updates review status to `failed`, PR status to `failed`, logs the error
7. Uses a `TaskTimeout` of `CELERY_TASK_TIMEOUT` seconds

**Acceptance Criteria:**
1. `review_pr` is a registered Celery task in the `review` queue
2. Accepts a `pull_request_id: str` (UUID)
3. Updates PR status through `pending` → `reviewing` → `completed` / `failed`
4. Creates a `Review` record and passes it through the pipeline
5. On failure, catches all exceptions and marks the review as `failed`
6. Logs start, completion, and failure with structured logging

---

## Phase 4: Review Pipeline

### T-019: LangGraph State Schema

**Priority:** P0  
**Dependencies:** T-002  
**File(s):** `app/agent/__init__.py`, `app/agent/state.py`

**Description:**
Define the LangGraph state as a `TypedDict`. The state flows through all nodes in the review pipeline.

```python
class ReviewState(TypedDict):
    pull_request_id: str           # UUID of the PR record
    repository_id: str             # UUID of the repo record
    github_owner: str              # e.g. "acme-corp"
    github_repo: str               # e.g. "backend-api"
    github_pr_number: int          # e.g. 42
    diff_raw: str                  # Raw unified diff text
    parsed_files: list[ParsedFile] # Chunked and parsed diff per file
    llm_analysis: list[AnalysisResult]  # LLM output per chunk
    formatted_comments: list[FormattedComment]  # Comment templates ready to post
    posted_comment_ids: list[int]  # GitHub comment IDs from posting
    summary: str                   # Summary comment body
    quality_score: int             # 0–100
    top_concerns: list[str]        # Top 3 issues
    errors: list[str]              # Non-fatal errors encountered
```

Define supporting data classes: `ParsedFile` (file_path, hunks: list of Hunk), `Hunk` (start_line, end_line, content), `AnalysisResult` (file, line, category, severity, description, suggestion), `FormattedComment` (file_path, line_number, body).

**Acceptance Criteria:**
1. `ReviewState` is a `TypedDict` with all fields listed above
2. All supporting data classes are defined as `@dataclass` or Pydantic models
3. Each field has a type hint and a docstring comment
4. Optional fields use `NotRequired` from TypedDict
5. The state can be instantiated with just `pull_request_id`, `repository_id`, `github_owner`, `github_repo`, `github_pr_number`

---

### T-020: LangGraph Pipeline Graph

**Priority:** P0  
**Dependencies:** T-019  
**File(s):** `app/agent/graph.py`

**Description:**
Define the LangGraph state machine that wires all review nodes together. Create a `StateGraph` with `ReviewState`. Add all 6 nodes (T-021 through T-026). Add conditional edges so the pipeline can short-circuit on errors.

**Node order:**
1. `fetch_diff` — always runs
2. `parse_diff` — runs after fetch_diff succeeds
3. `analyze` — runs after parse_diff succeeds
4. `format_comments` — runs after analyze succeeds
5. `post_comments` — runs after format succeeds, skipped if no comments
6. `post_summary` — always runs at the end (even if previous nodes failed)

**Edges:**
- If `fetch_diff` produces errors → go to `post_summary` (skip analysis)
- If `analyze` produces errors → go to `post_summary` (post what we have)
- If no comments to post → skip `post_comments` go directly to `post_summary`

**Acceptance Criteria:**
1. `StateGraph` is created with `ReviewState`
2. All 6 nodes are added with `graph.add_node("name", func)`
3. Conditional edges handle error paths correctly
4. The graph compiles without errors
5. `graph.invoke(...)` with initial state runs through the full pipeline

---

### T-021: Pipeline Node — Fetch Diff

**Priority:** P0  
**Dependencies:** T-011, T-019  
**File(s):** `app/agent/nodes/__init__.py`, `app/agent/nodes/fetch_diff.py`

**Description:**
Implement the first LangGraph node. Takes the current `ReviewState`, calls the MCP `get_pr_diff` tool (or directly calls the GitHub client) to fetch the raw diff for the PR. Stores the diff in `state["diff_raw"]` and the file list in `state["parsed_files"]` (as a basic file list — full parsing happens in the next node). Sets `state["errors"]` if the fetch fails.

**Acceptance Criteria:**
1. Node function accepts `state: ReviewState` and returns `partial` state updates
2. Fetches diff using `github_client.get_pr_diff(owner, repo, pr_number)`
3. On success: populates `diff_raw` and sets initial `parsed_files` with file paths
4. On failure: appends error to `state["errors"]` — does NOT raise
5. Handles empty diffs (draft PR, no changes) by setting an error and continuing

---

### T-022: Pipeline Node — Parse & Chunk Diff

**Priority:** P0  
**Dependencies:** T-021  
**File(s):** `app/agent/nodes/parse_diff.py`

**Description:**
Implement the diff parsing node. Receives `state["diff_raw"]`, parses the unified diff format into structured per-file chunks. Split each file's diff into hunks of max 50 lines (for LLM context window management). Filter out binary files, generated files (lockfiles, `node_modules/`, `dist/`, `__pycache__/`), and files matching `EXCLUDE_PATTERNS`. Populate `state["parsed_files"]` with a list of `ParsedFile` objects each containing their hunks.

**Acceptance Criteria:**
1. Parses raw unified diff text into structured `ParsedFile` objects
2. Each `ParsedFile` contains a list of hunks with line ranges and content
3. Hunks are capped at 50 lines each (split larger hunks)
4. Excluded file patterns are respected (binary files, lockfiles, generated dirs)
5. Files with only excluded changes are removed from the list
6. Returns an empty list gracefully if the diff is empty

---

### T-023: Pipeline Node — LLM Analysis

**Priority:** P0  
**Dependencies:** T-022  
**File(s):** `app/agent/nodes/analyze.py`

**Description:**
Implement the AI analysis node. For each parsed file, build a prompt that describes the code changes and asks the LLM to find bugs, security issues, and performance problems. Send the prompt to the configured LLM (Ollama or Anthropic based on `LLM_PROVIDER`). Parse the LLM's JSON response into a list of `AnalysisResult`. Temperature is set to 0.1 for deterministic outputs. If a chunk fails (timeout, parse error), log the error and continue with the next chunk — one bad chunk should not fail the entire review.

**Prompt structure:**
```
You are a senior code reviewer. Analyze this code diff for bugs, security vulnerabilities, and performance anti-patterns. Only flag real issues — ignore style preferences.

File: {file_path}
Changes:
{formatted_hunks}

Respond in JSON format:
{ "comments": [ { "file": "...", "line": 42, "category": "bug|security|performance|style|suggestion", "severity": "blocking|warning|suggestion", "description": "...", "suggestion": "..." } ] }
```

**Acceptance Criteria:**
1. Builds a prompt for each parsed file/hunk combination
2. Sends the prompt to Ollama HTTP API (`POST /api/generate`) or Anthropic API (`POST /v1/messages`)
3. Parses the JSON response into `AnalysisResult` objects
4. If a file fails (timeout, parse error), logs the error and continues to the next file
5. Validates that returned line numbers exist in the actual diff (drops hallucinated line numbers)
6. Caps the number of returned comments at `MAX_COMMENTS_PER_REVIEW` (default 15)

---

### T-024: Pipeline Node — Format Comments

**Priority:** P0  
**Dependencies:** T-023  
**File(s):** `app/agent/nodes/format_comments.py`

**Description:**
Implement the comment formatting node. Converts each `AnalysisResult` into a Markdown-formatted comment string following the templates defined in the Frontend Specification Document. Each comment includes:
- Severity badge (🚫 BLOCKING / ⚠️ WARNING / 💡 SUGGESTION) with category tag
- Description paragraph
- Code snippet in fenced code block (max 20 lines)
- Fix suggestion (if provided)
- Footer with file path and line number

Also computes `state["quality_score"]` (0–100) based on the number and severity of issues found. Populates `state["top_concerns"]` with the 3 most severe items. Populates `state["summary"]` with the summary comment template (score bar, top concerns table, review stats).

**Acceptance Criteria:**
1. Each `AnalysisResult` is formatted into a proper Markdown comment string
2. Severity badge is always the first line
3. Code snippets are truncated to 20 lines with `# ... truncated` if longer
4. `quality_score` is computed: 100 minus deductions per issue (blocking=-15, warning=-10, suggestion=-5)
5. `top_concerns` contains the 3 highest-severity issues as short strings
6. Summary includes score bar (20 block characters), top concerns, and review stats table
7. Footer includes file path and line number in GitHub reference format

---

### T-025: Pipeline Node — Post Inline Comments

**Priority:** P0  
**Dependencies:** T-013, T-024  
**File(s):** `app/agent/nodes/post_comments.py`

**Description:**
Implement the comment posting node. Iterates over `state["formatted_comments"]` and posts each one to GitHub using the MCP `post_comment` tool (or direct GitHub client call). Records each returned `github_comment_id` into `state["posted_comment_ids"]`. If a single comment fails to post (bad line number, permission error), logs the error and continues with the next comment.

**Acceptance Criteria:**
1. Iterates over all formatted comments and posts each to GitHub
2. Posts via `github_client.post_review_comment()` with the correct file, line, and commit SHA
3. Records returned comment IDs in `state["posted_comment_ids"]`
4. If a comment fails to post (422, 403), logs error and continues — does NOT fail the entire review
5. If no comments exist, the node is a no-op (skipped by graph logic)

---

### T-026: Pipeline Node — Post Summary Comment

**Priority:** P0  
**Dependencies:** T-014, T-024  
**File(s):** `app/agent/nodes/post_summary.py`

**Description:**
Implement the summary posting node. Posts `state["summary"]` to the PR conversation timeline using the MCP `post_summary` tool. Updates the `Review` record in the database with the final `quality_score`, `summary`, `top_concerns`, `total_comments`, `duration_seconds`, and `completed_at`. Updates the `PullRequest` status to `completed` (or `failed` if errors occurred).

**Acceptance Criteria:**
1. Summary is posted via `github_client.post_pr_comment()`
2. Review record is updated with quality_score, summary, top_concerns, total_comments, model_used, duration_seconds, completed_at
3. PullRequest status is set to `completed`
4. If errors occurred during the pipeline, summary still posts but mentions the errors
5. If even the summary fails to post (API down), the DB record is still updated

---

## Phase 5: Testing & Scripts

### T-027: Test Webhook Script

**Priority:** P1  
**Dependencies:** T-016  
**File(s):** `scripts/test_webhook.py`

**Description:**
Create a CLI script that sends a fake GitHub webhook payload to the local server. The script:
1. Generates a realistic PR opened payload with random PR number
2. Signs it with a known webhook secret (from args or env)
3. Sends it via HTTP POST to `http://localhost:8000/webhook/github` (or custom URL)
4. Prints the response status and body
5. Also prints the signature it computed for debugging

Usage: `python scripts/test_webhook.py --url http://localhost:8000 --secret mysecret --owner acme-corp --repo backend-api`

**Acceptance Criteria:**
1. Script sends a valid HMAC-signed webhook payload
2. Server returns `202 Accepted` when signature matches
3. Server returns `401` when signature is wrong
4. All command-line arguments have defaults for quick testing
5. The payload includes realistic data (realistic PR title, author, branch names)

---

### T-028: Unit Tests — Diff Parsing

**Priority:** P1  
**Dependencies:** T-022  
**File(s):** `tests/unit/test_parse_diff.py`

**Description:**
Write unit tests for the diff parser. Cover: parsing a normal multi-file diff, parsing an empty diff, parsing a single-file diff, filtering binary files, filtering excluded patterns, splitting large hunks into 50-line chunks, handling malformed diff input gracefully.

**Acceptance Criteria:**
1. All test cases pass with `pytest`
2. Coverage includes normal, edge case, and error inputs
3. Tests use realistic diff strings, not placeholders
4. Excluded pattern filtering is tested for at least 3 patterns

---

### T-029: Unit Tests — Comment Formatting

**Priority:** P1  
**Dependencies:** T-024  
**File(s):** `tests/unit/test_format_comments.py`

**Description:**
Write unit tests for the comment formatter. Cover: formatting a blocking bug comment, formatting a warning comment, formatting a suggestion comment, truncating long code snippets, computing quality score, generating top concerns, empty input (no comments to format), score boundaries (0 and 100).

**Acceptance Criteria:**
1. All test cases pass with `pytest`
2. Verify generated markdown contains correct severity badges and category emojis
3. Verify quality score is between 0–100
4. Verify code snippets >20 lines are truncated

---

### T-030: Integration Test — Webhook to Review

**Priority:** P1  
**Dependencies:** T-020, T-027  
**File(s):** `tests/conftest.py`, `tests/integration/test_review_pipeline.py`

**Description:**
Write an integration test that simulates the full flow: send a fake webhook → verify PR is created in DB → verify review task is enqueued → run the LangGraph pipeline in-process → verify comments are generated. Use a mock GitHub API (or `responses` library to mock HTTP calls to GitHub and Ollama). Do NOT hit real GitHub or real Ollama.

**Acceptance Criteria:**
1. Test creates a FastAPI `TestClient`, sends a signed webhook, asserts `202`
2. Test verifies a `PullRequest` record exists in the database
3. Test runs the LangGraph pipeline directly with mocked external calls
4. Test verifies `ReviewState` has populated fields after pipeline runs
5. Test verifies the review was saved to the database

---

### T-031: Docker Setup

**Priority:** P1  
**Dependencies:** T-015, T-017  
**File(s):** `docker/Dockerfile`, `docker/Dockerfile.worker`, `docker-compose.yml`

**Description:**
Create Docker setup for local development. `Dockerfile` builds the FastAPI app. `Dockerfile.worker` builds the Celery worker (same base but different entrypoint). `docker-compose.yml` defines services: `app` (FastAPI), `worker` (Celery), `db` (PostgreSQL 16), `redis` (Redis 7), `chromadb` (ChromaDB server). The app and worker depend on db and redis. All services share a `.env` file for configuration.

**Acceptance Criteria:**
1. `docker-compose up` starts all 5 services
2. App health check passes after services are up
3. Worker connects to Redis and is visible in `celery -A app.celery_app inspect ping`
4. PostgreSQL is accessible at the configured URL
5. `.env` file is read by docker-compose correctly

---

## Phase 6: v2 / Nice-to-Have

### T-032: RAG — Embeddings Module

**Priority:** P2  
**Dependencies:** T-005  
**File(s):** `app/rag/__init__.py`, `app/rag/embeddings.py`

**Description:**
Create the embeddings module for RAG. Use `sentence-transformers` to load `all-MiniLM-L6-v2` locally. Provide `generate_embedding(text: str) -> list[float]` that returns a 384-dimensional vector. Provide `generate_embeddings_batch(texts: list[str]) -> list[list[float]]` for batch processing. Cache the loaded model so it's only loaded once.

**Acceptance Criteria:**
1. `generate_embedding` returns a list of 384 floats
2. `generate_embeddings_batch` returns a list of embeddings in the same order
3. Model is loaded once and cached (singleton pattern)
4. Works without GPU (CPU fallback)

---

### T-033: RAG — Codebase Indexer

**Priority:** P2  
**Dependencies:** T-032  
**File(s):** `app/rag/indexer.py`

**Description:**
Create a codebase indexer that walks a local repository directory, reads all source files, generates embeddings, and stores them in ChromaDB. Exclude binary files, `.git/`, `node_modules/`, `__pycache__/`, `venv/`, and files >1MB. Chunk files by function/class boundaries when possible, or by 200-line sliding windows with 50-line overlap. Store the file path, language (from extension), and the chunk text as metadata.

**Acceptance Criteria:**
1. `index_repository(repo_path: str, repo_full_name: str)` indexes all source files
2. Excluded patterns are respected
3. Files are chunked intelligently (function boundaries preferred, fallback to sliding window)
4. Each chunk is stored in ChromaDB with file path, language, and line range metadata
5. Running the indexer twice updates (does not duplicate) existing entries

---

### T-034: RAG — Retrieval & Pipeline Node

**Priority:** P2  
**Dependencies:** T-033  
**File(s):** `app/rag/retriever.py`, `app/agent/nodes/rag_lookup.py`

**Description:**
Create the RAG retriever that queries ChromaDB for code patterns similar to the PR changes. For each file in the PR diff, compute its embedding and query ChromaDB for the top-5 most similar code chunks from the existing codebase. Return the chunks as additional context in the review prompt so the LLM can check for consistency with existing patterns.

Add the `rag_lookup` node to the LangGraph pipeline (between `parse_diff` and `analyze`). It enriches each parsed file's analysis context with similar patterns from the indexed codebase.

**Acceptance Criteria:**
1. `retrieve_similar_patterns(file_diff: str, top_k: int = 5)` returns matching code chunks
2. The `rag_lookup` node adds retrieved patterns to the state
3. The `analyze` node includes retrieved patterns in the prompt when available
4. If ChromaDB is unavailable, the node logs a warning and continues (non-blocking)

---

### T-035: Feedback Learning Loop

**Priority:** P2  
**Dependencies:** T-007  
**File(s):** `app/agent/nodes/feedback.py`, updates to `app/api/webhook.py`

**Description:**
Implement the feedback learning mechanism. When an engineer dismisses or resolves a comment on GitHub, the system needs to detect this and store it. In v2, this means:
1. Polling GitHub periodically for comment resolution state (or using webhook events for issue_comment.edited)
2. Storing dismissed comment patterns in ChromaDB as "negative examples"
3. Excluding similar patterns from future reviews

Create a `process_feedback` function that reads dismissed/resolved comments from the database and updates the RAG index with exclusion markers.

**Acceptance Criteria:**
1. A `/webhook/github` handler for `issue_comment.edited` events detects dismissals
2. Dismissed comments are marked in the database (`was_dismissed = True`)
3. The RAG retriever excludes patterns similar to previously dismissed comments
4. Feedback metrics are logged (dismissal rate per PR, per engineer)

---

### T-036: Multi-Repo Support

**Priority:** P2  
**Dependencies:** T-016, T-007  
**File(s):** Updates to `app/api/webhook.py`, `app/db/crud/repository.py`

**Description:**
Extend the app to support multiple repositories. Each repo has its own entry in the `repositories` table with its own `webhook_secret` and `is_active` flag. The webhook endpoint:
1. Looks up the repo by `repository.full_name` from the payload
2. Uses the repo-specific `webhook_secret` for signature validation
3. Uses the repo-specific GitHub token (stored per-repo, or use GitHub App installation tokens)
4. All queries filter by the resolved `repository_id`

**Acceptance Criteria:**
1. Multiple repos can be registered in the database
2. Each repo has its own webhook secret for validation
3. Webhook payloads are validated against the correct repo's secret
4. Reviews are stored scoped to the correct repository_id
5. A repo can be disabled (`is_active = False`) without affecting other repos

---

## Build Order Summary

```
Phase 0 — Foundation (parallel)
  T-001: Project scaffolding & deps
  T-002: Config & env loading
  T-003: Structured logging

Phase 1 — Database (sequential)
  T-004: DB session & engine
  T-005: All 5 models
  T-006: Alembic migrations
  T-007: CRUD operations

Phase 2 — GitHub Integration
  T-008: GitHub client factory
  T-009: Webhook signature validation
  T-010: MCP server entry point
  T-011: MCP tool — get_pr_diff
  T-012: MCP tool — get_pr_files
  T-013: MCP tool — post_comment
  T-014: MCP tool — post_summary

Phase 3 — API Layer
  T-015: FastAPI app + health endpoint
  T-016: Webhook endpoint
  T-017: Celery config
  T-018: Async review task

Phase 4 — Review Pipeline
  T-019: LangGraph state schema
  T-020: Pipeline graph
  T-021: Node — fetch diff
  T-022: Node — parse diff
  T-023: Node — LLM analysis
  T-024: Node — format comments
  T-025: Node — post inline comments
  T-026: Node — post summary

Phase 5 — Testing & Scripts
  T-027: Test webhook script
  T-028: Unit tests — diff parsing
  T-029: Unit tests — comment formatting
  T-030: Integration test
  T-031: Docker setup

Phase 6 — v2 / Nice-to-Have
  T-032: RAG embeddings
  T-033: RAG codebase indexer
  T-034: RAG retrieval + pipeline node
  T-035: Feedback learning loop
  T-036: Multi-repo support
```

---

## Quick Stats

| Phase | Tickets | P0 | P1 | P2 |
|---|---|---|---|---|
| 0 — Foundation | 3 | 2 | 1 | 0 |
| 1 — Database | 4 | 3 | 1 | 0 |
| 2 — GitHub | 7 | 7 | 0 | 0 |
| 3 — API Layer | 4 | 3 | 1 | 0 |
| 4 — Pipeline | 8 | 8 | 0 | 0 |
| 5 — Testing | 5 | 0 | 5 | 0 |
| 6 — v2 Features | 5 | 0 | 0 | 5 |
| **Total** | **36** | **23** | **8** | **5** |
