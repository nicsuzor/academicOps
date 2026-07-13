#!/usr/bin/env python3
"""
Path resolution for tests — self-contained.

Previously delegated to ``lib.paths``, which was removed when ``aops-core`` was
folded into ``aops/``. These helpers replicate the old ``lib.paths`` semantics
directly from the repo layout and the ``ACA_DATA`` environment variable, so the
test harness no longer depends on the deleted ``lib`` package.
"""

import os
from pathlib import Path

# Repo root is the parent of tests/; the plugin source lives at <repo>/aops
# (formerly the separate aops-core plugin).
_repo_root = Path(__file__).resolve().parent.parent
_plugin_root = _repo_root / "aops"


def get_plugin_root() -> Path:
    """Framework plugin root (``<repo>/aops`` — formerly ``aops-core``)."""
    return _plugin_root


def get_bots_dir() -> Path:
    """Framework root (alias of the plugin root; the old "bots" dir)."""
    return _plugin_root


def get_data_dir() -> Path:
    """Shared data vault root (``$ACA_DATA``).

    Raises:
        RuntimeError: if ``ACA_DATA`` is unset or the path doesn't exist.
    """
    data = os.environ.get("ACA_DATA")
    if not data:
        raise RuntimeError(
            "ACA_DATA environment variable not set.\n"
            "Add to ~/.bashrc or ~/.zshrc:\n"
            "  export ACA_DATA='$HOME/writing/data'"
        )
    path = Path(data).resolve()
    if not path.exists():
        raise RuntimeError(f"ACA_DATA path doesn't exist: {path}")
    return path


def get_hooks_dir() -> Path:
    """Hooks directory (``plugin_root/hooks``)."""
    return _plugin_root / "hooks"


# Writing root historically aliased the framework root.
get_writing_root = get_bots_dir


def get_repo_root() -> Path:
    """Repository root (parent of the plugin).

    GitHub workflows and other repo-level files live here, not in the plugin.
    """
    return _repo_root


def get_hook_script(name: str) -> Path:
    """Return the path to a specific hook script.

    Args:
        name: Hook script filename (e.g., "router.py").

    Raises:
        RuntimeError: If the hook script doesn't exist.
    """
    hook_path = get_hooks_dir() / name
    if not hook_path.exists():
        msg = f"Hook script not found: {hook_path}"
        raise RuntimeError(msg)
    return hook_path


__all__ = [
    "get_bots_dir",
    "get_data_dir",
    "get_hook_script",
    "get_hooks_dir",
    "get_plugin_root",
    "get_repo_root",
    "get_writing_root",
]
