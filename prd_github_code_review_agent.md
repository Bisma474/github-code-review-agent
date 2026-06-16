# Product Requirements Document
## Autonomous GitHub Code Review Agent

---

## Problem Statement

Code reviews are a bottleneck in engineering teams. Senior engineers spend 30–60 minutes reviewing a single pull request — time that could go toward architecture, system design, and higher-leverage work. At scale, this blocks shipping velocity. Most routine review comments (style issues, common bugs, security patterns) are repetitive and can be automated.

There is no lightweight, self-hosted tool that connects an AI agent directly to GitHub PRs, understands your existing codebase patterns, and posts structured, actionable review comments automatically.

---

## Target Users

- **Primary:** Backend and full-stack engineers at mid-size to large engineering teams (5–50 engineers)
- **Secondary:** Solo developers and open-source maintainers who want automated quality gates
- **Tech comfort:** High — users are comfortable with GitHub, webhooks, and CLI tools
- **Frustrations:** Slow review cycles, inconsistent review quality, reviewer availability bottlenecks
- **Goals:** Ship faster, catch bugs earlier, reduce cognitive load on senior engineers

---

## Product Vision

An AI-powered code review agent that automatically reviews every pull request, posts structured line-by-line comments on GitHub, and improves over time based on engineer feedback — so senior engineers can focus on what only humans can do.

---

## Core Features

### Must-Have

| Feature | Description |
|---|---|
| GitHub PR Trigger | Automatically activates when a new PR is opened via webhook |
| PR Diff Analysis | Reads and parses the full diff of the PR |
| AI Code Review | Detects bugs, security vulnerabilities, and performance anti-patterns |
| GitHub Comment Posting | Posts structured, line-by-line review comments directly on the PR |
| Summary Comment | Generates an overall quality score and top 3 concerns as a summary comment |
| MCP Server (GitHub) | Custom-built MCP server connecting the AI agent to the GitHub API |

### Nice-to-Have

| Feature | Description |
|---|---|
| RAG over Codebase | Cross-references PR changes against existing codebase patterns using vector search |
| Feedback Learning | Dismissed or resolved suggestions are stored and avoided in future PRs |
| Multi-repo Support | Agent can be configured across multiple repositories |
| Review Severity Levels | Comments labeled as `blocking`, `warning`, or `suggestion` |

---

## App Flow

1. **Developer opens a PR** on GitHub
2. **Webhook fires** → hits the FastAPI listener endpoint
3. **Agent fetches PR diff** via GitHub API (through MCP server)
4. **LangGraph workflow kicks off:**
   - Node 1: Parse and chunk the diff
   - Node 2: (Optional) RAG lookup — match changed code against existing patterns in ChromaDB
   - Node 3: Send to LLM for analysis — bugs, security, performance
   - Node 4: Format structured comments (file, line number, issue, suggestion)
   - Node 5: Post comments to GitHub PR via MCP
   - Node 6: Post summary comment with quality score + top 3 concerns
5. **Engineer reviews AI comments** — accepts, dismisses, or resolves
6. **(Optional) Feedback stored** in ChromaDB — dismissed patterns excluded from future reviews

---

## MVP Scope

The v1 MVP includes:

- Webhook listener that receives PR open events
- MCP server that reads PR diffs and posts comments via GitHub API
- LLM-powered review for bugs, security issues, and performance patterns (Ollama + local model for free, or Anthropic API for better quality)
- Structured line-by-line comment posting
- Summary comment on each PR

**Explicitly NOT in v1:**
- RAG over existing codebase (add in v2)
- Feedback/learning loop (add in v2)
- Multi-repo support
- Dashboard or UI
- Review approval gating (blocking merges)

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agent Runtime | Ollama + local LLM (free) or Anthropic API (pay-per-use) |
| Agent Orchestration | LangGraph |
| GitHub Integration | Custom MCP Server + PyGithub + GitHub REST API |
| Webhook Listener | FastAPI (Python) |
| Vector Store (v2) | ChromaDB |
| Language | Python 3.12+ |

---

## Success Metrics

| Metric | Target |
|---|---|
| PR review latency | Agent posts first comment within 60 seconds of PR open |
| Comment relevance | ≥ 70% of AI comments rated useful by engineers (thumbs up) |
| Bug catch rate | At least 1 valid issue flagged per PR (on non-trivial diffs) |
| Engineer time saved | ≥ 20 min/PR saved on routine review comments |
| False positive rate | < 30% of comments dismissed as irrelevant |

---

## Deliberately NOT Building (v1)

- A UI or dashboard — everything happens on GitHub natively
- Auto-merge or PR gating based on AI score
- Support for non-GitHub platforms (GitLab, Bitbucket)
- ML model fine-tuning or custom model training
- Natural language chat interface on top of the agent
