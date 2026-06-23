from app.core.logging import get_logger
from app.agent.state import ReviewState
from app.agent.llm import llm_invoke

logger = get_logger(__name__)

SUMMARY_PROMPT = """Based on the following code review analysis, provide:
1. A brief PR summary (2-3 sentences)
2. A quality score from 0-100
3. Top 3 concerns

Analysis:
{analysis}

Return a JSON object:
{{
  "summary": "...",
  "quality_score": 85,
  "top_concerns": ["concern 1", "concern 2", "concern 3"]
}}"""


async def generate_summary(state: ReviewState) -> dict:
    logger.info(f"Generating summary for PR #{state['github_pr_number']}")

    analysis_text = ""
    for item in state["llm_analysis"]:
        analysis_text += f"\nFile: {item['file']}\n"
        for c in item.get("comments", []):
            analysis_text += f"  [{c.get('severity','info')}] Line {c.get('line','?')}: {c.get('message','')}\n"

    if not analysis_text.strip():
        return {"summary": "No issues found in this pull request.", "quality_score": 100, "top_concerns": []}

    prompt = SUMMARY_PROMPT.format(analysis=analysis_text[:6000])
    response = await llm_invoke([
        {"role": "system", "content": "You are a code review assistant. Respond only with valid JSON."},
        {"role": "user", "content": prompt},
    ])

    import re
    import json
    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    try:
        result = json.loads(content)
        summary = result.get("summary", "")
        quality_score = result.get("quality_score", 0)
        top_concerns = result.get("top_concerns", [])
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse summary from LLM: {response.content[:200]}")
        summary = analysis_text[:500]
        quality_score = 0
        top_concerns = []

    # Format and post review summary to GitHub
    summary_body = f"## 🤖 AI Code Review Summary\n\n"
    summary_body += f"**Quality Score:** `{quality_score}/100`\n\n"
    summary_body += f"### Summary\n{summary}\n\n"
    if top_concerns:
        summary_body += "### Top Concerns\n"
        for concern in top_concerns:
            summary_body += f"- {concern}\n"

    try:
        from app.github.client import post_pr_comment
        repo_full = f"{state['github_owner']}/{state['github_repo']}"
        post_pr_comment(repo_full, state["github_pr_number"], summary_body)
        logger.info(f"Posted review summary comment to PR #{state['github_pr_number']}")
    except Exception as e:
        logger.warning(f"Failed to post PR summary comment: {e}")

    return {
        "summary": summary,
        "quality_score": quality_score,
        "top_concerns": top_concerns,
    }

