from app.core.logging import get_logger
from app.agent.state import ReviewState
from app.agent.llm import llm_invoke
from app.rag.retrieve import retrieve_similar_patterns

logger = get_logger(__name__)

RAG_REVIEW_PROMPT = """You are an expert code reviewer. Review the following code changes.

SIMILAR PAST ISSUES (for reference):
{context}

For each issue provide:
- severity: "critical", "warning", or "nitpick"
- line: the line number (or null)
- message: clear actionable description
- suggestion: how to fix it

Return a JSON array. Example:
[{{"severity":"critical","line":42,"message":"...","suggestion":"..."}}]

File: {file_path}
```diff
{diff}
```"""


async def analyze_with_rag(state: ReviewState) -> dict:
    logger.info(f"RAG analysis for {len(state['parsed_files'])} files")
    results = []
    for file in state["parsed_files"]:
        if not file.get("patch"):
            continue

        similar = retrieve_similar_patterns(file["patch"], n_results=3)
        context = ""
        for s in similar:
            context += f"- [{s['metadata'].get('severity','?')}] {s['document'][:200]}\n"

        prompt = RAG_REVIEW_PROMPT.format(file_path=file["path"], diff=file["patch"][:8000], context=context or "No similar past issues found.")
        response = await llm_invoke([
            {"role": "system", "content": "You are a code review assistant. Respond only with valid JSON."},
            {"role": "user", "content": prompt},
        ])

        import json
        try:
            analysis = json.loads(response.content)
            results.append({"file": file["path"], "comments": analysis if isinstance(analysis, list) else []})
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response for {file['path']}")
            results.append({"file": file["path"], "comments": []})

    return {"llm_analysis": results}
