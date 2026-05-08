#!/usr/bin/env python3
"""
dump_pr_state.py - Fetch raw PR data from tracked repos and dump to JSON.

Part of repo-sync-cron.sh. Producer for the PR state index.
"""

import json
import os
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

GH_FIELDS = [
    "number",
    "title",
    "url",
    "state",
    "isDraft",
    "author",
    "createdAt",
    "updatedAt",
    "mergedAt",
    "closedAt",
    "headRefName",
    "baseRefName",
    "body",
    "mergeable",
    "reviewDecision",
    "statusCheckRollup",
    "labels",
    "mergeStateStatus",
]

BODY_LIMIT = 2048


def fetch_prs(repo_path: Path, state: str, limit: int = 50, since: str | None = None) -> list:
    """Fetch PRs for a specific repo and state."""
    if not repo_path.exists():
        return []

    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        ",".join(GH_FIELDS),
    ]

    if since:
        qualifier = "merged" if state == "merged" else "closed"
        cmd += ["--search", f"{qualifier}:>{since}"]

    try:
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Truncate body
        for pr in data:
            if pr.get("body") and len(pr["body"]) > BODY_LIMIT:
                pr["body"] = pr["body"][:BODY_LIMIT] + "... [truncated]"

        return data
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
