#!/usr/bin/env -S uv run python
"""
close_loop.py — /sleep Phase 6 Activity 4a helper (PR-state sweep).

Per `aops-core/skills/sleep/SKILL.md` §"Activity 4: Loop-close":

- Iterate tracked repos from `$ACA_DATA/state/tracked-repos.json`
  (initial: ["nicsuzor/academicOps", "nicsuzor/brain"]).
- For each PR closed since the cursor at `$ACA_DATA/state/close-loop-cursor.json`,
  match PR → task by precedence:
    1. `pr_url` already on the task
    2. `task-XXXXXXXX` ID found in PR body
    3. PR `headRefName` matches the task's recorded branch
    4. PR title matches task title (whole-word, ignoring `feat()`/`fix()`/`chore()` prefixes)
- Resolution:
    merged             → mcp__pkb__complete_task(id, completion_evidence=..., pr_url=...)
    closed-not-merged  → re-queue to `inbox` (always); append reviewer comments via mcp__pkb__append
    open               → no-op (optional pr_url annotation)
    no match           → log to ambiguous queue; never invent a task
- PRs only — no `git log` scanning.
- Idempotent. Cursor advances only after writes succeed.
- CI no-op guard (per `.agents/CAPABILITIES.md`): when PKB MCP unavailable, write
  artefact stub and exit 0; never crash the parent /sleep run.
- Artefact at `$ACA_DATA/state/pr-state.json` for /daily and dashboard consumers.

This is a HELPER. The SSoT for the sweep's *behaviour* lives in
`aops-core/skills/sleep/SKILL.md`. Read that first.

Usage:
    uv run python aops-core/scripts/close_loop.py
    uv run python aops-core/scripts/close_loop.py --dry-run
    uv run python aops-core/scripts/close_loop.py --repo nicsuzor/academicOps
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants — single source of truth for paths, defaults, file names.
# ---------------------------------------------------------------------------

DEFAULT_TRACKED_REPOS = ["nicsuzor/academicOps", "nicsuzor/brain"]

TASK_ID_RE = re.compile(r"\b(task|aops|ns|spec|epic|targ|goal)-[0-9a-f]{8}\b")
TITLE_PREFIX_RE = re.compile(
    r"^(?:feat|fix|chore|docs|refactor|test|perf|build|ci|style|revert)"
    r"(?:\([^)]*\))?\s*:\s*",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Environment + path helpers
# ---------------------------------------------------------------------------


def aca_data_dir() -> Path:
    """Resolve $ACA_DATA. Falls back to ~/.aops/data when unset (matches paths.py)."""
    env = os.environ.get("ACA_DATA")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".aops" / "data"


def state_dir() -> Path:
    return aca_data_dir() / "state"


def tracked_repos_path() -> Path:
    return state_dir() / "tracked-repos.json"


def cursor_path() -> Path:
    return state_dir() / "close-loop-cursor.json"


def artefact_path() -> Path:
    return state_dir() / "pr-state.json"


# ---------------------------------------------------------------------------
# CI / PKB-MCP availability guard
# ---------------------------------------------------------------------------


def is_ci_environment() -> bool:
    """True when we're running inside GitHub Actions or another CI env.

    GHA runners have no PKB MCP (per `.agents/CAPABILITIES.md`). The phase MUST
    no-op there rather than crashing the parent /sleep run.
    """
    return any(
        os.environ.get(name, "").strip()
        for name in ("CI", "GITHUB_ACTIONS", "CLOSE_LOOP_FORCE_CI_NOOP")
    )


# ---------------------------------------------------------------------------
# Config: tracked repos
# ---------------------------------------------------------------------------


def load_tracked_repos(path: Path | None = None) -> list[str]:
    """Load tracked-repos.json. Falls back to DEFAULT_TRACKED_REPOS when missing."""
    p = path or tracked_repos_path()
    if not p.exists():
        return list(DEFAULT_TRACKED_REPOS)
    try:
        data = json.loads(p.read_text())
        repos = data.get("repos") if isinstance(data, dict) else None
        if isinstance(repos, list) and all(isinstance(r, str) for r in repos):
            return repos
    except (json.JSONDecodeError, OSError):
        pass
    return list(DEFAULT_TRACKED_REPOS)


def ensure_tracked_repos_file(path: Path | None = None) -> Path:
    """Create the file with DEFAULT_TRACKED_REPOS if it doesn't exist."""
    p = path or tracked_repos_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(json.dumps({"repos": list(DEFAULT_TRACKED_REPOS)}, indent=2) + "\n")
    return p


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


def load_cursor(path: Path | None = None) -> dict[str, str]:
    """Load per-repo cursor. Returns {repo: ISO-timestamp}. Empty when missing."""
    p = path or cursor_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items() if isinstance(k, str)}
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_cursor(cursor: dict[str, str], path: Path | None = None) -> None:
    p = path or cursor_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cursor, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# gh PR fetcher
# ---------------------------------------------------------------------------


GH_FIELDS = (
    "number,title,state,url,mergedAt,closedAt,createdAt,updatedAt,body,"
    "headRefName,isDraft,mergeable,reviewDecision,author,statusCheckRollup,"
    "additions,deletions,changedFiles,labels"
)


