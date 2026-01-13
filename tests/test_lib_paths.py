#!/usr/bin/env python3
"""Tests for lib/paths.py module."""

import os
import pytest
from pathlib import Path

# Add lib to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import paths


class TestPathResolution:
    """Test path resolution functions."""

    def test_get_aops_root_requires_env_var(self, monkeypatch):
        """Test that get_aops_root fails without AOPS env var (fail-fast per AXIOMS #7)."""
        monkeypatch.delenv("AOPS", raising=False)

        # Should fail fast - no auto-detection, explicit config required
        with pytest.raises(RuntimeError, match="AOPS environment variable not set"):
            paths.get_aops_root()

    def test_get_aops_root_uses_valid_aops_if_set(self, monkeypatch, tmp_path):
        """Test that get_aops_root respects valid AOPS env var."""
        test_dir = tmp_path / "aops"
        test_dir.mkdir()
        (test_dir / "aops-core").mkdir()  # v1.0: validation checks for aops-core/
        monkeypatch.setenv("AOPS", str(test_dir))

        result = paths.get_aops_root()

        assert isinstance(result, Path)
        assert result == test_dir.resolve()

    def test_get_aops_root_fails_on_invalid_aops(self, monkeypatch, tmp_path):
        """Test that get_aops_root fails fast if AOPS is explicitly set but invalid (AXIOMS #7)."""
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setenv("AOPS", str(nonexistent))

        # Should fail fast (not fall back) when AOPS explicitly set to invalid path
        with pytest.raises(RuntimeError, match="AOPS path doesn't exist"):
            paths.get_aops_root()

    def test_get_data_root_requires_env_var(self, monkeypatch):
        """Test that get_data_root fails without ACA_DATA env var."""
        monkeypatch.delenv("ACA_DATA", raising=False)

        with pytest.raises(RuntimeError, match="ACA_DATA environment variable not set"):
            paths.get_data_root()

    def test_get_data_root_validates_path_exists(self, monkeypatch, tmp_path):
        """Test that get_data_root fails if path doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setenv("ACA_DATA", str(nonexistent))

        with pytest.raises(RuntimeError, match="ACA_DATA path doesn't exist"):
            paths.get_data_root()

    def test_get_data_root_returns_path(self, monkeypatch, tmp_path):
        """Test that get_data_root returns valid Path."""
        test_dir = tmp_path / "data"
        test_dir.mkdir()
        monkeypatch.setenv("ACA_DATA", str(test_dir))

        result = paths.get_data_root()

        assert isinstance(result, Path)
        assert result == test_dir.resolve()

    def test_get_skills_dir(self, monkeypatch, tmp_path):
        """Test that get_skills_dir returns AOPS/aops-core/skills."""
        test_dir = tmp_path / "aops"
        test_dir.mkdir()
        (test_dir / "aops-core").mkdir()  # v1.0: validation checks for aops-core/
        monkeypatch.setenv("AOPS", str(test_dir))

        result = paths.get_skills_dir()

        assert result == test_dir / "aops-core" / "skills"

    def test_get_tasks_dir(self, monkeypatch, tmp_path):
        """Test that get_tasks_dir returns ACA_DATA/tasks."""
        test_dir = tmp_path / "data"
        test_dir.mkdir()
        monkeypatch.setenv("ACA_DATA", str(test_dir))

        result = paths.get_tasks_dir()

        assert result == test_dir / "tasks"

    def test_validate_environment_success(self, monkeypatch, tmp_path):
        """Test validate_environment with valid setup."""
        aops_dir = tmp_path / "aops"
        data_dir = tmp_path / "data"
        aops_dir.mkdir()
        (aops_dir / "aops-core").mkdir()  # v1.0: validation checks for aops-core/
        data_dir.mkdir()

        monkeypatch.setenv("AOPS", str(aops_dir))
        monkeypatch.setenv("ACA_DATA", str(data_dir))

        result = paths.validate_environment()

        assert "AOPS" in result
        assert "ACA_DATA" in result
        assert result["AOPS"] == aops_dir.resolve()
        assert result["ACA_DATA"] == data_dir.resolve()

    def test_validate_environment_fails_without_aops(self, monkeypatch, tmp_path):
        """Test validate_environment fails without AOPS (fail-fast per AXIOMS #7)."""
        monkeypatch.delenv("AOPS", raising=False)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setenv("ACA_DATA", str(data_dir))

        # Should fail fast - no auto-detection
        with pytest.raises(RuntimeError, match="AOPS environment variable not set"):
            paths.validate_environment()


class TestRealEnvironment:
    """Tests using actual environment (skipped if not set up)."""

    @pytest.mark.skipif(
        not os.environ.get("AOPS"), reason="AOPS environment variable not set"
    )
    def test_real_aops_root(self):
        """Test get_aops_root with real environment."""
        result = paths.get_aops_root()

        assert result.exists()
        assert result.is_dir()
        assert (result / "AXIOMS.md").exists()

    @pytest.mark.skipif(
        not os.environ.get("ACA_DATA"), reason="ACA_DATA environment variable not set"
    )
    def test_real_data_root(self):
        """Test get_data_root with real environment."""
        result = paths.get_data_root()

        assert result.exists()
        assert result.is_dir()
        assert (result / "tasks").exists()
