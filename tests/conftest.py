"""Pytest fixtures for aOps framework tests.

Provides fixtures for common paths and test setup.
All paths resolve using AOPS and ACA_DATA environment variables.
"""

from pathlib import Path

import pytest

from .paths import get_bots_dir, get_data_dir, get_hooks_dir, get_writing_root


@pytest.fixture
def writing_root() -> Path:
    """Return Path to framework root (AOPS).

    Legacy alias - actually returns framework root, not writing repo.

    Returns:
        Path: Absolute path to framework root ($AOPS)
    """
    return get_writing_root()


@pytest.fixture
def bots_dir() -> Path:
    """Return Path to framework root (AOPS).

    Legacy alias - framework root is the old "bots" directory.

    Returns:
        Path: Absolute path to framework root ($AOPS)
    """
    return get_bots_dir()


@pytest.fixture
def data_dir() -> Path:
    """Return Path to data directory (ACA_DATA).

    Returns:
        Path: Absolute path to data directory ($ACA_DATA)
    """
    return get_data_dir()


@pytest.fixture
def hooks_dir() -> Path:
    """Return Path to hooks directory.

    Returns:
        Path: Absolute path to hooks/ directory ($AOPS/hooks)
    """
    return get_hooks_dir()


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory structure for task tests.

    Creates the standard task directory structure in a temp location.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path: Path to the temporary data directory
    """
    data_dir = tmp_path / "data"
    (data_dir / "tasks/inbox").mkdir(parents=True)
    (data_dir / "tasks/queue").mkdir(parents=True)
    (data_dir / "tasks/archived").mkdir(parents=True)
    return data_dir
