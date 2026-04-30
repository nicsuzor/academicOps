"""Structural tests for the rbg PR Review Detection Rules.

These tests verify that the four detection rules are present in the rbg agent
prompt and properly referenced from the review-context descriptors. They are
prose-rule structural tests — they do not exercise the LLM's judgment, but
they prevent silent regression of the rule surface (the prose itself).

Replay scenarios that the rules must produce on a judging agent:

- PR #610 case (GH #621): docs-only diff for a claimed config move →
  criterion-substitution: BLOCK.
- GH #624 case: load-bearing structural inference about Gemini Policy
  Engine without runtime verification or disclosure →
  keystone-disclosure: REVISE.
- Diff containing `*.ts.net` or RFC1918 host literal in a production file →
  sensitive-data: BLOCK (or WARN in test fixtures).
- A clean substantive PR that edits production code matching its title with
  no private hosts and no unverified keystones → all four rules PASS,
  overall APPROVE.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RBG = REPO_ROOT / "aops-core" / "agents" / "rbg.md"
PR_CODE = REPO_ROOT / "aops-core" / "skills" / "strategic-review" / "review-contexts" / "pr-code.md"
PR_FRAMEWORK = (
    REPO_ROOT / "aops-core" / "skills" / "strategic-review" / "review-contexts" / "pr-framework.md"
)


@pytest.fixture(scope="module")
def rbg_text() -> str:
    return RBG.read_text(encoding="utf-8")


def test_pr_review_section_present(rbg_text: str) -> None:
    assert "## PR Review Detection Rules" in rbg_text, (
        "rbg.md missing PR Review Detection Rules section"
    )


@pytest.mark.parametrize(
    "heading",
    [
        "Rule 1 — Criterion Substitution Detector",
        "Rule 2 — Scope Awareness",
        "Rule 3 — Unverified-Keystone Disclosure",
        "Rule 4 — Sensitive-Data Scanner",
    ],
)
def test_each_rule_section_present(rbg_text: str, heading: str) -> None:
    assert heading in rbg_text, f"rbg.md missing rule heading: {heading}"


@pytest.mark.parametrize(
    "verdict_label",
    [
        "criterion-substitution:",
        "scope-error:",
        "keystone-disclosure:",
        "sensitive-data:",
    ],
)
def test_verdict_labels_present(rbg_text: str, verdict_label: str) -> None:
    assert verdict_label in rbg_text, f"rbg.md verdict block missing label: {verdict_label}"


def test_overall_verdict_format_specified(rbg_text: str) -> None:
    assert "Overall:" in rbg_text
    # Overall ladder must include all four verdict states.
    for state in ("BLOCK", "REVISE", "WARN", "APPROVE"):
        assert state in rbg_text, f"Verdict ladder missing state: {state}"


def test_sensitive_data_patterns_named(rbg_text: str) -> None:
    # Each canonical private-host pattern must be explicitly named so a
    # judging agent has the actual signature to match against.
    for pattern in [
        ".ts.net",
        "RFC1918",
        ".local",
        "10.0.0.0/8",
        "192.168.0.0/16",
        "172.16.0.0/12",
    ]:
        assert pattern in rbg_text, f"sensitive-data rule missing pattern: {pattern}"


def test_replay_scenarios_documented_in_test_module() -> None:
    """The module docstring must call out the three required replay cases."""
    here = Path(__file__).read_text(encoding="utf-8")
    for marker in ("PR #610", "#624", "ts.net"):
        assert marker in here, f"replay scenario marker missing: {marker}"


def test_pr_code_context_references_rules() -> None:
    text = PR_CODE.read_text(encoding="utf-8")
    assert "PR Review Detection Rules" in text, "pr-code.md must commission the new detection rules"


def test_pr_framework_context_references_rules() -> None:
    text = PR_FRAMEWORK.read_text(encoding="utf-8")
    assert "PR Review Detection Rules" in text, (
        "pr-framework.md must commission the new detection rules"
    )


def test_carve_outs_present(rbg_text: str) -> None:
    """Each rule must have at least one carve-out so the rules don't fire on
    legitimate cases (docs-only PRs, test-only PRs, RFC1918 ranges in a CIDR
    parser, disclosed unverified claims).
    """
    # Count occurrences of "Carve-outs:" — one per rule that needs them.
    matches = re.findall(r"Carve-outs?:", rbg_text)
    assert len(matches) >= 3, f"expected carve-outs for at least 3 rules, found {len(matches)}"
