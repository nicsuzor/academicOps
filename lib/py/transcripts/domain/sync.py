"""Git sync automation for the transcripts sessions repository."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Both the Mac and the WSL host run this same function against the same
# sessions repo on the same 5-minute cron cadence. A single pull-then-push is
# not enough: host A can pull cleanly, then host B pushes into the gap before
# A's push lands, and A's push is rejected non-fast-forward exactly as if it
# had never pulled at all. Bounded retry closes that window. Kept small and
# fixed (no backoff/sleep) so a contested cycle still finishes well inside the
# 5-minute window the flock single-instance guard in session sync runner allows
# before a slow run costs the next cycle entirely.
_MAX_PUSH_ATTEMPTS = 3

# Commit identity for *every* commit this function creates. That includes the
# merge commit `git pull --no-rebase` writes: cron has no user.name/user.email
# configured, so git refuses to build a merge commit without an identity in the
# environment. Passing this only to `git commit` is the single easiest way to
# ship a pull-before-push fix that still fails in exactly the environment it
# exists for, so both calls read the same constant.
_BOT_IDENTITY = {
    "GIT_AUTHOR_NAME": "aops-bot",
    "GIT_AUTHOR_EMAIL": "aops-bot@users.noreply.github.com",
    "GIT_COMMITTER_NAME": "aops-bot",
    "GIT_COMMITTER_EMAIL": "aops-bot@users.noreply.github.com",
}


def _bot_env() -> dict[str, str]:
    """Process environment plus the aops-bot commit identity."""
    return {**os.environ, **_BOT_IDENTITY}


def _try(args: list[str], cwd: Path) -> bool:
    """Run a git command, swallowing failure. Returns True on exit 0."""
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    return result.returncode == 0


def _resolve_git_dir(sessions_dir: Path) -> Path | None:
    """Absolute .git directory for sessions_dir, or None if it is not a repo."""
    result = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=sessions_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _current_branch(sessions_dir: Path) -> str:
    """Checked-out branch name, defaulting to main on a detached/unknown HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=sessions_dir,
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip() if result.returncode == 0 else ""
    return branch if branch and branch != "HEAD" else "main"


def _abort_merge(sessions_dir: Path, git_dir: Path) -> None:
    """Return the repo to a mergeable state after a failed or interrupted merge.

    `git merge --abort` is the clean path; `git reset --merge` covers the case
    where the merge state is too damaged for --abort to run; removing MERGE_HEAD
    is the last-ditch unwedge. Safe here for the same reason it is safe in
    scripts/git-sync.sh: auto-sync commits are mechanical snapshots that get
    re-derived from HEAD on the next pull, so nothing unique is lost.
    """
    aborted = _try(["git", "merge", "--abort"], sessions_dir) or _try(
        ["git", "reset", "--merge"], sessions_dir
    )
    if not aborted:
        logger.warning(
            "Could not abort merge cleanly in %s; clearing merge state by hand", sessions_dir
        )
    (git_dir / "MERGE_HEAD").unlink(missing_ok=True)


def _recover_interrupted_state(sessions_dir: Path, git_dir: Path) -> None:
    """Clear leftover rebase/merge state from a sync that was killed mid-flight.

    Without this, one interrupted cycle (cron killed, machine slept) traps every
    subsequent cycle forever: git refuses to commit or pull while MERGE_HEAD or
    a rebase-merge directory is present, so the sync never self-heals.
    """
    for state in ("rebase-merge", "rebase-apply"):
        state_dir = git_dir / state
        if state_dir.is_dir():
            logger.warning("Interrupted rebase detected in %s; aborting", sessions_dir)
            if not (
                _try(["git", "rebase", "--abort"], sessions_dir)
                or _try(["git", "reset", "--merge"], sessions_dir)
            ):
                logger.warning("git rebase --abort failed; removing %s directly", state_dir)
            # --abort refuses when the state metadata itself is corrupt, leaving
            # the directory in place and trapping the next run. Remove it.
            shutil.rmtree(state_dir, ignore_errors=True)

    if (git_dir / "MERGE_HEAD").exists():
        logger.warning("Interrupted merge detected in %s; aborting", sessions_dir)
        _abort_merge(sessions_dir, git_dir)


def _pull_then_push(sessions_dir: Path, git_dir: Path, branch: str) -> bool:
    """Integrate the remote and push, retrying the push across a bounded window.

    Integrate whatever else has landed on the remote before pushing. Without
    this, any commit made from another host since this host last synced makes
    the push a non-fast-forward, git rejects it, and every subsequent cycle
    drops its transcripts on the floor.

    A single pull-then-push is not enough on its own: two hosts share this
    repo on the same 5-minute cron cadence, so the remote can advance again in
    the gap between our pull and our push, rejecting the push exactly as if we
    had never pulled. Each retry re-pulls before pushing again, so it always
    integrates the latest remote state first.

    Merge rather than rebase: a killed merge is cleanly recoverable by the
    interrupted-state preflight, whereas partial-rebase replay state is not,
    and `ort` auto-resolves cleanly between mechanical auto-sync snapshots.

    The pull refspec is explicit (`origin <branch>`), not implicit upstream
    tracking config, which cron must not depend on ever having been set. The
    env on both the pull and the push-adjacent commands carries the bot
    identity because the merge commit the pull may create needs a committer
    and cron has none.

    A genuine conflict (pull itself fails) is not retried -- it is
    deterministic and retrying would just fail the same way again -- and is
    reported exactly as today: logged, merge aborted so the repo is not left
    wedged, and False returned.
    """
    for attempt in range(1, _MAX_PUSH_ATTEMPTS + 1):
        pull_result = subprocess.run(
            ["git", "pull", "--no-rebase", "--no-edit", "origin", branch],
            cwd=sessions_dir,
            capture_output=True,
            text=True,
            env=_bot_env(),
        )
        if pull_result.returncode != 0:
            logger.error(
                "Git sync failed: git pull origin %s returned %d\nStdout: %s\nStderr: %s",
                branch,
                pull_result.returncode,
                pull_result.stdout,
                pull_result.stderr,
            )
            _abort_merge(sessions_dir, git_dir)
            return False

        push_result = subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=sessions_dir,
            capture_output=True,
            text=True,
        )
        if push_result.returncode == 0:
            return True

        logger.warning(
            "git push rejected (attempt %d/%d), another host likely pushed in the gap; "
            "re-pulling and retrying\nStdout: %s\nStderr: %s",
            attempt,
            _MAX_PUSH_ATTEMPTS,
            push_result.stdout,
            push_result.stderr,
        )

    logger.error("Git sync failed: push still rejected after %d attempts", _MAX_PUSH_ATTEMPTS)
    return False


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

    git_dir = _resolve_git_dir(sessions_dir)
    if git_dir is None:
        logger.warning(
            "Could not resolve the git directory for %s, skipping git sync", sessions_dir
        )
        return False

    try:
        # Preflight: unwedge any half-finished rebase/merge before doing anything
        # else, so a single interrupted cycle does not trap all the later ones.
        _recover_interrupted_state(sessions_dir, git_dir)

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
            env=_bot_env(),
        )

        # Pull, then push, retrying the push across a bounded window to survive
        # a second host winning the race in the gap between our pull and our
        # push (see _pull_then_push). In cron, GH_TOKEN is set and the git
        # push credential helper is configured.
        branch = _current_branch(sessions_dir)
        if not _pull_then_push(sessions_dir, git_dir, branch):
            return False

        logger.info("Successfully synced transcripts sessions repo")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Git sync failed: %s\nStdout: %s\nStderr: %s", e, e.stdout, e.stderr)
        return False
