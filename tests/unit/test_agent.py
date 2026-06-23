"""Tests for agent nodes — parse_diff, format_comments, LLM clients."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agent.nodes.parse_files import parse_diff
from app.agent.nodes.format_comments import format_comments
from app.agent.llm import GrokClient, LLMResponse


class TestGrokClient:
    @pytest.mark.asyncio
    async def test_invoke_success(self):
        from unittest.mock import MagicMock
        from app.agent.llm import GrokClient

        client = GrokClient("test-model", "fake-key", "http://localhost:1", 4096)
        with patch("app.agent.llm.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "Hello from Grok"}}],
                "model": "test-model",
                "usage": {"total_tokens": 15},
            }
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            MockClient.return_value.__aenter__.return_value = mock_client

            result = await client.invoke([{"role": "user", "content": "hi"}])
            assert isinstance(result, LLMResponse)
            assert result.content == "Hello from Grok"
            assert result.model == "test-model"
            assert result.tokens_used == 15


SAMPLE_DIFF = """diff --git a/src/main.py b/src/main.py
index abc..def 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,7 @@
 def hello():
-    print("world")
+    print("world!")
+    print("new line")
+    return True

diff --git a/src/utils.py b/src/utils.py
new file mode 100644
index 000..111
--- /dev/null
+++ b/src/utils.py
@@ -0,0 +1,3 @@
+def util():
+    pass
"""


class TestParseDiff:
    def test_parse_standard_diff(self):
        files = parse_diff(SAMPLE_DIFF)
        assert len(files) == 2

    def test_parse_modified_file(self):
        files = parse_diff(SAMPLE_DIFF)
        main = [f for f in files if f["path"] == "src/main.py"][0]
        assert main["additions"] == 3
        assert main["deletions"] == 1
        assert "patch" in main

    def test_parse_new_file(self):
        files = parse_diff(SAMPLE_DIFF)
        utils = [f for f in files if f["path"] == "src/utils.py"][0]
        # New file with 2 + lines (no trailing newline in sample)
        assert utils["additions"] == 2
        assert utils["deletions"] == 0

    def test_empty_diff(self):
        assert parse_diff("") == []

    def test_diff_with_no_changes(self):
        diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -0,0 +0,0 @@\n"
        files = parse_diff(diff)
        assert len(files) == 1

    def test_multi_hunk_file(self):
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,3 +1,4 @@
 a
-b
+c
@@ -10,5 +10,6 @@
 d
-e
+f
+g
"""
        files = parse_diff(diff)
        assert len(files) == 1
        assert files[0]["additions"] == 3
        assert files[0]["deletions"] == 2


class TestFormatComments:
    def test_formats_comment_with_severity(self):
        state = {
            "llm_analysis": [
                {
                    "file": "app/main.py",
                    "comments": [
                        {"severity": "critical", "line": 10, "message": "Security issue"},
                        {"severity": "suggestion", "line": 20, "message": "Consider refactoring"},
                    ],
                }
            ]
        }
        result = format_comments(state)
        comments = result["formatted_comments"]
        assert len(comments) == 2
        assert comments[0]["body"].startswith("[CRITICAL]")
        assert comments[1]["body"].startswith("[SUGGESTION]")

    def test_empty_analysis(self):
        result = format_comments({"llm_analysis": []})
        assert result["formatted_comments"] == []

    def test_preserves_metadata(self):
        state = {
            "llm_analysis": [
                {
                    "file": "x.py",
                    "comments": [
                        {"severity": "warning", "line": 5, "message": "style issue"},
                    ],
                }
            ]
        }
        result = format_comments(state)
        c = result["formatted_comments"][0]
        assert c["path"] == "x.py"
        assert c["line"] == 5
        assert c["severity"] == "warning"
