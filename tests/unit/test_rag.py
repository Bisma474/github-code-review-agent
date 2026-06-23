"""Tests for ChromaDB pattern repository."""

import uuid

import pytest

from app.rag.repository import PatternRepository


class TestPatternRepository:
    """PatternRepository creates a default collection if none given."""

    def test_init_without_collection(self):
        repo = PatternRepository()
        assert repo.collection is not None

    def test_add_and_search(self, mock_chroma):
        repo = PatternRepository(mock_chroma)
        pid = repo.add_pattern(
            pattern_id=str(uuid.uuid4()),
            code_snippet="def foo(): pass",
            issue_type="style",
            severity="nitpick",
            message="Use snake_case",
            suggestion="rename",
            repo_full_name="test/repo",
            file_path="src/main.py",
        )
        assert pid is not None
        mock_chroma.add.assert_called_once()

    def test_search_similar(self, mock_chroma):
        repo = PatternRepository(mock_chroma)
        results = repo.search_similar("def foo", n_results=5)
        assert len(results) >= 1
        assert results[0]["distance"] == 0.15
        mock_chroma.query.assert_called_once()

    def test_count(self, mock_chroma):
        repo = PatternRepository(mock_chroma)
        assert repo.count() == 3

    def test_delete_pattern(self, mock_chroma):
        repo = PatternRepository(mock_chroma)
        repo.delete_pattern("pat1")
        mock_chroma.delete.assert_called_once_with(ids=["pat1"])
