#!/usr/bin/env python3
"""
Generate FRAMEWORK-PATHS.md from paths.py functions.

This script creates a markdown file with resolved absolute paths
for agent consumption during prompt hydration. All paths are expanded
to absolute values at generation time.

Usage:
    python3 aops-core/scripts/generate_framework_paths.py

Exit codes:
    0 - Success
    1 - Error (environment not configured, paths missing, etc.)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add lib to path for imports
script_dir = Path(__file__).parent
lib_dir = script_dir.parent / "lib"
sys.path.insert(0, str(lib_dir))

try:
    from paths import (
        get_aops_root,
        get_data_root,
        get_skills_dir,
        get_hooks_dir,
        get_commands_dir,
        get_tests_dir,
        get_config_dir,
        get_workflows_dir,
        get_sessions_dir,
        get_projects_dir,
        get_logs_dir,
        get_context_dir,
        get_goals_dir,
    )
except ImportError as e:
    print(f"Error: Failed to import from paths.py: {e}", file=sys.stderr)
    print("Make sure you're running from the aOps framework root.", file=sys.stderr)
    sys.exit(1)


def generate_markdown() -> str:
    """
    Generate FRAMEWORK-PATHS.md content from current environment.

    Returns:
        str: Complete markdown content with frontmatter and path tables

    Raises:
        RuntimeError: If environment variables not set or paths invalid
    """
    # Get timestamp
    now = datetime.now(timezone.utc)
    timestamp_iso = now.isoformat()
    timestamp_human = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Get all paths (will raise RuntimeError if env vars missing)
    aops_root = get_aops_root()
    data_root = get_data_root()

    skills_dir = get_skills_dir()
    hooks_dir = get_hooks_dir()
    commands_dir = get_commands_dir()
    tests_dir = get_tests_dir()
    config_dir = get_config_dir()
    workflows_dir = get_workflows_dir()

    tasks_dir = get_tasks_dir()
    sessions_dir = get_sessions_dir()
    projects_dir = get_projects_dir()
    logs_dir = get_logs_dir()
    context_dir = get_context_dir()
    goals_dir = get_goals_dir()

    tasks_inbox_dir = get_tasks_inbox_dir()
    tasks_completed_dir = get_tasks_completed_dir()
    tasks_archived_dir = get_tasks_archived_dir()

    # Build markdown content
    content = f"""---
name: framework-paths
title: Framework Paths (Generated)
category: reference
type: reference
description: Resolved absolute paths for this framework instance (generated from paths.py)
audience: agents
generated: {timestamp_iso}
permalink: framework-paths
tags:
  - framework
  - paths
  - generated
---

# Framework Paths

**⚠️ GENERATED FILE - DO NOT EDIT MANUALLY**

Generated: {timestamp_human}
Source: `aops-core/lib/paths.py`

This file provides resolved absolute paths for agent use during sessions.
All paths are expanded to absolute values at generation time.

## Resolved Paths

These are the concrete absolute paths for this framework instance:

| Path Variable | Resolved Path |
|--------------|---------------|
| $AOPS        | {aops_root}   |
| $ACA_DATA    | {data_root}   |

## Framework Directories

Framework component directories within $AOPS:

| Directory | Absolute Path |
|-----------|---------------|
| Skills    | {skills_dir}  |
| Hooks     | {hooks_dir}   |
| Commands  | {commands_dir} |
| Tests     | {tests_dir}   |
| Config    | {config_dir}  |
| Workflows | {workflows_dir} |

## Data Directories

User data directories within $ACA_DATA:

| Directory | Absolute Path |
|-----------|---------------|
| Tasks     | {tasks_dir}    |
| Sessions  | {sessions_dir} |
| Projects  | {projects_dir} |
| Logs      | {logs_dir}     |
| Context   | {context_dir}  |
| Goals     | {goals_dir}    |

## Task Subdirectories

Task management subdirectories:

| Directory | Absolute Path |
|-----------|---------------|
| Inbox     | {tasks_inbox_dir}     |
| Completed | {tasks_completed_dir} |
| Archived  | {tasks_archived_dir}  |

---

**Generation Command**: `python3 aops-core/scripts/generate_framework_paths.py`

Run this script after changing $AOPS or $ACA_DATA environment variables,
or after modifying the framework directory structure.
"""

    return content


def main() -> int:
    """
    Main entry point - generate and write FRAMEWORK-PATHS.md.

    Returns:
        int: Exit code (0=success, 1=error)
    """
    try:
        # Generate content
        content = generate_markdown()

        # Determine output path (always at framework root)
        output_path = get_aops_root() / "FRAMEWORK-PATHS.md"

        # Write file
        output_path.write_text(content)

        print(f"✓ Generated {output_path}")
        print(f"  Framework root: {get_aops_root()}")
        print(f"  Data root:      {get_data_root()}")

        return 0

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nEnvironment configuration required:", file=sys.stderr)
        print("  1. Run: ./setup.sh", file=sys.stderr)
        print("  2. Or set manually:", file=sys.stderr)
        print("       export AOPS='/path/to/academicOps'", file=sys.stderr)
        print("       export ACA_DATA='/path/to/data'", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
