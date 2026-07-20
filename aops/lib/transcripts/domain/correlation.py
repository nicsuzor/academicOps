"""Correlation inference (PR/task/project inference from session contents)."""

from __future__ import annotations

import re

from transcripts.model import NormalizedSession


def infer_correlation(session: NormalizedSession) -> dict[str, str | None]:
    """Infer project, task_id, and pr_number from session events and metadata."""
    task_id = None
    pr_number = None
    project = None

    # Patterns matching PKB task/epic identifiers
    task_patterns = [
        re.compile(r"\b(task-[a-f0-9]{8})\b", re.IGNORECASE),
        re.compile(r"\b(task_[a-f0-9]{8})\b", re.IGNORECASE),
        re.compile(r"\b(epic_[a-f0-9]{8})\b", re.IGNORECASE),
        re.compile(r"\b(aops_[a-f0-9]{8})\b", re.IGNORECASE),
    ]

    # Patterns matching GitHub Pull Request indicators
    pr_patterns = [
        re.compile(r"\b(?:PR|pull\s+request)\s+#?(\d+)\b", re.IGNORECASE),
        re.compile(r"github\.com/[^/]+/[^/]+/pull/(\d+)\b", re.IGNORECASE),
    ]

    # 1. Check session_id itself for task ID
    for pattern in task_patterns:
        match = pattern.search(session.session_id)
        if match:
            task_id = match.group(1).lower()
            break

    # 2. Check events content and metadata
    for event in session.events:
        content = event.content or ""
        if not isinstance(content, str):
            content = str(content)

        # Search for task_id if not found yet
        if not task_id:
            for pattern in task_patterns:
                match = pattern.search(content)
                if match:
                    task_id = match.group(1).lower()
                    break

        # Search for PR number if not found yet
        if not pr_number:
            for pattern in pr_patterns:
                match = pattern.search(content)
                if match:
                    pr_number = match.group(1)
                    break

        # Check git branch in metadata if present
        meta = event.meta or {}
        git_branch = meta.get("gitBranch") or meta.get("attachment", {}).get("gitBranch", "")
        if git_branch and not pr_number:
            branch_match = re.search(r"\b(?:pr|issue)-?(\d+)\b", git_branch, re.IGNORECASE)
            if branch_match:
                pr_number = branch_match.group(1)

    # 3. Infer project
    paths_to_check = [str(session.source_file)]
    for event in session.events:
        meta = event.meta or {}
        if meta.get("cwd"):
            paths_to_check.append(meta.get("cwd"))

    for p in paths_to_check:
        if "aops-tools" in p:
            project = "aops-tools"
            break
        elif "aops-jr" in p:
            project = "aops-jr"
            break
        elif "aops-ts" in p:
            project = "aops-ts"
            break
        elif "aops" in p or "academicOps" in p:
            project = "aops"
            break

    return {
        "project": project,
        "task_id": task_id,
        "pr_number": pr_number,
    }
