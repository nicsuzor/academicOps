#!/usr/bin/env python3
"""
Path resolution for aOps framework (plugin-centric).

Resolves paths relative to this file's location in the aops-core plugin.
Dependency on $AOPS environment variable has been removed.

Required environment variables:
- $ACA_DATA: User data directory (still required for user data)
"""

from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


def get_plugin_root() -> Path:
    """
    Get the root directory of the aops-core plugin.

    Resolution strategy:
    - This file is in <root>/lib/paths.py
    - Root is 2 levels up from this file

    Returns:
        Path: Absolute path to aops-core plugin root
    """
    # this file is at .../aops-core/lib/paths.py
    return Path(__file__).resolve().parent.parent


def get_aops_root() -> Path:
    """
    Get the AOPS root directory (alias for plugin root).

    In plugin-only architecture, this is always the plugin root.
    The $AOPS environment variable is no longer used.
    """
    return get_plugin_root()


def get_bots_dir() -> Path:
    """Alias for get_aops_root."""
    return get_aops_root()


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
# All resolved relative to get_plugin_root()


def get_skills_dir() -> Path:
    """Get skills directory (plugin_root/skills)."""
    return get_plugin_root() / "skills"


def get_hooks_dir() -> Path:
    """Get hooks directory (plugin_root/hooks)."""
    return get_plugin_root() / "hooks"


def get_commands_dir() -> Path:
    """Get commands directory (plugin_root/commands)."""
    return get_plugin_root() / "commands"


def get_tests_dir() -> Path:
    """Get tests directory (plugin_root/tests)."""
    return get_plugin_root() / "tests"


def get_config_dir() -> Path:
    """Get config directory (plugin_root/config)."""
    return get_plugin_root() / "config"


def get_workflows_dir() -> Path:
    """Get workflows directory (plugin_root/workflows)."""
    return get_plugin_root() / "workflows"


def get_indices_dir() -> Path:
    """Get indices directory (plugin_root/indices)."""
    return get_plugin_root() / "indices"


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
    Validate that required environment variables are set and paths exist.

    Returns:
        dict: Dictionary mapping names to resolved paths
    """
    return {
        "PLUGIN_ROOT": get_plugin_root(),
        "ACA_DATA": get_data_root(),
    }


def print_environment() -> None:
    """Print current environment configuration."""
    try:
        env = validate_environment()
        print("aOps Environment Configuration:")
        print(f"  PLUGIN_ROOT: {env['PLUGIN_ROOT']}")
        print(f"  ACA_DATA:    {env['ACA_DATA']}")
        print("\nFramework directories:")
        print(f"  Skills:      {get_skills_dir()}")
        print(f"  Hooks:       {get_hooks_dir()}")
        print(f"  Commands:    {get_commands_dir()}")
        print(f"  Tests:       {get_tests_dir()}")
        print(f"  Workflows:   {get_workflows_dir()}")
        print(f"  Indices:     {get_indices_dir()}")
        print("\nData directories:")
        print(f"  Sessions:    {get_sessions_dir()}")
        print(f"  Projects:    {get_projects_dir()}")
        print(f"  Logs:        {get_logs_dir()}")
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


def get_ntfy_config() -> dict[str, str | bool | int] | None:
    """
    Get ntfy notification configuration from environment variables.

    Configuration is entirely through environment variables (fail-fast pattern).
    If NTFY_TOPIC is not set, returns None (notifications disabled).

    Required env vars (all must be set if notifications are desired):
    - NTFY_TOPIC: The ntfy topic to publish to (e.g., "aops-alerts")
    - NTFY_SERVER: Server URL (e.g., "https://ntfy.sh")
    - NTFY_PRIORITY: Priority 1-5 (e.g., "3")
    - NTFY_TAGS: Comma-separated tags (e.g., "robot,aops")

    Returns:
        dict with config if NTFY_TOPIC is set, None if not set

    Raises:
        RuntimeError: If NTFY_TOPIC is set but other required vars are missing
    """
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        # Notifications disabled - this is the opt-in check
        return None

    # Once opted in via NTFY_TOPIC, all other config is required (fail-fast)
    server = os.environ.get("NTFY_SERVER")
    if not server:
        raise RuntimeError(
            "NTFY_TOPIC is set but NTFY_SERVER is missing.\n"
            "Add to environment:\n"
            "  export NTFY_SERVER='https://ntfy.sh'"
        )

    priority_str = os.environ.get("NTFY_PRIORITY")
    if not priority_str:
        raise RuntimeError(
            "NTFY_TOPIC is set but NTFY_PRIORITY is missing.\n"
            "Add to environment:\n"
            "  export NTFY_PRIORITY='3'"
        )

    tags = os.environ.get("NTFY_TAGS")
    if not tags:
        raise RuntimeError(
            "NTFY_TOPIC is set but NTFY_TAGS is missing.\n"
            "Add to environment:\n"
            "  export NTFY_TAGS='robot,aops'"
        )

    return {
        "enabled": True,
        "topic": topic,
        "server": server,
        "priority": int(priority_str),
        "tags": tags,
    }


if __name__ == "__main__":
    try:
        print_environment()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
