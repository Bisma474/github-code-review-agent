# Frontend Specification Document
## Autonomous GitHub Code Review Agent

---

**Important note:** This app has no traditional browser-based UI. The "frontend" is the GitHub Pull Request interface — every review comment is rendered as GitHub-flavored Markdown inside GitHub's native PR conversation view. All design decisions optimize for readability inside that constrained environment.

---

## Table of Contents

1. [Design System](#1-design-system)
2. [Comment Component Library](#2-comment-component-library)
3. [Summary Comment Template](#3-summary-comment-template)
4. [API & Integration Spec](#4-api--integration-spec)

---

## 1. Design System

### Color Palette (Severity Badges)

Since GitHub renders comments as Markdown, we use emoji + bold labels to simulate color-coded severity badges. No custom CSS is possible inside GitHub PR comments.

| Severity | Badge | Emoji | Label | Hex Intent |
|---|---|---|---|---|
| **blocking** | `🚫 BLOCKING` | `:no_entry_sign:` | Red / danger | #D73A4A (GitHub red) |
| **warning** | `⚠️ WARNING` | `:warning:` | Amber / caution | #BF8A0C (GitHub amber) |
| **suggestion** | `💡 SUGGESTION` | `:bulb:` | Blue / info | #0969DA (GitHub blue) |

### Category Labels

Each comment also carries a smaller category tag below the severity badge.

| Category | Label | Emoji |
|---|---|---|
| **bug** | `🐛 Bug` | `:bug:` |
| **security** | `🔒 Security` | `:lock:` |
| **performance** | `⚡ Performance` | `:zap:` |
| **style** | `🎨 Style` | `:art:` |
| **suggestion** | `💡 Suggestion` | `:bulb:` |

### Typography

The app does not control fonts, sizes, or line heights — these are determined entirely by GitHub's markdown renderer. The comment templates are designed to work well with GitHub's defaults:

| Element | GitHub Rendering |
|---|---|
| Headers | `###` or `**bold**` — rendered as bold 14px |
| Body text | Plain text, 14px, `-apple-system` font stack |
| Code blocks | ```triple backticks``` — monospace, syntax-highlighted |
| Inline code | `` `backticks` `` — monospace, gray background |
| Lists | `- ` dash lists or `1. ` numbered lists |
| Horizontal rules | `---` — thin gray line separator |
| Blockquotes | `> ` — indented, gray left border |

### Spacing & Layout Rules

Since comments live inside GitHub's native PR diff view and PR conversation timeline, the layout rules are:

| Context | Max Width | Behavior |
|---|---|---|
| Inline diff comment | 900px (GitHub default) | Posted on a specific line in the diff |
| PR review summary comment | 900px | Posted as a PR-level comment thread |
| Reply / discussion | N/A — GitHub handles threading natively |

**Internal spacing within a comment:**

```
[SEVERITY BADGE]           ← blank line after
[Category tag]             ← no blank line after
                           ← 1 blank line
Issue description          ← plain sentence(s)
                           ← 1 blank line
Code snippet (if needed)  ← wrapped in triple backticks
                           ← 1 blank line
Recommended fix            ← bold "Fix:" prefix, then plain text
                           ← 1 blank line
---                        ← horizontal rule as footer
Reference links / metadata ← file path + line number
```

---

## 2. Comment Component Library

All comments are generated server-side as Markdown strings by `format_comments.py` and posted via the MCP `post_comment` tool. There are four comment components.

### Component 1: Inline Bug / Vulnerability Comment

Posted directly on the offending line of the PR diff.

**Template:**

```markdown
🚫 **BLOCKING** · 🐛 Bug

This SQL query interpolates user input directly into the string. An attacker can craft input that modifies the query to read or delete arbitrary data.

```python
cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")
```

**Fix:** Use parameterized queries instead:

```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_input,))
```

---
`src/auth/login.py:47` · Reviewed by code-review-agent v1.0
```

**Render behavior on GitHub:**
- Badge in bold at the top
- Category emoji + label dimmed next to badge
- Description in plain paragraph
- Code blocks with syntax highlighting
- Fix section differentiated by bold prefix
- Footer with GitHub-style reference

### Component 2: Inline Warning Comment

Posted on a line that has room for improvement but is not immediately dangerous.

**Template:**

```markdown
⚠️ **WARNING** · ⚡ Performance

This list comprehension is recomputed on every loop iteration. On large datasets this adds measurable overhead.

**Fix:** Hoist the computation outside the loop.

```python
# Before
for item in data:
    processed = [transform(x) for x in item.subset]
    save(processed)

# After
for item in data:
    processed = precomputed_map[item.id]
    save(processed)
```

---
`src/processing/batch.py:102` · Reviewed by code-review-agent v1.0
```

### Component 3: Inline Suggestion Comment

A non-blocking style or maintainability suggestion.

**Template:**

```markdown
💡 **SUGGESTION** · 🎨 Style

This function name is ambiguous. `process_data` does not describe what kind of processing happens. Consider a more descriptive name.

**Fix:** Rename to `validate_user_input` or `sanitize_payload`.

---
`src/validation/forms.py:11` · Reviewed by code-review-agent v1.0
```

### Component 4: PR-Level Warning (Partial Review)

Used when the PR is too large, has merge conflicts, or could not be fully reviewed.

**Template:**

```markdown
⚠️ **WARNING** · Partial Review

This PR contains 47 changed files. Only the first 20 files were reviewed to keep response time under 60 seconds. Open a new PR with fewer changes for a full review.

---
Reviewed by code-review-agent v1.0
```

### Comment Formatting Rules (enforced in `format_comments.py`)

| Rule | Implementation |
|---|---|
| Max comment body length | 5000 characters (GitHub hard limit is 65536, lower limit keeps LLM outputs constrained) |
| Max code snippet length | 20 lines per snippet. Longer snippets are truncated with `# ... truncated` |
| File path format | Always relative to repo root: `src/auth/login.py` not `./src/auth/login.py` |
| Line number format | Single line: `:42`. Range: `:42-48`. Always prefixed with the file path. |
| Severity badge | Always the first line of the comment. Followed by a blank line. |
| Empty suggestions | If the LLM provides no fix suggestion, the Fix line is omitted entirely. |

---

## 3. Summary Comment Template

One summary comment per PR, posted to the PR conversation timeline after all inline comments are posted.

### Structure

```
## AI Code Review · Quality Score: [SCORE]/100

[PROGRESS BAR — 20 block characters, filled proportionally]

### Top 3 Concerns

1. **Concern title** — Brief explanation
2. **Concern title** — Brief explanation
3. **Concern title** — Brief explanation

### Summary

[Paragraph summarizing the overall state of the PR]

### Review Stats

| Metric | Value |
|---|---|
| Files reviewed | 12 |
| Inline comments | 8 |
| Blocking | 2 |
| Warnings | 4 |
| Suggestions | 2 |
| Review duration | 34s |
| Model | deepseek-coder |

---
_Reviewed by code-review-agent v1.0 · [Learn more](https://github.com/your-org/code-review-agent)_
```

### Quality Score Bar

Generated as a Markdown table row with block characters. No images or external assets.

| Score Range | Visual (20 chars) | Label |
|---|---|---|
| 90–100 | `████████████████████` | Excellent |
| 70–89 | `████████████████░░░░` | Good |
| 50–69 | `██████████░░░░░░░░░░` | Needs improvement |
| 0–49 | `████░░░░░░░░░░░░░░░░` | Critical |

Generation logic: `█` = filled block (U+2588), `░` = empty block (U+2591).  
Filled count = `round(score / 100 * 20)`.

### Summary Comment Rules (enforced in `post_summary.py`)

| Rule | Implementation |
|---|---|
| Post timing | Must post AFTER all inline comments are confirmed posted (check for `github_comment_id` on each) |
| Top concerns | Pulled from the LangGraph state. Max 3. Each is 50–120 chars. |
| Review stats | Computed from the completed review record in the database. |
| Model name | Read from `LLM_PROVIDER` / `LLM_MODEL` config. |

---

## 4. API & Integration Spec

Every external service the app talks to, what data is sent, and what comes back.

### 4.1 GitHub REST API (via PyGithub)

**Service:** GitHub API v3 (REST)  
**Auth:** `Authorization: Bearer <GITHUB_TOKEN>`  
**Base URL:** `https://api.github.com`  
**Library:** `PyGithub` (wraps raw HTTP calls)

#### Endpoint 1: Get PR Diff

| Field | Value |
|---|---|
| **Purpose** | Fetch the unified diff of a pull request |
| **Method** | `GET` |
| **URL** | `/repos/{owner}/{repo}/pulls/{pr_number}` |
| **Headers** | `Accept: application/vnd.github.v3.diff` (returns raw diff text) |
| **Sent** | Nothing in body |
| **Response** | Raw diff text (`Content-Type: text/plain`). Lines prefixed with `+`, `-`, or space. Includes `diff --git` headers with file paths. |
| **Error** | `404` — PR not found or token lacks access. `403` — token scope insufficient. |
| **Caching** | Cache by `(repo, pr_number)` for 60s via Redis (prevent refetch on retries). |

**PyGithub equivalent:**
```python
from github import Github
g = Github(token)
repo = g.get_repo("owner/repo")
pr = repo.get_pull(number)
diff = pr.diff  # property that fetches the raw diff
```

#### Endpoint 2: List PR Files

| Field | Value |
|---|---|
| **Purpose** | Get a list of all files changed in the PR with metadata |
| **Method** | `GET` |
| **URL** | `/repos/{owner}/{repo}/pulls/{pr_number}/files` |
| **Sent** | Nothing |
| **Response** | JSON array. Each entry: `{ filename, status, additions, deletions, changes, blob_url, raw_url, contents_url, patch }` |
| **Error** | Same as above |
| **Caching** | Cache by `(repo, pr_number)` for 60s. Invalidated if webhook re-fires for the same PR. |

**Used for:** Filtering binary files, counting changed files, building file-level metadata for comments.

#### Endpoint 3: Post Inline Review Comment

| Field | Value |
|---|---|
| **Purpose** | Post a comment on a specific line of a specific file in the diff |
| **Method** | `POST` |
| **URL** | `/repos/{owner}/{repo}/pulls/{pr_number}/comments` |
| **Sent** | `{ "body": "...", "path": "src/auth/login.py", "line": 42, "commit_id": "sha..." }` |
| **Response** | The created comment object: `{ id, body, path, line, created_at, user, ... }` |
| **Error** | `422` — invalid line number or position. `403` — token lacks write access to pull_requests. |

**Rules:**
- `commit_id` must be the latest commit SHA on the PR's head branch (fetched from the PR object)
- `line` is the line number in the final diff (not the file)
- If the line number is in a removed section (prefixed with `-` in the diff), the comment is still posted — GitHub handles it correctly

#### Endpoint 4: Post PR-Level Comment (Summary)

| Field | Value |
|---|---|
| **Purpose** | Post the summary comment on the main PR conversation timeline |
| **Method** | `POST` |
| **URL** | `/repos/{owner}/{repo}/issues/{pr_number}/comments` |
| **Sent** | `{ "body": "..." }` (full markdown summary) |
| **Response** | The created comment object |
| **Error** | `403` — token lacks write access to issues |

**Why Issues endpoint:** GitHub treats PR comments as issue comments internally. This is the correct endpoint for PR-level (not inline) comments.

#### Endpoint 5: Get Repo Details (Setup)

| Field | Value |
|---|---|
| **Purpose** | Register a repo when setting up the agent |
| **Method** | `GET` |
| **URL** | `/repos/{owner}/{repo}` |
| **Sent** | Nothing |
| **Response** | `{ id, name, full_name, owner, private, ... }` |
| **Used by:** `scripts/setup_repo.py` or the repo registration flow |

---

### 4.2 GitHub Webhooks (Inbound)

**Service:** GitHub Webhook events  
**Auth:** HMAC-SHA256 signature verification  

#### Event: Pull Request Opened

| Field | Value |
|---|---|
| **Trigger** | User opens a new PR |
| **Payload method** | `POST` to `/webhook/github` |
| **Content type** | `application/json` |
| **Sent by GitHub** | Full webhook payload including `action: "opened"`, `pull_request` object, `repository` object, `sender` object |
| **Your app does** | Validates signature → Parses JSON → Extracts `action`, `pull_request.number`, `repository.full_name`, `sender.login` → Checks if repo is active → Enqueues review job |
| **Response to GitHub** | `202 Accepted` — webhook received |
| **Payload shape (relevant fields)** | `{ "action": "opened", "pull_request": { "number": 42, "title": "...", "head": { "sha": "abc123", "ref": "feat/x" }, "base": { "sha": "def456", "ref": "main" }, "user": { "login": "dev1" }, "url": "..." }, "repository": { "full_name": "owner/repo", "id": 12345 }, "sender": { "login": "dev1" } }` |

#### Event: Pull Request Synchronize (v2)

| Field | Value |
|---|---|
| **Trigger** | New commits pushed to an existing PR |
| **Handling (v1)** | Ignored. Logged at DEBUG level. v1 only triggers on `action: "opened"`. |
| **v2 plan** | Re-run review on new commits. Delete previous review comments and replace. |

#### Event: Pull Request Closed

| Field | Value |
|---|---|
| **Trigger** | PR merged or closed without merge |
| **Handling (v1)** | Ignored. The review stays on the PR as a record. |

#### Webhook Signature Validation Flow

```
Incoming POST /webhook/github
         │
         ▼
Read header: X-Hub-Signature-256
         │
         ▼
Compute HMAC-SHA256(webhook_secret, request_body)
         │
         ▼
Compare? ──── No ──→ 401 Unauthorized, log warning
         │
        Yes
         │
         ▼
Parse JSON → validate required fields → enqueue review
```

---

### 4.3 Ollama API (Local LLM)

**Service:** Ollama HTTP API  
**Auth:** None (localhost only — bind to `127.0.0.1`)  
**Base URL:** `http://localhost:11434`  
**Documentation:** https://github.com/ollama/ollama/blob/main/docs/api.md

#### Endpoint: Generate Completion

| Field | Value |
|---|---|
| **Purpose** | Send code diff chunks for analysis. Returns structured review comments. |
| **Method** | `POST` |
| **URL** | `/api/generate` |
| **Headers** | `Content-Type: application/json` |
| **Sent** | ```json { "model": "deepseek-coder", "prompt": "...formatted prompt with diff...", "stream": false, "options": { "temperature": 0.1, "top_p": 0.9, "max_tokens": 4096 } }``` |
| **Response** | ```json { "model": "deepseek-coder", "response": "...LLM output...", "done": true, "total_duration": 12345678900, "eval_count": 512 }``` |
| **Error** | Connection refused — Ollama not running. `500` — model OOM or invalid config. |

**Temperature setting:** `0.1` (low). Code review is a deterministic task — low temperature ensures consistent, reproducible outputs.

**Prompt structure sent to Ollama:**
```
You are a senior code reviewer. Analyze the following code diff for bugs, security vulnerabilities, and performance issues.

File: src/auth/login.py
Changes:
- line 42: cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")
- line 55: password = request.form.get("password")

Respond in this JSON format:
{
  "comments": [
    {
      "file": "src/auth/login.py",
      "line": 42,
      "category": "security",
      "severity": "blocking",
      "description": "...",
      "suggestion": "..."
    }
  ]
}

Only include real issues. Do not flag style preferences or subjective opinions.
```

#### Endpoint: List Models (Setup)

| Field | Value |
|---|---|
| **Purpose** | Verify the configured model is available |
| **Method** | `GET` |
| **URL** | `/api/tags` |
| **Sent** | Nothing |
| **Response** | `{ "models": [ { "name": "deepseek-coder:latest", ... } ] }` |
| **Called during:** App startup, health check |

---

### 4.4 Anthropic API (Optional, Pay-Per-Use)

**Service:** Anthropic Messages API  
**Auth:** `x-api-key: <ANTHROPIC_API_KEY>`  
**Base URL:** `https://api.anthropic.com/v1`  
**Documentation:** https://docs.anthropic.com/en/api/messages

#### Endpoint: Create Message

| Field | Value |
|---|---|
| **Purpose** | Higher-quality code review using Claude |
| **Method** | `POST` |
| **URL** | `/v1/messages` |
| **Headers** | `x-api-key: <key>`, `anthropic-version: 2023-06-01`, `Content-Type: application/json` |
| **Sent** | ```json { "model": "claude-sonnet-4-6", "max_tokens": 4096, "temperature": 0.1, "system": "You are a senior code reviewer...", "messages": [ { "role": "user", "content": "Analyze this diff:\n..." } ] } ``` |
| **Response** | ```json { "id": "msg_...", "type": "message", "content": [ { "type": "text", "text": "..." } ], "model": "claude-sonnet-4-6", "usage": { "input_tokens": 500, "output_tokens": 300 } } ``` |
| **Error** | `401` — invalid API key. `429` — rate limited or quota exceeded. `529` — temporary overload (retry with backoff). |

**Switching logic in `analyze.py`:**
```python
if config.LLM_PROVIDER == "ollama":
    return call_ollama(diff_chunks)
elif config.LLM_PROVIDER == "anthropic":
    return call_anthropic(diff_chunks)
```

---

### 4.5 ChromaDB (Vector Store, v2)

**Service:** ChromaDB HTTP API  
**Auth:** None (localhost only for v1)  
**Base URL:** `http://localhost:8000`  
**Library:** `chromadb` Python client

#### Endpoint: Add Documents (Indexing)

| Field | Value |
|---|---|
| **Purpose** | Index codebase files into the vector store for pattern matching |
| **Method** | `POST` (via Python client, underlying HTTP) |
| **URL** | `/api/v1/collections/{name}/add` |
| **Sent** | `{ "ids": ["file1.py"], "embeddings": [[...]], "metadatas": [{"file": "src/auth/login.py", "language": "python"}], "documents": ["def login(): ..."] }` |
| **Response** | `{ "success": true }` |

#### Endpoint: Query (Retrieval)

| Field | Value |
|---|---|
| **Purpose** | Find code patterns similar to the PR diff |
| **Method** | `POST` (via Python client) |
| **URL** | `/api/v1/collections/{name}/query` |
| **Sent** | `{ "query_embeddings": [[...]], "n_results": 5 }` |
| **Response** | `{ "ids": [...], "distances": [...], "metadatas": [...], "documents": [...] }` |

#### Endpoint: Heartbeat

| Field | Value |
|---|---|
| **Purpose** | Check ChromaDB is alive |
| **Method** | `GET` |
| **URL** | `/api/v1/heartbeat` |
| **Response** | `{ "nanosecond heartbeat": 1712345678000000000 }` |

---

### 4.6 HuggingFace Embeddings (Local)

**Service:** Sentence-Transformers (local Python library)  
**Auth:** None  
**Library:** `sentence-transformers` Python package

#### Usage: Generate Embedding

| Field | Value |
|---|---|
| **Purpose** | Convert code text into vector embeddings for RAG |
| **How it works** | Loads `all-MiniLM-L6-v2` model locally via `sentence-transformers`. Calls `model.encode(text)` in Python. Returns a 384-dimensional float vector. |
| **Sent** | `model.encode("def login(password): ...")` |
| **Response** | `np.array([0.123, -0.456, ...])` — 384 floats |
| **Performance** | ~5ms per call on CPU. ~1ms on GPU. |

**No HTTP endpoint.** The model runs in-process via the Python library. The embedding calculation happens inside `app/rag/embeddings.py`.

---

### 4.7 Cloudflared Tunnel (Local Dev)

**Service:** Cloudflare Tunnel (`cloudflared`)  
**Auth:** None (invoked locally, creates a public URL)  
**Documentation:** https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

#### Usage: Expose Local Server

| Field | Value |
|---|---|
| **Purpose** | Give GitHub a public URL to send webhooks during local development |
| **Command** | `cloudflared tunnel --url http://localhost:8000` |
| **Output** | `https://random-name.trycloudflare.com` — public URL that forwards to `localhost:8000` |
| **Sent** | Nothing (creates a TCP tunnel) |
| **Response** | GitHub sends webhooks to the cloudflared URL, which forwards them to FastAPI |
| **Limits** | No account needed. No rate limits. Session lasts as long as the process runs. |

**Setup step:** Register the webhook on GitHub with URL: `https://random-name.trycloudflare.com/webhook/github`

---

### 4.8 Internal API: FastAPI Endpoints

These are the endpoints your own app exposes. No third party involved, but documented here for completeness.

#### `GET /health`

| Field | Value |
|---|---|
| **Purpose** | Liveness check for monitoring and Docker health checks |
| **Response** | `{ "status": "ok", "timestamp": "2026-06-16T10:30:00Z", "version": "1.0.0" }` |
| **Called by** | Docker health check, monitoring tools, engineers verifying the app is running |

#### `POST /webhook/github`

| Field | Value |
|---|---|
| **Purpose** | Receive GitHub webhook events for pull requests |
| **Request** | GitHub webhook payload (JSON) |
| **Response** | `202 Accepted` — `{ "status": "queued", "pr_number": 42 }` |
| **Called by** | GitHub webhook delivery system |

---

## Data Flow Summary

```
                     ┌──────────────────────────────┐
                     │       GitHub Webhook          │
                     │  POST /webhook/github          │
                     └──────────┬───────────────────┘
                                │
                                ▼
                     ┌──────────────────────────────┐
                     │     FastAPI (validate +        │
                     │     enqueue in Celery)         │
                     └──────────┬───────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
        ┌───────────────────┐   ┌──────────────────────┐
        │  Celery Worker     │   │   Redis Queue         │
        │  picks up job      │   │   (de-duplication)    │
        └──────────┬─────────┘   └──────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────┐
        │      LangGraph Pipeline              │
        │                                      │
        │  1. Fetch diff ──────────────────► GitHub API      │
        │  2. Parse & chunk                    │
        │  3. (v2) RAG lookup ───────────────► ChromaDB      │
        │  4. LLM analysis ──────────────────► Ollama/Anthropic  │
        │  5. Format comments                  │
        │  6. Post inline ───────────────────► GitHub API      │
        │  7. Post summary ──────────────────► GitHub API      │
        └──────────────────────────────────────┘
```

---

## Rendering Behavior on GitHub (What Engineers See)

| Scenario | Visual |
|---|---|
| **Single inline comment** | A badge-labeled comment attached to the exact line in the Files Changed tab. Collapsed by default — expand to read. |
| **Multiple inline comments in one file** | Each line has its own comment thread. Comments on adjacent lines stack vertically. |
| **Summary comment** | Posted as a new comment in the PR Conversation tab. Pinned by the bot user. Contains score bar, top concerns, and stats table. |
| **PR with no issues** | No inline comments. Summary comment says "No issues found — this PR looks clean." |
| **Failed review** | No comments posted. The bot posts an issue comment: "Review failed due to [reason]. Check the app logs for details." |

---

## Frontend File Structure

The "frontend" logic lives entirely in the comment formatting and posting modules:

```
app/agent/nodes/
├── format_comments.py     # Comment templates, Markdown generation, validation
├── post_comments.py       # Calls MCP post_comment tool for each comment
└── post_summary.py        # Generates summary comment with score bar + stats
```

No HTML, CSS, JavaScript, or frontend framework is needed for v1.
