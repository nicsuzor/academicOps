#!/usr/bin/env python3
"""
dump_pr_state.py - Fetch raw PR data from tracked repos and dump to JSON.

Part of repo-sync-cron.sh. Producer for the PR state index.
"""

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# Add polecat to path for manager import
if str(REPO_ROOT / "polecat") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "polecat"))

from lib.triage_labels import ensure_triage_labels
from manager import PolecatManager

# Fields fetched per state. Open PRs need bucketing signals (CI rollup, mergeable,
# reviewDecision); closed/merged need only what /sleep's PR→task matcher reads.
# New field added during projection:
# - trailers: List[str] - git-style trailers (Closes: #123, etc.) extracted from full body
OPEN_FIELDS = [
    "number",
    "title",
    "url",
    "state",
    "isDraft",
    "author",
    "createdAt",
    "updatedAt",
    "headRefName",
    "baseRefName",
    "body",
    "mergeable",
    "reviewDecision",
    "statusCheckRollup",
    "files",
    "labels",
]
CLOSED_FIELDS = [
    "number",
    "title",
    "url",
    "state",
    "author",
    "createdAt",
    "updatedAt",
    "mergedAt",
    "closedAt",
    "headRefName",
    "baseRefName",
    "body",
]

BODY_LIMIT = 2048

# Only fields any consumer actually reads. Everything else gh emits is dropped.
_AUTHOR_KEEP = ("login", "is_bot")
# CheckRun entries carry name/conclusion/status; StatusContext entries (the
# pipeline agent statuses posted via the statuses API, e.g. mechanic-status)
# carry context/state. Keep both shapes so apply_triage can tell a transient
# red check apart from a halted pipeline.
_CHECK_KEEP = ("name", "conclusion", "status", "context", "state")

TRAILER_RE = re.compile(
    r"^\b(Closes|Refs|Fixes|Resolves|Closes-issue|Closes-pr)\b:\s*.+",
    re.MULTILINE | re.IGNORECASE,
)


def _extract_trailers(body: str | None) -> list[str]:
    r"""Extract git-style trailers from PR body.

    Trailers match: ^\b(Closes|Refs|Fixes|Resolves|Closes-issue|Closes-pr)\b:\s*.+
    (case-insensitive, multi-line).
    """
    if not body:
        return []
    return [m.group(0).strip() for m in TRAILER_RE.finditer(body)]


def _project_pr(pr: dict, *, is_open: bool) -> dict:
    author = pr.get("author") or {}
    if author and isinstance(author, dict):
        pr["author"] = {k: author[k] for k in _AUTHOR_KEEP if k in author}
    if is_open:
        pr["statusCheckRollup"] = [
            {k: c[k] for k in _CHECK_KEEP if k in c}
            for c in pr.get("statusCheckRollup") or []
            if isinstance(c, dict)
        ]

    body = pr.get("body")
    pr["trailers"] = _extract_trailers(body)

    if body and len(body) > BODY_LIMIT:
        pr["body"] = body[:BODY_LIMIT] + "... [truncated]"
    return pr


