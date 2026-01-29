"""Tests for GateResult model and Router formatting logic."""

import pytest
import json
from lib.gate_model import GateResult, GateVerdict
from hooks.router import format_for_gemini, format_for_claude, merge_outputs


class TestGateModel:
    """Tests for GateResult dataclass."""

    def test_gate_result_json_serialization(self):
        result = GateResult(
            verdict=GateVerdict.DENY,
            system_message="Access Denied",
            context_injection="Do this instead",
            metadata={"rule": "compliance"},
        )
        json_out = result.to_json()
        assert json_out["verdict"] == "deny"
        assert json_out["system_message"] == "Access Denied"
        assert json_out["context_injection"] == "Do this instead"
        assert json_out["metadata"]["rule"] == "compliance"


class TestRouterFormatting:
    """Tests for format_for_gemini and format_for_claude."""

    def test_format_for_gemini_deny(self):
        canonical = {
            "verdict": "deny",
            "system_message": "Blocked",
            "context_injection": "Reasoning here",
        }
        output = format_for_gemini(canonical, "BeforeTool")
        assert output["decision"] == "deny"
        assert output["systemMessage"] == "Blocked"
        assert output["reason"] == "Reasoning here"

    def test_format_for_gemini_allow_with_context(self):
        canonical = {"verdict": "allow", "context_injection": "Info"}
        output = format_for_gemini(canonical, "BeforeTool")
        # Allow implies no 'decision' field in Gemini typically, or decision="allow"
        # The formatter implementation only sets decision="deny" if verdict="deny"
        assert "decision" not in output
        assert output["reason"] == "Info"

    def test_format_for_claude_deny(self):
        canonical = {
            "verdict": "deny",
            "system_message": "Blocked",
            "context_injection": "Reasoning here",
        }
        output = format_for_claude(canonical, "PreToolUse")
        assert output["systemMessage"] == "Blocked"
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert output["hookSpecificOutput"]["additionalContext"] == "Reasoning here"

    def test_format_for_claude_updated_input(self):
        canonical = {
            "verdict": "allow",
            "metadata": {"updated_input": {"arg": "value"}},
        }
        output = format_for_claude(canonical, "PreToolUse")
        assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
        assert output["hookSpecificOutput"]["updatedInput"] == {"arg": "value"}

    def test_format_for_gemini_updated_input(self):
        # Gemini formatter supports updatedInput now?
        # I added support in format_for_gemini:
        #     if "updated_input" in metadata:
        #        result["updatedInput"] = metadata["updated_input"]
        # So yes, it should pass it through as top-level field?
        # Let's check my implementation of format_for_gemini in Step 96.
        # Yes: result["updatedInput"] = metadata["updated_input"]

        canonical = {
            "verdict": "allow",
            "metadata": {"updated_input": {"arg": "value"}},
        }
        output = format_for_gemini(canonical, "BeforeTool")
        assert output["updatedInput"] == {"arg": "value"}


class TestRouterMerge:
    """Tests for merge_outputs logic."""

    def test_merge_metadata(self):
        out1 = {"verdict": "allow", "metadata": {"updated_input": {"a": 1}}}
        out2 = {
            "verdict": "warn",
            "context_injection": "Warning",
            "metadata": {"other": "value"},
        }

        merged = merge_outputs([out1, out2], "PreToolUse")

        # Verdict: warn > allow
        assert merged["verdict"] == "warn"
        assert merged["context_injection"] == "Warning"
        assert merged["metadata"]["updated_input"] == {"a": 1}
        assert merged["metadata"]["other"] == "value"

    def test_merge_legacy_ignored(self):
        # Legacy fields should be ignored now as we removed the else branch
        legacy = {"hookSpecificOutput": {"permissionDecision": "deny"}}
        canonical = {"verdict": "allow"}

        merged = merge_outputs([legacy, canonical], "PreToolUse")

        # 'legacy' input has NO 'verdict', so it should be skipped by the new loop logic
        # merge_outputs loop: if "verdict" in out: ...
        # So legacy input is completely ignored.
        # Thus result should be 'allow' (from canonical)

        assert merged["verdict"] == "allow"
        # And no 'deny' from legacy
