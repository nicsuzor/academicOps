#!/usr/bin/env python3
"""Task ID validation for polecat operations.

Validates task IDs before use in:
- Git branch names (polecat/<task_id>)
- Filesystem paths (~/.aops/<task_id>/)
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
"""

import re

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
