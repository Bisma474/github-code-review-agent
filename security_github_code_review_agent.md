# Security & Access Document
## Autonomous GitHub Code Review Agent

---

## Table of Contents

1. [Authentication Method](#1-authentication-method)
2. [User Roles & Permissions](#2-user-roles--permissions)
3. [Row-Level Security](#3-row-level-security)
4. [Error Handling Guide](#4-error-handling-guide)
5. [Edge Cases](#5-edge-cases)

---

## 1. Authentication Method

This app does not have a traditional user login page. It is a backend service that authenticates in two directions.

### Outbound (Your App → GitHub)

| Method | How It Works | When To Use |
|---|---|---|
| **GitHub Personal Access Token (PAT)** | A token you create in GitHub Settings → Developer Settings. Passed in every API call as a header. | v1 recommended. Simple, single-repo setups. One token = access to repos you have permission for. |
| **GitHub App (private key + App ID)** | A GitHub App generates short-lived installation tokens using its private key. More secure — tokens auto-rotate, scoped per installation. | v2 when you add multi-repo support. Each org/repo gets its own installation with minimum permissions. |

**Which one for v1:** Start with a PAT. Scope it to exactly the repos the agent needs to review. Use a fine-grained PAT (repo-scoped), not a classic one with global access.

### Inbound (GitHub → Your App)

| Method | How It Works |
|---|---|
| **Webhook secret validation** | When you register a webhook on GitHub, you set a secret. GitHub signs every webhook payload with this secret using HMAC-SHA256. Your app recomputes the signature on every incoming request and rejects mismatches. |

**What gets blocked:** Any HTTP request that hits `/webhook/github` without a valid signature is rejected with a 401 before any code runs. This stops attackers from faking PR events.

### Secret Storage Rules

| Secret | Where It Lives | Never Do This |
|---|---|---|
| `GITHUB_TOKEN` | `.env` file (never committed) | Hardcode in source code |
| `GITHUB_WEBHOOK_SECRET` | `.env` file | Log it, return it in API responses |
| `GITHUB_APP_PRIVATE_KEY` | Separate `.pem` file, loaded at startup | Store it in the database |
| Database credentials | `.env` file | Use the same password in dev and prod |
| `APP_SECRET_KEY` | `.env` file | Share it across teams — each deployment gets its own |

**v1 rule:** All secrets live in environment variables. No secret management service needed for v1. If you deploy to a cloud server, use that platform's env var feature.

---

## 2. User Roles & Permissions

There are no user accounts in this app. Instead, there are two roles that emerge from how the system is set up:

### Role 1: System Admin

Whoever deploys and runs the service.

| Can Do | Cannot Do |
|---|---|
| Start / stop the service | Access GitHub user data outside the configured repos |
| Set which repos the agent watches | Bypass GitHub's own access controls — the agent inherits the PAT's permissions |
| Configure the LLM model (Ollama / Anthropic) | Post to GitHub as any user — comments always come from the bot |
| View logs and review history in the database | |
| Run the `/health` endpoint to check the service is alive | |

**How the admin proves who they are:** By having access to the server or the `.env` file. There is no admin login screen. The admin is whoever controls the deployment.

### Role 2: PR Author (Engineer)

Any developer who opens a pull request on a watched repo.

| Can Do | Cannot Do |
|---|---|
| Receive AI review comments on their PR | Stop the agent from reviewing their PR |
| Dismiss or resolve individual AI comments on GitHub | Delete review history from the database |
| Give feedback (thumbs up / down) on comments | Access the service directly — everything happens through GitHub |

**How the engineer proves who they are:** They authenticate with GitHub normally. The app trusts GitHub's identity system implicitly.

### Role 3: Unauthenticated (Everyone Else)

Anyone hitting the service who is not a valid GitHub webhook.

| Can Do | Cannot Do |
|---|---|
| Hit `/health` (returns 200 OK, no sensitive data) | Trigger a review |
| Receive a 401 on `/webhook/github` if signature is invalid | Read any data from the database |
| | Access any internal route or MCP endpoint |

### Permission Matrix (v1)

| Action | Admin | Engineer | Unauthenticated |
|---|---|---|---|
| Trigger review via webhook | — (triggered by GitHub) | — (triggered by GitHub) | Blocked (401) |
| Read health endpoint | Allowed | Allowed | Allowed |
| Read review results from DB | Allowed | Via GitHub only | Blocked |
| Change configuration | Allowed | Blocked | Blocked |
| Post comments to GitHub | Via bot token | Via their own GitHub auth | Blocked |
| Shut down the service | Allowed | Blocked | Blocked |

---

## 3. Row-Level Security

Row-level security means: a user should only see data they are allowed to see. Since this app has no user accounts, RLS works differently.

### Data Boundary: Per Repository

All data in the database is scoped to a repository. A row in `pull_requests`, `reviews`, or `review_comments` belongs to exactly one repository.

**Rule:** If the service is configured for multiple repos in v2, data from Repo A must never leak into queries for Repo B.

### How RLS Is Enforced

| Layer | Enforcement |
|---|---|
| **Application code (CRUD layer)** | Every query in `app/db/crud/` filters by `repository_id`. There is no "list all PRs" query without a repo filter. |
| **Database foreign keys** | `pull_requests.repository_id` references `repositories.id`. A review can't exist without belonging to a PR, which belongs to a repo. The chain is enforced at the database level. |
| **GitHub API token scope** | The PAT or GitHub App token is scoped to specific repos. Even if the app tries to fetch data from a repo outside its scope, GitHub rejects it. This is a safety net, not the primary control. |

### What RLS Prevents

| Scenario | Outcome |
|---|---|
| Engineer opens PR on Repo A, app stores it. Engineer on Repo B opens PR. | Data stays separate by `repository_id`. No cross-repo data mixing. |
| Attacker sends fake payload to `/webhook/github` | Blocked by webhook signature validation. Never reaches the database. |
| Logs accidentally expose a PR from a different repo | Logs include `repository_id` and `full_name` but never the diff content. Sensitive data is logged at `DEBUG` level only, never `INFO`. |

### v1 Note

In v1, the app is configured for a single repo. RLS is still important because it prevents bugs even with one repo — you never accidentally return data from the wrong repo when you add more later.

---

## 4. Error Handling Guide

Every failure point in the system and what happens when it breaks.

### Webhook & Ingress

| Failure | What Happens | Response | Recovery |
|---|---|---|---|
| Invalid webhook signature | Request rejected before any processing | `401 Unauthorized` — no body detail given to caller | Check that `GITHUB_WEBHOOK_SECRET` in `.env` matches what you set in GitHub webhook settings |
| Missing required fields in webhook payload (no `action`, no `pull_request`) | Validation fails | `422 Unprocessable Entity` with a message like "Missing pull_request in payload" | Check GitHub webhook payload format — may be a different event type |
| Webhook received but repo is not in `is_active = true` | Event ignored. Logged at INFO level | `202 Accepted` — webhook is valid, but no review runs | Register the repo in the database first or set `is_active = true` |
| Webhook received for a PR action other than `opened` (e.g. `synchronize`, `closed`) | Ignored. v1 only reviews on open | `202 Accepted` — no review triggered | This is by design. v2 may add re-review on push. |

### GitHub API Calls

| Failure | What Happens | Response | Recovery |
|---|---|---|---|
| `GITHUB_TOKEN` is invalid or expired | MCP tool fails to fetch diff or post comment | Review status set to `failed`. Error logged with "401 from GitHub API" | Regenerate the token and update `.env`. Restart the service. |
| GitHub API rate limit exceeded (secondary rate limit) | MCP tool backs off with exponential retry (1s, 2s, 4s, 8s — up to 3 retries) | If all retries fail, review status set to `failed` | Reduce review frequency for busy repos. Cache API responses more aggressively. |
| PR is too large (thousands of files) | Diff fetch succeeds but diff parsing hits a size limit | Comment posted: "PR too large to review fully. Reviewed first 20 files." | In production, configure `MAX_FILES_TO_REVIEW` in env vars. |
| PR has no diff (e.g. draft PR, no commits yet) | Diff fetch returns empty | Review skipped. Status set to `completed` with 0 comments. | This is normal — no code to review yet. Logged at INFO level. |

### LLM / AI Analysis

| Failure | What Happens | Response | Recovery |
|---|---|---|---|
| Ollama is not running or model not pulled | HTTP connection refused to `localhost:11434` | Review status set to `failed`. Error: "Ollama not reachable at OLLAMA_BASE_URL" | Run `ollama serve` and `ollama pull deepseek-coder` |
| Ollama model runs out of memory (OOM) | Ollama process crashes or returns a 500 | Review status set to `failed` | Use a smaller model (e.g. `qwen2.5-coder:1.5b` instead of `7b`) or add more RAM |
| Anthropic API key is invalid or quota exhausted | API returns 401 or 429 | Review status set to `failed` | Check `ANTHROPIC_API_KEY`. Check billing at console.anthropic.com |
| LLM returns empty or unparseable response | Formatting step fails to extract comments | Review status set to `failed`. Raw LLM output logged at DEBUG level. | Retry with a stronger model or different prompt template. |
| LLM takes too long (>60s for a single analysis) | LangGraph node times out | Node retries once. If it fails again, review continues with whatever comments were generated so far. | Reduce diff chunk size per analysis call. |

### Database

| Failure | What Happens | Response | Recovery |
|---|---|---|---|
| Database connection refused (Postgres not running) | App fails to start or first DB query fails | `500 Internal Server Error` on health/webhook endpoints | Check `docker-compose up -d` or verify PostgreSQL service is running |
| Database migration not applied (missing column) | SQLAlchemy throws a programming error on insert | Review status set to `failed` | Run `alembic upgrade head` |
| Unique constraint violation (duplicate PR review) | Only happens if webhook fires twice for the same PR | Second webhook event is ignored at the DB level. Logged as a warning. | This is safe — the constraint prevents duplicate reviews. No action needed. |
| SQLite lock (if using SQLite for dev) | Write query times out. Happens under concurrent writes. | Review fails with "database is locked" | Switch to PostgreSQL for anything beyond local single-user testing. |

### Internal / Unexpected

| Failure | What Happens | Response | Recovery |
|---|---|---|---|
| Celery worker crashes mid-review | Task state is lost if not using result backend | The webhook event was already processed (200 returned). The PR will NOT get a review. | v2: Add a retry queue. v1: Manually re-trigger by re-opening the PR or hitting a debug endpoint. |
| Disk full | App logs stop writing. DB writes fail. | Unhealthy. `/health` endpoint should check disk space in production. | Free disk space or increase volume size. |
| Power loss / sudden shutdown | In-memory Celery tasks are lost. DB writes that were in-flight may be incomplete. | At startup, the app checks for PRs with `status = pending` and marks them as `failed`. | Re-open the PR to trigger a fresh review. |

### Error Response Format

All API errors follow the same shape:

```json
{
  "detail": "Human-readable message about what went wrong",
  "error_code": "WEBHOOK_INVALID_SIGNATURE",
  "timestamp": "2026-06-16T10:30:00Z"
}
```

| HTTP Code | Meaning | When |
|---|---|---|
| 200 | Success | Health check |
| 202 | Accepted | Webhook received, review queued |
| 401 | Unauthorized | Invalid webhook signature |
| 422 | Unprocessable | Missing or invalid payload fields |
| 429 | Too Many Requests | (Future) Rate limiting on webhook endpoint |
| 500 | Internal Error | Unexpected server failure |
| 502 | Bad Gateway | GitHub API or LLM is unreachable |
| 503 | Service Unavailable | App is starting up or shutting down |

---

## 5. Edge Cases

Things that will happen eventually. Handled before launch.

### PR & Diff Edge Cases

| Edge Case | What Happens |
|---|---|
| **PR has zero files changed** (e.g. just a merge commit) | Review runs, generates 0 comments. Summary says "No code changes to review." |
| **PR contains only binary files** (images, .exe, .zip) | Binary files are detected by extension and skipped. Review only runs on text files. |
| **PR deletes files only** (no additions/modifications) | Review runs on deleted lines. Can still flag issues in the removed code if relevant. Summary notes "Only deletions — no new code introduced." |
| **PR has 500+ files changed** | First 20 files are reviewed. A warning comment is posted saying the review is partial. Logged for admin awareness. |
| **PR contains generated files** (lockfiles, compiled output, `dist/`, `node_modules/`) | Path patterns in config exclude known generated directories. Not reviewed. |
| **Same line is changed multiple times across commits** | GitHub's diff API handles this — the review sees the final diff state only. |
| **PR has merge conflicts** | GitHub does not generate a diff for conflicted files. The agent skips conflicted files and reviews the rest. Warms in the summary comment. |

### Webhook Edge Cases

| Edge Case | What Happens |
|---|---|
| **Webhook fires twice for the same PR open event** | Second event hits the unique constraint in `(repository_id, github_pr_number)`. Ignored. Logged as warning. |
| **Webhook delivers with a delay** (>10 minutes after PR open) | Still processed normally. No SLA guarantee for delayed webhooks. |
| **Webhook arrives during app restart** | FastAPI queues the request up to the OS backlog limit. If the app is down, the request is lost. Retry by re-opening the PR. |
| **Attacker sends thousands of fake webhooks** | Each one fails signature validation at the middleware level. Very cheap to reject. No database writes. No review spawned. |
| **Webhook from an unregistered repo** | The webhook is validated by signature (it came from GitHub) but the repo is not in the app's database. Event ignored. Logged. |

### LLM / Review Edge Cases

| Edge Case | What Happens |
|---|---|
| **LLM returns a suggestion that references a line number that doesn't exist** | The formatting step validates all line numbers against the actual diff. Invalid references are dropped with a debug log. |
| **LLM hallucinates a file that wasn't changed** | Same as above — cross-checked against `get_pr_files` results. Dropped. |
| **LLM review is too long** (>10 comments) | Comments are capped at `MAX_COMMENTS_PER_REVIEW` (default 15). Additional comments are logged but not posted. |
| **LLM flags something that is actually intentional** (e.g. a security test) | The engineer dismisses the comment. In v2, dismissed comments are used to train future reviews. In v1, the comment stays dismissed. |
| **LLM is completely unavailable** (Ollama down, API down) | Review fails with a clear error. Status set to `failed`. Admin notified via logs. |
| **Two PRs opened simultaneously** | Both webhooks arrive. Celery queues both. They run sequentially or in parallel depending on `CELERY_WORKER_CONCURRENCY`. |

### Config & Deployment Edge Cases

| Edge Case | What Happens |
|---|---|
| **`.env` file is missing a required variable** | App fails to start with a clear error listing which variable is missing (powered by pydantic-settings). |
| **`GITHUB_TOKEN` only has read access** (no write) | Fetching diffs works. Posting comments fails with a 403. Review status set to `failed`. |
| **Two instances of the app run simultaneously** (same DB, same queue) | Both process webhooks. The unique constraint on `(repository_id, github_pr_number)` prevents duplicate reviews. The second gets a DB error and skips. |
| **App runs out of disk space mid-review** | Writing the review record to the DB fails. The PR does not get a review. |
| **Ollama model is swapped without restarting the app** | The app was initialized with the old model. Restart the app for it to pick up `OLLAMA_MODEL` from `.env`. |
| **Running behind a reverse proxy** (nginx, Caddy) | Webhook source IP changes. Signature validation still works because it uses the secret, not the IP. Ensure `X-Forwarded-*` headers are trusted for logging. |

### v1 Explicitly Not Handling

These are deferred to v2:

| Edge Case | v2 Plan |
|---|---|
| Malicious code in PR that attacks the LLM (prompt injection) | Add input sanitization and a "suspicious content" detector |
| Engineer spam-dismisses every comment to game quality metrics | Track dismissal rate per engineer and flag outliers |
| Large monorepo with 10,000+ files | Pre-filter by diff relevance before sending to LLM |
| PR with sensitive data (API keys committed accidentally) | Add a secret scanning node before the main review |

---

## Configuration: Security-First Defaults

Add these to `.env.example` for v1:

```env
# Security
APP_ENV=development
MAX_FILES_TO_REVIEW=20
MAX_COMMENTS_PER_REVIEW=15
REVIEW_TIMEOUT_SECONDS=300
EXCLUDE_PATTERNS=*.lock,*.exe,*.dll,*.so,*.bin,node_modules/,dist/,build/,vendor/,__pycache__/

# Rate limiting (v1 uses basic, v2 can switch to Redis-backed)
RATE_LIMIT_WEBHOOKS_PER_MINUTE=30
```

---

## Quick Security Checklist

Before putting this in front of real PRs:

- [ ] `GITHUB_TOKEN` is a fine-grained PAT scoped only to the repos being reviewed
- [ ] `GITHUB_WEBHOOK_SECRET` is set to a random string (at least 32 chars)
- [ ] Webhook signature validation is the FIRST thing that runs in the webhook handler
- [ ] `.env` is in `.gitignore` — never committed
- [ ] Database password is different from the default `password` in production
- [ ] Logs do not contain `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, or webhook secrets
- [ ] Health endpoint (`/health`) exposes no sensitive info — just returns `{"status": "ok"}`
- [ ] Only `/health` and `/webhook/github` are exposed to the internet. The MCP server and DB port are internal-only.
- [ ] Ollama is bound to `127.0.0.1` (localhost), not `0.0.0.0` — no external access to the LLM
