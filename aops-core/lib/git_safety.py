"""Git push-safety guard for agent worktrees.

Problem class this closes
-------------------------
Harness-created worktrees (e.g. Claude Code ``claude/<codename>`` branches) are
branched from ``refs/remotes/origin/main``. With git's ``branch.autoSetupMerge``,
the new branch inherits ``origin/main`` as its upstream. Combined with a user's
global ``push.default=upstream``, a bare ``git push`` then resolves to *main* —
pushing the agent's work directly to the default branch and silently bypassing
PR review (only "allowed" when the user has branch-protection bypass rights).

Polecat worktrees avoid this by fixing tracking at creation time in
``polecat/manager.py``. Harness worktrees never go through that path, so this
guard runs at SessionStart (via ``hooks/session_env_setup.py``) and neutralises
the footgun for ANY worktree, regardless of who created it.

Design
------
The guard is intentionally network-free and idempotent (it must run on every
SessionStart without side effects beyond the first remediation):

1. ``push.default=current`` (worktree-local) — the primary guard. ``current``
   pushes the checked-out branch to a *same-named* remote branch and never
   consults the upstream, so a bare ``git push`` can never resolve to main even
   if some later step re-sets the upstream.
2. ``git branch --unset-upstream`` — removes the misleading main tracking so
   ``git status`` / ``git pull`` stop referencing main, matching the polecat
   invariant that a feature branch must not track main.

It acts only on the dangerous condition (a non-main branch whose upstream is
main), so the main checkout and correctly-tracked polecat worktrees are left
untouched.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Upstream refs that mean "a bare push could hit the default branch".
_MAIN_UPSTREAMS = {"origin/main", "main", "origin/master", "master"}
# Branches whose own tracking we must never touch (they *should* track main).
_PROTECTED_BRANCHES = {"main", "master"}


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def ensure_worktree_push_safety(cwd: Path | str) -> str | None:
    """Make pushes from a main-tracking worktree safe.

    Detects the condition where the current (non-main) branch's upstream is
    main/origin/main — meaning a bare ``git push`` under ``push.default=upstream``
    would target main — and remediates it (see module docstring).

    Returns a concise status string when it remediates, else ``None``. Never
    raises: any git failure degrades to ``None`` so SessionStart is never
    blocked by this guard.
    """
    cwd = Path(cwd)
    try:
        inside = _git(["rev-parse", "--is-inside-work-tree"], cwd)
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return None

        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd).stdout.strip()
        if not branch or branch == "HEAD":  # unborn or detached HEAD
            return None
        if branch in _PROTECTED_BRANCHES:
            return None

        upstream = _git(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
            cwd,
        )
        if upstream.returncode != 0:
            return None  # no upstream configured — nothing dangerous
        upstream_ref = upstream.stdout.strip()
        if upstream_ref.split("/")[-1] not in _PROTECTED_BRANCHES:
            return None  # tracks its own branch (or something else safe)

        actions: list[str] = []

        # Primary guard: push.default=current. Prefer worktree-scoped config so
        # we don't mutate the shared repo config; fall back to local repo config
        # when the worktreeConfig extension is not enabled (push.default=current
        # is a safe default for every branch, so repo-wide is acceptable).
        pd = _git(["config", "--worktree", "push.default", "current"], cwd)
        if pd.returncode != 0:
            pd = _git(["config", "push.default", "current"], cwd)
        if pd.returncode == 0:
            actions.append("push.default=current")

        # Secondary hygiene: drop the main-tracking upstream.
        if _git(["branch", "--unset-upstream"], cwd).returncode == 0:
            actions.append(f"unset upstream (was {upstream_ref})")

        if not actions:
            return None
        return (
            f"git push-safety: branch '{branch}' tracked '{upstream_ref}' — a bare "
            f"push would have hit main. Applied: {', '.join(actions)}."
        )
    except Exception:
        return None
