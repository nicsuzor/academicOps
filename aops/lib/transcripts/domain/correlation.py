import re

from transcripts.model import NormalizedSession


def infer_correlations(session: NormalizedSession) -> dict[str, list[str]]:
    """Infer related PRs, tasks, and projects from the session content and metadata."""
    prs: set[str] = set()
    tasks: set[str] = set()
    projects: set[str] = set()

    # Search in session source_file path
    file_str = str(session.source_file)
    for match in re.finditer(
        r"(?:epic|aops)_[a-f0-9]{8}|task-[a-f0-9]{8}", file_str, re.IGNORECASE
    ):
        tasks.add(match.group(0).lower())

    # Search in all events content
    for event in session.events:
        content = event.content
        # Find PR numbers: "PR #123", "pull/123", "PR 123"
        for match in re.finditer(r"(?:PR\s*#?\s*|pull/|pulls/)(\d+)", content, re.IGNORECASE):
            prs.add(match.group(1))

        # Find tasks: "epic_1234abcd", "aops_1234abcd", "task-1234abcd"
        for match in re.finditer(
            r"((?:epic|aops)_[a-f0-9]{8}|task-[a-f0-9]{8})", content, re.IGNORECASE
        ):
            tasks.add(match.group(1).lower())

        # Find project from task labels if present in meta
        if "project" in event.meta:
            projects.add(str(event.meta["project"]))

    # Default project from source file path if possible
    # e.g., if /home/worker/.gemini/antigravity-cli/plugins/aops
    for part in session.source_file.parts:
        if part in {"aops", "academicOps", "aops-tools"}:
            projects.add("aops")

    return {
        "prs": sorted(list(prs)),
        "tasks": sorted(list(tasks)),
        "projects": sorted(list(projects)),
    }
