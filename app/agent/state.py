import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    pull_request_id: str
    repository_id: str
    github_owner: str
    github_repo: str
    github_pr_number: int
    diff_raw: str
    parsed_files: Annotated[list, operator.add]
    llm_analysis: Annotated[list, operator.add]
    formatted_comments: Annotated[list, operator.add]
    posted_comment_ids: Annotated[list, operator.add]
    summary: str
    quality_score: int
    top_concerns: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]
