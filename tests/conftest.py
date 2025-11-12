"""Pytest fixtures for bots framework tests.

Provides fixtures for common paths and test setup.
"""

from pathlib import Path

import pytest

from .paths import get_bots_dir, get_data_dir, get_hooks_dir, get_writing_root


@pytest.fixture
def writing_root() -> Path:
    """Return Path to writing repository root.

    Returns:
        Path: Absolute path to repository root
    """
    return get_writing_root()


@pytest.fixture
def bots_dir() -> Path:
    """Return Path to bots/ directory.

    Returns:
        Path: Absolute path to bots/ directory
    """
    return get_bots_dir()


@pytest.fixture
def data_dir() -> Path:
    """Return Path to data/ directory.

    Returns:
        Path: Absolute path to data/ directory
    """
    return get_data_dir()


@pytest.fixture
def hooks_dir() -> Path:
    """Return Path to bots/hooks/ directory.

    Returns:
        Path: Absolute path to bots/hooks/ directory
    """
    return get_hooks_dir()
