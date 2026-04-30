#!/usr/bin/env python3
"""Regression tests for issue #803.

P#65 (enforcement-map currency) MUST be a blocking REQUEST_CHANGES rule in the
rbg/enforcer prompt — never deferrable, never "may flag". A PR that adds a new
enforcement gate without updating the enforcement map in the same PR must be
caught at review time, not merged with a "fix it later" promise.

These tests are fixture-based regression checks: they assert the rule's literal
phrasing is present in the prompt and in HEURISTICS.md, and they verify a
sample PR diff (gate definition added, map untouched) matches the trigger
patterns the enforcer is told to watch for.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent / "aops-core"
RBG_PATH = PLUGIN_ROOT / "agents" / "rbg.md"
HEURISTICS_PATH = PLUGIN_ROOT / "HEURISTICS.md"

# Verbatim phrase from issue #803 acceptance criteria.
BLOCKING_PHRASE = (
    "If the PR adds, removes, or modifies an enforcement gate and "
    "`specs/enforcement-map.md` is not updated in the same PR, REQUEST_CHANGES."
)


# Fixture: a unified-diff snippet representing a PR that adds a new gate
# definition to aops-core/lib/gates/definitions.py and does NOT touch the
# enforcement map. The enforcer must REQUEST_CHANGES on this diff.
FIXTURE_PR_DIFF_GATE_WITHOUT_MAP = """\
diff --git a/aops-core/lib/gates/definitions.py b/aops-core/lib/gates/definitions.py
index 1111111..2222222 100644
--- a/aops-core/lib/gates/definitions.py
+++ b/aops-core/lib/gates/definitions.py
@@ -42,6 +42,15 @@ GATES: list[GateDef] = [
         tier="warn",
         scope="all",
     ),
+    GateDef(
+        name="new_secrets_scan",
+        event="PreToolUse",
+        rule_ids=("R8.4",),
+        tier="block",
+        scope="all",
+        description="Block tool calls that emit secrets to public surfaces.",
+    ),
 ]
diff --git a/aops-core/HEURISTICS.md b/aops-core/HEURISTICS.md
index 3333333..4444444 100644
--- a/aops-core/HEURISTICS.md
+++ b/aops-core/HEURISTICS.md
@@ -200,3 +200,5 @@ Some unrelated heuristic update here.
+
+(unrelated wording fix)
"""


# Fixture: the same PR but WITH the map updated. Enforcer must NOT
# REQUEST_CHANGES on this diff (P#65 satisfied).
FIXTURE_PR_DIFF_GATE_WITH_MAP = """\
diff --git a/aops-core/lib/gates/definitions.py b/aops-core/lib/gates/definitions.py
index 1111111..2222222 100644
--- a/aops-core/lib/gates/definitions.py
+++ b/aops-core/lib/gates/definitions.py
@@ -42,6 +42,15 @@ GATES: list[GateDef] = [
+    GateDef(
+        name="new_secrets_scan",
+        event="PreToolUse",
+        rule_ids=("R8.4",),
+        tier="block",
+        scope="all",
+        description="Block tool calls that emit secrets to public surfaces.",
+    ),
 ]
