"""Tests for task-required gate integration.

Tests the safe temp path detection logic used by the gate system.
"""

import os
import sys
import pytest
from unittest.mock import patch
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))


class TestSafeTempPaths:
    """Test safe temp directory allowlist for writes without task binding."""

    def test_is_safe_temp_path_claude_tmp(self):
        """Writes to ~/.claude/tmp/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        claude_tmp = str(Path.home() / ".claude" / "tmp" / "test.txt")
        assert _is_safe_temp_path(claude_tmp), "~/.claude/tmp/ should be safe"

    def test_is_safe_temp_path_claude_projects(self):
        """Writes to ~/.claude/projects/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        claude_projects = str(
            Path.home() / ".claude" / "projects" / "abc" / "state.json"
        )
        assert _is_safe_temp_path(claude_projects), "~/.claude/projects/ should be safe"

    def test_is_safe_temp_path_gemini_tmp(self):
        """Writes to ~/.gemini/tmp/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        gemini_tmp = str(Path.home() / ".gemini" / "tmp" / "hash" / "logs.jsonl")
        assert _is_safe_temp_path(gemini_tmp), "~/.gemini/tmp/ should be safe"

    def test_is_safe_temp_path_aops_tmp(self):
        """Writes to ~/.aops/tmp/ should be allowed without task."""
        from hooks.gate_registry import _is_safe_temp_path

        aops_tmp = str(Path.home() / ".aops" / "tmp" / "hydrator" / "ctx.md")
        assert _is_safe_temp_path(aops_tmp), "~/.aops/tmp/ should be safe"

    def test_is_safe_temp_path_user_file_blocked(self):
        """Writes to regular user files should NOT be safe (require task)."""
        from hooks.gate_registry import _is_safe_temp_path

        user_file = str(Path.home() / "src" / "project" / "main.py")
        assert not _is_safe_temp_path(user_file), "User files should not be safe"

    def test_is_safe_temp_path_claude_settings_blocked(self):
        """Writes to ~/.claude/settings.json should NOT be safe."""
        from hooks.gate_registry import _is_safe_temp_path

        settings = str(Path.home() / ".claude" / "settings.json")
        assert not _is_safe_temp_path(settings), (
            "~/.claude/settings.json should not be safe"
        )

    def test_is_safe_temp_path_handles_none(self):
        """None path should be handled safely."""
        from hooks.gate_registry import _is_safe_temp_path

        assert not _is_safe_temp_path(None), "None path should not be safe"

    def test_is_safe_temp_path_handles_empty(self):
        """Empty path should be handled safely."""
        from hooks.gate_registry import _is_safe_temp_path

        assert not _is_safe_temp_path(""), "Empty path should not be safe"
