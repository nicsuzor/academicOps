#!/usr/bin/env -S uv run python
"""
PreToolUse policy enforcer for Claude Code.

Implements deterministic protection rules that don't require LLM judgment.
Scope drift detection and axiom compliance are handled by the custodiet skill
(local sessions) and auditor.agent.md (GitHub PRs). See .agent/curia/CURIA.md.

Blocks operations that violate framework principles:
- MINIMAL: *-GUIDE.md files, .md files > 200 lines
- Git Safety: destructive git commands

Exit codes:
    0: Always (JSON output determines allow/deny via permissionDecision field)
"""

import re
import sys
from pathlib import Path
from typing import Any

# Destructive git operations that should be blocked
DESTRUCTIVE_GIT_PATTERNS = [
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[fd]",
    r"git\s+push\s+--force",
    r"git\s+checkout\s+--\s+\.",
    r"git\s+stash\s+drop",
]

# Bulk destructive shell operations that should be blocked (#346)
DESTRUCTIVE_SHELL_PATTERNS = [
    # rm -rf with glob or multiple targets (allow single specific files)
    r"\brm\b\s+-r[f]?\s+\S+\s+\S+",  # rm -rf dir1 dir2 dir3...
    r"\brm\b\s+-r[f]?\s+.*[*?\[\]].*",  # rm -rf * or rm -rf *.something
    r"\brm\b\s+-r[f]?\s+\.\s",  # rm -rf .
    r"\brm\b\s+-r[f]?\s+\.$",  # rm -rf .
]


def count_prose_lines(content: str) -> int:
    """Count lines excluding mermaid/code blocks."""
    lines = content.split("\n")
    count = 0
    in_code_block = False

    for line in lines:
        # Toggle on code fence (``` or ```mermaid, etc.)
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            count += 1

    return count


def validate_minimal_documentation(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Block *-GUIDE.md files and .md files > 200 prose lines."""
    if tool_name != "Write":
        return None

    if "file_path" not in args:
        raise ValueError("Write tool args requires 'file_path' parameter (P#8: fail-fast)")
    if "content" not in args:
        raise ValueError("Write tool args requires 'content' parameter (P#8: fail-fast)")
    file_path = args["file_path"]
    content = args["content"]

    if file_path.endswith("-GUIDE.md") or "GUIDE.md" in file_path.upper():
        return {
            "continue": False,
            "systemMessage": (
                "BLOCKED: *-GUIDE.md files violate MINIMAL principle.\n"
                "Add 2 sentences to README.md instead."
            ),
        }

    if file_path.endswith(".md"):
        prose_lines = count_prose_lines(content)
        if prose_lines > 200:
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: {prose_lines} prose lines exceeds 200 line limit.\n"
                    "(Code/mermaid blocks excluded from count.)\n"
                    "Split into focused chunks or reduce content."
                ),
            }

    return None


def validate_safe_git_usage(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Block destructive git and shell operations."""
    if tool_name != "Bash":
        return None

    if "command" not in args:
        raise ValueError("Bash tool args requires 'command' parameter (P#8: fail-fast)")
    command = args["command"]

    for pattern in DESTRUCTIVE_GIT_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: Destructive git command.\n"
                    f"Command: {command}\n"
                    f"Use safe alternatives or ask user for explicit confirmation."
                ),
            }

    for pattern in DESTRUCTIVE_SHELL_PATTERNS:
        if re.search(pattern, command):
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: Bulk destructive operation (P#50: Explicit Approval).\n"
                    f"Command: {command}\n"
                    f"Ask user for explicit confirmation before bulk deletions."
                ),
            }

    return None


def validate_branch_protection(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Block git commit on protected branches (main/master) (#322).

    When agents commit directly to main instead of a feature branch, it
    bypasses the PR review pipeline. This gate catches the most common case.
    """
    if tool_name != "Bash":
        return None

    command = args.get("command", "")

    # Only check commands that contain git commit
    if not re.search(r"git\s+commit", command, re.IGNORECASE):
        return None

    # Check current branch by looking for explicit branch indicators in command
    # This catches: git commit on main when the command doesn't specify a branch
    # The real check is against the working directory's current branch
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        current_branch = result.stdout.strip()
    except Exception as e:
        print(
            f"WARNING: Failed to determine git branch in validate_branch_protection: {e}",
            file=sys.stderr,
        )
        return None  # Can't determine branch — allow and let other checks handle it

    if current_branch in ("main", "master"):
        return {
            "continue": False,
            "systemMessage": (
                f"BLOCKED: git commit on protected branch '{current_branch}' (P#26: Verify First).\n"
                f"Create a feature branch first: git checkout -b <branch-name>\n"
                f"Direct commits to {current_branch} bypass the PR review pipeline."
            ),
        }

    return None


def _load_protected_paths() -> list[str]:
    """Load protected paths from project-local config."""
    local_config = Path(".agent/rules/protected_paths.txt")
    if not local_config.exists():
        return []
    try:
        return [
            line.strip()
            for line in local_config.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    except Exception as e:
        print(f"WARNING: Failed to read {local_config}: {e}", file=sys.stderr)
        return []


def _path_is_protected(file_path: str, protected_paths: list[str]) -> str | None:
    """Return matching protected path, or None."""
    for protected in protected_paths:
        if file_path.startswith(protected) or f"/{protected}" in file_path:
            return protected
    return None


def validate_protect_artifacts(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Block modification of protected files (H#94, #354, #381).

    Checks both file-writing tools (Write/Edit) and Bash commands that
    copy/move files into protected directories.
    """
    protected_paths = _load_protected_paths()
    if not protected_paths:
        return None

    # Check Write/Edit/replace tools
    if tool_name in ("Write", "Edit", "replace"):
        file_path = args.get("file_path")
        if file_path:
            match = _path_is_protected(file_path, protected_paths)
            if match:
                return {
                    "continue": False,
                    "systemMessage": (
                        f"BLOCKED: Modification of protected path '{file_path}'.\n"
                        f"This path is protected by project-local rule (see .agent/rules/protected_paths.txt).\n"
                        "Modify source files instead and run build scripts if necessary."
                    ),
                }

    # Check Bash commands that write to protected paths (cp, mv, etc.)
    if tool_name == "Bash":
        command = args.get("command", "")
        # Match cp/mv commands targeting protected directories
        for protected in protected_paths:
            # cp ... dist/ or mv ... dist/
            if re.search(rf"\b(cp|mv)\b.*\s\S*{re.escape(protected)}\S*", command):
                return {
                    "continue": False,
                    "systemMessage": (
                        f"BLOCKED: Shell command writes to protected path '{protected}' (P#97: Never Edit Generated Files).\n"
                        f"Command: {command}\n"
                        "Use the build pipeline instead: uv run python scripts/build.py"
                    ),
                }

    return None
