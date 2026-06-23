"""Integration tests for FastAPI endpoints."""

import hashlib
import hmac
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport


class TestHealth:
    async def test_health_returns_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        assert "version" in data


class TestWebhook:
    async def test_missing_signature_returns_401(self, client):
        r = await client.post(
            "/webhook/github",
            content=b'{"action":"opened"}',
        )
        assert r.status_code == 401

    async def test_invalid_signature_returns_401(self, client):
        r = await client.post(
            "/webhook/github",
            content=b'{"action":"opened"}',
            headers={"X-Hub-Signature-256": "sha256=invalid"},
        )
        assert r.status_code == 401

    async def test_valid_signature_with_unknown_action_ignored(self, client):
        payload = b'{"action":"synchronize","pull_request":{"number":1},"repository":{"full_name":"x/y"}}'
        sig = "sha256=" + hmac.new(b"test_secret", payload, hashlib.sha256).hexdigest()
        r = await client.post(
            "/webhook/github",
            content=payload,
            headers={"X-Hub-Signature-256": sig},
        )
        assert r.status_code in (200, 202)
        data = r.json()
        assert data["status"] == "ignored"

    async def test_valid_signature_opened_with_unknown_repo(self, client, db_session):
        payload = (
            b'{"action":"opened","pull_request":{"id":100,"number":2,"html_url":"u",'
            b'"title":"T","user":{"login":"dev"},"base":{"ref":"main"},'
            b'"head":{"ref":"feat"}},"repository":{"id":9999,"full_name":"unknown/repo","owner":{"login":"unknown"},"name":"repo"}}'
        )
        sig = "sha256=" + hmac.new(b"test_secret", payload, hashlib.sha256).hexdigest()
        r = await client.post(
            "/webhook/github",
            content=payload,
            headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": "pull_request"},
        )
        assert r.status_code in (200, 202)
        data = r.json()
        assert data["status"] == "queued"
        assert data["pr_number"] == 2

    async def test_webhook_synchronize_existing_pr(self, client, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.models.enums import PullRequestStatus

        repo = await create_repo(
            db_session, github_repo_id=12345, owner="o", name="r",
            full_name="o/r-sync", webhook_secret="test_secret",
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=1010,
            github_pr_number=50, title="Old Title", author="a",
            base_branch="main", head_branch="feat", github_pr_url="http://url",
            status=PullRequestStatus.COMPLETED,
        )

        payload = (
            b'{"action":"synchronize","pull_request":{"number":50,"html_url":"http://url",'
            b'"title":"New Title","user":{"login":"a"},"base":{"ref":"main"},'
            b'"head":{"ref":"feat"}},"repository":{"id":12345,"full_name":"o/r-sync","owner":{"login":"o"},"name":"r"}}'
        )
        sig = "sha256=" + hmac.new(b"test_secret", payload, hashlib.sha256).hexdigest()

        with patch("app.tasks.review.review_pr.delay") as mock_delay:
            r = await client.post(
                "/webhook/github",
                content=payload,
                headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": "pull_request"},
            )
            assert r.status_code in (200, 202)
            data = r.json()
            assert data["status"] == "queued"
            assert data["pr_number"] == 50
            mock_delay.assert_called_once()

        # Store repo ID before expiring session to avoid lazy loading trigger
        repo_id = repo.id

        # Expire session to load fresh update from the database
        db_session.expire_all()

        # Check DB to verify PR was updated instead of duplicated
        from app.db.crud.pull_request import get_pr_by_github_number
        updated_pr = await get_pr_by_github_number(db_session, repo_id, 50)
        assert updated_pr.title == "New Title"
        assert updated_pr.status == PullRequestStatus.PENDING





class TestFeedback:
    async def test_submit_feedback_invalid_rating(self, client):
        r = await client.post(
            "/feedback",
            json={"review_id": "00000000-0000-0000-0000-000000000000", "rating": 0},
        )
        assert r.status_code == 422

    async def test_submit_and_get_feedback(self, client, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review

        repo = await create_repo(
            db_session, github_repo_id=30, owner="o", name="r",
            full_name="o/r-fb", webhook_secret=__import__('uuid').uuid4().hex[:12],
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=40,
            github_pr_number=70, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)

        r = await client.post(
            "/feedback",
            json={
                "review_id": str(review.id),
                "rating": 5,
                "category": "accurate",
                "notes": "Excellent review",
            },
        )
        assert r.status_code == 200
        fb_id = r.json()["id"]

        r2 = await client.get(f"/feedback/{review.id}")
        assert r2.status_code == 200
        data = r2.json()
        assert len(data) == 1
        assert data[0]["id"] == fb_id
        assert data[0]["rating"] == 5
