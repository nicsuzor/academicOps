#!/usr/bin/env python3
"""Tests for polecat Gemini policy generation.

Verifies that create_sandbox_settings() produces a .gemini/policies/sandbox.toml
that permits Write and Edit operations within the worktree directory.
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch

# Add polecat to path
TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))


class TestCreateGeminiPolicy:
    """Tests for PolecatManager.create_sandbox_settings() Gemini policy generation."""

    def test_creates_gemini_policies_dir(self, tmp_path):
        """create_sandbox_settings creates .gemini/policies/ directory in worktree."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        manager.create_sandbox_settings(worktree)

        assert (worktree / ".gemini" / "policies").is_dir()

    def test_creates_policy_file(self, tmp_path):
        """create_sandbox_settings creates .gemini/policies/sandbox.toml."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        manager.create_sandbox_settings(worktree)
        policy_path = worktree / ".gemini" / "policies" / "sandbox.toml"

        assert policy_path.exists()

    def test_policy_content_allows_worktree(self, tmp_path):
        """Policy file contains allow rules for the worktree."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        manager.create_sandbox_settings(worktree)
        policy_path = worktree / ".gemini" / "policies" / "sandbox.toml"
        content = policy_path.read_text()

        worktree_str = str(worktree.resolve())
        # re.escape() is used in manager.py — verify the pattern matches exactly.
        expected_pattern = 'argsPattern = "^' + re.escape(worktree_str) + '.*"'
        assert expected_pattern in content
        assert 'decision = "allow"' in content
        assert "priority = 50" in content

    def test_policy_content_denies_others(self, tmp_path):
        """Policy file contains deny rules for other paths."""
        manager = _make_manager(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        manager.create_sandbox_settings(worktree)
        policy_path = worktree / ".gemini" / "policies" / "sandbox.toml"
        content = policy_path.read_text()

        assert 'decision = "deny"' in content
        assert "priority = 10" in content
        assert f"File writes are restricted to the worktree: {worktree}" in content


def _make_manager(tmp_path: Path):
    """Create a PolecatManager with mocked dependencies for unit tests."""
    config = {
        "projects": {},
        "crew_names": ["test"],
        "git_identity": {},
    }

    with (
        patch("manager.load_config", return_value=config),
        patch("manager.load_projects", return_value={}),
        patch("manager.load_crew_names", return_value=["test"]),
        patch("manager._TaskStorage"),
    ):
        from manager import PolecatManager

        home_dir = tmp_path / "home"
        home_dir.mkdir()
        return PolecatManager(home_dir=home_dir)
