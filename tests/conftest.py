#!/usr/bin/env python3
"""
Shared fixtures for integration tests.

This provides common utilities for testing Claude Code in headless mode.
"""

from pathlib import Path

import pytest

from .paths import get_aops_root, get_aca_root, get_hook_script

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def repo_root() -> Path:
    """Get the aOps framework repository root."""
    return get_aops_root()


@pytest.fixture
def aops_root() -> Path:
    """Get the aOps framework repository root."""
    return get_aops_root()


@pytest.fixture
def aca_root() -> Path:
    """Get the user's personal workspace root (ACA)."""
    return get_aca_root()


@pytest.fixture
def validate_tool_script() -> Path:
    """Path to validate_tool.py hook script."""
    return get_hook_script("validate_tool.py")


@pytest.fixture
def validate_env_script() -> Path:
    """Path to load_instructions.py hook script (SessionStart hook)."""
    return get_hook_script("load_instructions.py")


@pytest.fixture
def validate_stop_script() -> Path:
    """Path to validate_stop.py hook script (Stop/SubagentStop hooks)."""
    return get_hook_script("validate_stop.py")


@pytest.fixture
def request_scribe_stop_script() -> Path:
    """Path to request_scribe_stop.py hook script (Stop/SubagentStop hooks)."""
    return get_hook_script("request_scribe_stop.py")


@pytest.fixture
def log_userpromptsubmit_script() -> Path:
    """Path to log_userpromptsubmit.py hook script (UserPromptSubmit hook)."""
    return get_hook_script("log_userpromptsubmit.py")


@pytest.fixture
def personal_repo_root() -> Path:
    """Get the user's personal workspace root (ACA)."""
    return get_aca_root()


@pytest.fixture
def has_user_context(personal_repo_root: Path) -> bool:
    """Check if user context files are available."""
    # TODO: Update this path if user context location changes
    return (personal_repo_root / "docs" / "agents" / "INSTRUCTIONS.md").exists()
