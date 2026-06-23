"""Tests for Celery task."""

from unittest.mock import patch, AsyncMock


class TestReviewTask:
    def test_task_module_imports(self):
        from app.tasks.review import review_pr
        from app.celery_app import app

        assert review_pr.name == "review.review_pr"
        assert review_pr.queue == "review"
        assert app.conf.task_always_eager is True

    def test_task_routes(self):
        from app.celery_app import app

        assert "review.*" in app.conf.task_routes
        assert app.conf.task_routes["review.*"]["queue"] == "review"
