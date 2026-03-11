#!/usr/bin/env python3
"""
Tests for path resolution in academicOps framework.

Tests the core path resolution functions that locate the academicOps repository
root and its key subdirectories using AOPS and ACA_DATA environment variables.
"""

from pathlib import Path

import pytest

from tests.paths import (
    get_bots_dir,  # Alias for get_aops_root (backwards compatibility)
    get_data_dir,
    get_hook_script,
    get_hooks_dir,
    get_writing_root,  # Alias for get_aops_root (backwards compatibility)
)


class TestGetWritingRoot:
    """Tests for get_writing_root() function.

    Note: Architecture changed - $AOPS env var is no longer used.
    get_writing_root() now always returns the plugin root (aops-core directory).
    """

    def test_get_writing_root_returns_plugin_root(self, monkeypatch):
        """Test get_writing_root() returns plugin root regardless of env vars.

        In the new plugin-centric architecture, get_writing_root() always returns
        the aops-core plugin directory, not the $AOPS environment variable.
        """
        # Arrange - $AOPS should have no effect
        monkeypatch.setenv("AOPS", "/some/other/path")

        # Act
        result = get_writing_root()

        # Assert - returns plugin root (aops-core), not $AOPS
        assert isinstance(result, Path)
        assert result.name == "aops-core"
        assert (result / "lib").exists()  # Sanity check - plugin root has lib/

    def test_get_writing_root_fallbacks(self, monkeypatch):
        """Test get_writing_root() returns plugin root without env var."""
        monkeypatch.delenv("AOPS", raising=False)
        # Should return a Path (plugin root)
        result = get_writing_root()
        assert isinstance(result, Path)
        assert result.name == "aops-core"

    def test_get_writing_root_is_always_plugin_root(self, monkeypatch):
        """Test get_writing_root always returns plugin root (no env var support)."""
        # Arrange - set bogus AOPS path
        monkeypatch.setenv("AOPS", "/nonexistent/path")

        # Act
        result = get_writing_root()

        # Assert - should still be plugin root, ignoring $AOPS
        assert isinstance(result, Path)
        assert result.exists()
        assert result.name == "aops-core"


class TestGetBotsDir:
    """Tests for get_bots_dir() function (backwards compat alias).

    Note: Architecture changed - get_bots_dir() is now an alias for get_aops_root()
    which always returns the plugin root (aops-core directory).
    """

    def test_get_bots_dir(self, monkeypatch):
        """Test get_bots_dir() returns plugin root (alias for get_aops_root())."""
        # Arrange - $AOPS should have no effect (architecture changed)
        monkeypatch.setenv("AOPS", "/some/ignored/path")

        # Act
        result = get_bots_dir()

        # Assert - Returns plugin root (aops-core)
        assert isinstance(result, Path)
        assert result.name == "aops-core"
        assert result.exists()


class TestGetDataDir:
    """Tests for get_data_dir() function."""

    def test_get_data_dir(self, tmp_path, monkeypatch):
        """Test get_data_dir() returns ACA_DATA root."""
        # Arrange - Uses ACA_DATA environment variable
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setenv("ACA_DATA", str(data_dir))

        # Act
        result = get_data_dir()

        # Assert
        assert result == data_dir
        assert isinstance(result, Path)


class TestGetHooksDir:
    """Tests for get_hooks_dir() function."""

    def test_get_hooks_dir(self, tmp_path, monkeypatch):
        """Test get_hooks_dir() returns aops_root / 'aops-core' / 'hooks'."""
        # Arrange - Hooks are now under AOPS/aops-core/ in v1.0
        aops_root = tmp_path / "academicOps"
        aops_core = aops_root / "aops-core"
        hooks_dir = aops_core / "hooks"
        aops_root.mkdir()
        aops_core.mkdir()
        hooks_dir.mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))
        # Patch get_plugin_root to return our temp path
        monkeypatch.setattr("lib.paths.get_plugin_root", lambda: aops_core)

        # Act
        result = get_hooks_dir()

        # Assert
        assert result == hooks_dir
        assert isinstance(result, Path)


class TestGetHookScript:
    """Tests for get_hook_script() function."""

    def test_get_hook_script_exists(self, tmp_path, monkeypatch):
        """Test get_hook_script(name) returns correct path for existing hook."""
        # Arrange - Hooks are under AOPS/aops-core/hooks/ in v1.0
        aops_root = tmp_path / "academicOps"
        aops_core = aops_root / "aops-core"
        hooks_dir = aops_core / "hooks"
        aops_root.mkdir()
        aops_core.mkdir()
        hooks_dir.mkdir()

        hook_script = hooks_dir / "router.py"
        hook_script.touch()

        monkeypatch.setenv("AOPS", str(aops_root))
        # Patch get_plugin_root to return our temp path
        monkeypatch.setattr("lib.paths.get_plugin_root", lambda: aops_core)

        # Act
        result = get_hook_script("router.py")

        # Assert
        assert result == hook_script
        assert isinstance(result, Path)
        assert result.exists()

    def test_get_hook_script_missing_fails(self, tmp_path, monkeypatch):
        """Test RuntimeError when hook doesn't exist."""
        # Arrange
        aops_root = tmp_path / "academicOps"
        aops_core = aops_root / "aops-core"
        hooks_dir = aops_core / "hooks"
        aops_root.mkdir()
        aops_core.mkdir()
        hooks_dir.mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))
        # Patch get_plugin_root to return our temp path
        monkeypatch.setattr("lib.paths.get_plugin_root", lambda: aops_core)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Hook script not found"):
            get_hook_script("nonexistent_hook.py")


class TestPathsUsePathlib:
    """Tests that all path functions return Path objects."""

    def test_paths_use_pathlib(self, tmp_path, monkeypatch):
        """Test all functions return Path objects, not strings."""
        # Arrange - Set up both AOPS and ACA_DATA environments
        aops_root = tmp_path / "academicOps"
        aops_core = aops_root / "aops-core"
        data_dir = tmp_path / "data"
        hooks_dir = aops_core / "hooks"
        aops_root.mkdir()
        aops_core.mkdir()
        hooks_dir.mkdir()
        data_dir.mkdir()

        hook_script = hooks_dir / "test_hook.py"
        hook_script.touch()

        monkeypatch.setenv("AOPS", str(aops_root))
        monkeypatch.setenv("ACA_DATA", str(data_dir))
        # Patch get_plugin_root to return our temp path
        monkeypatch.setattr("lib.paths.get_plugin_root", lambda: aops_core)

        # Act
        writing_root_result = get_writing_root()
        bots_dir_result = get_bots_dir()
        data_dir_result = get_data_dir()
        hooks_dir_result = get_hooks_dir()
        hook_script_result = get_hook_script("test_hook.py")

        # Assert
        assert isinstance(writing_root_result, Path), "get_writing_root must return Path"
        assert isinstance(bots_dir_result, Path), "get_bots_dir must return Path"
        assert isinstance(data_dir_result, Path), "get_data_dir must return Path"
        assert isinstance(hooks_dir_result, Path), "get_hooks_dir must return Path"
        assert isinstance(hook_script_result, Path), "get_hook_script must return Path"

        # Ensure they're not strings
        assert not isinstance(writing_root_result, str)
        assert not isinstance(bots_dir_result, str)
        assert not isinstance(data_dir_result, str)
        assert not isinstance(hooks_dir_result, str)
        assert not isinstance(hook_script_result, str)