diff --git a/.agents/ENFORCEMENT-MAP.md b/.agents/ENFORCEMENT-MAP.md
index 5555555..6666666 100644
--- a/.agents/ENFORCEMENT-MAP.md
+++ b/.agents/ENFORCEMENT-MAP.md
@@ -25,3 +25,4 @@ Some prior row.
+| `new_secrets_scan` | PreToolUse | aops-core/lib/gates/definitions.py | R8.4 | All | block | Blocks secret emission |
"""


# Patterns the enforcer prompt cites as enforcement-gate touchpoints. These
# are the file paths whose modification triggers the P#65 obligation.
GATE_TOUCHPOINT_PATTERNS = [
    r"aops-core/lib/gates/definitions\.py",
    r"\.pre-commit-config\.yaml",
    r"settings\.json",
    r"policies/.*\.toml",
    r"aops-core/hooks/",
    r"aops-core/scripts/",
]

MAP_PATH_PATTERNS = [
    r"specs/enforcement-map\.md",
    r"\.agents/ENFORCEMENT-MAP\.md",
]


def _diff_touches_gate_definition(diff: str) -> bool:
    """True if the diff modifies any known gate-definition file."""
    return any(re.search(p, diff) for p in GATE_TOUCHPOINT_PATTERNS)


def _diff_touches_enforcement_map(diff: str) -> bool:
    """True if the diff modifies the enforcement map (under either path)."""
    return any(re.search(p, diff) for p in MAP_PATH_PATTERNS)


def enforcer_verdict_for_diff(diff: str, prompt: str) -> str:
    """Simulate the rbg/enforcer verdict for a PR diff against a prompt.

    The simulation is deterministic: it checks whether the prompt declares
    P#65 as a BLOCKING rule, and whether the diff matches the
    "gate-without-map" pattern. If both hold, the verdict is REQUEST_CHANGES.
    """
    if BLOCKING_PHRASE not in prompt:
        return "APPROVE"  # Rule isn't blocking in the prompt; can't request.
    if _diff_touches_gate_definition(diff) and not _diff_touches_enforcement_map(diff):
        return "REQUEST_CHANGES"
    return "APPROVE"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRbgPromptHasBlockingRule:
    """rbg.md must contain the literal blocking phrase from issue #803."""

    def test_rbg_md_exists(self) -> None:
        assert RBG_PATH.exists(), f"Missing {RBG_PATH}"

    def test_blocking_phrase_present(self) -> None:
        content = RBG_PATH.read_text()
        assert BLOCKING_PHRASE in content, (
            "rbg.md must contain the verbatim blocking phrase for P#65 "
            "(see issue #803 acceptance criteria)."
        )

    def test_blocking_section_marked(self) -> None:
        content = RBG_PATH.read_text()
        assert "Blocking Verdict Rules" in content or "BLOCKING" in content, (
            "rbg.md must explicitly mark P#65 as blocking, not a soft flag."
        )

    def test_no_deferrable_language_for_p65(self) -> None:
        content = RBG_PATH.read_text()
        # The rule must not be downgraded to soft language.
        bad_phrases = [
            "P#65 is deferrable",
            "may flag P#65",
            "P#65 may be deferred",
            "follow-up PR is acceptable",
        ]
        for bad in bad_phrases:
            assert bad not in content, f"rbg.md must not contain soft-flag language: {bad!r}"


class TestHeuristicsP65Tightened:
    """HEURISTICS.md P#65 must say the map is updated in the SAME PR."""

    def test_heuristics_exists(self) -> None:
        assert HEURISTICS_PATH.exists(), f"Missing {HEURISTICS_PATH}"

    def test_p65_section_present(self) -> None:
        content = HEURISTICS_PATH.read_text()
        assert "(P#65)" in content, "HEURISTICS.md must define P#65"

    def test_p65_says_same_pr(self) -> None:
        content = HEURISTICS_PATH.read_text()
        # Locate the P#65 section.
        match = re.search(
            r"##\s+Enforcement Changes Require enforcement-map\.md Update \(P#65\)(.+?)(?=\n##\s|\Z)",
            content,
            re.DOTALL,
        )
        assert match, "Could not locate P#65 section in HEURISTICS.md"
        section = match.group(1)
        assert "same PR" in section, "P#65 must explicitly require the map update in the SAME PR"
        # And must NOT permit deferral.
        assert "NOT permissible to defer" in section or "not permissible to defer" in section, (
            "P#65 must explicitly forbid deferring the map update"
        )


class TestEnforcerVerdictOnFixtureDiff:
    """End-to-end fixture: gate added without map update -> REQUEST_CHANGES."""

    @pytest.fixture
    def prompt(self) -> str:
        return RBG_PATH.read_text()

    def test_gate_without_map_triggers_request_changes(self, prompt: str) -> None:
        verdict = enforcer_verdict_for_diff(FIXTURE_PR_DIFF_GATE_WITHOUT_MAP, prompt)
        assert verdict == "REQUEST_CHANGES", (
            "PR diff that adds a gate without updating the enforcement map "
            "must be flagged REQUEST_CHANGES under P#65."
        )

    def test_gate_with_map_approves(self, prompt: str) -> None:
        verdict = enforcer_verdict_for_diff(FIXTURE_PR_DIFF_GATE_WITH_MAP, prompt)
        assert verdict == "APPROVE", "PR diff that adds a gate AND updates the map satisfies P#65."

    def test_simulator_recognises_gate_touchpoint(self) -> None:
        assert _diff_touches_gate_definition(FIXTURE_PR_DIFF_GATE_WITHOUT_MAP)

    def test_simulator_detects_missing_map_update(self) -> None:
        assert not _diff_touches_enforcement_map(FIXTURE_PR_DIFF_GATE_WITHOUT_MAP)

    def test_simulator_detects_present_map_update(self) -> None:
        assert _diff_touches_enforcement_map(FIXTURE_PR_DIFF_GATE_WITH_MAP)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
