#!/usr/bin/env python3
"""
Path resolution module for tests - delegates to lib.paths.

This module exists for backwards compatibility with tests that import from tests.paths.
All functionality delegates to lib.paths which uses AOPS and ACA_DATA environment variables.
"""

from pathlib import Path

from lib.paths import (
    get_aops_root as get_bots_dir,  # Framework root IS the old bots dir
    get_data_root as get_data_dir,
    get_hooks_dir,
)


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


__all__ = [
    "get_bots_dir",
    "get_data_dir",
    "get_hooks_dir",
    "get_hook_script",
]
