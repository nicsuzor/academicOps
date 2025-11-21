#!/usr/bin/env python3
"""
Path resolution module for aOps framework.

Provides robust path resolution with automatic framework detection:
- $AOPS: Framework root (preferred if set correctly)
- $ACA_DATA: Shared memory vault (required for data access)

AOPS Resolution Strategy (fail-fast when explicitly set):
1. Use $AOPS if set (fail immediately if invalid - AXIOMS #5)
2. Auto-detect from module location (only if $AOPS not set)
3. Check common installation locations (only if $AOPS not set)
4. Auto-set $AOPS when detected

ACA_DATA Resolution (fail-fast):
- Must be explicitly set (no auto-detection for user data)
"""

from __future__ import annotations

import os
from pathlib import Path


def get_aops_root() -> Path:
    """
    Get framework root directory with fail-fast validation.

    Resolution strategy:
    1. Use $AOPS if set (fail immediately if invalid - AXIOMS #5)
    2. Detect from this module's location if $AOPS not set (lib/ -> parent)
    3. Check common known locations if $AOPS not set
    4. Fail with clear error if none found

    Once found, sets $AOPS for consistency.

    Returns:
        Path: Absolute path to aOps framework root

    Raises:
        RuntimeError: If framework directory cannot be found
    """
    # Try $AOPS if set (fail-fast if invalid - AXIOMS #5)
    if aops := os.environ.get("AOPS"):
        aops_path = Path(aops).resolve()
        if not aops_path.exists():
            raise RuntimeError(
                f"$AOPS is set but path doesn't exist: {aops_path}\n"
                f"Fix by setting AOPS to valid path or unsetting it."
            )
        if not (aops_path / "lib").is_dir():
            raise RuntimeError(
                f"$AOPS is set but doesn't look like aOps framework (missing lib/): {aops_path}\n"
                f"Fix by setting AOPS to framework root or unsetting it."
            )
        return aops_path

    # Detect from this module's location (lib/paths.py -> lib/ -> framework root)
    module_path = Path(__file__).parent  # lib/
    framework_root = module_path.parent  # framework root
    if (framework_root / "lib").is_dir() and (framework_root / "hooks").is_dir():
        # Set AOPS for consistency with other code
        os.environ["AOPS"] = str(framework_root.resolve())
        return framework_root.resolve()

    # Check common known locations
    for candidate in [
        Path.home() / "src" / "aOps",
        Path.home() / "src" / "academicOps",
    ]:
        if candidate.is_dir() and (candidate / "lib").is_dir():
            os.environ["AOPS"] = str(candidate.resolve())
            return candidate.resolve()

    # Failed to find framework
    raise RuntimeError(
        "Cannot locate aOps framework directory.\n"
        f"  Tried:\n"
        f"    - $AOPS: {os.environ.get('AOPS', '<not set>')}\n"
        f"    - Module location: {module_path.parent}\n"
        f"    - {Path.home() / 'src' / 'aOps'}\n"
        f"    - {Path.home() / 'src' / 'academicOps'}\n"
        f"  Fix by setting AOPS:\n"
        f"    export AOPS='/path/to/aOps'"
    )


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
    """Get skills directory ($AOPS/skills)."""
    return get_aops_root() / "skills"


def get_hooks_dir() -> Path:
    """Get hooks directory ($AOPS/hooks)."""
    return get_aops_root() / "hooks"


def get_commands_dir() -> Path:
    """Get commands directory ($AOPS/commands)."""
    return get_aops_root() / "commands"


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
