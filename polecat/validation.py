#!/usr/bin/env python3
"""Task ID and PR URL validation for polecat operations.

Validates task IDs before use in:
- Git branch names (polecat/<task_id>)
- Filesystem paths ($POLECAT_HOME/<task_id>/)
- Subprocess commands

This prevents path traversal attacks and git ref injection by ensuring
task IDs conform to expected formats before they reach git or filesystem operations.

Valid task ID formats:
- New format: <project>-<hash8> (e.g., aops-a1b2c3d4, ns-12345678)
- Legacy format: YYYYMMDD-slug (e.g., 20260119-my-task)
- Simple slug: (e.g., my-task-id)

Threat models addressed:
- Path traversal: ../../../etc/passwd
- Git ref injection: HEAD, @{, ..
- Command injection via specially crafted IDs
- DoS via extremely long strings

Also validates `pr_url` before release_task accepts it. The A3/A8 integrity
gate: terminal-status release must not succeed with a fabricated or
unresolvable PR URL (see task-0e4d20a8 / cheryl 2026-04-18 incident).
"""

import os
import re
import shutil
import subprocess
import sys

# Maximum task ID length to prevent DoS/buffer issues
MAX_TASK_ID_LENGTH = 100

# Minimum task ID length (must have at least prefix-hash or short slug)
MIN_TASK_ID_LENGTH = 2

# Pattern for valid task IDs:
# - Lowercase alphanumeric, hyphens, underscores
# - Must start and end with alphanumeric
# - No consecutive dots (prevents .. in paths and git refs)
TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$")

# Git special refs that should never be used as task IDs
GIT_SPECIAL_REFS = frozenset(
    {
        "head",
        "fetch_head",
        "orig_head",
        "merge_head",
        "cherry_pick_head",
        "revert_head",
        "stash",
        "main",
        "master",
        "develop",
        "origin",
    }
)

# Dangerous substrings that indicate injection attempts
DANGEROUS_PATTERNS = frozenset(
    {
        "..",  # Path traversal and git ref separator
        "/",  # Path separator
        "\\",  # Windows path separator
        "@{",  # Git reflog syntax
        "\x00",  # Null byte
        "\n",  # Newline (command injection)
        "\r",  # Carriage return
        " ",  # Space (command injection)
    }
)


class TaskIDValidationError(ValueError):
    """Raised when a task ID fails validation.

    Attributes:
        task_id: The invalid task ID
        reason: Why the validation failed
    """

    def __init__(self, task_id: str, reason: str):
        self.task_id = task_id
        self.reason = reason
        # Truncate displayed task_id to prevent log injection
        safe_id = repr(task_id[:50]) if task_id else repr(task_id)
        super().__init__(f"Invalid task ID {safe_id}: {reason}")


def validate_task_id(task_id: str) -> bool:
    """Check if a task ID is valid for use in polecat operations.

    Args:
        task_id: The task ID to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_task_id("aops-5056bc83")
        True
        >>> validate_task_id("20260119-my-task")
        True
        >>> validate_task_id("../etc/passwd")
        False
        >>> validate_task_id("HEAD")
        False
    """
    try:
        validate_task_id_or_raise(task_id)
        return True
    except TaskIDValidationError:
        return False


def validate_task_id_or_raise(task_id: str) -> str:
    """Validate a task ID, raising an exception if invalid.

    Use this function at entry points before any git or filesystem operations.

    Args:
        task_id: The task ID to validate

    Returns:
        The validated task ID (unchanged if valid)

    Raises:
        TaskIDValidationError: If the task ID is invalid

    Examples:
        >>> validate_task_id_or_raise("aops-5056bc83")
        'aops-5056bc83'
        >>> validate_task_id_or_raise("../escape")
        Traceback (most recent call last):
            ...
        validation.TaskIDValidationError: Invalid task ID '../escape': ...
    """
    # Type check
    if not isinstance(task_id, str):
        raise TaskIDValidationError(
            str(task_id) if task_id is not None else "None", "must be a string"
        )

    # Length bounds
    if len(task_id) < MIN_TASK_ID_LENGTH:
        raise TaskIDValidationError(task_id, "too short (minimum 2 characters)")

    if len(task_id) > MAX_TASK_ID_LENGTH:
        raise TaskIDValidationError(task_id, f"too long (maximum {MAX_TASK_ID_LENGTH} characters)")

    # Check for dangerous patterns first (before regex, since regex won't catch all)
    for pattern in DANGEROUS_PATTERNS:
        if pattern in task_id:
            raise TaskIDValidationError(task_id, f"contains forbidden pattern: {repr(pattern)}")

    # Check for git special refs (case-insensitive)
    if task_id.lower() in GIT_SPECIAL_REFS:
        raise TaskIDValidationError(task_id, "conflicts with git special ref")

    # Normalize to lowercase for validation (task IDs should be lowercase)
    normalized = task_id.lower()

    # Check against pattern
    if not TASK_ID_PATTERN.match(normalized):
        raise TaskIDValidationError(
            task_id,
            "must contain only lowercase alphanumeric characters, hyphens, and underscores, "
            "and must start/end with alphanumeric",
        )

    return task_id


