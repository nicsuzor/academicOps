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
    """Tests for get_writing_root() function."""

    def test_get_writing_root_from_env(self, tmp_path, monkeypatch):
        """Test get_writing_root() with AOPS env var set."""
        # Arrange
        aops_root = tmp_path / "academicOps"
        aops_root.mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))

        # Act
        result = get_writing_root()

        # Assert
        assert result == aops_root
        assert isinstance(result, Path)

    def test_get_writing_root_without_env(self, monkeypatch):
        """Test RuntimeError when AOPS env var not set (fail-fast)."""
        # Arrange - Unset environment variable
        monkeypatch.delenv("AOPS", raising=False)

        # Act & Assert - New implementation is fail-fast, no discovery
        with pytest.raises(
            RuntimeError,
            match="AOPS environment variable not set",
        ):
            get_writing_root()

    def test_get_writing_root_fails_with_invalid_env(self, monkeypatch):
        """Test RuntimeError when AOPS points to non-existent path."""
        # Arrange
        monkeypatch.setenv("AOPS", "/nonexistent/path")

        # Act & Assert
        with pytest.raises(
            RuntimeError,
            match="AOPS path doesn't exist",
        ):
            get_writing_root()

    def test_get_writing_root_fails_without_context(self, monkeypatch):
        """Test RuntimeError when AOPS env var not set (duplicate test for backwards compat)."""
        # Arrange - Unset env var (fail-fast, no discovery in new implementation)
        monkeypatch.delenv("AOPS", raising=False)

        # Act & Assert
        with pytest.raises(
            RuntimeError,
            match="AOPS environment variable not set",
        ):
            get_writing_root()


class TestGetBotsDir:
    """Tests for get_bots_dir() function (backwards compat alias)."""

    def test_get_bots_dir(self, tmp_path, monkeypatch):
        """Test get_bots_dir() returns AOPS root (it's an alias for get_aops_root())."""
        # Arrange - get_bots_dir is now just an alias for get_aops_root()
        aops_root = tmp_path / "academicOps"
        aops_root.mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))

        # Act
        result = get_bots_dir()

        # Assert - Returns framework root (no /bots/ subdirectory)
        assert result == aops_root
        assert isinstance(result, Path)


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
        """Test get_hooks_dir() returns aops_root / 'hooks'."""
        # Arrange - Hooks are now directly under AOPS root
        aops_root = tmp_path / "academicOps"
        hooks_dir = aops_root / "hooks"
        aops_root.mkdir()
        hooks_dir.mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))

        # Act
        result = get_hooks_dir()

        # Assert
        assert result == hooks_dir
        assert isinstance(result, Path)


class TestGetHookScript:
    """Tests for get_hook_script() function."""

    def test_get_hook_script_exists(self, tmp_path, monkeypatch):
        """Test get_hook_script(name) returns correct path for existing hook."""
        # Arrange - Hooks are directly under AOPS/hooks/
        aops_root = tmp_path / "academicOps"
        hooks_dir = aops_root / "hooks"
        hooks_dir.mkdir(parents=True)

        hook_script = hooks_dir / "session_start.py"
        hook_script.touch()

        monkeypatch.setenv("AOPS", str(aops_root))

        # Act
        result = get_hook_script("session_start.py")

        # Assert
        assert result == hook_script
        assert isinstance(result, Path)
        assert result.exists()

    def test_get_hook_script_missing_fails(self, tmp_path, monkeypatch):
        """Test RuntimeError when hook doesn't exist."""
        # Arrange
        aops_root = tmp_path / "academicOps"
        hooks_dir = aops_root / "hooks"
        hooks_dir.mkdir(parents=True)
        monkeypatch.setenv("AOPS", str(aops_root))

        # Act & Assert
        with pytest.raises(RuntimeError, match="Hook script not found"):
            get_hook_script("nonexistent_hook.py")


class TestPathsUsePathlib:
    """Tests that all path functions return Path objects."""

    def test_paths_use_pathlib(self, tmp_path, monkeypatch):
        """Test all functions return Path objects, not strings."""
        # Arrange - Set up both AOPS and ACA_DATA environments
        aops_root = tmp_path / "academicOps"
        data_dir = tmp_path / "data"
        hooks_dir = aops_root / "hooks"
        hooks_dir.mkdir(parents=True)
        data_dir.mkdir()

        hook_script = hooks_dir / "test_hook.py"
        hook_script.touch()

        monkeypatch.setenv("AOPS", str(aops_root))
        monkeypatch.setenv("ACA_DATA", str(data_dir))

        # Act
        writing_root_result = get_writing_root()
        bots_dir_result = get_bots_dir()
        data_dir_result = get_data_dir()
        hooks_dir_result = get_hooks_dir()
        hook_script_result = get_hook_script("test_hook.py")

        # Assert
        assert isinstance(
            writing_root_result, Path
        ), "get_writing_root must return Path"
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
