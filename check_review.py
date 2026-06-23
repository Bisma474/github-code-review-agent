"""Check review results."""
import asyncio
from app.db.session import get_async_session
from app.db.crud.pull_request import get_pr_by_github_number
from app.db.crud.repository import get_repo_by_full_name
from app.db.crud.review import get_review_by_pr_id
from app.db.crud.comment import get_comments_by_review_id


async def check():
    async with get_async_session() as db:
        repo = await get_repo_by_full_name(db, "Bisma474/github-code-review-agent")
        pr = await get_pr_by_github_number(db, repo.id, 4)
        if not pr:
            print("PR not found")
            return
        print(f"PR status: {pr.status.value}")

        review = await get_review_by_pr_id(db, pr.id)
        if review:
            print(f"Review score: {review.quality_score}")
            print(f"Summary: {(review.summary or '')[:120]}")
            print(f"Model used: {review.model_used}")
            print(f"Duration: {review.duration_seconds}s")
            comments = await get_comments_by_review_id(db, review.id)
            print(f"Total comments: {len(comments)}")
            for c in comments:
                print(f"  [{c.severity.value}] {c.file_path}:{c.line_number} {c.body[:80]}")
        else:
            print("No review found")


asyncio.run(check())
