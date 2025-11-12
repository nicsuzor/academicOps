#!/usr/bin/env python3
"""
Tests for monorepo path resolution in writing/bots framework.

Tests the core path resolution functions that locate the writing repository
root and its key subdirectories. These functions are critical for enabling
the bots framework to work correctly in a monorepo structure.
"""

from pathlib import Path

import pytest

from bots.tests.paths import (
    get_bots_dir,
    get_data_dir,
    get_hook_script,
    get_hooks_dir,
    get_writing_root,
)


class TestGetWritingRoot:
    """Tests for get_writing_root() function."""

    def test_get_writing_root_from_env(self, tmp_path, monkeypatch):
        """Test get_writing_root() with WRITING_ROOT env var set."""
        # Arrange
        writing_root = tmp_path / "writing"
        writing_root.mkdir()
        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

        # Act
        result = get_writing_root()

        # Assert
        assert result == writing_root
        assert isinstance(result, Path)

    def test_get_writing_root_without_env(self, tmp_path, monkeypatch):
        """Test get_writing_root() discovering from __file__ location."""
        # Arrange - Create directory structure: writing/bots/tests/
        writing_root = tmp_path / "writing"
        bots_dir = writing_root / "bots"
        tests_dir = bots_dir / "tests"
        tests_dir.mkdir(parents=True)

        # Create marker file to identify writing root
        (writing_root / "README.md").touch()

        # Unset environment variable
        monkeypatch.delenv("WRITING_ROOT", raising=False)

        # Mock __file__ to point to our temporary structure
        import bots.tests.paths as paths_module

        fake_paths_file = tests_dir / "paths.py"
        monkeypatch.setattr(paths_module, "__file__", str(fake_paths_file))

        # Act
        result = get_writing_root()

        # Assert
        assert result == writing_root
        assert isinstance(result, Path)

    def test_get_writing_root_fails_with_invalid_env(self, monkeypatch):
        """Test RuntimeError when WRITING_ROOT points to non-existent path."""
        # Arrange
        monkeypatch.setenv("WRITING_ROOT", "/nonexistent/path")

        # Act & Assert
        with pytest.raises(
            RuntimeError,
            match="WRITING_ROOT env var set but path doesn't exist",
        ):
            get_writing_root()

    def test_get_writing_root_fails_without_context(self, monkeypatch):
        """Test RuntimeError when can't determine root."""
        # Arrange - Unset env var and no way to discover
        monkeypatch.delenv("WRITING_ROOT", raising=False)

        # Mock __file__ to point to a location without README.md/bots markers
        import bots.tests.paths as paths_module

        fake_paths_file = Path("/tmp/nowhere/paths.py")
        monkeypatch.setattr(paths_module, "__file__", str(fake_paths_file))

        # Act & Assert
        with pytest.raises(
            RuntimeError,
            match="Cannot determine writing root",
        ):
            get_writing_root()


class TestGetBotsDir:
    """Tests for get_bots_dir() function."""

    def test_get_bots_dir(self, tmp_path, monkeypatch):
        """Test get_bots_dir() returns writing_root / 'bots'."""
        # Arrange
        writing_root = tmp_path / "writing"
        bots_dir = writing_root / "bots"
        writing_root.mkdir()
        bots_dir.mkdir()
        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

        # Act
        result = get_bots_dir()

        # Assert
        assert result == bots_dir
        assert isinstance(result, Path)


class TestGetDataDir:
    """Tests for get_data_dir() function."""

    def test_get_data_dir(self, tmp_path, monkeypatch):
        """Test get_data_dir() returns writing_root / 'data'."""
        # Arrange
        writing_root = tmp_path / "writing"
        data_dir = writing_root / "data"
        writing_root.mkdir()
        data_dir.mkdir()
        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

        # Act
        result = get_data_dir()

        # Assert
        assert result == data_dir
        assert isinstance(result, Path)


class TestGetHooksDir:
    """Tests for get_hooks_dir() function."""

    def test_get_hooks_dir(self, tmp_path, monkeypatch):
        """Test get_hooks_dir() returns bots_dir / 'hooks'."""
        # Arrange
        writing_root = tmp_path / "writing"
        bots_dir = writing_root / "bots"
        hooks_dir = bots_dir / "hooks"
        writing_root.mkdir()
        bots_dir.mkdir()
        hooks_dir.mkdir()
        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

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
        writing_root = tmp_path / "writing"
        bots_dir = writing_root / "bots"
        hooks_dir = bots_dir / "hooks"
        hooks_dir.mkdir(parents=True)

        hook_script = hooks_dir / "session_start.py"
        hook_script.touch()

        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

        # Act
        result = get_hook_script("session_start.py")

        # Assert
        assert result == hook_script
        assert isinstance(result, Path)
        assert result.exists()

    def test_get_hook_script_missing_fails(self, tmp_path, monkeypatch):
        """Test RuntimeError when hook doesn't exist."""
        # Arrange
        writing_root = tmp_path / "writing"
        bots_dir = writing_root / "bots"
        hooks_dir = bots_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

        # Act & Assert
        with pytest.raises(RuntimeError, match="Hook script not found"):
            get_hook_script("nonexistent_hook.py")


class TestPathsUsePathlib:
    """Tests that all path functions return Path objects."""

    def test_paths_use_pathlib(self, tmp_path, monkeypatch):
        """Test all functions return Path objects, not strings."""
        # Arrange
        writing_root = tmp_path / "writing"
        bots_dir = writing_root / "bots"
        data_dir = writing_root / "data"
        hooks_dir = bots_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        data_dir.mkdir()

        hook_script = hooks_dir / "test_hook.py"
        hook_script.touch()

        monkeypatch.setenv("WRITING_ROOT", str(writing_root))

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
