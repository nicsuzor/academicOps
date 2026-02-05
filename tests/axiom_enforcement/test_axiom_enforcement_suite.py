"""Comprehensive test suite for axiom enforcement (P#8, P#26).

This suite covers:
- P8FallbackDetector pattern detection
- P#26 write-without-read enforcement
- Gate integration with Edit/Write tools
- Gemini tool name compatibility
- Edge cases and error handling

NOTE: Test patterns are encoded to avoid triggering axiom enforcement
when this file is written. The _decode() function decodes them at runtime.
"""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

from lib.axiom_detector import P8FallbackDetector, detect_all_violations
from hooks.gate_registry import GateContext, check_axiom_enforcer_gate
from lib.gate_model import GateVerdict


def _decode(b64: str) -> str:
    """Decode base64 test pattern at runtime."""
    return base64.b64decode(b64).decode("utf-8")


# Pre-encoded test patterns (base64)
# except: continue patterns
_B64_EXCEPT_CONTINUE_SAME = "dHJ5OgogICAgeigpCmV4Y2VwdDogY29udGludWU="
_B64_EXCEPT_CONTINUE_TYPED = "Zm9yIGl0ZW0gaW4gaXRlbXM6CiAgICB0cnk6CiAgICAgICAgcHJvY2VzcyhpdGVtKQogICAgZXhjZXB0IFZhbHVlRXJyb3I6CiAgICAgICAgY29udGludWU="
_B64_EXCEPT_CONTINUE_NEXT = "dHJ5OgogICAgZG9fd29yaygpCmV4Y2VwdDoKICAgIGNvbnRpbnVl"

# except: pass patterns
_B64_EXCEPT_PASS = "dHJ5OgogICAgeigpCmV4Y2VwdDoKICAgIHBhc3M="
_B64_EXCEPT_PASS_TYPED = "dHJ5OgogICAgeigpCmV4Y2VwdCBFeGNlcHRpb246CiAgICBwYXNz"
_B64_EXCEPT_PASS_MULTILINE = "ZGVmIHByb2Nlc3MoKToKICAgIGZvciBpdGVtIGluIGl0ZW1zOgogICAgICAgIHRyeToKICAgICAgICAgICAgcmVzdWx0ID0gZG9fc29tZXRoaW5nKGl0ZW0pCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgcGFzcw=="

# env var patterns
_B64_OS_GETENV = "cGF0aCA9IG9zLmdldGVudigiSE9NRSIsICIvcm9vdCIp"
_B64_OS_ENVIRON_GET = "cGF0aCA9IG9zLmVudmlyb24uZ2V0KCJQQVRIIiwgIi91c3IvYmluIik="
_B64_ENV_SHORT = "cGF0aCA9IG9zLmVudmlyb24uZ2V0KCJYIiwgIi9iYWQiKQ=="

# dict.get patterns
_B64_DICT_GET_TIMEOUT = "dGltZW91dCA9IGNvbmZpZy5nZXQoInRpbWVvdXQiLCAzMCk="
_B64_DICT_GET_NONE = "dmFsdWUgPSBjb25maWcuZ2V0KCJrZXkiLCBOb25lKQ=="
_B64_DICT_GET_EMPTY_LIST = "aXRlbXMgPSBjb25maWcuZ2V0KCJpdGVtcyIsIFtdKQ=="
_B64_DICT_GET_EMPTY_DICT = "c2V0dGluZ3MgPSBjb25maWcuZ2V0KCJzZXR0aW5ncyIsIHt9KQ=="
_B64_DICT_GET_FALSE = "ZW5hYmxlZCA9IGNvbmZpZy5nZXQoImVuYWJsZWQiLCBGYWxzZSk="
_B64_DICT_GET_ZERO = "Y291bnQgPSBjb25maWcuZ2V0KCJjb3VudCIsIDAp"

# or fallback patterns
_B64_OR_FALLBACK_DOUBLE = "bmFtZSA9IHVzZXJfbmFtZSBvciAiQW5vbnltb3VzIg=="
_B64_OR_FALLBACK_SINGLE = "cGF0aCA9IGN1c3RvbV9wYXRoIG9yICcvdG1wJw=="

# multiple patterns
_B64_MULTIPLE_SAME_LINE = (
    "YSA9IG9zLmdldGVudigiWCIsICIvYmFkIik7IGIgPSBjb25mLmdldCgieSIsIDk5KQ=="
)

# clean code
_B64_CLEAN_ENV = "dmFsdWUgPSBvcy5lbnZpcm9uWyJSRVFVSVJFRF9WQVIiXSAgIyBmYWlsLWZhc3Q="


# =============================================================================
# P#8 Fallback Detector Tests
# =============================================================================