def apply_triage(pr: dict, repo_path: Path):
    raw_names = [lbl.get("name") for lbl in pr.get("labels", []) if isinstance(lbl, dict)]
    labels: list[str] = [n for n in raw_names if isinstance(n, str)]
    existing_triage_labels = [lbl for lbl in labels if lbl.startswith("triage:")]

    new_label = None
    updated_at_str = pr.get("updatedAt", "")
    try:
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        is_stale = (datetime.now(UTC) - updated_at).days > 7
    except Exception:
        is_stale = False

    is_draft = pr.get("isDraft", False)

    mergeable = pr.get("mergeable")
    rollups = pr.get("statusCheckRollup", [])
    failed_checks = [
        r.get("name", "Unknown check")
        for r in rollups
        if isinstance(r, dict) and r.get("conclusion") == "FAILURE"
    ]

    # Has the automated fix pipeline halted and handed this PR back to a human?
    # The mechanic (Stage-2 fix-loop agent) posts mechanic-status=FAILURE only
    # when it gives up — loop-ceiling exhaustion (it also requests the
    # maintainer as reviewer) or an agent crash it cannot self-recover. Either
    # is a genuine "needs a human" event. Transient red CI and merge conflicts
    # on their own are the pipeline's NORMAL working state — the enforcer/qa/
    # mechanic churn on them — so they stay pipeline-owned, NOT escalate. The
    # state lives on a StatusContext rollup entry (context/state), distinct
    # from CheckRun build/lint failures (name/conclusion).
    pipeline_halted = any(
        isinstance(r, dict)
        and r.get("context") == "mechanic-status"
        and isinstance(r.get("state"), str)
        and r["state"].upper() in ("FAILURE", "ERROR")
        for r in rollups
    )

    branch = pr.get("headRefName", "")
    login = pr.get("author", {}).get("login", "")

    if pipeline_halted:
        new_label = "triage:escalate"
    elif is_stale and not is_draft:
        new_label = "triage:stale"
    elif branch.startswith("release") or login in ("app/github-actions", "github-actions[bot]"):
        new_label = "triage:auto-mergeable"
    elif (
        mergeable == "MERGEABLE"
        and not failed_checks
        and rollups
        and all(
            r.get("conclusion") in ("SUCCESS", "NEUTRAL", "SKIPPED")
            or r.get("status") == "COMPLETED"
            for r in rollups
            if isinstance(r, dict)
        )
        and pr.get("reviewDecision") == "APPROVED"
    ):
        new_label = "triage:auto-mergeable"
    else:
        # Everything still in flight — including red CI and merge conflicts the
        # pipeline is expected to resolve. Owned by the merge pipeline, not you.
        new_label = "triage:pipeline"

    if new_label and new_label not in existing_triage_labels:
        cmd = ["gh", "pr", "edit", str(pr["number"]), "--add-label", new_label]
        if existing_triage_labels:
            cmd.extend(["--remove-label", ",".join(existing_triage_labels)])
        try:
            subprocess.run(cmd, cwd=repo_path, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = (
                e.stderr or ""
            )  # allow-fallback: CalledProcessError.stderr is None when not captured
            print(
                f"Warning: label-edit failed for {repo_path.name} PR #{pr['number']}: "
                f"{' '.join(cmd)} -> exit {e.returncode} {stderr.strip()}",
                file=sys.stderr,
            )
            return


def fetch_prs(repo_path: Path, state: str, limit: int = 50, since: str | None = None) -> list:
    """Fetch PRs for a specific repo and state."""
    if not repo_path.exists():
        return []

    is_open = state == "open"
    fields = OPEN_FIELDS if is_open else CLOSED_FIELDS

    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        ",".join(fields),
    ]

    if since:
        qualifier = "merged" if state == "merged" else "closed"
        cmd += ["--search", f"{qualifier}:>{since}"]

    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        prs = [_project_pr(pr, is_open=is_open) for pr in data]
    except subprocess.CalledProcessError as e:
        print(f"Error fetching {state} PRs for {repo_path.name}: {e.stderr}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error processing {state} PRs for {repo_path.name}: {e}", file=sys.stderr)
        raise

    if is_open:
        for pr in prs:
            try:
                apply_triage(pr, repo_path)
            except Exception as e:
                print(
                    f"Warning: apply_triage failed for {repo_path.name} PR #{pr.get('number')}: {e}",
                    file=sys.stderr,
                )

    return prs


def main():
    manager = PolecatManager()

    # Identify output path
    aops_sessions = os.environ.get("AOPS_SESSIONS")
    if not aops_sessions:
        # Fallback to manager's home/sessions if env not set
        sessions_path = manager.home_dir / "sessions"
    else:
        sessions_path = Path(aops_sessions).expanduser()

    state_dir = sessions_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    output_path = state_dir / "pr-state.json"
    tmp_path = output_path.with_suffix(".json.tmp")

    cutoff = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%d")
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "generator": "repo-sync-cron",
        "repos": {},
    }

    seen_paths = set()

    for slug, proj in manager.projects.items():
        if proj.get("is_repo") is False:
            continue
        repo_path = proj.get("path")
        if not repo_path or not repo_path.exists():
            print(f"Skipping {slug}: path not found or doesn't exist", file=sys.stderr)
            continue

        resolved_path = repo_path.resolve()
        if resolved_path in seen_paths:
            print(f"Skipping {slug}: repo {resolved_path} already processed", file=sys.stderr)
            continue
        seen_paths.add(resolved_path)

        print(f"Fetching PRs for {slug}...")
        repo_data = {
            "repo_path": str(resolved_path),
            "fetched_at": datetime.now(UTC).isoformat(),
            "open_prs": [],
            "recent_merged": [],
            "recent_closed": [],
        }

        try:
            ensure_triage_labels(repo_path)
            repo_data["open_prs"] = fetch_prs(repo_path, "open", limit=100)
            repo_data["recent_merged"] = fetch_prs(repo_path, "merged", limit=50, since=cutoff)
            repo_data["recent_closed"] = fetch_prs(repo_path, "closed", limit=20, since=cutoff)
        except Exception as e:
            repo_data["error"] = str(e)

        report["repos"][slug] = repo_data

    # Atomic write
    with open(tmp_path, "w") as f:
        json.dump(report, f, indent=2)

    tmp_path.rename(output_path)
    print(f"PR state dumped to {output_path}")


if __name__ == "__main__":
    main()
