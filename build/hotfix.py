#!/usr/bin/env python3
"""Hotfix release automation and patch-only bump enforcement for academicOps.

Under the academicOps v1 feature freeze (announcement #3206):
- Until release/v1.0-rc0 is merged, all academicOps work targets release/v1.0-rc0.
- New features and big changes require a dedicated branch, PR, and user approval.
- Hotfixes merge straight to the target branch once CI checks are green after
  a review check confirms the change is genuinely a hotfix.
- Hotfixes are clearly labelled so release-please bumps only the patch version
  and releases a new build without requiring user approval.
- Non-hotfix changes yield no automatic release and wait for user approval.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from build.version import validate_version

DEFAULT_HOTFIX_LABELS = {"hotfix", "type:hotfix"}
DEFAULT_HOTFIX_PREFIXES = ("hotfix:",)


@dataclass(frozen=True)
class HotfixDecision:
    is_hotfix: bool
    should_automerge: bool
    target_version: str
    reason: str


def is_hotfix(
    labels: list[str] | None = None,
    commit_messages: list[str] | None = None,
    pr_title: str = "",
) -> bool:
    """Determine whether a change is explicitly designated as a hotfix."""
    if labels:
        for lbl in labels:
            if lbl.strip().lower() in DEFAULT_HOTFIX_LABELS:
                return True

    title_lower = pr_title.strip().lower()
    if (
        title_lower.startswith("[hotfix]")
        or title_lower.startswith("hotfix:")
        or bool(re.match(r"^hotfix(\([^\)]+\))?:", title_lower))
    ):
        return True

    if commit_messages:
        for msg in commit_messages:
            first_line = msg.strip().splitlines()[0].lower() if msg.strip() else ""
            if (
                first_line.startswith("[hotfix]")
                or first_line.startswith(DEFAULT_HOTFIX_PREFIXES)
                or bool(re.match(r"^hotfix(\([^\)]+\))?:", first_line))
            ):
                return True

    return False


def compute_next_patch(current_version: str) -> str:
    """Compute the next patch version for a PEP 440 version string.

    Given '0.10.26', returns '0.10.27'.
    Given '1.0.0', returns '1.0.1'.
    Raises ValueError if version is invalid PEP 440.
    """
    norm = validate_version(current_version)
    base = re.split(r"[-+]", norm)[0]
    parts = base.split(".")
    if len(parts) < 3:
        parts += ["0"] * (3 - len(parts))
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    return f"{major}.{minor}.{patch + 1}"


def is_patch_bump(current_version: str, target_version: str) -> bool:
    """Check if target_version is strictly a patch increment over current_version."""
    expected = compute_next_patch(current_version)
    norm_target = validate_version(target_version)
    return norm_target == expected


def evaluate_hotfix_release(
    current_version: str,
    proposed_version: str,
    labels: list[str] | None = None,
    commit_messages: list[str] | None = None,
    pr_title: str = "",
) -> HotfixDecision:
    """Evaluate whether a release candidate should auto-release as a hotfix.

    If hotfix-labelled and strictly a patch bump:
      - Sets should_automerge = True with target_version.
    If hotfix-labelled but proposed bump is NOT a patch bump:
      - Sets should_automerge = False (fails fast without silent clamping).
    If non-hotfix:
      - Sets should_automerge = False (waits for user approval).
    """
    hotfix_flag = is_hotfix(labels=labels, commit_messages=commit_messages, pr_title=pr_title)

    if hotfix_flag:
        if is_patch_bump(current_version, proposed_version):
            return HotfixDecision(
                is_hotfix=True,
                should_automerge=True,
                target_version=proposed_version,
                reason=(
                    f"Hotfix detected: patch-only release approved ({current_version} -> {proposed_version}). "
                    "Automatic release enabled."
                ),
            )
        return HotfixDecision(
            is_hotfix=True,
            should_automerge=False,
            target_version=proposed_version,
            reason=(
                f"Hotfix proposed non-patch bump ({current_version} -> {proposed_version}); "
                "clamping forbidden. Waiting for user approval."
            ),
        )

    return HotfixDecision(
        is_hotfix=False,
        should_automerge=False,
        target_version=proposed_version,
        reason=(
            f"Non-hotfix change: waiting for user approval. "
            f"No automatic release ({current_version} -> {proposed_version})."
        ),
    )


def evaluate_release_pr(pr_number: int | str, repo: str = "nicsuzor/academicOps") -> HotfixDecision:
    """Inspect an open release-please pull request and evaluate hotfix release status."""
    project_root = Path(__file__).resolve().parent.parent
    manifest_path = project_root / ".release-please-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest file at {manifest_path}")

    manifest_data = json.loads(manifest_path.read_text())
    current_version = manifest_data.get(".")
    if not current_version:
        raise ValueError(f"Root package version not found in {manifest_path}")

    # Read PR metadata via gh CLI
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr_number}",
        "--jq",
        "{title: .title, body: .body, labels: [.labels[].name]}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    pr_data = json.loads(res.stdout)
    pr_title = pr_data.get("title", "")
    pr_labels = list(pr_data.get("labels", []))

    # Parse proposed version from title, e.g. 'chore(release/v1.0-rc0): release 0.10.27'
    m = re.search(r"release\s+([0-9a-zA-Z\.\-]+)", pr_title)
    if not m:
        raise ValueError(f"Could not parse proposed version from PR title: {pr_title}")
    proposed_version = m.group(1)

    # Read constituent commits in the release PR
    cmd_commits = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr_number}/commits",
        "--jq",
        "[.[].commit.message]",
    ]
    res_commits = subprocess.run(cmd_commits, capture_output=True, text=True, check=True)
    commit_messages = json.loads(res_commits.stdout)

    # Resolve label provenance: check constituent commits and referenced PR labels
    hotfix_found = is_hotfix(labels=pr_labels, commit_messages=commit_messages, pr_title=pr_title)
    if not hotfix_found:
        for msg in commit_messages:
            for pr_ref in re.findall(r"\(#(\d+)\)", msg):
                cmd_ref = [
                    "gh",
                    "api",
                    f"repos/{repo}/pulls/{pr_ref}",
                    "--jq",
                    "[.labels[].name]",
                ]
                res_ref = subprocess.run(cmd_ref, capture_output=True, text=True, check=False)
                if res_ref.returncode == 0:
                    ref_labels = json.loads(res_ref.stdout)
                    if any(lbl.strip().lower() in DEFAULT_HOTFIX_LABELS for lbl in ref_labels):
                        hotfix_found = True
                        break
            if hotfix_found:
                break

    if hotfix_found and not any(lbl.strip().lower() in DEFAULT_HOTFIX_LABELS for lbl in pr_labels):
        # Propagate hotfix label to release PR
        subprocess.run(
            ["gh", "pr", "edit", str(pr_number), "--add-label", "hotfix", "--repo", repo],
            check=True,
        )
        pr_labels.append("hotfix")

    decision = evaluate_hotfix_release(
        current_version=current_version,
        proposed_version=proposed_version,
        labels=pr_labels,
        commit_messages=commit_messages,
        pr_title=pr_title,
    )

    if decision.should_automerge:
        subprocess.run(
            ["gh", "pr", "merge", str(pr_number), "--auto", "--merge", "--repo", repo],
            check=True,
        )

    return decision


def main() -> None:
    parser = argparse.ArgumentParser(
        description="academicOps hotfix evaluation and patch-only release automation"
    )
    parser.add_argument(
        "--is-hotfix",
        action="store_true",
        help="Check if arguments represent a hotfix",
    )
    parser.add_argument(
        "--next-patch",
        type=str,
        metavar="VERSION",
        help="Compute next patch version for given version",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run evaluation for hotfix vs non-hotfix release",
    )
    parser.add_argument(
        "--eval-release-pr",
        type=str,
        metavar="PR_NUMBER",
        help="Evaluate an open release PR for hotfix auto-release",
    )
    parser.add_argument("--current-version", type=str, default="0.10.26")
    parser.add_argument("--proposed-version", type=str, default=None)
    parser.add_argument("--label", action="append", dest="labels", default=[])
    parser.add_argument("--commit-message", action="append", dest="commit_messages", default=[])
    parser.add_argument("--pr-title", type=str, default="")
    parser.add_argument("--repo", type=str, default="nicsuzor/academicOps")

    args = parser.parse_args()

    if args.next_patch:
        print(compute_next_patch(args.next_patch))
        return

    if args.dry_run:
        proposed = args.proposed_version or compute_next_patch(args.current_version)
        decision = evaluate_hotfix_release(
            current_version=args.current_version,
            proposed_version=proposed,
            labels=args.labels,
            commit_messages=args.commit_messages,
            pr_title=args.pr_title,
        )
        print(f"HOTFIX: {str(decision.is_hotfix).lower()}")
        print(f"AUTO_MERGE: {str(decision.should_automerge).lower()}")
        print(f"TARGET_VERSION: {decision.target_version}")
        print(f"REASON: {decision.reason}")
        return

    if args.eval_release_pr:
        decision = evaluate_release_pr(args.eval_release_pr, repo=args.repo)
        print(f"HOTFIX: {str(decision.is_hotfix).lower()}")
        print(f"AUTO_MERGE: {str(decision.should_automerge).lower()}")
        print(f"TARGET_VERSION: {decision.target_version}")
        print(f"REASON: {decision.reason}")
        return

    if args.is_hotfix:
        res = is_hotfix(
            labels=args.labels,
            commit_messages=args.commit_messages,
            pr_title=args.pr_title,
        )
        print("true" if res else "false")
        sys.exit(0 if res else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
