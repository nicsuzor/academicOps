#!/usr/bin/env python3
"""
Shared fixtures for integration tests.

This provides common utilities for testing Claude Code in headless mode.
"""

import json
import subprocess
from pathlib import Path

import pytest


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def repo_root() -> Path:
    """Get the personal repository root directory from environment variable."""
    import os

    project_root = os.getenv("ACADEMICOPS_BOT")
    if not project_root:
        raise RuntimeError(
            "ACADEMICOPS_BOT environment variable not set. "
            "This must point to your personal repository root."
        )

    path = Path(project_root)
    if not path.exists():
        raise RuntimeError(f"ACADEMICOPS_BOT path does not exist: {project_root}")

    return path


@pytest.fixture
def validate_tool_script() -> Path:
    """Path to validate_tool.py hook script."""
    import os

    bot_root = os.getenv("ACADEMICOPS_BOT")
    if not bot_root:
        raise RuntimeError(
            "ACADEMICOPS_BOT environment variable not set. "
            "This must point to the academicOps bot repository root."
        )

    path = Path(bot_root) / "bots" / "hooks" / "validate_tool.py"
    if not path.exists():
        raise RuntimeError(f"validate_tool.py not found at expected path: {path}")

    return path


@pytest.fixture
def validate_env_script() -> Path:
    """Path to load_instructions.py hook script (SessionStart hook)."""
    import os

    bot_root = os.getenv("ACADEMICOPS_BOT")
    if not bot_root:
        raise RuntimeError(
            "ACADEMICOPS_BOT environment variable not set. "
            "This must point to the academicOps bot repository root."
        )

    path = Path(bot_root) / "bots" / "hooks" / "load_instructions.py"
    if not path.exists():
        raise RuntimeError(f"load_instructions.py not found at expected path: {path}")

    return path

@pytest.fixture
def validate_stop_script() -> Path:
    """Path to validate_stop.py hook script (Stop/SubagentStop hooks)."""
    import os

    bot_root = os.getenv("ACADEMICOPS_BOT")
    if not bot_root:
        raise RuntimeError(
            "ACADEMICOPS_BOT environment variable not set. "
            "This must point to the academicOps bot repository root."
        )

    path = Path(bot_root) / "bots" / "hooks" / "validate_stop.py"
    if not path.exists():
        raise RuntimeError(f"validate_stop.py not found at expected path: {path}")

    return path


@pytest.fixture
def personal_repo_root() -> Path:
    """Get the personal repository root from environment variable."""
    import os

    personal_root = os.getenv("ACADEMICOPS_PERSONAL")
    if not personal_root:
        raise RuntimeError(
            "ACADEMICOPS_PERSONAL environment variable not set. "
            "This must point to your personal repository root."
        )

    path = Path(personal_root)
    if not path.exists():
        raise RuntimeError(
            f"ACADEMICOPS_PERSONAL path does not exist: {personal_root}"
        )

    return path


@pytest.fixture
def has_user_context(personal_repo_root: Path) -> bool:
    """Check if user context files are available."""
    return (personal_repo_root / "docs" / "agents" / "INSTRUCTIONS.md").exists()

