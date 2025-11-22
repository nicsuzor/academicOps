#!/usr/bin/env python3
"""
Tests for path resolution aliases in tests/paths.py.

Tests the legacy alias functions that delegate to lib.paths for backwards
compatibility with tests written for the old monorepo structure.
"""

from pathlib import Path

import pytest

from tests.paths import (
    get_bots_dir,
    get_data_dir,
    get_hook_script,
    get_hooks_dir,
)


class TestGetBotsDir:
    """Tests for get_bots_dir() function (legacy alias for get_aops_root)."""

    def test_get_bots_dir(self, tmp_path, monkeypatch):
        """Test get_bots_dir() returns framework root ($AOPS)."""
        # Arrange
        aops_root = tmp_path / "aOps"
        aops_root.mkdir()
        (aops_root / "lib").mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))

        # Act
        result = get_bots_dir()

        # Assert
        assert result == aops_root
        assert isinstance(result, Path)


class TestGetDataDir:
    """Tests for get_data_dir() function (delegates to get_data_root)."""

    def test_get_data_dir(self, tmp_path, monkeypatch):
        """Test get_data_dir() returns ACA_DATA path."""
        # Arrange
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
        """Test get_hooks_dir() returns AOPS/hooks."""
        # Arrange
        aops_root = tmp_path / "aOps"
        hooks_dir = aops_root / "hooks"
        aops_root.mkdir()
        (aops_root / "lib").mkdir()
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
        # Arrange
        aops_root = tmp_path / "aOps"
        hooks_dir = aops_root / "hooks"
        hooks_dir.mkdir(parents=True)
        (aops_root / "lib").mkdir()

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
        aops_root = tmp_path / "aOps"
        hooks_dir = aops_root / "hooks"
        hooks_dir.mkdir(parents=True)
        (aops_root / "lib").mkdir()
        monkeypatch.setenv("AOPS", str(aops_root))

        # Act & Assert
        with pytest.raises(RuntimeError, match="Hook script not found"):
            get_hook_script("nonexistent_hook.py")


class TestPathsUsePathlib:
    """Tests that all path functions return Path objects."""

    def test_paths_use_pathlib(self, tmp_path, monkeypatch):
        """Test all functions return Path objects, not strings."""
        # Arrange
        aops_root = tmp_path / "aOps"
        hooks_dir = aops_root / "hooks"
        data_dir = tmp_path / "data"
        hooks_dir.mkdir(parents=True)
        (aops_root / "lib").mkdir()
        data_dir.mkdir()

        hook_script = hooks_dir / "test_hook.py"
        hook_script.touch()

        monkeypatch.setenv("AOPS", str(aops_root))
        monkeypatch.setenv("ACA_DATA", str(data_dir))

        # Act
        bots_dir_result = get_bots_dir()
        data_dir_result = get_data_dir()
        hooks_dir_result = get_hooks_dir()
        hook_script_result = get_hook_script("test_hook.py")

        # Assert
        assert isinstance(bots_dir_result, Path), "get_bots_dir must return Path"
        assert isinstance(data_dir_result, Path), "get_data_dir must return Path"
        assert isinstance(hooks_dir_result, Path), "get_hooks_dir must return Path"
        assert isinstance(hook_script_result, Path), "get_hook_script must return Path"

        # Ensure they're not strings
        assert not isinstance(bots_dir_result, str)
        assert not isinstance(data_dir_result, str)
        assert not isinstance(hooks_dir_result, str)
        assert not isinstance(hook_script_result, str)
