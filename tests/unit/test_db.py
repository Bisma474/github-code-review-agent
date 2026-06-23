"""Tests for DB models and CRUD operations."""

from uuid import uuid4

import pytest
from sqlalchemy import text


def _secret():
    return uuid4().hex[:12]


class TestModels:
    """Verify all 5 models can be created and have correct table names."""

    async def test_tables_exist(self, db_session):
        result = await db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        )
        tables = [r[0] for r in result]
        assert tables == [
            "feedback",
            "pull_requests",
            "repositories",
            "review_comments",
            "reviews",
        ]

    async def test_create_repository(self, db_session):
        from app.db.crud.repository import create_repo

        repo = await create_repo(
            db_session,
            github_repo_id=1,
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            webhook_secret=_secret(),
        )
        assert repo.id is not None
        assert repo.full_name == "test-owner/test-repo"
        assert repo.is_active is True

    async def test_create_pull_request(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr

        repo = await create_repo(
            db_session, github_repo_id=2, owner="o", name="r",
            full_name="o/r", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=10,
            github_pr_number=42, title="Fix bug", author="dev",
            base_branch="main", head_branch="fix", github_pr_url="http://",
        )
        assert pr.github_pr_number == 42
        assert pr.status.value == "pending"

    async def test_create_review(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review

        repo = await create_repo(
            db_session, github_repo_id=3, owner="o", name="r",
            full_name="o/r2", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=11,
            github_pr_number=43, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)
        assert review.id is not None
        assert review.pull_request_id == pr.id

    async def test_create_comment(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review
        from app.db.crud.comment import create_comment

        repo = await create_repo(
            db_session, github_repo_id=4, owner="o", name="r",
            full_name="o/r3", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=12,
            github_pr_number=44, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)
        comment = await create_comment(
            db_session, review_id=review.id, file_path="src/main.py",
            line_number=10, category="bug", severity="blocking",
            body="This is a bug", suggestion="Fix it",
        )
        assert comment.file_path == "src/main.py"
        assert comment.category.value == "bug"

    async def test_create_feedback(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review
        from app.db.crud.feedback import create_feedback

        repo = await create_repo(
            db_session, github_repo_id=5, owner="o", name="r",
            full_name="o/r4", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=13,
            github_pr_number=45, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)
        fb = await create_feedback(
            db_session, review_id=review.id, rating=5,
            category="accurate", notes="Great review",
        )
        assert fb.rating == 5
        assert fb.notes == "Great review"


class TestCRUD:
    """Test CRUD read / update operations."""

    async def test_get_repo_by_full_name(self, db_session):
        from app.db.crud.repository import create_repo, get_repo_by_full_name

        await create_repo(
            db_session, github_repo_id=6, owner="find", name="me",
            full_name="find/me", webhook_secret=_secret(),
        )
        found = await get_repo_by_full_name(db_session, "find/me")
        assert found is not None
        assert found.github_repo_id == 6

        missing = await get_repo_by_full_name(db_session, "not/found")
        assert missing is None

    async def test_get_active_repos(self, db_session):
        from app.db.crud.repository import create_repo, get_active_repos, set_repo_active_status

        r1 = await create_repo(
            db_session, github_repo_id=7, owner="a", name="b",
            full_name="a/b", webhook_secret=_secret(),
        )
        r2 = await create_repo(
            db_session, github_repo_id=8, owner="c", name="d",
            full_name="c/d", webhook_secret=_secret(),
        )
        await set_repo_active_status(db_session, r2.id, False)

        active = await get_active_repos(db_session)
        ids = [r.id for r in active]
        assert r1.id in ids
        assert r2.id not in ids

    async def test_update_pr_status(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr, update_pr_status, get_pr_by_id

        repo = await create_repo(
            db_session, github_repo_id=9, owner="o", name="r",
            full_name="o/r5", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=14,
            github_pr_number=46, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        updated = await update_pr_status(db_session, pr.id, "completed")
        assert str(updated.status) == "completed"

        fetched = await get_pr_by_id(db_session, pr.id)
        assert str(fetched.status) == "completed"

    async def test_update_review(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review, update_review

        repo = await create_repo(
            db_session, github_repo_id=10, owner="o", name="r",
            full_name="o/r6", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=15,
            github_pr_number=47, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)
        updated = await update_review(
            db_session, review.id,
            {"quality_score": 85, "summary": "Great PR"},
        )
        assert updated.quality_score == 85
        assert updated.summary == "Great PR"

    async def test_get_comments_by_review_id(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review
        from app.db.crud.comment import create_comment, get_comments_by_review_id

        repo = await create_repo(
            db_session, github_repo_id=11, owner="o", name="r",
            full_name="o/r7", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=16,
            github_pr_number=48, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)
        await create_comment(
            db_session, review_id=review.id, file_path="a.py",
            line_number=1, category="style", severity="warning", body="lint",
        )
        await create_comment(
            db_session, review_id=review.id, file_path="b.py",
            line_number=5, category="bug", severity="blocking", body="crash",
        )

        comments = await get_comments_by_review_id(db_session, review.id)
        assert len(comments) == 2

    async def test_get_feedback_by_review_id(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review
        from app.db.crud.feedback import create_feedback, get_feedback_by_review_id

        repo = await create_repo(
            db_session, github_repo_id=12, owner="o", name="r",
            full_name="o/r8", webhook_secret=_secret(),
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=17,
            github_pr_number=49, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)
        await create_feedback(db_session, review_id=review.id, rating=3)
        await create_feedback(db_session, review_id=review.id, rating=4)

        feedbacks = await get_feedback_by_review_id(db_session, review.id)
        assert len(feedbacks) == 2
