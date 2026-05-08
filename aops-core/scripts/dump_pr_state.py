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
_CHECK_KEEP = ("name", "conclusion", "status")

TRAILER_RE = re.compile(
    r"^(Closes|Refs|Fixes|Resolves|Closes-issue|Closes-pr):\s*\S+",
    re.MULTILINE | re.IGNORECASE,
)


def _extract_trailers(body: str | None) -> list[str]:
    r"""Extract git-style trailers from PR body.

    Trailers match: ^(Closes|Refs|Fixes|Resolves|Closes-issue|Closes-pr):\s*\S+
    (case-insensitive, multi-line).
    """
    if not body:
        return []
    return [m.group(0) for m in TRAILER_RE.finditer(body)]


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
        return [_project_pr(pr, is_open=is_open) for pr in data]
    except subprocess.CalledProcessError as e:
        print(f"Error fetching {state} PRs for {repo_path.name}: {e.stderr}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error processing {state} PRs for {repo_path.name}: {e}", file=sys.stderr)
        raise


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

    for slug, proj in manager.projects.items():
        repo_path = proj.get("path")
        if not repo_path or not repo_path.exists():
            print(f"Skipping {slug}: path not found or doesn't exist", file=sys.stderr)
            continue

        print(f"Fetching PRs for {slug}...")
        repo_data = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "open_prs": [],
            "recent_merged": [],
            "recent_closed": [],
        }

        try:
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
