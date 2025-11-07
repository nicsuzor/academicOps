#!/usr/bin/env python3
"""
Shared fixtures for integration tests.

This provides common utilities for testing Claude Code in headless mode.
"""

from pathlib import Path

import pytest

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def repo_root() -> Path:
    """Get the personal repository root directory from environment variable."""
    import os

    project_root = os.getenv("ACADEMICOPS")
    if not project_root:
        msg = (
            "ACADEMICOPS environment variable not set. "
            "This must point to your personal repository root."
        )
        raise RuntimeError(msg)

    path = Path(project_root)
    if not path.exists():
        msg = f"ACADEMICOPS path does not exist: {project_root}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def validate_tool_script() -> Path:
    """Path to validate_tool.py hook script."""
    import os

    bot_root = os.getenv("ACADEMICOPS")
    if not bot_root:
        msg = (
            "ACADEMICOPS environment variable not set. "
            "This must point to the academicOps bot repository root."
        )
        raise RuntimeError(msg)

    path = Path(bot_root) / "bots" / "hooks" / "validate_tool.py"
    if not path.exists():
        msg = f"validate_tool.py not found at expected path: {path}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def validate_env_script() -> Path:
    """Path to load_instructions.py hook script (SessionStart hook)."""
    import os

    bot_root = os.getenv("ACADEMICOPS")
    if not bot_root:
        msg = (
            "ACADEMICOPS environment variable not set. "
            "This must point to the academicOps bot repository root."
        )
        raise RuntimeError(msg)

    path = Path(bot_root) / "bots" / "hooks" / "load_instructions.py"
    if not path.exists():
        msg = f"load_instructions.py not found at expected path: {path}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def validate_stop_script() -> Path:
    """Path to validate_stop.py hook script (Stop/SubagentStop hooks)."""
    import os

    bot_root = os.getenv("ACADEMICOPS")
    if not bot_root:
        msg = (
            "ACADEMICOPS environment variable not set. "
            "This must point to the academicOps bot repository root."
        )
        raise RuntimeError(msg)

    path = Path(bot_root) / "hooks" / "validate_stop.py"
    if not path.exists():
        msg = f"validate_stop.py not found at expected path: {path}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def request_scribe_stop_script() -> Path:
    """Path to request_scribe_stop.py hook script (Stop/SubagentStop hooks)."""
    import os

    bot_root = os.getenv("ACADEMICOPS")
    if not bot_root:
        msg = (
            "ACADEMICOPS environment variable not set. "
            "This must point to the academicOps bot repository root."
        )
        raise RuntimeError(msg)

    path = Path(bot_root) / "hooks" / "request_scribe_stop.py"
    if not path.exists():
        msg = f"request_scribe_stop.py not found at expected path: {path}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def log_userpromptsubmit_script() -> Path:
    """Path to log_userpromptsubmit.py hook script (UserPromptSubmit hook)."""
    import os

    bot_root = os.getenv("ACADEMICOPS")
    if not bot_root:
        msg = (
            "ACADEMICOPS environment variable not set. "
            "This must point to the academicOps bot repository root."
        )
        raise RuntimeError(msg)

    path = Path(bot_root) / "hooks" / "log_userpromptsubmit.py"
    if not path.exists():
        msg = f"log_userpromptsubmit.py not found at expected path: {path}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def personal_repo_root() -> Path:
    """Get the personal repository root from environment variable."""
    import os

    personal_root = os.getenv("ACADEMICOPS_PERSONAL")
    if not personal_root:
        msg = (
            "ACADEMICOPS_PERSONAL environment variable not set. "
            "This must point to your personal repository root."
        )
        raise RuntimeError(msg)

    path = Path(personal_root)
    if not path.exists():
        msg = f"ACADEMICOPS_PERSONAL path does not exist: {personal_root}"
        raise RuntimeError(msg)

    return path


@pytest.fixture
def has_user_context(personal_repo_root: Path) -> bool:
    """Check if user context files are available."""
    return (personal_repo_root / "docs" / "agents" / "INSTRUCTIONS.md").exists()
