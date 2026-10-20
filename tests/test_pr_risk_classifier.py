"""Tests for PR risk taxonomy classification and labeling.

Verifies that PRs are correctly classified into Tier 1 (auto-mergeable),
Tier 2 (needs-judgment), or Tier 3 (criticality:critical) based on changed file
paths and author metadata, strictly asserting against policy in tests/policy.toml.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

from classify_pr_risk import PRRiskClassifier  # noqa: E402


@pytest.fixture
def pr_policy() -> dict[str, object]:
    assert POLICY_FILE.exists(), "tests/policy.toml must exist"
    data = tomllib.loads(POLICY_FILE.read_text(encoding="utf-8"))
    assert "pr_risk" in data, "tests/policy.toml must contain [pr_risk] section"
    return data["pr_risk"]


def test_tier1_documentation_pr_is_auto_mergeable(pr_policy: dict[str, object]):
    """Pure docs and specs from a bot author are classified as Tier 1."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    files = ["specs/meta/doc-taxonomy.md", "docs/architecture.md", "references/evidence.md"]
    result = classifier.classify(files=files, author="botnicbot")

    tier1_label = str(pr_policy["tier1_label"])
    tier2_label = str(pr_policy["tier2_label"])
    tier3_labels = [str(lbl) for lbl in pr_policy["tier3_labels"]]  # type: ignore[union-attr]

    assert result.tier == 1
    assert tier1_label in result.labels
    assert tier2_label not in result.labels
    for label in tier3_labels:
        assert label not in result.labels


def test_policy_file_and_tests_escalate_to_tier2(pr_policy: dict[str, object]):
    """Modifying policy.toml or test suite must be Tier 2, never Tier 1 auto-mergeable."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    tier2_label = str(pr_policy["tier2_label"])
    tier1_label = str(pr_policy["tier1_label"])

    for file_path in ["tests/policy.toml", "tests/test_something.py"]:
        result = classifier.classify(files=[file_path], author="botnicbot")
        assert result.tier == 2, f"{file_path} must be Tier 2"
        assert tier2_label in result.labels
        assert tier1_label not in result.labels


def test_plugin_skills_and_prompts_escalate_to_tier2(pr_policy: dict[str, object]):
    """Modifying any plugin skill or prompt must be Tier 2, never Tier 1."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    tier2_label = str(pr_policy["tier2_label"])
    tier1_label = str(pr_policy["tier1_label"])

    test_paths = [
        "plugins/tools/skills/analyst/SKILL.md",
        "plugins/ida/skills/reconcile/SKILL.md",
        "plugins/rbg/rules/rules.md",
    ]
    for file_path in test_paths:
        result = classifier.classify(files=[file_path], author="botnicbot")
        assert result.tier == 2, f"{file_path} must be Tier 2"
        assert tier2_label in result.labels
        assert tier1_label not in result.labels


def test_pre_commit_config_escalates_to_tier2(pr_policy: dict[str, object]):
    """Modifying repository governance like .pre-commit-config.yaml must be Tier 2."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    result = classifier.classify(files=[".pre-commit-config.yaml"], author="botnicbot")
    assert result.tier == 2
    assert str(pr_policy["tier2_label"]) in result.labels
    assert str(pr_policy["tier1_label"]) not in result.labels


def test_tier3_paths_escalate_to_tier3(pr_policy: dict[str, object]):
    """Scholarly manuscripts or host infra files escalate to Tier 3."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    tier3_labels = [str(lbl) for lbl in pr_policy["tier3_labels"]]  # type: ignore[union-attr]
    tier1_label = str(pr_policy["tier1_label"])

    for file_path in ["tox/paper.md", "systemd/polecat.service", "launchd/agent.plist"]:
        result = classifier.classify(files=[file_path], author="botnicbot")
        assert result.tier == 3, f"{file_path} must be Tier 3"
        for label in tier3_labels:
            assert label in result.labels
        assert tier1_label not in result.labels


def test_human_author_escalates_any_pr_to_tier3(pr_policy: dict[str, object]):
    """PR authored by any human (not a bot) must escalate to Tier 3 even for docs."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    tier3_labels = [str(lbl) for lbl in pr_policy["tier3_labels"]]  # type: ignore[union-attr]
    tier1_label = str(pr_policy["tier1_label"])

    for human in ["nicsuzor", "external-contributor", "alice"]:
        result = classifier.classify(files=["specs/example.md"], author=human)
        assert result.tier == 3, f"PR by human '{human}' must be Tier 3"
        for label in tier3_labels:
            assert label in result.labels
        assert tier1_label not in result.labels


def test_empty_files_fails_fast(pr_policy: dict[str, object]):
    """Empty files list must fail closed by raising ValueError, never defaulting to Tier 1."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    with pytest.raises(ValueError, match="No changed files"):
        classifier.classify(files=[], author="botnicbot")


def test_missing_policy_keys_fails_fast():
    """Policy missing mandatory tier configuration must raise KeyError."""
    incomplete_policy = {"tier1_label": "triage:auto-mergeable"}
    with pytest.raises(KeyError):
        PRRiskClassifier.from_policy(incomplete_policy)


def test_sync_pr_labels_removes_stale_and_adds_target(monkeypatch: pytest.MonkeyPatch):
    """sync_pr_labels removes outdated tier labels and applies target tier labels."""
    from classify_pr_risk import sync_pr_labels

    calls: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs: object):
        calls.append(cmd)

        class DummyProc:
            stdout = '{"labels": [{"name": "triage:auto-mergeable"}, {"name": "other-label"}]}'

        return DummyProc()

    monkeypatch.setattr("subprocess.run", mock_run)

    target_labels = ["triage:needs-judgment"]
    all_tier_labels = ["triage:auto-mergeable", "triage:needs-judgment", "criticality:critical"]

    sync_pr_labels(pr_number=2984, target_labels=target_labels, all_tier_labels=all_tier_labels)

    assert len(calls) == 2
    assert calls[0] == ["gh", "pr", "view", "2984", "--json", "labels"]
    assert calls[1] == [
        "gh",
        "pr",
        "edit",
        "2984",
        "--add-label",
        "triage:needs-judgment",
        "--remove-label",
        "triage:auto-mergeable",
    ]
