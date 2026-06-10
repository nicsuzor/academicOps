#!/usr/bin/env python3
"""freshness_check.py — read-only project-state freshness diff CLI.

Layer 1 of the project-state reconcile epic (aops-46b5c0ad / epic-ef498cc7).
Given a repo (Tier-1 ground truth) and one or more narrative anchors (Tier-2
markdown: PKB docs, epic bodies, README/CLAUDE.md), emits a FRESH / DRIFTED /
STALE verdict per anchor plus a project aggregate.

Strictly read-only: shells out to read-only git plumbing and reads files. Never
writes to the repo, the PKB, or the instruction layer.

Examples
--------
    # Diff a PKB anchor markdown against a repo, human-legible:
    freshness_check.py --repo ~/src/explorations \\
        --anchor ~/data/projects/tja/tja-project-48450f13.md

    # Machine-readable for downstream layers (3/4) to consume:
    freshness_check.py --repo ~/src/explorations --anchor a.md --anchor b.md --json

    # Tune the band boundaries (defaults are TJA-calibrated):
    freshness_check.py --repo R --anchor a.md --stale-commits 40 --stale-days 21

Exit codes: 0 = all anchors FRESH, 1 = at least one DRIFTED, 2 = at least one
STALE (incl. UNKNOWN -> STALE fail-safe). This lets callers gate on staleness.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add aops-core to path for lib imports (mirrors the other scripts here).
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE = SCRIPT_DIR.parent
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.freshness import (  # noqa: E402
    Band,
    Thresholds,
    evaluate_project,
    parse_anchor,
    read_repo_state,
)

_BAND_EXIT = {Band.FRESH: 0, Band.DRIFTED: 1, Band.STALE: 2}
_BAND_GLYPH = {Band.FRESH: "✅", Band.DRIFTED: "⚠️ ", Band.STALE: "🛑"}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="freshness_check",
        description="Read-only FRESH/DRIFTED/STALE freshness diff between PKB "
        "narrative anchors and repo ground truth.",
    )
    p.add_argument(
        "--repo", required=True, help="Path to the project's git repo (Tier-1 ground truth)."
    )
    p.add_argument(
        "--anchor",
        action="append",
        default=[],
        metavar="MARKDOWN",
        help="Narrative-anchor markdown file (PKB doc / epic body / README). Repeatable.",
    )
    p.add_argument(
        "--project", default=None, help="Project name for the aggregate (default: repo dir name)."
    )
    p.add_argument(
        "--artifact-glob",
        action="append",
        default=[],
        metavar="GLOB",
        help="Repo-relative glob of ground-truth artifacts (e.g. 'report/*.qmd'); "
        "files not mentioned by an anchor become a drift signal. Repeatable.",
    )
    p.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON instead of human text."
    )
    # Threshold overrides (defaults are TJA-calibrated; see lib.freshness.Thresholds).
    p.add_argument("--drifted-commits", type=int, default=None)
    p.add_argument("--stale-commits", type=int, default=None)
    p.add_argument("--drifted-days", type=int, default=None)
    p.add_argument("--stale-days", type=int, default=None)
    return p


def _thresholds(args: argparse.Namespace) -> Thresholds:
    base = Thresholds()
    return Thresholds(
        drifted_commits=args.drifted_commits
        if args.drifted_commits is not None
        else base.drifted_commits,
        stale_commits=args.stale_commits if args.stale_commits is not None else base.stale_commits,
        drifted_days=args.drifted_days if args.drifted_days is not None else base.drifted_days,
        stale_days=args.stale_days if args.stale_days is not None else base.stale_days,
    )


def _render_human(result, repo_state) -> str:
    lines: list[str] = []
    agg = result.aggregate_band
    lines.append(f"{_BAND_GLYPH[agg]} project '{result.project}': aggregate {agg.value}")
    head = repo_state.head_sha[:9] if repo_state.head_sha else "UNKNOWN"
    if repo_state.reachable:
        lines.append(
            f"   ground truth: HEAD {head}"
            + (f" ({repo_state.head_date.date()})" if repo_state.head_date else "")
        )
    else:
        lines.append(f"   ground truth: UNREACHABLE — {repo_state.error}")
    lines.append("")
    for v in result.anchors:
        lines.append(f"{_BAND_GLYPH[v.band]} {v.anchor_id}: {v.band.value}")
        lines.append(f"     {v.rationale}")
        banner = v.banner()
        if banner:
            lines.append(f"     banner: {banner}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo = Path(args.repo).expanduser()
    project = args.project or repo.name or "project"
    thresholds = _thresholds(args)

    repo_state = read_repo_state(repo, artifact_globs=args.artifact_glob or None)
    artifact_terms = repo_state.artifacts

    if not args.anchor:
        print("error: at least one --anchor is required", file=sys.stderr)
        return 2

    anchors = []
    for a in args.anchor:
        ap = Path(a).expanduser()
        if not ap.exists():
            print(f"error: anchor file not found: {ap}", file=sys.stderr)
            return 2
        anchors.append(parse_anchor(ap, artifact_terms=artifact_terms))

    result = evaluate_project(project, anchors, repo_state, repo=repo, thresholds=thresholds)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(_render_human(result, repo_state))

    return _BAND_EXIT[result.aggregate_band]


if __name__ == "__main__":
    raise SystemExit(main())
