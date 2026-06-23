"""Full E2E test: webhook -> Celery -> LangGraph -> review in DB."""
import asyncio, json, hmac, hashlib, sys
from httpx import AsyncClient, ASGITransport
from app.main import create_app

PR_NUMBER = 5

app = create_app()
transport = ASGITransport(app=app)
secret = "ITz0SZYONFDcJn54oPBp83jkbr6UvxR9h2GXu7AV"

payload = json.dumps({
    "action": "opened",
    "pull_request": {
        "number": PR_NUMBER, "id": 999005, "title": "Full E2E Test",
        "html_url": f"https://github.com/Bisma474/github-code-review-agent/pull/{PR_NUMBER}",
        "user": {"login": "test-user"},
        "base": {"ref": "main"}, "head": {"ref": "feature/test"},
    },
    "repository": {"full_name": "Bisma474/github-code-review-agent", "id": 828882517},
}).encode()
sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def check_db():
    from app.db.session import get_async_session
    from app.db.crud.pull_request import get_pr_by_github_number
    from app.db.crud.repository import get_repo_by_full_name
    from app.db.crud.review import get_review_by_pr_id
    from app.db.crud.comment import get_comments_by_review_id

    async with get_async_session() as db:
        repo = await get_repo_by_full_name(db, "Bisma474/github-code-review-agent")
        pr = await get_pr_by_github_number(db, repo.id, PR_NUMBER)
        if not pr:
            return None
        result = {"status": pr.status.value, "review": None, "comments": []}
        review = await get_review_by_pr_id(db, pr.id)
        if review:
            result["review"] = {
                "score": review.quality_score,
                "summary": (review.summary or "")[:120],
                "model": review.model_used,
                "duration": review.duration_seconds,
            }
            comments = await get_comments_by_review_id(db, review.id)
            result["comments"] = [
                {"severity": c.severity.value, "file": c.file_path, "line": c.line_number, "body": c.body[:80]}
                for c in comments
            ]
        return result


async def main():
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/webhook/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        print(f"1. Webhook: {r.status_code} {r.json()}")

    # Poll for review completion (up to 120s)
    for _ in range(120):
        await asyncio.sleep(1)
        result = await check_db()
        if result and result["status"] in ("COMPLETED", "FAILED"):
            break
    else:
        print("2. TIMEOUT: Review not completed after 120s")
        sys.exit(1)

    print(f"2. PR status: {result['status']}")
    if rev := result["review"]:
        print(f"3. Review: score={rev['score']}, summary={rev['summary']}")
        print(f"   Model={rev['model']}, Duration={rev['duration']}s")
        print(f"4. Comments in DB: {len(result['comments'])}")
        for c in result["comments"]:
            print(f"   [{c['severity']}] {c['file']}:{c['line']} {c['body']}")

    verdict = "FAILED"
    if result["status"] == "COMPLETED" and result["review"] and len(result["comments"]) > 0:
        verdict = "PASSED"
    elif result["status"] == "COMPLETED" and result["review"]:
        verdict = "PARTIAL (no comments)"

    print(f"\n=== VERDICT: {verdict} ===")
    sys.exit(0 if verdict == "PASSED" else 1)


asyncio.run(main())
