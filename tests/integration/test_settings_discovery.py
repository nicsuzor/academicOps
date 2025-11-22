#!/usr/bin/env python3
"""Settings.json discovery validation tests.

Validates that Claude Code can discover settings.json at expected locations.
This ensures hooks, permissions, and other Claude Code configuration are loaded.

Test approach:
- Check for settings.json at canonical locations (user global and project)
- Verify at least one location has valid settings.json
- Validate settings.json contains required hook configuration

Running tests:
- pytest tests/integration/test_settings_discovery.py -xvs
"""

import json
from pathlib import Path

import pytest


def test_settings_json_discoverable_by_claude(bots_dir: Path) -> None:
    """Test that Claude Code can discover settings.json at expected locations.

    Claude Code looks for settings.json at:
    1. ~/.claude/settings.json (user global)
    2. <project>/.claude/settings.json (project-specific)

    At least ONE of these locations must exist and contain valid configuration
    with SessionStart hooks defined.

    Args:
        bots_dir: Path to framework root $AOPS (from fixture)

    Raises:
        AssertionError: If settings.json is not discoverable or invalid
    """
    # Define expected locations where Claude Code looks for settings.json
    user_settings = Path.home() / ".claude" / "settings.json"
    project_settings = bots_dir / ".claude" / "settings.json"

    # Check if either location exists
    user_exists = user_settings.exists()
    project_exists = project_settings.exists()

    assert user_exists or project_exists, (
        f"Claude Code cannot discover settings.json. Expected at:\n"
        f"  - User global: {user_settings} (exists: {user_exists})\n"
        f"  - Project: {project_settings} (exists: {project_exists})\n"
        f"At least one location must exist for Claude Code to load configuration."
    )

    # Determine which settings file to validate
    settings_path = user_settings if user_exists else project_settings

    # If it's a symlink, verify it points to a valid target
    if settings_path.is_symlink():
        target = settings_path.resolve()
        assert target.exists(), (
            f"settings.json at {settings_path} is a broken symlink.\n"
            f"Points to: {target} (does not exist)"
        )
        settings_path = target

    # Verify file is readable and contains valid JSON
    try:
        with settings_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        msg = f"settings.json at {settings_path} is not valid JSON: {e}"
        raise AssertionError(msg) from e
    except Exception as e:
        msg = f"Cannot read settings.json at {settings_path}: {e}"
        raise AssertionError(msg) from e

    # Validate SessionStart hooks are configured
    assert "hooks" in config, (
        f"settings.json at {settings_path} missing 'hooks' section.\n"
        f"Claude Code requires hooks configuration."
    )

    assert "SessionStart" in config["hooks"], (
        f"settings.json at {settings_path} missing 'SessionStart' hooks.\n"
        f"Available hooks: {list(config['hooks'].keys())}\n"
        f"SessionStart hooks are required for framework initialization."
    )

    session_start_hooks = config["hooks"]["SessionStart"]
    assert isinstance(session_start_hooks, list), (
        f"SessionStart hooks must be a list, got {type(session_start_hooks).__name__}"
    )

    assert len(session_start_hooks) > 0, (
        f"SessionStart hooks list is empty at {settings_path}.\n"
        f"At least one SessionStart hook configuration is required."
    )
