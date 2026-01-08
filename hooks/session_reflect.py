#!/usr/bin/env python3
"""
Stop hook: Synthesize session summary and trigger reflection.

1. Synthesizes task contributions into session summary (no LLM - H31 compliant)
2. Injects instruction for agent to invoke session-insights if needed

Exit codes:
    0: Success (session synthesized, no further action needed)
    1: Warning with reflection instruction (agent should review/enhance)
"""

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any


def synthesize_session_summary(session_id: str, project: str) -> bool:
    """Synthesize task contributions into session summary.

    Args:
        session_id: Session UUID
        project: Project name (extracted from cwd)

    Returns:
        True if summary was created, False if no task contributions exist
    """
    # Import here to avoid issues if lib not in path during hook execution
    try:
        sys.path.insert(0, os.environ.get("AOPS", ""))
        from lib.session_summary import (
            load_task_contributions,
            synthesize_session,
            save_session_summary,
        )
    except ImportError:
        # Library not available - skip synthesis
        return False

    # Check if we have task contributions
    tasks = load_task_contributions(session_id)
    if not tasks:
        return False

    # Synthesize and save
    today = date.today().strftime("%Y-%m-%d")
    summary = synthesize_session(
        session_id,
        project=project,
        date=today,
    )
    save_session_summary(session_id, summary)
    return True


def get_project_from_cwd(cwd: str) -> str:
    """Extract project name from cwd path.

    Args:
        cwd: Current working directory

    Returns:
        Project shortname (last path component)
    """
    if not cwd:
        return "unknown"
    parts = Path(cwd).parts
    return parts[-1] if parts else "unknown"


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Get session info
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")
    cwd = input_data.get("cwd", "")

    # Skip for very short sessions (no transcript)
    if not transcript_path:
        print(json.dumps({}))
        sys.exit(0)

    # Synthesize task contributions into session summary
    project = get_project_from_cwd(cwd)
    summary_created = False
    if session_id:
        try:
            summary_created = synthesize_session_summary(session_id, project)
        except Exception as e:
            # Log error but don't fail the hook
            sys.stderr.write(f"Session synthesis error: {e}\n")

    # Build message for agent
    if summary_created:
        message = (
            "Session summary synthesized from task contributions. "
            "Run `Skill(skill='session-insights', args='current')` "
            "if you want to analyze patterns and update heuristics."
        )
    else:
        message = (
            "No task contributions found for this session. "
            "Consider running `Skill(skill='session-insights', args='current')` "
            "to mine the transcript for accomplishments and learnings."
        )

    output: dict[str, Any] = {
        "reason": message,
        "continue": True,
    }

    print(json.dumps(output))
    sys.exit(1)  # 1 = warn but allow (shows message to agent)


if __name__ == "__main__":
    main()
