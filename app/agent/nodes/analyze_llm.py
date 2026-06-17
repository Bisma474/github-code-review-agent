from app.core.logging import get_logger
from app.agent.state import ReviewState
from app.agent.llm import llm_invoke

logger = get_logger(__name__)

REVIEW_PROMPT = """You are an expert code reviewer. Review the following code changes and identify bugs, security issues, performance problems, and style violations.

For each issue, provide:
- severity: "critical", "warning", or "nitpick"
- line: the line number (or null if not applicable)
- message: a clear, actionable description of the issue
- suggestion: how to fix it (if applicable)

Return your analysis as a JSON array. Example:
[
  {{
    "severity": "critical",
    "line": 42,
    "message": "SQL injection vulnerability: user input is concatenated into query string.",
    "suggestion": "Use parameterized queries instead of string interpolation."
  }}
]

If no issues are found, return an empty array [].

File: {file_path}
```diff
{diff}
```"""


async def analyze_file(file_path: str, diff: str) -> list[dict]:
    prompt = REVIEW_PROMPT.format(file_path=file_path, diff=diff[:8000])
    response = await llm_invoke([
        {"role": "system", "content": "You are a code review assistant. Respond only with valid JSON."},
        {"role": "user", "content": prompt},
    ])

    import json
    try:
        analysis = json.loads(response.content)
        return analysis if isinstance(analysis, list) else []
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM response for {file_path}: {response.content[:200]}")
        return []


async def analyze_with_llm(state: ReviewState) -> dict:
    logger.info(f"Analyzing {len(state['parsed_files'])} files with LLM")
    results = []
    for file in state["parsed_files"]:
        if not file.get("patch"):
            continue
        analysis = await analyze_file(file["path"], file["patch"])
        results.append({"file": file["path"], "comments": analysis})
    return {"llm_analysis": results}
