#!/usr/bin/env -S uv run python
"""Detect GitHub Actions runs whose wallclock exceeded the declared `timeout-minutes`.

GitHub kills jobs at `timeout-minutes`, so a true breach is rare. This script
exists to surface them if they ever happen — and, more often in practice, to
shake out misconceptions about *what the cap bounds* (per-run wallclock, not
daily aggregate or billable minutes).

Usage:
    check_workflow_timeout_breaches.py [--repo OWNER/NAME] [--days N] [--all-workflows]

Defaults:
    --repo derived from `gh repo view` (current repo)
    --days 30
    Only scans .github/workflows/*.yml files that declare an explicit job-level
    `timeout-minutes`. Pass --all-workflows to also flag missing caps.

Exit codes:
    0  no breaches found
    1  one or more runs exceeded their workflow's declared timeout-minutes
    2  setup/configuration error (no gh, no workflow files, etc.)
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

WORKFLOWS_DIR = Path(".github/workflows")
SLOP_SECONDS = 60  # GitHub kills slightly after the cap; only flag clear breaches.


def gh_api(path: str) -> Any:
    """Run `gh api <path>` and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def gh_api_paginate(path: str) -> Any:
    """Run `gh api --paginate <path>` and return concatenated JSON output."""
    result = subprocess.run(
        ["gh", "api", "--paginate", path],
        capture_output=True,
        text=True,
        check=True,
    )
    # --paginate concatenates JSON objects; join arrays manually.
    out: list[Any] = []
    decoder = json.JSONDecoder()
    text = result.stdout.strip()
    idx = 0
    while idx < len(text):
        obj, end = decoder.raw_decode(text, idx)
        out.append(obj)
        idx = end
        while idx < len(text) and text[idx].isspace():
            idx += 1
    return out


def current_repo() -> str:
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def declared_caps(workflows_dir: Path) -> dict[str, dict[str, int | None]]:
    """For each workflow file, return {job_id: timeout_minutes_or_None}.

    Returns {} for workflows we can't parse or that have no jobs.
    """
    out: dict[str, dict[str, int | None]] = {}
    for path in sorted(workflows_dir.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        jobs = data.get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        out[path.name] = {
            job_id: (job.get("timeout-minutes") if isinstance(job, dict) else None)
            for job_id, job in jobs.items()
        }
    return out


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iter_runs(repo: str, workflow_file: str, since: datetime) -> Iterator[dict[str, Any]]:
    """Yield workflow runs created after `since`."""
    created = since.strftime("%Y-%m-%d")
    path = f"repos/{repo}/actions/workflows/{workflow_file}/runs?per_page=100&created=>={created}"
    for page in gh_api_paginate(path):
        yield from page.get("workflow_runs", [])


def jobs_for_run(repo: str, run_id: int) -> list[dict[str, Any]]:
    path = f"repos/{repo}/actions/runs/{run_id}/jobs"
    data = gh_api(path)
    return data.get("jobs", [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--repo", help="OWNER/NAME (defaults to current repo)")
    parser.add_argument("--days", type=int, default=30, help="Days of history to scan")
    parser.add_argument(
        "--all-workflows",
        action="store_true",
        help="Also flag workflows that declare no timeout-minutes (warning, not breach)",
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=WORKFLOWS_DIR,
        help="Workflows directory to read (default: .github/workflows)",
    )
    args = parser.parse_args()

    if not shutil.which("gh"):
        print("error: gh CLI not on PATH", file=sys.stderr)
        return 2
    if not args.workflows_dir.exists():
        print(f"error: workflows dir not found: {args.workflows_dir}", file=sys.stderr)
        return 2

    repo = args.repo or current_repo()
    caps = declared_caps(args.workflows_dir)
    if not caps:
        print(f"error: no workflows parsed under {args.workflows_dir}", file=sys.stderr)
        return 2

    since = datetime.now(UTC) - timedelta(days=args.days)
    print(f"Scanning {repo} for runs since {since.date()} ({args.days}d).")

    breaches: list[dict[str, Any]] = []
    uncapped_warnings: list[str] = []
    runs_scanned = 0

    for workflow_file, job_caps in caps.items():
        capped = {jid: cap for jid, cap in job_caps.items() if isinstance(cap, int)}
        if not capped:
            if args.all_workflows:
                uncapped_warnings.append(f"  {workflow_file}: no job declares timeout-minutes")
            continue

        for run in iter_runs(repo, workflow_file, since):
            runs_scanned += 1
            run_started = run.get("run_started_at")
            updated = run.get("updated_at")
            if not run_started or not updated:
                continue
            wallclock_s = (parse_dt(updated) - parse_dt(run_started)).total_seconds()
            # Cheap pre-filter: only inspect jobs when wallclock looks suspicious.
            if wallclock_s <= max(capped.values()) * 60 + SLOP_SECONDS:
                continue
            for job in jobs_for_run(repo, run["id"]):
                cap = capped.get(job.get("name") or "") or capped.get(
                    job.get("workflow_name") or ""
                )
                if cap is None:
                    # Job name in API doesn't always match the YAML key. Fall back to
                    # the single capped job's value if there's only one.
                    if len(capped) == 1:
                        cap = next(iter(capped.values()))
                    else:
                        continue
                started = job.get("started_at")
                completed = job.get("completed_at")
                if not started or not completed:
                    continue
                job_wallclock_s = (parse_dt(completed) - parse_dt(started)).total_seconds()
                if job_wallclock_s > cap * 60 + SLOP_SECONDS:
                    breaches.append(
                        {
                            "workflow": workflow_file,
                            "run_id": run["id"],
                            "job": job.get("name"),
                            "cap_minutes": cap,
                            "actual_minutes": math.ceil(job_wallclock_s / 60),
                            "conclusion": job.get("conclusion"),
                            "url": run.get("html_url"),
                        }
                    )

    print(f"Scanned {runs_scanned} run(s) across {len(caps)} workflow file(s).")
    if uncapped_warnings:
        print("Workflows without a declared cap (warning only):")
        print("\n".join(uncapped_warnings))

    if not breaches:
        print("OK — no runs exceeded their declared timeout-minutes.")
        return 0

    print(f"\nBREACH — {len(breaches)} run(s) exceeded declared timeout-minutes:")
    for b in breaches:
        print(
            f"  {b['workflow']} job={b['job']!r}  "
            f"cap={b['cap_minutes']}m  actual={b['actual_minutes']}m  "
            f"conclusion={b['conclusion']}  {b['url']}"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
