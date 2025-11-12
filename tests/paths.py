#!/usr/bin/env python3
"""
Path resolution module for writing/bots framework.

Provides functions to locate the writing repository root and its key subdirectories.
Supports both environment variable configuration and automatic discovery.
"""

import os
from pathlib import Path


def get_writing_root() -> Path:
    """
    Return the writing repository root directory.

    Resolution order:
    1. WRITING_ROOT environment variable (if set and valid)
    2. Discover from __file__ location by traversing up

    Returns:
        Path: Absolute path to writing repository root

    Raises:
        RuntimeError: If WRITING_ROOT is set but invalid, or if root cannot be determined
    """
    # Check environment variable first
    env_root = os.environ.get("WRITING_ROOT")
    if env_root is not None:
        root_path = Path(env_root)
        if not root_path.exists():
            msg = f"WRITING_ROOT env var set but path doesn't exist: {root_path}"
            raise RuntimeError(msg)
        return root_path

    # Fallback: discover from __file__ location
    # Traverse up directory tree looking for README.md and bots/ markers
    current_file = Path(__file__).resolve()

    # Try to find writing root by looking for README.md marker
    current_dir = current_file.parent
    for _ in range(5):  # Reasonable depth limit
        if (current_dir / "README.md").exists() and (current_dir / "bots").exists():
            return current_dir
        current_dir = current_dir.parent
        if current_dir == current_dir.parent:  # Reached filesystem root
            break

    msg = (
        "Cannot determine writing root: WRITING_ROOT env var not set and "
        "could not discover from file location"
    )
    raise RuntimeError(msg)


def get_bots_dir() -> Path:
    """
    Return the bots/ directory.

    Returns:
        Path: Absolute path to writing/bots/

    Raises:
        RuntimeError: If bots/ directory doesn't exist
    """
    bots_dir = get_writing_root() / "bots"
    if not bots_dir.exists():
        msg = f"Bots directory doesn't exist: {bots_dir}"
        raise RuntimeError(msg)
    return bots_dir


def get_data_dir() -> Path:
    """
    Return the data/ directory.

    Returns:
        Path: Absolute path to writing/data/

    Raises:
        RuntimeError: If data/ directory doesn't exist
    """
    data_dir = get_writing_root() / "data"
    if not data_dir.exists():
        msg = f"Data directory doesn't exist: {data_dir}"
        raise RuntimeError(msg)
    return data_dir


def get_hooks_dir() -> Path:
    """
    Return the bots/hooks/ directory.

    Returns:
        Path: Absolute path to writing/bots/hooks/

    Raises:
        RuntimeError: If hooks/ directory doesn't exist
    """
    hooks_dir = get_bots_dir() / "hooks"
    if not hooks_dir.exists():
        msg = f"Hooks directory doesn't exist: {hooks_dir}"
        raise RuntimeError(msg)
    return hooks_dir


def get_hook_script(name: str) -> Path:
    """
    Return path to a specific hook script.

    Args:
        name: Hook script filename (e.g., "session_start.py")

    Returns:
        Path: Absolute path to the hook script

    Raises:
        RuntimeError: If hook script doesn't exist
    """
    hook_path = get_hooks_dir() / name
    if not hook_path.exists():
        msg = f"Hook script not found: {hook_path}"
        raise RuntimeError(msg)
    return hook_path
