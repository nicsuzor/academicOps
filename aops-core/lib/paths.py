#!/usr/bin/env python3
"""
Path resolution for aOps framework (fail-fast, no fallbacks).

Required environment variables:
- $AOPS: Framework root
- $ACA_DATA: User data directory
"""

from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


def get_aops_root() -> Path:
    """
    Get framework root directory (fail-fast).

    Returns:
        Path: Absolute path to aOps framework root

    Raises:
        RuntimeError: If $AOPS not set or invalid
    """
    aops = os.environ.get("AOPS")
    if not aops:
        raise RuntimeError(
            "$AOPS environment variable not set.\n"
            "Run: ./setup.sh  or  export AOPS='/path/to/aOps'"
        )

    aops_path = Path(aops).resolve()
    if not aops_path.exists():
        raise RuntimeError(f"$AOPS path doesn't exist: {aops_path}")
    # v1.0: lib/ moved into aops-core plugin
    if not (aops_path / "aops-core").is_dir():
        raise RuntimeError(
            f"$AOPS doesn't look like aOps framework (missing aops-core/): {aops_path}"
        )

    return aops_path


def get_data_root() -> Path:
    """
    Get shared memory vault root.

    Returns:
        Path: Absolute path to data directory ($ACA_DATA)

    Raises:
        RuntimeError: If ACA_DATA environment variable not set or path doesn't exist
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


# Framework component directories


def get_skills_dir() -> Path:
    """Get skills directory ($AOPS/aops-core/skills)."""
    return get_aops_root() / "aops-core" / "skills"


def get_hooks_dir() -> Path:
    """Get hooks directory ($AOPS/aops-core/hooks)."""
    return get_aops_root() / "aops-core" / "hooks"


def get_commands_dir() -> Path:
    """Get commands directory ($AOPS/aops-core/commands)."""
    return get_aops_root() / "aops-core" / "commands"


def get_tests_dir() -> Path:
    """Get tests directory ($AOPS/tests)."""
    return get_aops_root() / "tests"


def get_config_dir() -> Path:
    """Get config directory ($AOPS/config)."""
    return get_aops_root() / "config"


def get_workflows_dir() -> Path:
    """Get workflows directory ($AOPS/workflows)."""
    return get_aops_root() / "workflows"


# Data directories


def get_sessions_dir() -> Path:
    """Get sessions directory (sibling of $ACA_DATA, not inside it)."""
    return get_data_root().parent / "sessions"


def get_projects_dir() -> Path:
    """Get projects directory ($ACA_DATA/projects)."""
    return get_data_root() / "projects"


def get_logs_dir() -> Path:
    """Get logs directory ($ACA_DATA/logs)."""
    return get_data_root() / "logs"


def get_context_dir() -> Path:
    """Get context directory ($ACA_DATA/context)."""
    return get_data_root() / "context"


def get_goals_dir() -> Path:
    """Get goals directory ($ACA_DATA/goals)."""
    return get_data_root() / "goals"


# Validation utilities


def validate_environment() -> dict[str, Path]:
    """
    Validate that all required environment variables are set and paths exist.

    Returns:
        dict: Dictionary mapping variable names to resolved paths

    Raises:
        RuntimeError: If any required environment variable is missing or invalid
    """
    return {
        "AOPS": get_aops_root(),
        "ACA_DATA": get_data_root(),
    }


def print_environment() -> None:
    """Print current environment configuration."""
    try:
        env = validate_environment()
        print("aOps Environment Configuration:")
        print(f"  AOPS:     {env['AOPS']}")
        print(f"  ACA_DATA: {env['ACA_DATA']}")
        print("\nFramework directories:")
        print(f"  Skills:   {get_skills_dir()}")
        print(f"  Hooks:    {get_hooks_dir()}")
        print(f"  Commands: {get_commands_dir()}")
        print(f"  Tests:    {get_tests_dir()}")
        print("\nData directories:")
        print(f"  Sessions: {get_sessions_dir()}")
        print(f"  Projects: {get_projects_dir()}")
        print(f"  Logs:     {get_logs_dir()}")
    except RuntimeError as e:
        print(f"Environment validation failed: {e}")
        raise


# External binary resolution


@lru_cache(maxsize=8)
def resolve_binary(name: str) -> Path | None:
    """
    Resolve an external binary to its absolute path with caching.

    Uses shutil.which() to find the binary in PATH, then validates it exists
    and is executable. Results are cached to avoid repeated lookups.

    Args:
        name: Binary name to resolve (e.g., 'bd', 'git')

    Returns:
        Path: Absolute path to the binary if found and executable
        None: If binary not found or not executable

    Note:
        Logs a warning at DEBUG level if binary not found.
        This function intentionally returns None rather than raising
        to support graceful degradation for optional dependencies.
    """
    binary_path = shutil.which(name)
    if binary_path is None:
        logger.debug(f"Binary '{name}' not found in PATH")
        return None

    resolved = Path(binary_path).resolve()
    if not resolved.is_file():
        logger.debug(f"Binary '{name}' resolved to non-file: {resolved}")
        return None

    if not os.access(resolved, os.X_OK):
        logger.debug(f"Binary '{name}' not executable: {resolved}")
        return None

    logger.debug(f"Binary '{name}' resolved to: {resolved}")
    return resolved


def get_bd_path() -> Path | None:
    """
    DEPRECATED: bd CLI is replaced by tasks MCP.

    Use mcp__plugin_aops-core_tasks__* functions instead.
    This function is kept for backwards compatibility but will be removed.

    Returns:
        Path: Absolute path to bd binary if found (deprecated)
        None: If bd not installed or not in PATH
    """
    import warnings
    warnings.warn(
        "get_bd_path() is deprecated. Use tasks MCP functions instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return resolve_binary("bd")


if __name__ == "__main__":
    print_environment()
