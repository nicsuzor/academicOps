"""Git sync automation for the transcripts sessions repository."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def git_sync_sessions(sessions_dir: Path) -> bool:
    """Git commit and push any new/updated transcripts in the sessions directory."""
    if not sessions_dir.exists():
        logger.warning("Sessions directory %s does not exist, skipping git sync", sessions_dir)
        return False

    if not (sessions_dir / ".git").exists():
        logger.warning(
            "Sessions directory %s is not a git repository, skipping git sync", sessions_dir
        )
        return False

    try:
        # Check if there are any changes (untracked or modified)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=sessions_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            logger.info("No changes to sync in sessions repo")
            return True

        # Git add. Use --ignore-errors so a single bad path (most commonly a
        # stray nested-git checkout left behind by a polecat/agy worker under
        # logs/ — git treats a directory containing its own .git as a broken
        # submodule/gitlink and refuses to add it if that nested repo has no
        # commit checked out) degrades gracefully instead of aborting the
        # entire sync. Everything else still gets staged.
        add_result = subprocess.run(
            ["git", "add", "--ignore-errors", "."],
            cwd=sessions_dir,
            capture_output=True,
            text=True,
        )
        if add_result.returncode != 0:
            logger.warning(
                "git add reported errors on some paths (continuing with what could be staged): %s",
                add_result.stderr.strip(),
            )

        # If nothing actually got staged (e.g. every changed path errored, or
        # the only changes were to paths that failed to add), there's nothing
        # to commit — bail out cleanly rather than creating an empty commit.
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=sessions_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        if not staged.stdout.strip():
            logger.warning(
                "git add staged no files (all changed paths failed to add); skipping commit/push"
            )
            return False

        # Git commit
        commit_msg = "auto: update session transcripts and metadata"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=sessions_dir,
            check=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "aops-bot",
                "GIT_AUTHOR_EMAIL": "aops-bot@users.noreply.github.com",
                "GIT_COMMITTER_NAME": "aops-bot",
                "GIT_COMMITTER_EMAIL": "aops-bot@users.noreply.github.com",
            },
        )

        # Git push
        # In cron, GH_TOKEN is set, and git helper configuration is done.
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=sessions_dir, check=True)
        logger.info("Successfully synced transcripts sessions repo")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Git sync failed: %s\nStdout: %s\nStderr: %s", e, e.stdout, e.stderr)
        return False
