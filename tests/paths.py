#!/usr/bin/env python3
"""
Path resolution module for tests - delegates to lib.paths.

This module exists for backwards compatibility with tests that import from tests.paths.
All functionality delegates to lib.paths which uses AOPS and ACA_DATA environment variables.
"""

import sys
from pathlib import Path

# Ensure academicOps is on path for lib imports
_aops_root = Path(__file__).parent.parent
if str(_aops_root) not in sys.path:
    sys.path.insert(0, str(_aops_root))

from lib.paths import (
    get_aops_root as get_bots_dir,  # Framework root IS the old bots dir
    get_data_root as get_data_dir,
    get_hooks_dir,
)

# Aliases for writing-related paths
get_writing_root = get_bots_dir  # Writing root points to framework root


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
    "get_writing_root",
]
