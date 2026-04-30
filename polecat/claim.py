#!/usr/bin/env python3
"""Polecat claim helpers.

Single canonical claim entrypoint shared between ``polecat run`` and
``polecat start``. Both commands originally inlined the same queue-claim
sequence (look up next ready task, exit 3 on empty queue); this module
holds the canonical implementation.
"""

import sys
from pathlib import Path

# Add aops-core to path for lib imports (mirrors polecat/cli.py).
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT / "aops-core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "aops-core"))


def claim_next_ready(manager, caller: str, project: str | None):
    """Claim the next ready task from the queue.

    Prints activity to stdout. Exits the process with code 3 (queue empty)
    if no ready task is found or the task backend is unavailable. Code 3
    is meaningful to the swarm runner: it treats non-zero as "stop worker"
    but distinguishes "queue empty" from genuine errors.

    Args:
        manager: A ``PolecatManager`` instance.
        caller: Identity to record as the assignee on the claimed task.
        project: Optional project filter; ``None`` claims from any project.

    Returns:
        The claimed task (status now ``in_progress`` in PKB).
    """
    print(f"Looking for ready tasks{' in project ' + project if project else ''}...")
    try:
        task = manager.claim_next_task(caller, project)
    except Exception as e:
        print(f"No ready tasks found (task backend unavailable: {e}).")
        sys.exit(3)  # Exit 3 = queue empty. Swarm treats non-zero as "stop worker".

    if not task:
        print("No ready tasks found.")
        sys.exit(3)  # Exit 3 = queue empty. Swarm treats non-zero as "stop worker".

    return task
