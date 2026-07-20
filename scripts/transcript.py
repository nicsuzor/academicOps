#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

# Ensure workspace and library directories are on Python path
SCRIPT_DIR = Path(__file__).parent.resolve()
WORKSPACE_ROOT = SCRIPT_DIR.parent.resolve()
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "aops" / "lib"))

from transcripts.domain.pipeline import run_batch_pipeline
from transcripts.domain.sync import git_sync


def main():
    parser = argparse.ArgumentParser(
        description="academicOps Transcript Generation & Sync Pipeline"
    )
    parser.add_argument(
        "--recent", action="store_true", help="Only process recent transcripts (last 48 hours)"
    )
    parser.add_argument("--no-sync", action="store_true", help="Skip git push sync step")

    args = parser.parse_args()

    # Read sessions repository directory from environment variable or fallback to ~/src/sessions
    sessions_env = os.environ.get("AOPS_SESSIONS")
    if sessions_env:
        sessions_repo_path = Path(sessions_env)
    else:
        sessions_repo_path = Path.home() / "src" / "sessions"

    print(f"Running transcript pipeline against sessions repo: {sessions_repo_path}")

    # Run the pipeline
    processed_count = run_batch_pipeline(sessions_repo_path, recent_only=args.recent)
    print(f"Successfully processed {processed_count} sessions.")

    # If not skipping sync, make sure git sync runs
    if not args.no_sync:
        print("Running git sync...")
        git_sync(sessions_repo_path)
    else:
        print("Skipping git push sync.")


if __name__ == "__main__":
    main()
