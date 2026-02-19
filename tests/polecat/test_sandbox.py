#!/usr/bin/env python3
"""Tests for polecat worker sandbox settings.

Verifies that create_sandbox_settings() produces a .claude/settings.json
that restricts Write and Edit operations to the worktree directory.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))


class TestCreateSandboxSettings:
    """Tests for PolecatManager.create_sandbox_settings()."""

    def test_creates_claude_dir(self, tmp_path):
        """create_sandbox_settings creates .claude/ directory in worktree."""
        from manager import PolecatManager

        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        manager.create_sandbox_settings(worktree)

        assert (worktree / ".claude").is_dir()

    def test_creates_settings_file(self, tmp_path):
        """create_sandbox_settings creates .claude/settings.json."""
        from manager import PolecatManager

        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        assert settings_path == worktree / ".claude" / "settings.json"
        assert settings_path.exists()

    def test_settings_valid_json(self, tmp_path):
        """Settings file contains valid JSON."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        with open(settings_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_deny_rules_block_writes_outside_worktree(self, tmp_path):
        """Deny rules cover Write and Edit for all paths."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        with open(settings_path) as f:
            data = json.load(f)

        deny = data["permissions"]["deny"]
        assert "Write(**)" in deny, "Must deny Write outside worktree"
        assert "Edit(**)" in deny, "Must deny Edit outside worktree"

    def test_allow_rules_permit_worktree_writes(self, tmp_path):
        """Allow rules permit Write and Edit within the worktree path."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        with open(settings_path) as f:
            data = json.load(f)

        allow = data["permissions"]["allow"]
        worktree_str = str(worktree.resolve())

        write_rule = f"Write({worktree_str}/**)"
        edit_rule = f"Edit({worktree_str}/**)"

        assert write_rule in allow, f"Must allow Write within worktree: {write_rule}"
        assert edit_rule in allow, f"Must allow Edit within worktree: {edit_rule}"

    def test_allow_rule_uses_absolute_path(self, tmp_path):
        """Allow rules use resolved absolute paths (no ~ or relative segments)."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        with open(settings_path) as f:
            data = json.load(f)

        for rule in data["permissions"].get("allow", []):
            assert not rule.startswith("Write(~"), "Allow rules must not use ~ paths"
            assert not rule.startswith("Edit(~"), "Allow rules must not use ~ paths"

    def test_idempotent_on_existing_claude_dir(self, tmp_path):
        """create_sandbox_settings is idempotent when .claude/ already exists."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        (worktree / ".claude").mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        assert settings_path.exists()

    def test_out_of_bounds_path_not_in_allow(self, tmp_path):
        """Paths outside the worktree are NOT in the allow list."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        settings_path = manager.create_sandbox_settings(worktree)

        with open(settings_path) as f:
            data = json.load(f)

        allow = data["permissions"]["allow"]
        # Home dir should not be explicitly allowed
        home_write = f"Write({Path.home()}/**)"
        assert home_write not in allow, "Home directory must not be in allow list"
        # /etc should not be explicitly allowed
        assert "Write(/etc/**)" not in allow


def _make_manager(tmp_path: Path):
    """Create a PolecatManager with mocked dependencies for unit tests."""
    from unittest.mock import MagicMock, patch

    config = {
        "projects": {},
        "crew_names": ["test"],
        "git_identity": {},
    }

    with (
        patch("manager.load_config", return_value=config),
        patch("manager.load_projects", return_value={}),
        patch("manager.load_crew_names", return_value=["test"]),
        patch("manager.TaskStorage"),
    ):
        from manager import PolecatManager

        home_dir = tmp_path / "home"
        home_dir.mkdir()
        return PolecatManager(home_dir=home_dir)
