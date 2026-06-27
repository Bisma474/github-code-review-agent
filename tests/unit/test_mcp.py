"""Tests for MCP tools."""

from unittest.mock import AsyncMock, patch

import pytest


class TestMCPTools:
    """MCP tool functions are sync (return dict, not coroutine)."""

    @patch("app.github.client._httpx_get")
    def test_get_pr_diff(self, mock_httpx_get, mock_github):
        mock_httpx_get.return_value.status_code = 200
        mock_httpx_get.return_value.text = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        from app.mcp.tools.get_pr_diff import get_pr_diff

        result = get_pr_diff("owner", "repo", 1)
        assert result["success"] is True
        assert result["diff"] == "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"

    def test_get_pr_files(self, mock_github):
        from app.mcp.tools.get_pr_files import get_pr_files

        result = get_pr_files("owner", "repo", 1)
        assert result["success"] is True

    def test_post_comment(self, mock_github):
        from app.mcp.tools.post_comment import post_comment

        result = post_comment("owner", "repo", 1, "body", "path", 1, "abc")
        assert result["success"] is True
        assert result["comment_id"] == 123

    def test_post_summary(self, mock_github):
        from app.mcp.tools.post_summary import post_summary

        result = post_summary("owner", "repo", 1, "summary body")
        assert result["success"] is True
        assert result["comment_id"] == 456

    async def test_store_feedback(self, db_session):
        from app.db.crud.repository import create_repo
        from app.db.crud.pull_request import create_pr
        from app.db.crud.review import create_review
        from app.mcp.tools.store_feedback import store_feedback

        repo = await create_repo(
            db_session, github_repo_id=20, owner="o", name="r",
            full_name="o/r-mcp", webhook_secret=__import__('uuid').uuid4().hex[:12],
        )
        pr = await create_pr(
            db_session, repository_id=repo.id, github_pr_id=30,
            github_pr_number=60, title="T", author="a",
            base_branch="m", head_branch="f", github_pr_url="u",
        )
        review = await create_review(db_session, pull_request_id=pr.id)

        result = await store_feedback(
            review_id=str(review.id), rating=4,
            category="accurate", notes="good",
        )
        assert result["success"] is True
        assert "feedback_id" in result
