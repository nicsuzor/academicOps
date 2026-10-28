"""Tests for hotfix evaluation and patch-only bump enforcement.

Verifies that:
1. Hotfix-designated changes are identified by label, commit prefix, or title.
2. Non-hotfix changes are recognized as requiring user approval (no auto-release).
3. Hotfix releases are constrained to strict patch-only bumps.
4. Auto-release decisions correctly permit hotfixes and block non-hotfixes.
5. Hotfix releases proposing non-patch increments fail fast without silent clamping.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from build.hotfix import (
    compute_next_patch,
    evaluate_hotfix_release,
    is_hotfix,
    is_patch_bump,
)

POLICY_FILE = Path(__file__).resolve().parent / "policy.toml"


@pytest.fixture(scope="module")
def hotfix_policy() -> dict[str, list[str]]:
    with open(POLICY_FILE, "rb") as f:
        data = tomllib.load(f)
    return data.get("hotfix", {})


def test_is_hotfix_matches_labels(hotfix_policy: dict[str, list[str]]) -> None:
    labels = hotfix_policy.get("hotfix_labels", ["hotfix"])
    for label in labels:
        assert is_hotfix(labels=[label], commit_messages=[])
        assert is_hotfix(labels=["other", label.upper()], commit_messages=[])


def test_is_hotfix_matches_prefixes(hotfix_policy: dict[str, list[str]]) -> None:
    prefixes = hotfix_policy.get("hotfix_prefixes", ["hotfix:"])
    for prefix in prefixes:
        msg = f"{prefix} fix null pointer exception"
        assert is_hotfix(labels=[], commit_messages=[msg])


def test_is_hotfix_matches_title_tags() -> None:
    assert is_hotfix(labels=[], commit_messages=[], pr_title="[hotfix] resolve crash on startup")
    assert is_hotfix(labels=[], commit_messages=[], pr_title="hotfix(engine): quick fix")


def test_is_hotfix_rejects_non_hotfix() -> None:
    assert not is_hotfix(labels=["enhancement"], commit_messages=["feat: add new CLI command"])
    assert not is_hotfix(labels=[], commit_messages=["chore: update uv.lock", "docs: fix typo"])
    assert not is_hotfix(labels=[], commit_messages=[], pr_title="feat: support new format")


def test_compute_next_patch_bumps_patch() -> None:
    assert compute_next_patch("0.10.26") == "0.10.27"
    assert compute_next_patch("1.0.0") == "1.0.1"
    assert compute_next_patch("v1.2.3") == "1.2.4"


def test_compute_next_patch_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid Python package version"):
        compute_next_patch("invalid-version")


def test_is_patch_bump() -> None:
    assert is_patch_bump("0.10.26", "0.10.27")
    assert is_patch_bump("1.0.0", "1.0.1")
    assert not is_patch_bump("0.10.26", "0.11.0")
    assert not is_patch_bump("0.10.26", "1.0.0")
    assert not is_patch_bump("0.10.26", "0.10.26")


def test_evaluate_hotfix_release_permits_hotfix_and_enforces_patch() -> None:
    decision = evaluate_hotfix_release(
        current_version="0.10.26",
        proposed_version="0.10.27",
        labels=["hotfix"],
        commit_messages=["fix: critical hook issue"],
        pr_title="fix: critical hook issue",
    )
    assert decision.is_hotfix is True
    assert decision.should_automerge is True
    assert decision.target_version == "0.10.27"
    assert "patch-only release approved" in decision.reason.lower()


def test_evaluate_hotfix_release_blocks_non_patch_bump_for_hotfix() -> None:
    # A hotfix proposing a minor bump must NOT be silently clamped; auto-merge must be blocked.
    decision = evaluate_hotfix_release(
        current_version="0.10.26",
        proposed_version="0.11.0",
        labels=["hotfix"],
        commit_messages=["hotfix: urgent repair"],
        pr_title="hotfix: urgent repair",
    )
    assert decision.is_hotfix is True
    assert decision.should_automerge is False
    assert decision.target_version == "0.11.0"
    assert "clamping forbidden" in decision.reason.lower()
    assert "waiting for user approval" in decision.reason.lower()


def test_evaluate_hotfix_release_blocks_non_hotfix() -> None:
    decision = evaluate_hotfix_release(
        current_version="0.10.26",
        proposed_version="0.11.0",
        labels=["feature"],
        commit_messages=["feat: add new feature"],
        pr_title="feat: add new feature",
    )
    assert decision.is_hotfix is False
    assert decision.should_automerge is False
    assert "waiting for user approval" in decision.reason.lower()


def test_hotfix_cli_dry_run() -> None:
    cmd_hotfix = [
        sys.executable,
        "-m",
        "build.hotfix",
        "--dry-run",
        "--current-version",
        "0.10.26",
        "--label",
        "hotfix",
        "--commit-message",
        "fix: resolve auth crash",
    ]
    res_hotfix = subprocess.run(cmd_hotfix, capture_output=True, text=True, check=False)
    assert res_hotfix.returncode == 0
    assert "HOTFIX: true" in res_hotfix.stdout
    assert "AUTO_MERGE: true" in res_hotfix.stdout
    assert "TARGET_VERSION: 0.10.27" in res_hotfix.stdout

    cmd_non_hotfix = [
        sys.executable,
        "-m",
        "build.hotfix",
        "--dry-run",
        "--current-version",
        "0.10.26",
        "--commit-message",
        "feat: new experimental capability",
    ]
    res_non_hotfix = subprocess.run(cmd_non_hotfix, capture_output=True, text=True, check=False)
    assert res_non_hotfix.returncode == 0
    assert "HOTFIX: false" in res_non_hotfix.stdout
    assert "AUTO_MERGE: false" in res_non_hotfix.stdout
    assert "waiting for user approval" in res_non_hotfix.stdout.lower()
