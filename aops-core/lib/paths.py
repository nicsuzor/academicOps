#!/usr/bin/env python3
"""
Path resolution for aOps framework (fail-fast, no fallbacks).

Required environment variables:
- $AOPS: Framework root
- $ACA_DATA: User data directory
"""

from __future__ import annotations

import os
from pathlib import Path


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


# Data directories


def get_tasks_dir() -> Path:
    """Get tasks directory ($ACA_DATA/tasks)."""
    return get_data_root() / "tasks"


def get_sessions_dir() -> Path:
    """Get sessions directory ($ACA_DATA/sessions)."""
    return get_data_root() / "sessions"


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


# Task subdirectories


def get_tasks_inbox_dir() -> Path:
    """Get tasks inbox directory ($ACA_DATA/tasks/inbox)."""
    return get_tasks_dir() / "inbox"


def get_tasks_completed_dir() -> Path:
    """Get tasks completed directory ($ACA_DATA/tasks/completed)."""
    return get_tasks_dir() / "completed"


def get_tasks_archived_dir() -> Path:
    """Get tasks archived directory ($ACA_DATA/tasks/archived)."""
    return get_tasks_dir() / "archived"


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
        print(f"  Tasks:    {get_tasks_dir()}")
        print(f"  Sessions: {get_sessions_dir()}")
        print(f"  Projects: {get_projects_dir()}")
        print(f"  Logs:     {get_logs_dir()}")
    except RuntimeError as e:
        print(f"Environment validation failed: {e}")
        raise


if __name__ == "__main__":
    print_environment()