# ---------------------------------------------------------------------------
# PR URL validation (A3/A8 integrity gate)
# ---------------------------------------------------------------------------

# GitHub pull / issue / commit URL. Accepts only github.com — the incident that
# motivated this gate involved a URL pointing at a non-existent org
# ("academic-ops") on github.com; other hosts would be a separate class of
# problem and are not in scope.
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/"
    r"(?P<org>[A-Za-z0-9][A-Za-z0-9-]*)/"
    r"(?P<repo>[A-Za-z0-9._][A-Za-z0-9._-]*)/"
    r"(?:"
    r"pull/(?P<pr>\d+)"
    r"|issues/(?P<issue>\d+)"
    r"|commit/(?P<sha>[0-9a-fA-F]{7,40})"
    r")/?$"
)


class PRURLValidationError(ValueError):
    """Raised when a pr_url fails format or live validation."""

    def __init__(self, pr_url: str, reason: str):
        self.pr_url = pr_url
        self.reason = reason
        safe = repr(pr_url[:200]) if pr_url else repr(pr_url)
        super().__init__(f"Invalid pr_url {safe}: {reason}")


def validate_pr_url_format(pr_url: str) -> re.Match:
    """Check that pr_url is a well-formed GitHub pull/issue/commit URL.

    Returns the regex Match so callers can extract org/repo/number/sha.
    Raises PRURLValidationError on malformed input. Does NOT check that the
    URL resolves to a real resource — use ``verify_pr_url_live`` for that.
    """
    if not isinstance(pr_url, str) or not pr_url.strip():
        raise PRURLValidationError(str(pr_url), "must be a non-empty string")
    m = GITHUB_URL_PATTERN.match(pr_url.strip())
    if m is None:
        raise PRURLValidationError(
            pr_url,
            "expected https://github.com/<org>/<repo>/{pull,issues,commit}/<n-or-sha>",
        )
    return m


def verify_pr_url_live(pr_url: str, expected_org: str | None = None) -> None:
    """Confirm that pr_url resolves to an actual GitHub resource.

    Uses ``gh`` (already an installation prerequisite for polecat finish). If
    ``expected_org`` is given, also asserts the URL targets that org.

    Skips the live check (format-only) when:
    - ``POLECAT_SKIP_PR_URL_CHECK=1`` (for offline tests, CI without gh auth).
    - ``gh`` is not installed on PATH (cannot verify; fail open with a warning
      printed to stderr so it's visible in the transcript).

    Raises PRURLValidationError when the live check runs and fails.
    """
    m = validate_pr_url_format(pr_url)

    if expected_org is not None and m.group("org").lower() != expected_org.lower():
        raise PRURLValidationError(
            pr_url,
            f"org is {m.group('org')!r} but expected {expected_org!r}",
        )

    if os.environ.get("POLECAT_SKIP_PR_URL_CHECK") == "1":
        return

    if shutil.which("gh") is None:
        # Honest epistemics: we can't verify, so say so. Don't silently pass.
        print(
            f"  ⚠️  gh not installed; cannot live-verify pr_url={pr_url}. "
            f"Set POLECAT_SKIP_PR_URL_CHECK=1 to silence this warning.",
            file=sys.stderr,
            flush=True,
        )
        return

    org, repo = m.group("org"), m.group("repo")
    if m.group("pr"):
        cmd = ["gh", "pr", "view", pr_url, "--json", "state,url"]
    elif m.group("issue"):
        cmd = ["gh", "issue", "view", pr_url, "--json", "state,url"]
    else:  # commit
        cmd = ["gh", "api", f"/repos/{org}/{repo}/commits/{m.group('sha')}"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
    except subprocess.TimeoutExpired as err:
        raise PRURLValidationError(pr_url, "gh live-check timed out after 15s") from err
    except FileNotFoundError:
        # Race: gh disappeared between shutil.which and run. Treat as fail-open.
        return

    if res.returncode != 0:
        stderr = (res.stderr or "").strip().splitlines()
        detail = stderr[-1] if stderr else f"exit code {res.returncode}"
        raise PRURLValidationError(pr_url, f"gh could not resolve URL ({detail})")