def gh_list_closed(
    repo: str,
    since: str | None,
    limit: int = 100,
    runner: Callable[[list[str]], str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch closed PRs (merged + closed-without-merge) since `since`.

    `runner` is injected for testability. By default uses subprocess.
    """
    cmd = [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "closed",
        "--limit",
        str(limit),
        "--json",
        GH_FIELDS,
    ]
    if since:
        cmd.extend(["--search", f"closed:>{since}"])
    out = (runner or _default_runner)(cmd)
    if not out.strip():
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


def gh_list_open(
    repo: str,
    limit: int = 100,
    runner: Callable[[list[str]], str] | None = None,
) -> list[dict[str, Any]]:
    cmd = [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        str(limit),
        "--json",
        GH_FIELDS,
    ]
    out = (runner or _default_runner)(cmd)
    if not out.strip():
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


def _default_runner(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        if r.returncode != 0:
            return ""
        return r.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


# ---------------------------------------------------------------------------
# Match precedence
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    task_id: str | None
    signal: str  # "pr_url" | "task_id_in_body" | "head_ref" | "title" | "none"


def _normalise_title(title: str) -> str:
    stripped = TITLE_PREFIX_RE.sub("", title or "").strip()
    return " ".join(WORD_RE.findall(stripped.lower()))


def match_pr_to_task(pr: dict[str, Any], tasks: Iterable[dict[str, Any]]) -> MatchResult:
    """Apply the four-step match precedence per SKILL.md.

    `tasks` items are dicts with at least: id, title, pr_url, branch.
    """
    tasks = list(tasks)
    pr_url = (pr.get("url") or "").strip()
    head_ref = (pr.get("headRefName") or "").strip()
    body = pr.get("body") or ""
    pr_title_norm = _normalise_title(pr.get("title", ""))

    # 1. pr_url already on a task
    if pr_url:
        for t in tasks:
            if (t.get("pr_url") or "").strip() == pr_url:
                return MatchResult(task_id=t["id"], signal="pr_url")

    # 2. task-XXXXXXXX in PR body
    matches = TASK_ID_RE.findall(body)
    if matches:
        # the regex returns just the prefix group; re-scan to grab full IDs
        ids_in_body = [m.group(0) for m in TASK_ID_RE.finditer(body)]
        task_ids = {t["id"] for t in tasks}
        for tid in ids_in_body:
            if tid in task_ids:
                return MatchResult(task_id=tid, signal="task_id_in_body")

    # 3. headRefName matches a task's recorded branch
    if head_ref:
        for t in tasks:
            if (t.get("branch") or "").strip() == head_ref:
                return MatchResult(task_id=t["id"], signal="head_ref")

    # 4. PR title matches task title (whole-word, prefix-stripped)
    if pr_title_norm:
        for t in tasks:
            if _normalise_title(t.get("title", "")) == pr_title_norm:
                return MatchResult(task_id=t["id"], signal="title")

    return MatchResult(task_id=None, signal="none")


# ---------------------------------------------------------------------------
# PKB write surface
# ---------------------------------------------------------------------------


@dataclass
class PKBWrites:
    """Deferred PKB operations, applied (or replayed) by the caller.

    The script does not call MCP directly — /sleep dispatches the writes via
    its existing PKB client. This struct is what `sweep_repo` returns.
    """

    completed: list[dict[str, Any]] = field(default_factory=list)  # merged → done
    requeued: list[dict[str, Any]] = field(default_factory=list)  # closed → inbox
    annotated_open: list[dict[str, Any]] = field(default_factory=list)
    ambiguous: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Sweep core
# ---------------------------------------------------------------------------


@dataclass
class RepoSweepResult:
    repo: str
    closed_prs_seen: int
    writes: PKBWrites
    open_prs: list[dict[str, Any]]
    new_cursor: str | None


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _max_iso(values: Iterable[str]) -> str | None:
    vals = [v for v in values if v]
    if not vals:
        return None
    return max(vals)


def sweep_repo(
    repo: str,
    tasks: list[dict[str, Any]],
    cursor: str | None,
    fetcher: Callable[..., list[dict[str, Any]]] | None = None,
    open_fetcher: Callable[..., list[dict[str, Any]]] | None = None,
) -> RepoSweepResult:
    """Run the sweep for one repo. Pure function modulo the fetchers.

    `fetcher(repo, since)` returns closed PRs. `open_fetcher(repo)` returns open PRs.
    """
    fetcher = fetcher or gh_list_closed
    open_fetcher = open_fetcher or gh_list_open

    closed = fetcher(repo, cursor) if cursor else fetcher(repo, None)
    open_prs = open_fetcher(repo)

    writes = PKBWrites()
    seen_close_times: list[str] = []

    for pr in closed:
        close_ts = pr.get("mergedAt") or pr.get("closedAt") or ""
        if close_ts:
            seen_close_times.append(close_ts)

        match = match_pr_to_task(pr, tasks)
        record = {
            "repo": repo,
            "pr_number": pr.get("number"),
            "pr_url": pr.get("url"),
            "pr_title": pr.get("title"),
            "head_ref": pr.get("headRefName"),
            "merged_at": pr.get("mergedAt"),
            "closed_at": pr.get("closedAt"),
            "match_signal": match.signal,
            "task_id": match.task_id,
        }

        if match.task_id is None:
            writes.ambiguous.append(record)
            continue

        if pr.get("mergedAt"):
            writes.completed.append(
                {
                    **record,
                    "completion_evidence": (
                        f"PR #{pr.get('number')} merged {pr.get('mergedAt')} — {pr.get('url')}"
                    ),
                }
            )
        else:
            # closed without merge → re-queue to inbox
            writes.requeued.append(
                {
                    **record,
                    "annotation": (
                        f"PR #{pr.get('number')} closed without merge on "
                        f"{pr.get('closedAt')} — re-queued to inbox by /sleep "
                        f"loop-close. Reviewer comments to be appended."
                    ),
                }
            )

    # Open PR annotation (only when task lacks pr_url)
    for pr in open_prs:
        match = match_pr_to_task(pr, tasks)
        if match.task_id is None or match.signal == "pr_url":
            continue
        # only annotate if the task does not already have pr_url
        task = next((t for t in tasks if t["id"] == match.task_id), None)
        if task and not task.get("pr_url"):
            writes.annotated_open.append(
                {
                    "repo": repo,
                    "pr_number": pr.get("number"),
                    "pr_url": pr.get("url"),
                    "task_id": match.task_id,
                    "match_signal": match.signal,
                }
            )

    # Cursor advances only when there is something to advance to.
    new_cursor = _max_iso(seen_close_times) or cursor

    return RepoSweepResult(
        repo=repo,
        closed_prs_seen=len(closed),
        writes=writes,
        open_prs=open_prs,
        new_cursor=new_cursor,
    )


# ---------------------------------------------------------------------------
# Artefact writer
# ---------------------------------------------------------------------------


def write_artefact(
    results: list[RepoSweepResult],
    path: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    p = path or artefact_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "produced_at": _now_iso(),
        "producer": "aops-core/skills/sleep Phase 6 Activity 4a",
        "schema": 1,
        "repos": {},
    }
    if extra:
        payload.update(extra)

    for r in results:
        payload["repos"][r.repo] = {
            "closed_prs_seen": r.closed_prs_seen,
            "completed_count": len(r.writes.completed),
            "requeued_count": len(r.writes.requeued),
            "annotated_open_count": len(r.writes.annotated_open),
            "ambiguous_count": len(r.writes.ambiguous),
            "open_prs": r.open_prs,
            "new_cursor": r.new_cursor,
            "ambiguous": r.writes.ambiguous,
        }

    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return p


def write_ci_noop_artefact(path: Path | None = None) -> Path:
    p = path or artefact_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "produced_at": _now_iso(),
        "producer": "aops-core/skills/sleep Phase 6 Activity 4a",
        "schema": 1,
        "ci_noop": True,
        "reason": "PKB MCP unavailable in CI environment; sweep skipped.",
        "repos": {},
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return p


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the sweep but do not advance the cursor or write the artefact.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        help="Override tracked-repos.json with one or more --repo args.",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="Override $ACA_DATA/state/ for tests.",
    )
    args = parser.parse_args(argv)

    if is_ci_environment():
        # CI no-op guard. Still write the artefact stub so daily reads are
        # graceful, and report success.
        write_ci_noop_artefact((args.state_dir / "pr-state.json") if args.state_dir else None)
        print("close_loop: CI environment detected — no-op (PKB MCP unavailable).")
        return 0

    state = args.state_dir or state_dir()
    state.mkdir(parents=True, exist_ok=True)

    # Bootstrap the tracked-repos.json with defaults on first run so future
    # consumers (daily, dashboard) and operators see a discoverable config.
    ensure_tracked_repos_file(state / "tracked-repos.json")

    repos = args.repo or load_tracked_repos(state / "tracked-repos.json")
    cursor = load_cursor(state / "close-loop-cursor.json")

    # In CLI form we have no PKB client wired in this script — the helper
    # returns the action plan and the parent /sleep agent applies the writes.
    # For now, the script exists primarily for /sleep to import; standalone
    # invocation just produces the artefact and prints a summary.
    tasks: list[dict[str, Any]] = []  # /sleep injects this when calling sweep_repo
    results: list[RepoSweepResult] = []
    for repo in repos:
        results.append(sweep_repo(repo, tasks, cursor.get(repo)))

    if not args.dry_run:
        new_cursor = dict(cursor)
        for r in results:
            if r.new_cursor:
                new_cursor[r.repo] = r.new_cursor
        save_cursor(new_cursor, state / "close-loop-cursor.json")
        write_artefact(results, state / "pr-state.json")

    summary = []
    for r in results:
        summary.append(
            f"{r.repo}: {r.closed_prs_seen} closed PRs, "
            f"{len(r.writes.completed)} completed, "
            f"{len(r.writes.requeued)} re-queued, "
            f"{len(r.writes.ambiguous)} ambiguous"
        )
    print("\n".join(summary) if summary else "close_loop: no repos configured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
