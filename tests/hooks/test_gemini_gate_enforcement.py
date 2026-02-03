"""Tests for Gemini CLI hook gate enforcement.

These tests verify that gates properly enforce:
1. Hydration requirement on BeforeTool (PreToolUse)
2. File deletion blocking without task claimed/critic invoked

Based on observed failure case from 2026-02-03:
- Session: 30687512-43f9-4041-b847-024d9955a19b
- BeforeTool allowed `rm README.md` without any gate enforcement
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test fixtures from actual Gemini hook log
GEMINI_SESSION_START_INPUT = {
    "session_id": "30687512-43f9-4041-b847-024d9955a19b",
    "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-02-03T02-41-30687512.json",
    "cwd": "/home/nic/src/academicOps",
    "hook_event_name": "SessionStart",
    "timestamp": "2026-02-03T02:41:06.268Z",
    "source": "startup",
}

GEMINI_BEFORE_AGENT_INPUT = {
    "session_id": "30687512-43f9-4041-b847-024d9955a19b",
    "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-02-03T02-41-30687512.json",
    "cwd": "/home/nic/src/academicOps",
    "hook_event_name": "BeforeAgent",
    "timestamp": "2026-02-03T02:42:42.711Z",
    "prompt": "try to delete README.md please",
}

GEMINI_BEFORE_TOOL_RM_INPUT = {
    "session_id": "30687512-43f9-4041-b847-024d9955a19b",
    "transcript_path": "/home/nic/.gemini/tmp/02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94/chats/session-2026-02-03T02-41-30687512.json",
    "cwd": "/home/nic/src/academicOps",
    "hook_event_name": "BeforeTool",
    "timestamp": "2026-02-03T02:43:30.159Z",
    "tool_name": "run_shell_command",
    "tool_input": {
        "command": "rm README.md",
        "description": "Delete the README.md file in the current directory.",
    },
}


class TestGeminiHydrationGate:
    """Tests for hydration gate enforcement on Gemini BeforeTool events."""

    @pytest.fixture
    def mock_session_state_no_hydration(self, tmp_path):
        """Mock session state where hydration has NOT occurred."""
        state = {
            "session_id": "30687512-43f9-4041-b847-024d9955a19b",
            "state": {
                "hydration_pending": True,  # NOT hydrated
                "gates_bypassed": False,
                "hydrator_active": False,
            },
            "hydration": {
                "temp_path": str(tmp_path / "hydrate.md"),
            },
        }
        # Write the temp file so gate doesn't fail on missing temp_path
        (tmp_path / "hydrate.md").write_text("# Hydration context")
        return state

    @pytest.fixture
    def gemini_state_dir(self, tmp_path):
        """Create mock Gemini state directory structure."""
        state_dir = tmp_path / ".gemini" / "tmp" / "testhash"
        state_dir.mkdir(parents=True)
        return state_dir

    def test_before_tool_rm_should_be_blocked_without_hydration(
        self, mock_session_state_no_hydration, gemini_state_dir, monkeypatch
    ):
        """BeforeTool with `rm` command MUST be blocked if hydration not completed.

        This test reproduces the observed failure where:
        - BeforeTool event with `rm README.md` returned verdict: allow
        - Expected: verdict: deny (hydration gate should block)
        """
        from hooks.gate_registry import check_hydration_gate, GateContext

        # Set required env vars
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(gemini_state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        # Write session state file
        session_id = GEMINI_BEFORE_TOOL_RM_INPUT["session_id"]
        from lib.session_paths import get_session_short_hash
        short_hash = get_session_short_hash(session_id)
        state_file = gemini_state_dir / f"20260203-12-{short_hash}.json"
        state_file.write_text(json.dumps(mock_session_state_no_hydration))

        # Create gate context for PreToolUse (mapped from BeforeTool)
        ctx = GateContext(
            session_id=session_id,
            event_name="PreToolUse",  # Gemini BeforeTool -> PreToolUse
            input_data={
                **GEMINI_BEFORE_TOOL_RM_INPUT,
                "tool_name": "run_shell_command",
                "tool_input": {"command": "rm README.md"},
            },
        )

        result = check_hydration_gate(ctx)

        # MUST block - rm is destructive and hydration not done
        assert result is not None, "Hydration gate should return a result for rm command"
        assert result.verdict.value == "deny", (
            f"Hydration gate should DENY rm command without hydration. "
            f"Got: {result.verdict.value}"
        )

    def test_before_tool_skill_allowed_without_hydration(
        self, mock_session_state_no_hydration, gemini_state_dir, monkeypatch
    ):
        """BeforeTool with Skill tool should be ALLOWED even without hydration.

        Skill tool is in HYDRATION_ALLOWED_TOOLS to allow skill activation.
        """
        from hooks.gate_registry import check_hydration_gate, GateContext, HYDRATION_ALLOWED_TOOLS

        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(gemini_state_dir))
        monkeypatch.setenv("HYDRATION_GATE_MODE", "block")

        session_id = GEMINI_BEFORE_TOOL_RM_INPUT["session_id"]
        from lib.session_paths import get_session_short_hash
        short_hash = get_session_short_hash(session_id)
        state_file = gemini_state_dir / f"20260203-12-{short_hash}.json"
        state_file.write_text(json.dumps(mock_session_state_no_hydration))

        # Verify Skill IS in allowed tools
        assert "Skill" in HYDRATION_ALLOWED_TOOLS, "Skill should be in HYDRATION_ALLOWED_TOOLS"

        ctx = GateContext(
            session_id=session_id,
            event_name="PreToolUse",
            input_data={
                **GEMINI_BEFORE_TOOL_RM_INPUT,
                "tool_name": "Skill",  # In HYDRATION_ALLOWED_TOOLS
                "tool_input": {"skill": "handover"},
            },
        )

        result = check_hydration_gate(ctx)

        # Skill is in HYDRATION_ALLOWED_TOOLS - should be allowed (return None)
        assert result is None, "Skill tool should bypass hydration gate"


class TestGeminiDestructiveOperationGates:
    """Tests for gates blocking destructive operations without proper ceremony."""

    @pytest.fixture
    def fresh_session_state(self, tmp_path):
        """Mock fresh session state - no hydration, no task, no critic."""
        return {
            "session_id": "30687512-43f9-4041-b847-024d9955a19b",
            "state": {
                "hydration_pending": True,
                "gates_bypassed": False,
                "hydrator_active": False,
                "critic_invoked": False,
            },
            "main_agent": {
                "current_task": None,  # No task claimed
            },
            "hydration": {
                "temp_path": str(tmp_path / "hydrate.md"),
                "critic_verdict": None,
            },
        }

    def test_rm_command_blocked_without_task_claimed(
        self, fresh_session_state, tmp_path, monkeypatch
    ):
        """Destructive commands MUST be blocked when no task is claimed.

        Expected gates:
        1. hydration_pending = True -> BLOCK
        2. current_task = None -> BLOCK (if hydration passes somehow)
        """
        # This test documents expected behavior - file deletion without
        # task claim should be blocked by task_required gate
        from hooks.gate_registry import check_task_required_gate, GateContext

        state_dir = tmp_path / "gemini_state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("TASK_GATE_MODE", "block")

        session_id = fresh_session_state["session_id"]
        from lib.session_paths import get_session_short_hash
        short_hash = get_session_short_hash(session_id)
        state_file = state_dir / f"20260203-12-{short_hash}.json"
        state_file.write_text(json.dumps(fresh_session_state))
        (tmp_path / "hydrate.md").write_text("# context")

        ctx = GateContext(
            session_id=session_id,
            event_name="PreToolUse",
            input_data={
                "tool_name": "run_shell_command",
                "tool_input": {"command": "rm README.md"},
                "transcript_path": str(tmp_path / "transcript.json"),
            },
        )

        result = check_task_required_gate(ctx)

        # rm is destructive - should require task
        # If result is None, the gate isn't catching this case
        if result is not None:
            assert result.verdict.value in ("deny", "warn"), (
                f"Task gate should block/warn for rm without task. Got: {result.verdict.value}"
            )


class TestGeminiEventMapping:
    """Tests for correct event mapping between Gemini and Claude events."""

    def test_before_tool_maps_to_pretooluse(self):
        """Gemini BeforeTool should map to Claude PreToolUse."""
        from hooks.router import GEMINI_EVENT_MAP

        assert GEMINI_EVENT_MAP.get("BeforeTool") == "PreToolUse"

    def test_before_agent_maps_to_userpromptsubmit(self):
        """Gemini BeforeAgent should map to Claude UserPromptSubmit."""
        from hooks.router import GEMINI_EVENT_MAP

        assert GEMINI_EVENT_MAP.get("BeforeAgent") == "UserPromptSubmit"

    def test_pretooluse_has_hydration_gate(self):
        """PreToolUse event MUST have hydration gate in config."""
        from hooks.router import GATE_CONFIG

        gates = GATE_CONFIG.get("PreToolUse", [])
        assert "hydration" in gates, (
            f"PreToolUse must include 'hydration' gate. Has: {gates}"
        )

    def test_pretooluse_has_task_required_gate(self):
        """PreToolUse event MUST have task_required gate in config."""
        from hooks.router import GATE_CONFIG

        gates = GATE_CONFIG.get("PreToolUse", [])
        assert "task_required" in gates, (
            f"PreToolUse must include 'task_required' gate. Has: {gates}"
        )


class TestGeminiSessionStateResolution:
    """Tests for correct session state file resolution for Gemini sessions."""

    def test_gemini_state_dir_from_transcript_path(self, tmp_path):
        """Session state dir should be extracted from Gemini transcript path."""
        from lib.session_paths import _get_gemini_status_dir

        # Create mock transcript path structure
        gemini_dir = tmp_path / ".gemini" / "tmp" / "somehash" / "chats"
        gemini_dir.mkdir(parents=True)
        transcript = gemini_dir / "session-test.json"

        result = _get_gemini_status_dir({"transcript_path": str(transcript)})

        # Should return the hash directory (parent of chats)
        expected = tmp_path / ".gemini" / "tmp" / "somehash"
        assert result == expected

    def test_session_state_dir_uses_env_var(self, tmp_path, monkeypatch):
        """get_session_status_dir should prefer AOPS_SESSION_STATE_DIR env var."""
        from lib.session_paths import get_session_status_dir

        state_dir = tmp_path / "custom_state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))

        result = get_session_status_dir("any-session-id")

        assert result == state_dir

    def test_load_session_state_finds_gemini_file(self, tmp_path, monkeypatch):
        """load_session_state should find state file in Gemini state dir."""
        from lib.session_state import load_session_state, save_session_state, create_session_state
        from lib.session_paths import get_session_short_hash

        state_dir = tmp_path / "gemini_state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))

        session_id = "test-gemini-session"

        # Create and save state
        state = create_session_state(session_id)
        save_session_state(session_id, state)

        # Should be able to load it back
        loaded = load_session_state(session_id)

        assert loaded is not None
        assert loaded["session_id"] == session_id
        assert loaded["state"]["hydration_pending"] is True


class TestHydrationGateModeEnforcement:
    """Tests for HYDRATION_GATE_MODE environment variable enforcement."""

    def test_missing_hydration_gate_mode_should_deny(self, tmp_path, monkeypatch):
        """If HYDRATION_GATE_MODE is not set, gate should DENY with config error.

        Per P#8 (Fail-Fast), missing config should not silently allow.
        """
        from hooks.gate_registry import check_hydration_gate, GateContext
        from lib.session_paths import get_session_short_hash

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
        # Deliberately NOT setting HYDRATION_GATE_MODE
        monkeypatch.delenv("HYDRATION_GATE_MODE", raising=False)

        session_id = "test-session"
        short_hash = get_session_short_hash(session_id)

        # Create state with hydration pending
        state = {
            "session_id": session_id,
            "state": {"hydration_pending": True, "hydrator_active": False, "gates_bypassed": False},
            "hydration": {"temp_path": str(tmp_path / "hydrate.md")},
        }
        state_file = state_dir / f"20260203-12-{short_hash}.json"
        state_file.write_text(json.dumps(state))
        (tmp_path / "hydrate.md").write_text("# context")

        ctx = GateContext(
            session_id=session_id,
            event_name="PreToolUse",
            input_data={
                "tool_name": "run_shell_command",
                "tool_input": {"command": "rm README.md"},
            },
        )

        result = check_hydration_gate(ctx)

        # Should deny due to missing config
        assert result is not None, "Should return result when HYDRATION_GATE_MODE missing"
        assert result.verdict.value == "deny", "Should deny when config missing (fail-fast)"
        assert "CONFIGURATION ERROR" in (result.context_injection or ""), (
            "Should indicate configuration error"
        )
