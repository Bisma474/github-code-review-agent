import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

server = Server("github-code-review-agent")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_pr_diff",
            description="Fetch the raw unified diff for a pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "pr_number": {"type": "integer", "description": "Pull request number"},
                },
                "required": ["owner", "repo", "pr_number"],
            },
        ),
        Tool(
            name="get_pr_files",
            description="List all files changed in a pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "pr_number": {"type": "integer", "description": "Pull request number"},
                },
                "required": ["owner", "repo", "pr_number"],
            },
        ),
        Tool(
            name="post_comment",
            description="Post an inline review comment on a specific line of a file in a PR",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "pr_number": {"type": "integer", "description": "Pull request number"},
                    "body": {"type": "string", "description": "Comment body in markdown"},
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "line": {"type": "integer", "description": "Line number in the diff"},
                    "commit_id": {"type": "string", "description": "SHA of the latest commit"},
                },
                "required": ["owner", "repo", "pr_number", "body", "path", "line", "commit_id"],
            },
        ),
        Tool(
            name="post_summary",
            description="Post a PR-level summary comment on the conversation timeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "pr_number": {"type": "integer", "description": "Pull request number"},
                    "body": {"type": "string", "description": "Summary comment body in markdown"},
                },
                "required": ["owner", "repo", "pr_number", "body"],
            },
        ),
        Tool(
            name="store_feedback",
            description="Store user feedback on a review comment or the overall review",
            inputSchema={
                "type": "object",
                "properties": {
                    "review_id": {"type": "string", "description": "UUID of the review record"},
                    "rating": {"type": "integer", "description": "Rating 1-5"},
                    "category": {"type": "string", "description": "Feedback category"},
                    "notes": {"type": "string", "description": "Free-text notes"},
                    "comment_id": {"type": "string", "description": "UUID of the specific comment"},
                },
                "required": ["review_id", "rating"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    from app.mcp.tools import get_pr_diff, get_pr_files, post_comment, post_summary, store_feedback

    try:
        if name == "get_pr_diff":
            result = get_pr_diff(
                owner=arguments["owner"],
                repo=arguments["repo"],
                pr_number=arguments["pr_number"],
            )

        elif name == "get_pr_files":
            result = get_pr_files(
                owner=arguments["owner"],
                repo=arguments["repo"],
                pr_number=arguments["pr_number"],
            )

        elif name == "post_comment":
            result = post_comment(
                owner=arguments["owner"],
                repo=arguments["repo"],
                pr_number=arguments["pr_number"],
                body=arguments["body"],
                path=arguments["path"],
                line=arguments["line"],
                commit_id=arguments["commit_id"],
            )

        elif name == "post_summary":
            result = post_summary(
                owner=arguments["owner"],
                repo=arguments["repo"],
                pr_number=arguments["pr_number"],
                body=arguments["body"],
            )

        elif name == "store_feedback":
            result = await store_feedback(
                review_id=arguments["review_id"],
                rating=arguments["rating"],
                comment_id=arguments.get("comment_id"),
                category=arguments.get("category"),
                notes=arguments.get("notes"),
            )

        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.error(f"MCP tool '{name}' failed: {e}")
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result))]


async def run_server() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server())
