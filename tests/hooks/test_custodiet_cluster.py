"""Tests for the custodiet reliability cluster fixes.

Covers four issues filed against the custodiet compliance gate:
  #314 - Empty session narrative (resilient JSONL parsing)
  #319 - Mid-work false BLOCK (defer enforcement during active todo)
  #338 - WARN inertia (WARN on Stop surfaces via systemMessage)
  #331 - O(n²) token cost (memoised audit file, skip re-parse)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gate_types import GateState
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_timestamp(offset: int = 0) -> str:
    from datetime import UTC, datetime, timedelta

    base = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
    return (base + timedelta(seconds=offset)).isoformat().replace("+00:00", "Z")


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _make_state() -> SessionState:
    return SessionState.create("test-custodiet-cluster")


def _make_ctx(**kwargs) -> HookContext:
    defaults = dict(session_id="test-custodiet-cluster", hook_event="PreToolUse")
    defaults.update(kwargs)
    return HookContext(**defaults)


@pytest.fixture(autouse=True)
def _reinit_gates(monkeypatch, tmp_path):
    """Use deterministic gate-mode env vars so tests are isolated from host."""
    import importlib

    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    monkeypatch.setenv("QA_GATE_MODE", "block")
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.setenv("HYDRATION_GATE_MODE", "off")
    monkeypatch.setenv("IDA_GATE_MODE", "warn")
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", "50")

    if "hooks.gate_config" in sys.modules:
        # sys.modules["hooks.gate_config"]._reset_gate_mode_cache()
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


# ===========================================================================
# #314 – Empty session narrative: resilient JSONL parsing
# ===========================================================================


class TestResilientJsonlParsing:
    """_parse_jsonl_file must not abort on malformed JSONL lines."""

    def test_null_message_field_is_skipped(self, tmp_path):
        """Entry with null message is skipped; valid entries are still parsed."""
        from lib.transcript_parser import SessionProcessor

        transcript = tmp_path / "session.jsonl"
        entries = [
            {"type": "user", "uuid": "bad", "message": None},  # corrupt
            {
                "type": "user",
                "uuid": "good",
                "timestamp": _make_timestamp(0),
                "message": {"content": [{"type": "text", "text": "Hello"}]},
            },
        ]
        _write_jsonl(transcript, entries)

        processor = SessionProcessor()
        _, parsed, _ = processor.parse_session_file(transcript, load_agents=False, load_hooks=False)
        # Corrupt line is skipped; valid entry is present
        assert len(parsed) == 1
        assert parsed[0].uuid == "good"

    def test_missing_message_key_is_skipped(self, tmp_path):
        """Entry without any message key does not crash the parser."""
        from lib.transcript_parser import SessionProcessor

        transcript = tmp_path / "session.jsonl"
        entries = [
            {"type": "assistant", "uuid": "no-msg"},  # missing message
            {
                "type": "user",
                "uuid": "ok",
                "timestamp": _make_timestamp(0),
                "message": {"content": [{"type": "text", "text": "ok"}]},
            },
        ]
        _write_jsonl(transcript, entries)

        processor = SessionProcessor()
        _, parsed, _ = processor.parse_session_file(transcript, load_agents=False, load_hooks=False)
        assert any(e.uuid == "ok" for e in parsed)

    def test_build_audit_context_nonempty_after_partial_corrupt(self, tmp_path):
        """build_audit_session_context returns non-empty when some lines are corrupt."""
        from lib.session_reader import build_audit_session_context

        transcript = tmp_path / "session.jsonl"
        _write_jsonl(
            transcript,
            [
                {"type": "user", "uuid": "bad", "message": None},
                {
                    "type": "user",
                    "uuid": "u1",
                    "timestamp": _make_timestamp(0),
                    "message": {"content": [{"type": "text", "text": "fix the parser bug"}]},
                },
                {
                    "type": "assistant",
                    "uuid": "a1",
                    "timestamp": _make_timestamp(1),
                    "message": {"content": [{"type": "text", "text": "Sure!"}]},
                },
            ],
        )
        result = build_audit_session_context(str(transcript))
        assert len(result) > 0
        assert result not in ("(Empty session)", "(No transcript path available)")
        assert "fix the parser bug" in result


# ===========================================================================
# #319 – Mid-work false BLOCK: defer enforcement during active todo
# ===========================================================================


class TestMidEditDeferral:
    """Enforcer must not block when agent has an in-progress todo item."""

    def _state_at_threshold(self, has_in_progress: bool = False) -> SessionState:
        from hooks.gate_config import ENFORCER_TOOL_CALL_THRESHOLD

        state = _make_state()
        state.gates["enforcer"].ops_since_open = ENFORCER_TOOL_CALL_THRESHOLD
        state.gates["enforcer"].metrics["has_in_progress_todo"] = has_in_progress
        return state

    def test_blocks_without_in_progress_todo(self, router):
        """Enforcer blocks at threshold when no todo is in-progress."""
        state = self._state_at_threshold(has_in_progress=False)
        ctx = _make_ctx(hook_event="PreToolUse", tool_name="Edit", tool_input={"file_path": "x.py"})

        result = router._dispatch_gates(ctx, state)

        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_allows_when_in_progress_todo(self, router):
        """Enforcer defers block when agent has an in-progress todo item."""
        state = self._state_at_threshold(has_in_progress=True)
        ctx = _make_ctx(hook_event="PreToolUse", tool_name="Edit", tool_input={"file_path": "x.py"})

        result = router._dispatch_gates(ctx, state)

        # Should allow (or at most WARN) — mid-edit deferral active
        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                "Enforcer must not BLOCK when agent has an in-progress todo. "
                f"Got verdict={result.verdict}"
            )

    def test_todowrite_trigger_sets_in_progress_metric(self, router):
        """PostToolUse on TodoWrite with in-progress item sets gate metric."""
        state = _make_state()
        todos = [
            {"content": "Step 1", "status": "completed"},
            {"content": "Step 2", "status": "in_progress"},
            {"content": "Step 3", "status": "pending"},
        ]
        ctx = _make_ctx(
            hook_event="PostToolUse",
            tool_name="TodoWrite",
            tool_input={"todos": todos},
        )

        router._dispatch_gates(ctx, state)

        assert state.gates["enforcer"].metrics.get("has_in_progress_todo") is True

    def test_todowrite_trigger_clears_flag_when_no_in_progress(self, router):
        """PostToolUse on TodoWrite with all completed clears the metric."""
        state = _make_state()
        state.gates["enforcer"].metrics["has_in_progress_todo"] = True

        todos = [
            {"content": "Step 1", "status": "completed"},
            {"content": "Step 2", "status": "completed"},
        ]
        ctx = _make_ctx(
            hook_event="PostToolUse",
            tool_name="TodoWrite",
            tool_input={"todos": todos},
        )

        router._dispatch_gates(ctx, state)

        assert state.gates["enforcer"].metrics.get("has_in_progress_todo") is False


# ===========================================================================
# #338 – WARN inertia: WARN on Stop surfaces in AGENT context, not user chat
#
# Originally fixed in #1187 by copying context_injection into stopReason +
# systemMessage. That channel turned out to be user-visible only — the
# advisory leaked to the user transcript while the agent saw nothing
# (aops-d10e7db6). Correct routing: WARN-with-context upgrades to
# decision="block" + reason so the agent reads the advisory on its next
# turn. The internal verdict stays "warn" so the safety net (auto-approve
# after 5 blocks/2min) is not tripped by routine RBG advisories.
# ===========================================================================


class TestWarnStopSurface:
    """WARN verdicts on Stop events must reach the agent, not the user."""

    def test_warn_stop_routes_advisory_to_agent(self, router):
        """WARN on Stop with context_injection routes to agent via decision=block + reason."""

        # Build a WARN result that mimics IDA / RBG advisory
        warn_result = GateResult.warn(
            system_message=None,
            context_injection="<SYSTEM HOOK INSTRUCTION>Proof required</SYSTEM HOOK INSTRUCTION>",
        )
        canonical = router._gate_result_to_canonical(warn_result)

        output = router.output_for_claude(canonical, "Stop")

        # decision="block" is the only Stop channel that feeds text to the agent
        assert output.decision == "block", (
            "WARN on Stop with advisory must upgrade to decision=block so the "
            "agent reads the advisory on its next turn (aops-d10e7db6). "
            f"got decision={output.decision!r}"
        )
        assert output.reason == "<SYSTEM HOOK INSTRUCTION>Proof required</SYSTEM HOOK INSTRUCTION>"
        # Must NOT leak the advisory to user-visible channels.
        assert output.stopReason is None or "SYSTEM HOOK INSTRUCTION" not in (
            output.stopReason or ""
        ), "Advisory must not leak into user-visible stopReason"
        assert output.systemMessage is None or "SYSTEM HOOK INSTRUCTION" not in (
            output.systemMessage or ""
        ), "Advisory must not leak into user-visible systemMessage"

    def test_warn_stop_without_context_does_not_block(self, router):
        """WARN on Stop without context_injection must still approve."""
        warn_result = GateResult.warn(
            system_message="just a note",
            context_injection=None,
        )
        canonical = router._gate_result_to_canonical(warn_result)
        output = router.output_for_claude(canonical, "Stop")
        # No advisory payload → no need to upgrade to block
        assert output.decision == "approve"

    def test_deny_stop_still_blocks(self, router):
        """DENY on Stop must still block (regression guard)."""
        deny_result = GateResult.deny(
            system_message="Handover required",
            context_injection="please run /end-session",
        )
        canonical = router._gate_result_to_canonical(deny_result)
        output = router.output_for_claude(canonical, "Stop")
        assert output.decision == "block"
        # Advisory in reason (agent-visible); short summary in stopReason
        # (user-visible).
        assert output.reason == "please run /end-session"
        assert output.stopReason == "Handover required"

    def test_warn_stop_with_only_system_message_user_facing(self, router):
        """WARN on Stop with only system_message (no advisory) stays user-facing."""
        warn_result = GateResult.warn(
            system_message="Reminder: show your work",
            context_injection=None,
        )
        canonical = router._gate_result_to_canonical(warn_result)
        output = router.output_for_claude(canonical, "Stop")
        # system_message-only WARN is a short user-facing note — no upgrade.
        assert output.decision == "approve"
        assert output.stopReason == "Reminder: show your work"
        assert output.systemMessage == "Reminder: show your work"

    def test_warn_pretooluse_uses_additional_context(self, router):
        """WARN on PreToolUse still routes to additionalContext (unchanged)."""
        warn_result = GateResult.warn(
            system_message="Caution",
            context_injection="watch out",
        )
        canonical = router._gate_result_to_canonical(warn_result)
        output = router.output_for_claude(canonical, "PreToolUse")
        assert output.hookSpecificOutput is not None
        assert output.hookSpecificOutput.additionalContext == "watch out"
        assert output.hookSpecificOutput.permissionDecision == "allow"

    def test_warn_stop_does_not_emit_hook_specific_output(self, router):
        """WARN on Stop must NOT emit hookSpecificOutput — Claude Code rejects it."""
        warn_result = GateResult.warn(
            system_message=None,
            context_injection="<SYSTEM HOOK INSTRUCTION>evidence?</SYSTEM HOOK INSTRUCTION>",
        )
        canonical = router._gate_result_to_canonical(warn_result)
        output = router.output_for_claude(canonical, "Stop")
        assert not hasattr(output, "hookSpecificOutput"), (
            "ClaudeStopHookOutput should not have hookSpecificOutput field"
        )
        assert output.decision == "block"
        assert output.reason == "<SYSTEM HOOK INSTRUCTION>evidence?</SYSTEM HOOK INSTRUCTION>"


# ===========================================================================
# #331 – O(n²) token cost: memoised audit file
# ===========================================================================


class TestAuditFileMemoisation:
    """Audit file is not recreated when transcript hasn't changed."""

    def test_same_transcript_size_reuses_audit_file(self, tmp_path):
        """prepare_compliance_report reuses existing audit file when transcript is unchanged."""
        from lib.gates.custom_actions import execute_custom_action

        # Create a minimal transcript file
        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "type": "user",
                    "uuid": "u1",
                    "timestamp": _make_timestamp(0),
                    "message": {"content": [{"type": "text", "text": "Hello"}]},
                }
            )
            + "\n"
        )

        # Create a fake pre-existing audit file
        existing_audit = tmp_path / "enforcer.md"
        existing_audit.write_text("# Prior audit\nContent")

        state = GateState()
        state.metrics["temp_path"] = str(existing_audit)
        state.metrics["transcript_parse_pos"] = transcript.stat().st_size

        session_state = _make_state()
        ctx = _make_ctx(
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "foo.py"},
        )
        ctx = ctx.model_copy(update={"transcript_path": str(transcript)})

        result = execute_custom_action("prepare_compliance_report", ctx, state, session_state)

        # Existing audit file should be reused (not recreated)
        assert existing_audit.read_text() == "# Prior audit\nContent", (
            "Audit file was re-created even though transcript size didn't change. "
            "This is the O(n²) bug."
        )
        assert result is not None

    def test_grown_transcript_triggers_reparse(self, tmp_path, monkeypatch):
        """prepare_compliance_report recreates audit when transcript has grown."""
        from lib.gates.custom_actions import execute_custom_action

        transcript = tmp_path / "session.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "type": "user",
                    "uuid": "u1",
                    "timestamp": _make_timestamp(0),
                    "message": {"content": [{"type": "text", "text": "Hello"}]},
                }
            )
            + "\n"
        )

        # State claims transcript was smaller before
        existing_audit = tmp_path / "enforcer_old.md"
        existing_audit.write_text("Old audit")

        state = GateState()
        state.metrics["temp_path"] = str(existing_audit)
        state.metrics["transcript_parse_pos"] = 5  # stale (too small)

        session_state = _make_state()

        created_calls = []

        # Patch create_audit_file to track calls
        def fake_create_audit(session_id, gate, ctx_arg):
            new_file = tmp_path / "new_audit.md"
            new_file.write_text("New audit")
            created_calls.append(new_file)
            return new_file

        monkeypatch.setattr("lib.gates.custom_actions.create_audit_file", fake_create_audit)

        ctx = _make_ctx(
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "bar.py"},
        )
        ctx = ctx.model_copy(update={"transcript_path": str(transcript)})

        execute_custom_action("prepare_compliance_report", ctx, state, session_state)

        assert len(created_calls) == 1, (
            "Expected create_audit_file to be called once when transcript grew."
        )

    def test_transcript_parse_pos_updated_after_reparse(self, tmp_path, monkeypatch):
        """transcript_parse_pos metric is updated after a full reparse."""
        from lib.gates.custom_actions import execute_custom_action

        transcript = tmp_path / "session.jsonl"
        content = json.dumps({"type": "user", "uuid": "u1", "message": {"content": []}}) + "\n"
        transcript.write_text(content)

        state = GateState()
        session_state = _make_state()

        new_file = tmp_path / "new_audit.md"
        new_file.write_text("New audit")
        monkeypatch.setattr("lib.gates.custom_actions.create_audit_file", lambda *a, **kw: new_file)

        ctx = _make_ctx(hook_event="PreToolUse", tool_name="Bash")
        ctx = ctx.model_copy(update={"transcript_path": str(transcript)})

        execute_custom_action("prepare_compliance_report", ctx, state, session_state)

        expected_size = transcript.stat().st_size
        assert state.metrics.get("transcript_parse_pos") == expected_size