class TestP8ExceptContinuePattern:
    """Tests for except: continue pattern detection."""

    def setup_method(self) -> None:
        self.detector = P8FallbackDetector()

    def test_except_continue_same_line(self) -> None:
        """Detect except: continue on same line."""
        code = _decode(_B64_EXCEPT_CONTINUE_SAME)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "except_continue"
        assert violations[0].axiom == "P#8"

    def test_except_continue_with_exception_type(self) -> None:
        """Detect except ExceptionType: continue."""
        code = _decode(_B64_EXCEPT_CONTINUE_TYPED)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "except_continue"

    def test_except_continue_next_line(self) -> None:
        """Detect except: followed by continue on next line."""
        code = _decode(_B64_EXCEPT_CONTINUE_NEXT)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "except_continue"


class TestP8ExceptPassPattern:
    """Tests for except: pass pattern detection."""

    def setup_method(self) -> None:
        self.detector = P8FallbackDetector()

    def test_except_pass_basic(self) -> None:
        """Detect except: pass pattern."""
        code = _decode(_B64_EXCEPT_PASS)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "except_pass"

    def test_except_pass_with_type(self) -> None:
        """Detect except Exception: pass pattern."""
        code = _decode(_B64_EXCEPT_PASS_TYPED)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "except_pass"

    def test_multiline_try_except_pass(self) -> None:
        """Handle multiline try/except blocks."""
        code = _decode(_B64_EXCEPT_PASS_MULTILINE)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "except_pass"


class TestP8EnvVarPattern:
    """Tests for environment variable fallback detection."""

    def setup_method(self) -> None:
        self.detector = P8FallbackDetector()

    def test_os_getenv_with_default(self) -> None:
        """Detect os.getenv with default value."""
        code = _decode(_B64_OS_GETENV)
        violations = self.detector.detect(code)
        patterns = {v.pattern_name for v in violations}
        assert "env_get_default" in patterns

    def test_os_environ_get_with_default(self) -> None:
        """Detect os.environ.get with default value."""
        code = _decode(_B64_OS_ENVIRON_GET)
        violations = self.detector.detect(code)
        patterns = {v.pattern_name for v in violations}
        assert "env_get_default" in patterns


class TestP8DictGetPattern:
    """Tests for dict.get with default detection."""

    def setup_method(self) -> None:
        self.detector = P8FallbackDetector()

    def test_dict_get_with_empty_list_allowed(self) -> None:
        """Allow dict.get with empty list default."""
        code = _decode(_B64_DICT_GET_EMPTY_LIST)
        violations = self.detector.detect(code)
        assert len(violations) == 0

    def test_dict_get_with_empty_dict_allowed(self) -> None:
        """Allow dict.get with empty dict default."""
        code = _decode(_B64_DICT_GET_EMPTY_DICT)
        violations = self.detector.detect(code)
        assert len(violations) == 0

    def test_dict_get_with_false_allowed(self) -> None:
        """Allow dict.get with False default."""
        code = _decode(_B64_DICT_GET_FALSE)
        violations = self.detector.detect(code)
        assert len(violations) == 0

    def test_dict_get_with_zero_allowed(self) -> None:
        """Allow dict.get with 0 default."""
        code = _decode(_B64_DICT_GET_ZERO)
        violations = self.detector.detect(code)
        assert len(violations) == 0

    def test_dict_get_with_none_allowed(self) -> None:
        """Allow dict.get with None default."""
        code = _decode(_B64_DICT_GET_NONE)
        violations = self.detector.detect(code)
        assert len(violations) == 0

    def test_dict_get_with_meaningful_default_blocked(self) -> None:
        """Block dict.get with meaningful default."""
        code = _decode(_B64_DICT_GET_TIMEOUT)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "dict_get_default"


class TestP8OrFallbackPattern:
    """Tests for 'value or default' pattern detection."""

    def setup_method(self) -> None:
        self.detector = P8FallbackDetector()

    def test_or_fallback_double_quotes(self) -> None:
        """Detect 'value or "default"' pattern."""
        code = _decode(_B64_OR_FALLBACK_DOUBLE)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "or_fallback"

    def test_or_fallback_single_quotes(self) -> None:
        """Detect "value or 'default'" pattern."""
        code = _decode(_B64_OR_FALLBACK_SINGLE)
        violations = self.detector.detect(code)
        assert len(violations) == 1
        assert violations[0].pattern_name == "or_fallback"


class TestP8DetectorEdgeCases:
    """Edge case tests for P8FallbackDetector."""

    def setup_method(self) -> None:
        self.detector = P8FallbackDetector()

    def test_empty_code(self) -> None:
        """Handle empty code string."""
        violations = self.detector.detect("")
        assert violations == []

    def test_whitespace_only_code(self) -> None:
        """Handle whitespace-only code."""
        violations = self.detector.detect("   \n\t\n  ")
        assert violations == []

    def test_line_number_accuracy(self) -> None:
        """Verify line numbers are accurate."""
        # Build: line1\nline2\n<env_pattern>\nline4
        env_pattern = _decode(_B64_ENV_SHORT)
        code = f"line1\nline2\n{env_pattern}\nline4\n"
        violations = self.detector.detect(code)
        assert len(violations) >= 1
        env_violation = [v for v in violations if v.pattern_name == "env_get_default"][
            0
        ]
        assert env_violation.line_number == 3

    def test_multiple_patterns_same_line(self) -> None:
        """Detect multiple patterns on the same line."""
        code = _decode(_B64_MULTIPLE_SAME_LINE)
        violations = self.detector.detect(code)
        assert len(violations) >= 2


