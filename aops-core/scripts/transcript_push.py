#!/usr/bin/env python3
"""
Session Transcript Wrapper with Auto-Commit and Push.

Runs transcript.py to process sessions, then automatically commits and
attempts to push changes in the writing repository.

Usage:
    python aops-core/scripts/transcript_push.py [args for transcript.py]
"""

import subprocess
import sys
from pathlib import Path

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.paths import get_sessions_repo


def run_transcript(args):
    """Run the original transcript.py script."""
    transcript_script = SCRIPT_DIR / "transcript.py"
    cmd = [sys.executable, str(transcript_script)] + args
    print(f"Running transcript generation: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def git_sync():
    """Commit and push changes in the sessions repository."""
    try:
        sessions_root = get_sessions_repo()
        if not (sessions_root / ".git").exists():
            print(f"Skipping git sync: {sessions_root} is not a git repository")
            return

        print(f"Syncing changes in {sessions_root}...")

        subprocess.run(
            ["git", "add", "transcripts/", "summaries/"],
            cwd=str(sessions_root), check=True,
        )

        # Check if there are staged changes to commit
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=str(sessions_root), check=False
        ).returncode

        if status == 0:
            print("No changes to sync.")
            return

        commit_msg = "Auto-commit: session transcripts and insights updated"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(sessions_root), check=True)
        print("Committed changes.")

        # Try to push (non-blocking failure)
        print("Attempting push...")
        push_result = subprocess.run(
            ["git", "push"], cwd=str(sessions_root), capture_output=True, text=True
        )

        if push_result.returncode == 0:
            print("Push successful.")
        else:
            print(f"Push failed (non-blocking):\n{push_result.stderr}")

    except Exception as e:
        print(f"Git sync failed: {e}", file=sys.stderr)


def main():
    # Pass all arguments to transcript.py
    exit_code = run_transcript(sys.argv[1:])

    # Even if transcript.py partially fails, we might still want to sync successful ones.
    # Exit code 0 is full success, exit code 2 is "skipped" (insufficient content).
    if exit_code in (0, 2):
        git_sync()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
