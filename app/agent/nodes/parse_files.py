import re
from app.core.logging import get_logger
from app.agent.state import ReviewState

logger = get_logger(__name__)


def parse_diff(diff_raw: str) -> list[dict]:
    if not diff_raw:
        return []

    files = []
    current_file = None
    current_patch = []

    for line in diff_raw.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                current_file["patch"] = "\n".join(current_patch)
                files.append(current_file)
            current_file = {"path": line.split()[2].removeprefix("a/").removeprefix("b/"), "additions": 0, "deletions": 0, "patch": ""}
            current_patch = []
        elif line.startswith("+++"):
            if current_file and line.removeprefix("+++ ").strip():
                current_file["path"] = line.split("+++ ")[-1].removeprefix("b/").strip()
            continue
        elif line.startswith("---"):
            continue
        elif current_file:
            if line.startswith("@@"):
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if match:
                    current_file["new_start_line"] = int(match.group(1))
            elif line.startswith("+") and line != "+++":
                current_file["additions"] += 1
            elif line.startswith("-") and line != "---":
                current_file["deletions"] += 1
            current_patch.append(line)

    if current_file:
        current_file["patch"] = "\n".join(current_patch)
        files.append(current_file)

    return files


async def parse_changed_files(state: ReviewState) -> dict:
    logger.info(f"Parsing diff for {state['github_owner']}/{state['github_repo']}#{state['github_pr_number']}")
    files = parse_diff(state["diff_raw"])
    logger.info(f"Found {len(files)} changed files")
    return {"parsed_files": files}