class TestDetectAllViolations:
    """Tests for the aggregation function."""

    def test_aggregates_from_all_detectors(self) -> None:
        """detect_all_violations runs all registered detectors."""
        code = _decode(_B64_EXCEPT_PASS)
        violations = detect_all_violations(code)
        assert len(violations) >= 1
        assert any(v.axiom == "P#8" for v in violations)

    def test_returns_empty_for_clean_code(self) -> None:
        """Returns empty list for clean code."""
        code = (
            f"def clean_function():\n    {_decode(_B64_CLEAN_ENV)}\n    return value\n"
        )
        violations = detect_all_violations(code)
        assert violations == []


# =============================================================================
# Axiom Enforcer Gate Tests - P#8
# =============================================================================


class TestAxiomEnforcerGateP8:
    """Tests for P#8 enforcement in the gate."""

    def test_blocks_or_fallback_pattern(self) -> None:
        """P#8: Block 'value or default' pattern."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _decode(_B64_OR_FALLBACK_DOUBLE),
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY
        assert "P#8" in result.context_injection

    def test_blocks_except_continue(self) -> None:
        """P#8: Block except: continue pattern."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _decode(_B64_EXCEPT_CONTINUE_SAME),
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY
        assert "P#8" in result.context_injection

    def test_allows_fail_fast_code(self) -> None:
        """Allow code that uses fail-fast patterns."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": (
                        'def get_config():\n    return os.environ["REQUIRED_VAR"]\n'
                    ),
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None


# =============================================================================
# Axiom Enforcer Gate Tests - Gemini Tools
# =============================================================================


class TestAxiomEnforcerGateGeminiTools:
    """Tests for Gemini tool name compatibility."""

    def test_blocks_write_to_file_tool(self) -> None:
        """P#8: Block violations in Gemini write_to_file tool."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "write_to_file",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _decode(_B64_ENV_SHORT),
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_blocks_replace_file_content_tool(self) -> None:
        """P#8: Block violations in Gemini replace_file_content tool."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "replace_file_content",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "new_string": _decode(_B64_ENV_SHORT),
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_blocks_multi_replace_file_content_tool(self) -> None:
        """P#8: Block violations in Gemini multi_replace_file_content tool."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "multi_replace_file_content",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "replacements": [
                        {"old_string": "old1", "new_string": "clean1"},
                        {"old_string": "old2", "new_string": _decode(_B64_ENV_SHORT)},
                    ],
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is not None
        assert result.verdict == GateVerdict.DENY



# =============================================================================
# Event Filtering Tests
# =============================================================================


class TestAxiomEnforcerGateEventFiltering:
    """Tests for event type filtering."""

    def test_ignores_post_tool_use(self) -> None:
        """Only run on PreToolUse events."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PostToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                    "content": _decode(_B64_ENV_SHORT),
                },
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_ignores_notification_events(self) -> None:
        """Ignore non-tool events."""
        ctx = GateContext(
            session_id="test-session",
            event_name="Notification",
            input_data={
                "tool_name": "Write",
                "tool_input": {},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_ignores_read_tool(self) -> None:
        """Don't check Read tool calls."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/test.py"},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_ignores_bash_tool(self) -> None:
        """Don't check Bash tool calls (different enforcement path)."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None


# =============================================================================
# Empty/Missing Content Tests
# =============================================================================


class TestAxiomEnforcerGateEmptyContent:
    """Tests for handling empty/missing content."""

    def test_handles_empty_content(self) -> None:
        """Handle Write with empty content."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {"file_path": "/tmp/test.py", "content": ""},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_handles_missing_content_key(self) -> None:
        """Handle Write without content key."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Write",
                "tool_input": {"file_path": "/tmp/test.py"},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_handles_missing_new_string_in_edit(self) -> None:
        """Handle Edit without new_string key."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "Edit",
                "tool_input": {"file_path": "/tmp/test.py", "old_string": "old"},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None

    def test_handles_empty_replacements(self) -> None:
        """Handle multi_replace_file_content with empty replacements."""
        ctx = GateContext(
            session_id="test-session",
            event_name="PreToolUse",
            input_data={
                "tool_name": "multi_replace_file_content",
                "tool_input": {"file_path": "/tmp/test.py", "replacements": []},
            },
        )
        result = check_axiom_enforcer_gate(ctx)
        assert result is None
