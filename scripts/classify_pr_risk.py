"""PR risk taxonomy classification and label synchronization.

Classifies PR risk into Tier 1 (auto-mergeable), Tier 2 (needs-judgment),
or Tier 3 (criticality:critical) based on policy in tests/policy.toml.
Fails closed on any error, missing file, or empty file list.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_POLICY_PATH = Path("tests/policy.toml")


@dataclass(frozen=True)
class PRRiskResult:
    tier: int
    labels: list[str]
    reasons: list[str]


class PRRiskClassifier:
    def __init__(
        self,
        tier1_label: str,
        tier2_label: str,
        tier3_labels: list[str],
        tier3_path_patterns: list[str],
        tier2_path_patterns: list[str],
        tier1_path_patterns: list[str],
        bot_authors: list[str],
    ) -> None:
        self.tier1_label = tier1_label
        self.tier2_label = tier2_label
        self.tier3_labels = tier3_labels
        self.tier3_path_patterns = tier3_path_patterns
        self.tier2_path_patterns = tier2_path_patterns
        self.tier1_path_patterns = tier1_path_patterns
        self.bot_authors = bot_authors

    @classmethod
    def from_policy(cls, policy_dict: dict[str, object]) -> PRRiskClassifier:
        # Mandatory policy keys without fallbacks: fail loud if missing
        return cls(
            tier1_label=str(policy_dict["tier1_label"]),
            tier2_label=str(policy_dict["tier2_label"]),
            tier3_labels=[str(lbl) for lbl in policy_dict["tier3_labels"]],  # type: ignore[union-attr]
            tier3_path_patterns=[str(p) for p in policy_dict["tier3_path_patterns"]],  # type: ignore[union-attr]
            tier2_path_patterns=[str(p) for p in policy_dict["tier2_path_patterns"]],  # type: ignore[union-attr]
            tier1_path_patterns=[str(p) for p in policy_dict["tier1_path_patterns"]],  # type: ignore[union-attr]
            bot_authors=[str(a) for a in policy_dict["bot_authors"]],  # type: ignore[union-attr]
        )

    @classmethod
    def load_from_policy_file(cls, path: Path = DEFAULT_POLICY_PATH) -> PRRiskClassifier:
        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {path}")
        with path.open("rb") as f:
            data = tomllib.load(f)
        if "pr_risk" not in data:
            raise KeyError(f"Policy file {path} missing [pr_risk] section")
        return cls.from_policy(data["pr_risk"])

    @staticmethod
    def _matches_any(file_path: str, patterns: Sequence[str]) -> bool:
        normalized = file_path.strip()
        for pat in patterns:
            if fnmatch.fnmatch(normalized, pat):
                return True
            # Support globstar prefix matching if pat ends with /**
            if pat.endswith("/**"):
                prefix = pat[:-3]
                if normalized == prefix or normalized.startswith(prefix + "/"):
                    return True
        return False

    def classify(self, files: Sequence[str], author: str = "") -> PRRiskResult:
        if not files:
            raise ValueError("No changed files provided for classification")

        # 1. Human author escalation (Tier 3)
        is_bot = author.endswith("[bot]") or author in self.bot_authors
        if not is_bot:
            return PRRiskResult(
                tier=3,
                labels=list(self.tier3_labels),
                reasons=[f"Author '{author}' classified as human author (Tier 3 gate)"],
            )

        # 2. Tier 3 path check
        tier3_files = [f for f in files if self._matches_any(f, self.tier3_path_patterns)]
        if tier3_files:
            return PRRiskResult(
                tier=3,
                labels=list(self.tier3_labels),
                reasons=[f"Matched Tier 3 paths: {tier3_files}"],
            )

        # 3. Tier 2 path check
        tier2_files = [f for f in files if self._matches_any(f, self.tier2_path_patterns)]
        if tier2_files:
            return PRRiskResult(
                tier=2,
                labels=[self.tier2_label],
                reasons=[f"Matched Tier 2 paths: {tier2_files}"],
            )

        # 4. Tier 1 path check: ALL files must match Tier 1 patterns
        unmatched = [f for f in files if not self._matches_any(f, self.tier1_path_patterns)]
        if not unmatched:
            return PRRiskResult(
                tier=1,
                labels=[self.tier1_label],
                reasons=[f"All {len(files)} files matched Tier 1 low-risk allowlist"],
            )

        # 5. Unclassified paths default to Tier 2 (operational gate)
        return PRRiskResult(
            tier=2,
            labels=[self.tier2_label],
            reasons=[f"Files outside Tier 1 allowlist: {unmatched}"],
        )


def sync_pr_labels(
    pr_number: int, target_labels: Sequence[str], all_tier_labels: Sequence[str]
) -> None:
    """Synchronize PR labels via gh CLI, adding target labels and removing stale tier labels."""
    view_cmd = ["gh", "pr", "view", str(pr_number), "--json", "labels"]
    proc = subprocess.run(view_cmd, capture_output=True, text=True, check=True)
    current_data = json.loads(proc.stdout)
    current_labels = {lbl["name"] for lbl in current_data.get("labels", [])}

    to_add = [lbl for lbl in target_labels if lbl not in current_labels]
    to_remove = [
        lbl for lbl in all_tier_labels if lbl in current_labels and lbl not in target_labels
    ]

    if not to_add and not to_remove:
        return

    edit_cmd = ["gh", "pr", "edit", str(pr_number)]
    if to_add:
        edit_cmd.extend(["--add-label", ",".join(to_add)])
    if to_remove:
        edit_cmd.extend(["--remove-label", ",".join(to_remove)])

    subprocess.run(edit_cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify PR risk tier and synchronize labels.")
    parser.add_argument("--pr-number", type=int, help="GitHub PR number")
    parser.add_argument("--author", type=str, default="", help="PR author login")
    parser.add_argument("--files", nargs="*", default=[], help="List of changed file paths")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH, help="Policy TOML file")
    args = parser.parse_args()

    classifier = PRRiskClassifier.load_from_policy_file(args.policy)
    result = classifier.classify(files=args.files, author=args.author)

    print(f"PR Risk Tier: {result.tier}")
    print(f"Labels: {', '.join(result.labels)}")
    for r in result.reasons:
        print(f"  - {r}")

    if args.pr_number:
        all_tier_labels = [
            classifier.tier1_label,
            classifier.tier2_label,
            *classifier.tier3_labels,
        ]
        sync_pr_labels(args.pr_number, result.labels, all_tier_labels)


if __name__ == "__main__":
    main()
