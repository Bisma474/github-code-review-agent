"""E2E dry-run — supports Groq, Anthropic, or Ollama as the LLM provider.

Exercises the complete pipeline end-to-end with a real LLM call:
  webhook payload -> DB -> LangGraph (all 6 nodes) -> Review record -> actual LLM review

Usage (pick any one):
  set GROQ_API_KEY=gsk_...        && .venv/Scripts/python tests/e2e_dryrun.py
  set ANTHROPIC_API_KEY=sk-ant-...&& .venv/Scripts/python tests/e2e_dryrun.py
  (Ollama running locally)           .venv/Scripts/python tests/e2e_dryrun.py
"""

import asyncio
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Load .env from project root so secrets (GROQ_API_KEY etc.) are available
# even when the script is run directly without pre-exporting env vars.
# ---------------------------------------------------------------------------
_dotenv_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    for _line in _dotenv_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _v = _v.strip().strip('"').strip("'")  # strip surrounding quotes
            os.environ.setdefault(_k.strip(), _v)

os.environ.setdefault("GITHUB_TOKEN", "ghp_e2e_test")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "e2e_secret")
os.environ.setdefault("APP_SECRET_KEY", "e2e_app_key")
os.environ.setdefault("CELERY_ALWAYS_EAGER", "true")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./.e2e_dryrun.db"

# Auto-detect which LLM provider is available
groq_key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROK_API_KEY")
anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

if groq_key:
    os.environ["LLM_PROVIDER"] = "groq"
    os.environ["GROQ_API_KEY"] = groq_key
    os.environ.setdefault("GROQ_MODEL", "llama-3.3-70b-versatile")
    print(f"[LLM] Using Groq ({os.environ['GROQ_MODEL']})")
elif anthropic_key:
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    os.environ.setdefault("ANTHROPIC_MODEL", "claude-haiku-3-5")
    print(f"[LLM] Using Anthropic ({os.environ['ANTHROPIC_MODEL']})")
else:
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ.setdefault("OLLAMA_MODEL", "deepseek-coder")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"[LLM] No API key found — using Ollama ({os.environ['OLLAMA_MODEL']} @ {os.environ['OLLAMA_BASE_URL']})")
    print("      Make sure Ollama is running: ollama serve")


async def main():
    db = pathlib.Path(".e2e_dryrun.db")
    db.unlink(missing_ok=True)

    from app.db.session import create_tables, get_async_session
    await create_tables()
    print("[1/5] DB tables created")

    # Seed repo + PR
    from app.db.crud.repository import create_repo
    from app.db.crud.pull_request import create_pr
    from app.db.models.enums import PullRequestStatus

    async with get_async_session() as session:
        repo = await create_repo(session, github_repo_id=9001, owner="e2e", name="testrepo", full_name="e2e/testrepo", webhook_secret="e2e_wh")
        pr = await create_pr(session, repository_id=repo.id, github_pr_id=101, github_pr_number=42, title="E2E test PR", author="e2e-bot", base_branch="main", head_branch="feature/e2e", github_pr_url="https://github.com/e2e/testrepo/pull/42", status=PullRequestStatus.PENDING)
        pr_id = str(pr.id)
        print(f"[2/5] PR #42 created (id={pr_id})")

    # Build state
    state = {
        "pull_request_id": pr_id,
        "repository_id": str(repo.id),
        "github_owner": "e2e",
        "github_repo": "testrepo",
        "github_pr_number": 42,
        "diff_raw": """diff --git a/src/main.py b/src/main.py
index abc..def 100644
--- a/src/main.py
+++ b/src/main.py
@@ -8,7 +8,9 @@ def process(data):
     if not data:
         return None
-    result = do_work(data)
+    result = do_work(data, timeout=30)
     log.info("done")
+    if result is None:
+        raise RuntimeError("failed")
     return result
""",
        "latest_commit_sha": "",
        "parsed_files": [],
        "llm_analysis": [],
        "formatted_comments": [],
        "posted_comment_ids": [],
        "summary": "",
        "quality_score": 0,
        "top_concerns": [],
        "errors": [],
    }

    # Mock GitHub functions to avoid real API calls
    from unittest.mock import patch, MagicMock

    sample_diff = """diff --git a/src/main.py b/src/main.py
index abc..def 100644
--- a/src/main.py
+++ b/src/main.py
@@ -8,7 +8,9 @@ def process(data):
     if not data:
         return None
-    result = do_work(data)
+    result = do_work(data, timeout=30)
     log.info("done")
+    if result is None:
+        raise RuntimeError("failed")
     return result
"""
    def _fake_post_comment(*a, **kw):
        return 777

    with patch("app.github.client.get_pr_diff", return_value=sample_diff), \
         patch("app.github.client.get_pr_head_sha", return_value="abc123commitsha"), \
         patch("app.github.client.get_pr_files", return_value=[{"filename": "src/main.py", "status": "modified", "additions": 3, "deletions": 1}]), \
         patch("app.github.client.post_review_comment", side_effect=_fake_post_comment), \
         patch("app.github.client.post_pr_comment", return_value=888):

        print("[3/5] Running LangGraph pipeline with REAL Groq LLM...")
        from app.agent.graph import build_review_graph
        graph = build_review_graph()
        result = await graph.ainvoke(state)

    print(f"[4/5] Pipeline complete")
    pf = result.get("parsed_files", [])
    la = result.get("llm_analysis", [])
    fc = result.get("formatted_comments", [])
    pc = result.get("posted_comment_ids", [])
    qs = result.get("quality_score", 0)
    summary = result.get("summary", "")
    concerns = result.get("top_concerns", [])
    errs = result.get("errors", [])

    print(f"  parsed_files:       {len(pf)} files")
    print(f"  llm_analysis:       {len(la)} files")
    print(f"  formatted_comments: {len(fc)} comments")
    print(f"  posted_comment_ids: {pc}")
    print(f"  quality_score:      {qs}")
    print(f"  summary:            {summary[:120] if summary else '(empty)'}")
    print(f"  top_concerns:       {concerns}")
    if errs:
        print(f"  errors:             {errs}")

    print("[5/5] Verifying DB records...")
    from app.db.crud.review import get_review_by_pr_id
    from app.db.crud.comment import get_comments_by_review_id

    async with get_async_session() as session:
        review = await get_review_by_pr_id(session, pr.id)
        if review:
            print(f"  Review score: {review.quality_score}")
            comments = await get_comments_by_review_id(session, review.id)
            print(f"  Comments in DB: {len(comments)}")

    passed = (
        len(pf) > 0 and
        len(fc) > 0 and
        qs > 0 and
        bool(summary)
    )

    print(f"\n{'='*40}")
    print(f"E2E DRY RUN: {'PASSED' if passed else 'FAILED'}")
    print(f"{'='*40}")

    from app.db.session import engine as _engine
    if _engine:
        await _engine.dispose()
    import gc; gc.collect()
    try:
        db.unlink(missing_ok=True)
    except PermissionError:
        pass
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
