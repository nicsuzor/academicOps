"""Orchestrator boundary detection.

The general CLI agent (the main Claude Code session) is an orchestrator —
it delegates feature work to polecat workers. Writing to project source files
from the orchestrator session is a boundary violation that should be surfaced.

This module provides two related capabilities:

1. `classify_prompt`: lightweight classifier distinguishing a user-typed
   slash command, a short question, and a work-request. Used by the hydrator
   to decide whether to inject the dispositor reminder.

2. `is_orchestrator_session` / `is_framework_path` / `is_project_source_write`:
   helpers used by the Level 4 PostToolUse detection hook to warn when the
   orchestrator writes to project source.

See `specs/orchestrator-boundary.md` for the full boundary definition.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any

# Tool names that write to files on disk. Bash is intentionally excluded —
# the boundary is about code edits, not shell commands. Destructive git /
# filesystem operations are covered by policy_enforcer.py.
WRITE_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "Edit",
        "Write",
        "MultiEdit",
        "NotebookEdit",
        # Gemini CLI equivalents
        "write_file",
        "replace",
    }
)

# Paths considered "framework files" — the orchestrator may freely edit these
# because framework maintenance is orchestrator scope. Any write outside this
# allowlist is project source and should be delegated to a polecat worker.
#
# Paths are matched as prefixes against the file_path relative to cwd, using
# forward-slash form.
FRAMEWORK_PATH_PREFIXES: tuple[str, ...] = (
    "aops-core/",
    "aops-tools/",
    "specs/",
    ".agents/",
    "docs/",
    "tests/",
    "scripts/",
    "templates/",
    "polecat/",
)

# Polecat sets POLECAT_SESSION_TYPE to one of these values inside a worker
# container/session. If set, the session is not the orchestrator CLI, so the
# boundary does not apply.
_POLECAT_WORKER_SESSION_TYPES: frozenset[str] = frozenset({"polecat", "crew"})


def is_orchestrator_session(env: dict[str, str] | None = None) -> bool:
    """Return True when the current session is the orchestrator CLI.

    A session is orchestrator iff POLECAT_SESSION_TYPE is unset (or not a
    known worker session type). Defaulting to True means the boundary applies
    by default — any deployment that wants to opt out must set the env var.
    """
    e = env if env is not None else os.environ
    session_type = e.get("POLECAT_SESSION_TYPE", "").strip()
    if not session_type:
        return True
    return session_type not in _POLECAT_WORKER_SESSION_TYPES


def _normalize_relative(path_str: str, cwd: str | None) -> str | None:
    """Return path_str as a forward-slash string relative to cwd if possible.

    Returns None when the path is outside cwd (not a project path) or when
    normalization fails. Absolute paths outside cwd are treated as "not a
    project write" (e.g. writing to ~/.claude/...).
    """
    if not path_str:
        return None
    try:
        p = Path(path_str)
        if p.is_absolute():
            if not cwd:
                return None
            try:
                rel = p.resolve().relative_to(Path(cwd).resolve())
            except ValueError:
                return None
            return PurePosixPath(rel).as_posix()
        # Relative path — already relative to cwd
        return PurePosixPath(path_str).as_posix()
    except (OSError, ValueError):
        return None


def is_framework_path(
    file_path: str,
    cwd: str | None = None,
    allowlist: tuple[str, ...] = FRAMEWORK_PATH_PREFIXES,
) -> bool:
    """Return True if file_path falls under a framework allowlist prefix.

    Framework paths (specs/, aops-core/, .agents/, docs/, tests/, etc.) are
    orchestrator scope. All other source writes should be delegated to a
    polecat worker.

    Top-level files (README.md, pyproject.toml, etc.) are considered project
    files — the orchestrator should not routinely edit them — but the caller
    may extend the allowlist.
    """
    rel = _normalize_relative(file_path, cwd)
    if rel is None:
        return False
    if rel.startswith("./"):
        rel = rel[2:]
    return any(rel.startswith(prefix) for prefix in allowlist)


def is_project_source_write(
    tool_name: str | None,
    tool_input: dict[str, Any] | None,
    cwd: str | None = None,
) -> bool:
    """Return True when the call is a write to non-framework project source.

    Used by the Level 4 PostToolUse detection hook to surface orchestrator
    boundary drift. Does NOT consult the environment — callers should combine
    this with `is_orchestrator_session()` to decide whether to warn.
    """
    if tool_name not in WRITE_TOOL_NAMES:
        return False
    if not isinstance(tool_input, dict):
        return False
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not isinstance(file_path, str) or not file_path.strip():
        return False
    return _normalize_relative(file_path, cwd) is not None and not is_framework_path(file_path, cwd)


def classify_prompt(prompt: str) -> str:
    """Classify a user prompt for hydrator routing.

    Returns one of:
    - "slash-command": starts with `/` — explicit skill invocation
    - "task-notification": background plumbing (already filtered elsewhere)
    - "question": short, question-shaped (ends with `?`, < 12 words)
    - "work-request": non-trivial prompt that may describe execution work
    - "empty": empty / whitespace-only

    The classifier is deliberately coarse. We do not attempt semantic
    classification here (P#49 — no shitty NLP). The classifier exists only
    to decide whether injecting the dispositor reminder is useful. The main
    agent, which has full context, decides whether to actually queue vs
    execute.
    """
    if not isinstance(prompt, str):
        return "empty"
    stripped = prompt.strip()
    if not stripped:
        return "empty"
    if stripped.startswith("<task-notification>"):
        return "task-notification"
    if stripped.startswith("/"):
        return "slash-command"
    word_count = len(stripped.split())
    if stripped.endswith("?") and word_count < 12:
        return "question"
    return "work-request"


def should_inject_dispositor_reminder(prompt: str, env: dict[str, str] | None = None) -> bool:
    """Return True when the hydrator should inject the dispositor reminder.

    Only injects in the orchestrator session and only for prompts that could
    plausibly be work requests. Slash commands and short questions are
    skipped — the former is explicit user intent, the latter is unlikely to
    describe feature work.
    """
    if not is_orchestrator_session(env):
        return False
    return classify_prompt(prompt) == "work-request"
