#!/usr/bin/env python3
"""PR Risk Taxonomy Classifier.

Implements the three-tier PR risk taxonomy (kb_48809ad0, aops_a7366995):
- Tier 1 (Low Risk / Autonomous QA-Merge): specs, documentation, type stubs, internal tests, linting.
  Label: triage:auto-mergeable
- Tier 2 (Medium Risk / Operational Gate): prompts, governance, reconcile, release workflows, storage sync.
  Label: triage:needs-judgment
- Tier 3 (Critical Hazard / Public Gate): scholarly manuscripts, host infra, credentials, human-authored PRs.
  Labels: criticality:critical, triage:needs-judgment

Enforces Policy-as-Code by loading pattern rules and labels from tests/policy.toml.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "tests" / "policy.toml"


def _matches_pattern(filepath: str, pattern: str) -> bool:
    norm_path = filepath.strip().lstrip("/")
    norm_pat = pattern.strip().lstrip("/")
    posix_path = PurePosixPath(norm_path)

    try:
        if posix_path.match(norm_pat):
            return True
    except Exception:
        pass

    if norm_pat.endswith("/**"):
        prefix = norm_pat[:-3]
        if norm_path == prefix or norm_path.startswith(prefix + "/"):
            return True

    if fnmatch.fnmatch(norm_path, norm_pat) or fnmatch.fnmatch(posix_path.name, norm_pat):
        return True

    return False


@dataclass(frozen=True)
class PRRiskResult:
    tier: int
    labels: list[str]
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "labels": self.labels,
            "reasons": self.reasons,
        }


class PRRiskClassifier:
    def __init__(
        self,
        tier1_label: str,
        tier2_label: str,
        tier3_labels: list[str],
        tier3_path_patterns: list[str],
        tier3_authors: list[str],
        tier2_path_patterns: list[str],
        tier1_path_patterns: list[str],
    ) -> None:
        self.tier1_label = tier1_label
        self.tier2_label = tier2_label
        self.tier3_labels = tier3_labels
        self.tier3_path_patterns = tier3_path_patterns
        self.tier3_authors = tier3_authors
        self.tier2_path_patterns = tier2_path_patterns
        self.tier1_path_patterns = tier1_path_patterns

    @classmethod
    def from_policy(cls, policy_dict: dict[str, Any]) -> PRRiskClassifier:
        return cls(
            tier1_label=str(policy_dict.get("tier1_label", "triage:auto-mergeable")),
            tier2_label=str(policy_dict.get("tier2_label", "triage:needs-judgment")),
            tier3_labels=list(
                policy_dict.get("tier3_labels", ["criticality:critical", "triage:needs-judgment"])
            ),
            tier3_path_patterns=list(policy_dict.get("tier3_path_patterns", [])),
            tier3_authors=list(policy_dict.get("tier3_authors", [])),
            tier2_path_patterns=list(policy_dict.get("tier2_path_patterns", [])),
            tier1_path_patterns=list(policy_dict.get("tier1_path_patterns", [])),
        )

    @classmethod
    def load_from_policy_file(cls, path: Path = DEFAULT_POLICY_PATH) -> PRRiskClassifier:
        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if "pr_risk" not in data:
            raise KeyError(f"Policy file {path} missing [pr_risk] section")
        return cls.from_policy(data["pr_risk"])

    def classify(self, files: Sequence[str], author: str = "") -> PRRiskResult:
        reasons: list[str] = []

        # 1. Tier 3 Author check (Human principal / critical authority)
        if author and author in self.tier3_authors:
            reasons.append(f"Author '{author}' requires principal review (Tier 3)")
            return PRRiskResult(tier=3, labels=list(self.tier3_labels), reasons=reasons)

        # 2. Tier 3 File check (Scholarly manuscripts, host infra, credentials)
        tier3_matches: list[str] = []
        for file in files:
            for pat in self.tier3_path_patterns:
                if _matches_pattern(file, pat):
                    tier3_matches.append(f"{file} matched {pat}")
                    break

        if tier3_matches:
            reasons.extend(f"Tier 3 path match: {m}" for m in tier3_matches)
            return PRRiskResult(tier=3, labels=list(self.tier3_labels), reasons=reasons)

        # 3. Tier 2 File check (Agent prompts, governance, reconcile, release workflows)
        tier2_matches: list[str] = []
        for file in files:
            for pat in self.tier2_path_patterns:
                if _matches_pattern(file, pat):
                    tier2_matches.append(f"{file} matched {pat}")
                    break

        if tier2_matches:
            reasons.extend(f"Tier 2 path match: {m}" for m in tier2_matches)
            return PRRiskResult(tier=2, labels=[self.tier2_label], reasons=reasons)

        # 4. Tier 1 File check (Allowlisted low-risk specs, docs, stubs, tests)
        if files:
            tier1_matches: list[str] = []
            unmatched: list[str] = []
            for file in files:
                matched = False
                for pat in self.tier1_path_patterns:
                    if _matches_pattern(file, pat):
                        tier1_matches.append(file)
                        matched = True
                        break
                if not matched:
                    unmatched.append(file)

            if not unmatched:
                reasons.append(f"All {len(files)} files matched Tier 1 low-risk allowlist")
                return PRRiskResult(tier=1, labels=[self.tier1_label], reasons=reasons)
            else:
                reasons.append(
                    f"Unclassified files outside Tier 1 allowlist: {unmatched[:5]}; defaulting to Tier 2"
                )
                return PRRiskResult(tier=2, labels=[self.tier2_label], reasons=reasons)

        # Default empty PR
        return PRRiskResult(tier=1, labels=[self.tier1_label], reasons=["Empty file list"])


def classify_pr_payload(
    payload: dict[str, Any], policy_path: Path = DEFAULT_POLICY_PATH
) -> PRRiskResult:
    classifier = PRRiskClassifier.load_from_policy_file(policy_path)
    files = payload.get("files", [])
    author = payload.get("author", "")
    return classifier.classify(files=files, author=author)


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify PR risk tier and apply triage labels.")
    parser.add_argument("--fixture", type=Path, help="Path to JSON fixture PR file to classify")
    parser.add_argument("--files", nargs="*", default=[], help="List of changed file paths")
    parser.add_argument("--author", default="", help="PR author username")
    parser.add_argument("--pr-number", help="PR number to label via gh CLI if available")
    parser.add_argument(
        "--policy", type=Path, default=DEFAULT_POLICY_PATH, help="Path to policy.toml"
    )
    parser.add_argument("--output-json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    files = list(args.files)
    author = args.author

    if args.fixture:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
        files = data.get("files", [])
        author = data.get("author", author)

    classifier = PRRiskClassifier.load_from_policy_file(args.policy)
    result = classifier.classify(files=files, author=author)

    if args.output_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"PR Risk Classification: Tier {result.tier}")
        print(f"Labels to apply: {', '.join(result.labels)}")
        for reason in result.reasons:
            print(f" - Reason: {reason}")

    # If pr-number is passed and GH_TOKEN / gh is available, attempt to apply labels
    if args.pr_number and result.labels:
        labels_arg = ",".join(result.labels)
        cmd = ["gh", "pr", "edit", str(args.pr_number), "--add-label", labels_arg]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully applied labels [{labels_arg}] to PR #{args.pr_number}")
        except FileNotFoundError:
            print(f"gh CLI not installed; skipped remote labeling for PR #{args.pr_number}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to apply labels via gh: {e.stderr}", file=sys.stderr)

    # Set GitHub Actions output if available
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"tier={result.tier}\n")
            f.write(f"labels={','.join(result.labels)}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
