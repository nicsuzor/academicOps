"""Canonical `triage:*` label set for repo-sync-cron PR routing.

The labels in `TRIAGE_LABELS` are consumed by `apply_triage()` in
`aops-core/scripts/dump_pr_state.py` and documented in
`.agents/ENFORCEMENT-MAP.md`. They must exist in every tracked repo for the
routing to be visible — `ensure_triage_labels()` provisions them idempotently
at the top of each cron cycle.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TriageLabel:
    name: str
    color: str  # hex without leading '#'
    description: str


TRIAGE_LABELS: tuple[TriageLabel, ...] = (
    TriageLabel(
        name="triage:escalate",
        color="d73a4a",
        description="PR has failing CI or merge conflicts; needs manual intervention.",
    ),
    TriageLabel(
        name="triage:stale",
        color="fbca04",
        description="PR has had no activity for over 7 days.",
    ),
    TriageLabel(
        name="triage:auto-mergeable",
        color="0e8a16",
        description="Routine release or bot-authored PR; safe for automatic merge.",
    ),
    TriageLabel(
        name="triage:needs-judgment",
        color="0075ca",
        description="PR requires human review and judgment before merging.",
    ),
)


def ensure_triage_labels(repo_path: Path) -> list[str]:
    """Idempotently provision the canonical `triage:*` labels in `repo_path`.

    Uses `gh label create --force`, which creates the label if missing and
    updates colour/description in place if it already exists. Returns the
    list of label names that failed to provision (empty on full success).

    Failures are warned-not-raised: a missing token scope on one repo must
    not abort the rest of the cron cycle.
    """
    failures: list[str] = []
    for label in TRIAGE_LABELS:
        cmd = [
            "gh",
            "label",
            "create",
            label.name,
            "--force",
            "--color",
            label.color,
            "--description",
            label.description,
        ]
        try:
            subprocess.run(cmd, cwd=repo_path, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            print(
                f"Warning: ensure_triage_labels failed for {repo_path.name} "
                f"label {label.name!r}: exit {e.returncode} {stderr}",
                file=sys.stderr,
            )
            failures.append(label.name)
    return failures
