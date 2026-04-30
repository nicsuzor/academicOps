#!/usr/bin/env -S uv run python
"""Allocator and collision lint for P# anchors in aops-core/HEURISTICS.md.

Two modes:

- Default: print the next free P# considering main + open PRs.
- ``--check``: collision-lint mode for pre-commit / CI. Reads the staged
  (or branch) diff, extracts proposed P# anchors, and fails if any of
  them already appear on main or in another open PR.

When ``gh`` is not available, open-PR awareness is skipped silently-but-
noisily (warning to stderr) and the result falls back to "main only".

Why this exists: parallel PRs were each picking "the next free P#" from
main and converging on the same number, producing merge conflicts on
HEURISTICS.md. See task-4fc42370.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEURISTICS_PATH = REPO_ROOT / "aops-core" / "HEURISTICS.md"

# The canonical P# anchor format used in HEURISTICS.md.
ANCHOR_RE = re.compile(r'<a id="P(\d+)"></a>')


def parse_existing_pnumbers(file_path: Path) -> set[int]:
    """Return the set of P# integers already declared in ``file_path``."""
    if not file_path.exists():
        return set()
    text = file_path.read_text(encoding="utf-8")
    return {int(m.group(1)) for m in ANCHOR_RE.finditer(text)}


def _run_gh(args: list[str]) -> str | None:
    """Run a ``gh`` command, returning stdout or None on any failure."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"warning: gh unavailable ({exc}); falling back to main-only", file=sys.stderr)
        return None
    if result.returncode != 0:
        print(f"warning: gh exited {result.returncode}: {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout


def parse_open_pr_pnumbers(exclude_pr: int | None = None) -> dict[int, list[int]]:
    """Return ``{pr_number: [pnumbers proposed in that PR]}`` for open PRs.

    Empty dict means either no PRs or gh unavailable. Caller treats both
    the same (degrades to main-only).
    """
    listing = _run_gh(["pr", "list", "--state", "open", "--json", "number"])
    if listing is None:
        return {}
    try:
        prs = json.loads(listing)
    except json.JSONDecodeError as exc:
        print(f"warning: gh pr list returned non-JSON: {exc}", file=sys.stderr)
        return {}

    out: dict[int, list[int]] = {}
    for pr in prs:
        n = pr.get("number")
        if not isinstance(n, int) or n == exclude_pr:
            continue
        diff = _run_gh(["pr", "diff", str(n)])
        if diff is None:
            continue
        # Only count *added* lines (those starting with a single '+'),
        # never '+++' headers, and only when they introduce a P# anchor.
        added = [
            line
            for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        nums = []
        for line in added:
            nums.extend(int(m.group(1)) for m in ANCHOR_RE.finditer(line))
        if nums:
            out[n] = sorted(set(nums))
    return out


def next_free(existing: set[int], reserved: set[int]) -> int:
    """Smallest integer strictly greater than max(existing | reserved).

    Preserves the project's monotonic numbering convention (we don't
    reuse holes - they're load-bearing for cross-references).
    """
    pool = existing | reserved
    return (max(pool) + 1) if pool else 1


def _staged_diff() -> str:
    """Get the diff that's about to be committed (or branch diff in CI).

    Tries ``--cached`` first (pre-commit), then falls back to
    ``origin/main...HEAD`` (CI).
    """
    try:
        cached = subprocess.run(
            ["git", "diff", "--cached", "--", str(HEURISTICS_PATH.relative_to(REPO_ROOT))],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        if cached.stdout.strip():
            return cached.stdout
        branch = subprocess.run(
            [
                "git",
                "diff",
                "origin/main...HEAD",
                "--",
                str(HEURISTICS_PATH.relative_to(REPO_ROOT)),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        return branch.stdout
    except FileNotFoundError:
        return ""


def find_collisions(
    staged_diff: str, open_pr_pnumbers: dict[int, list[int]]
) -> list[tuple[int, int]]:
    """Return ``[(pnumber, conflicting_pr), ...]`` for collisions in the diff."""
    proposed: set[int] = set()
    for line in staged_diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            proposed.update(int(m.group(1)) for m in ANCHOR_RE.finditer(line))
    collisions: list[tuple[int, int]] = []
    for n in sorted(proposed):
        for pr, pr_nums in open_pr_pnumbers.items():
            if n in pr_nums:
                collisions.append((n, pr))
    return collisions


def _cmd_next() -> int:
    existing = parse_existing_pnumbers(HEURISTICS_PATH)
    pr_map = parse_open_pr_pnumbers()
    reserved = {n for nums in pr_map.values() for n in nums}
    print(next_free(existing, reserved))
    return 0


def _cmd_check() -> int:
    diff = _staged_diff()
    if not diff.strip():
        return 0
    pr_map = parse_open_pr_pnumbers()
    collisions = find_collisions(diff, pr_map)
    if not collisions:
        return 0
    print("error: P# collision detected with open PR(s):", file=sys.stderr)
    for pnum, pr in collisions:
        print(f"  P{pnum} is already proposed in PR #{pr}", file=sys.stderr)
    print("Run `python scripts/next_p_number.py` to get a fresh P#.", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="collision-lint mode")
    args = parser.parse_args(argv)
    return _cmd_check() if args.check else _cmd_next()


if __name__ == "__main__":
    sys.exit(main())
