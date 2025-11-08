#!/usr/bin/env python3
"""
Path resolution for tests - loads from paths.toml as single source of truth.

This module provides standardized path resolution for all tests,
using paths.toml as the authoritative configuration.
"""

import os
import tomllib
from pathlib import Path


def get_aops_root() -> Path:
    """
    Get aOps framework repository root.

    Tries in order:
    1. $AOPS environment variable
    2. Parent directory of tests/ (for local testing)

    Raises:
        RuntimeError: If AOPS cannot be determined
    """
    # Try environment variable first
    if aops_env := os.getenv("AOPS"):
        path = Path(aops_env)
        if path.exists():
            return path
        raise RuntimeError(f"AOPS env var set but path doesn't exist: {aops_env}")

    # Fall back to parent of tests/ directory
    tests_dir = Path(__file__).parent
    aops_root = tests_dir.parent

    if (aops_root / "paths.toml").exists():
        return aops_root

    raise RuntimeError(
        "Cannot determine AOPS root. Set $AOPS environment variable "
        "or run tests from within aOps repository."
    )


def get_aca_root() -> Path:
    """
    Get user's personal workspace root.

    Tries in order:
    1. $ACA environment variable
    2. Parent directory of AOPS (assumes aOps is submodule)

    Raises:
        RuntimeError: If ACA cannot be determined
    """
    # Try environment variable first
    if aca_env := os.getenv("ACA"):
        path = Path(aca_env)
        if path.exists():
            return path
        raise RuntimeError(f"ACA env var set but path doesn't exist: {aca_env}")

    # Fall back to parent of AOPS (assumes aOps is submodule)
    aops_root = get_aops_root()
    aca_root = aops_root.parent

    if aca_root.exists():
        return aca_root

    raise RuntimeError(
        "Cannot determine ACA root. Set $ACA environment variable "
        "or ensure aOps is a subdirectory of your workspace."
    )


def load_paths_config() -> dict:
    """
    Load paths.toml configuration.

    Returns:
        dict: Parsed TOML configuration

    Raises:
        RuntimeError: If paths.toml cannot be found or parsed
    """
    aops_root = get_aops_root()
    paths_file = aops_root / "paths.toml"

    if not paths_file.exists():
        raise RuntimeError(f"paths.toml not found at {paths_file}")

    try:
        with paths_file.open("rb") as f:
            return tomllib.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to parse paths.toml: {e}") from e


def get_hooks_dir() -> Path:
    """Get hooks directory path."""
    return get_aops_root() / "hooks"


def get_skills_dir() -> Path:
    """Get skills directory path."""
    return get_aops_root() / "skills"


def get_scripts_dir() -> Path:
    """Get scripts directory path."""
    return get_aops_root() / "scripts"


def get_tests_dir() -> Path:
    """Get tests directory path."""
    return get_aops_root() / "tests"


def get_data_dir() -> Path:
    """Get user data directory path."""
    return get_aca_root() / "data"


def get_hook_script(hook_name: str) -> Path:
    """
    Get path to a hook script.

    Args:
        hook_name: Name of hook file (e.g., "validate_tool.py")

    Returns:
        Path to hook script

    Raises:
        RuntimeError: If hook script doesn't exist
    """
    hook_path = get_hooks_dir() / hook_name

    if not hook_path.exists():
        raise RuntimeError(f"Hook script not found: {hook_path}")

    return hook_path


# Convenience exports for common paths
AOPS_ROOT = None  # Lazy-loaded on first access
ACA_ROOT = None  # Lazy-loaded on first access


def _ensure_roots_loaded():
    """Ensure AOPS_ROOT and ACA_ROOT are loaded."""
    global AOPS_ROOT, ACA_ROOT
    if AOPS_ROOT is None:
        AOPS_ROOT = get_aops_root()
    if ACA_ROOT is None:
        ACA_ROOT = get_aca_root()


# Export functions for pytest fixtures to use
__all__ = [
    "get_aops_root",
    "get_aca_root",
    "load_paths_config",
    "get_hooks_dir",
    "get_skills_dir",
    "get_scripts_dir",
    "get_tests_dir",
    "get_data_dir",
    "get_hook_script",
]
