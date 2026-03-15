#!/usr/bin/env python3
"""Integration tests for aops-core plugin loading.

Consolidated from 6 tests to 2 (1 fast discovery + 1 slow smoke test).
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import extract_response_text


@pytest.fixture(autouse=True)
def mock_home(tmp_path):
    """Setup a mock ~/.claude/ structure in tmp_path."""
    # Create structure
    plugins_dir = tmp_path / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    # Create plugin symlink or dir
    aops_core = plugins_dir / "aops-core"
    aops_core.mkdir(parents=True, exist_ok=True)
    (aops_core / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (aops_core / ".claude-plugin" / "plugin.json").touch()

    with patch.object(Path, "home", return_value=tmp_path):
        yield


class TestPluginDiscovery:
    """Verify plugin is discovered via symlink (fast, no headless)."""

    @pytest.mark.integration
    def test_plugin_symlink_exists(self) -> None:
        """Plugin entry must exist in plugins dir."""
        from lib.paths import get_plugin_root
        plugin_root = get_plugin_root()
        assert plugin_root.exists(), f"Plugin not found at {plugin_root}"

    @pytest.mark.integration
    def test_plugin_target_valid(self) -> None:
        """Plugin entry must point to valid directory."""
        from lib.paths import get_plugin_root
        plugin_root = get_plugin_root()
        assert plugin_root.exists(), f"Plugin not found at {plugin_root}"
        target = plugin_root.resolve()
        assert target.is_dir(), f"Plugin target not a directory: {target}"
        assert (target / ".claude-plugin" / "plugin.json").exists(), "Missing plugin.json"


class TestHookFunctionality:
    """Verify hooks are functional (slow, uses headless)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_session_completes_from_tmp(self, claude_headless, tmp_path: Path) -> None:
        """Session should complete without hook errors when run from /tmp."""
        workdir = tmp_path / "plugin-test"
        workdir.mkdir()
        result = claude_headless(
            "What is 2+2? Answer with just the number.",
            cwd=workdir,
            timeout_seconds=60,
        )

        response = extract_response_text(result)
        assert "4" in response, f"Expected '4' in response: {response}"
