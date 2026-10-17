"""Tests for PR risk taxonomy classification and labeling.

Verifies that PRs are correctly classified into Tier 1 (auto-mergeable),
Tier 2 (needs-judgment), or Tier 3 (criticality:critical) based on changed file
paths and author metadata, strictly asserting against policy in tests/policy.toml.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "pr_risk"
POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

# Import classifier under test (will fail before implementation in TDD)
from classify_pr_risk import PRRiskClassifier, classify_pr_payload  # noqa: E402


@pytest.fixture
def pr_policy() -> dict[str, object]:
    assert POLICY_FILE.exists(), "tests/policy.toml must exist"
    data = tomllib.loads(POLICY_FILE.read_text(encoding="utf-8"))
    assert "pr_risk" in data, "tests/policy.toml must contain [pr_risk] section"
    return data["pr_risk"]


def test_fixture_prs_classified_and_labeled_by_tier(pr_policy: dict[str, object]):
    """Verify all JSON PR fixtures are classified and labeled according to policy."""
    classifier = PRRiskClassifier.from_policy(pr_policy)

    tier1_label = pr_policy["tier1_label"]
    tier2_label = pr_policy["tier2_label"]
    tier3_labels = pr_policy["tier3_labels"]

    fixture_files = sorted(FIXTURES_DIR.glob("*.json"))
    assert len(fixture_files) >= 3, "Must have fixtures for Tier 1, 2, and 3"

    for fixture_file in fixture_files:
        payload = json.loads(fixture_file.read_text(encoding="utf-8"))
        result = classifier.classify(files=payload["files"], author=payload.get("author", ""))

        assert result.tier == payload["expected_tier"], (
            f"Fixture {fixture_file.name} expected tier {payload['expected_tier']}, got {result.tier}"
        )

        expected_labels = payload["expected_labels"]
        for label in expected_labels:
            assert label in result.labels, (
                f"Fixture {fixture_file.name} missing expected label '{label}' in {result.labels}"
            )

        if result.tier == 1:
            assert tier1_label in result.labels
            assert tier2_label not in result.labels
        elif result.tier == 2:
            assert tier2_label in result.labels
            assert tier1_label not in result.labels
        elif result.tier == 3:
            for expected_label in tier3_labels:
                assert expected_label in result.labels
            assert tier1_label not in result.labels


def test_tier_precedence_tier3_overrides_tier1_and_tier2(pr_policy: dict[str, object]):
    """If a PR touches both Tier 1/2 files and a Tier 3 file (e.g. tox/paper.md), it must be Tier 3."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    files = [
        "specs/meta/doc-taxonomy.md",  # Tier 1
        "plugins/ida/agents/ida.md",  # Tier 2
        "tox/paper.md",  # Tier 3
    ]
    result = classifier.classify(files=files, author="agent")
    assert result.tier == 3
    for label in pr_policy["tier3_labels"]:
        assert label in result.labels


def test_tier_precedence_tier2_overrides_tier1(pr_policy: dict[str, object]):
    """If a PR touches Tier 1 files and a Tier 2 file, it must be Tier 2."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    files = [
        "specs/meta/doc-taxonomy.md",  # Tier 1
        "plugins/ida/skills/reconcile/SKILL.md",  # Tier 2
    ]
    result = classifier.classify(files=files, author="agent")
    assert result.tier == 2
    assert pr_policy["tier2_label"] in result.labels
    assert pr_policy["tier1_label"] not in result.labels


def test_human_author_escalates_to_tier3(pr_policy: dict[str, object]):
    """PR authored by principal is always Tier 3, regardless of files touched."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    files = ["specs/meta/doc-taxonomy.md"]  # pure Tier 1 file
    result = classifier.classify(files=files, author="nicsuzor")
    assert result.tier == 3
    for label in pr_policy["tier3_labels"]:
        assert label in result.labels


def test_unclassified_code_defaults_to_tier2(pr_policy: dict[str, object]):
    """Arbitrary/unrecognized application code outside low-risk allowlist defaults to Tier 2."""
    classifier = PRRiskClassifier.from_policy(pr_policy)
    files = ["src/core_engine.py"]
    result = classifier.classify(files=files, author="agent")
    assert result.tier == 2
    assert pr_policy["tier2_label"] in result.labels


def test_cli_classify_fixture_pr():
    """Verify scripts/classify_pr_risk.py CLI runs against fixture file and outputs labels."""
    fixture = FIXTURES_DIR / "pr_tier1_docs.json"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "classify_pr_risk.py"),
        "--fixture",
        str(fixture),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "triage:auto-mergeable" in proc.stdout
    assert "Tier 1" in proc.stdout


def test_classify_pr_payload():
    """Verify classify_pr_payload helper function classifies payload dictionary."""
    payload = {"files": ["specs/example.md"], "author": "agent"}
    result = classify_pr_payload(payload)
    assert result.tier == 1
    assert "triage:auto-mergeable" in result.labels
