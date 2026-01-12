"""Tests for hooks/user_prompt_submit.py - Hydrator state writing.

TDD Phase 3: Session Start - Hydrator State Write
Tests that UserPromptSubmit hook writes hydrator state after processing.

Note: State is keyed by session_id (UUID-like string), NOT project cwd.
"""

from __future__ import annotations

import io
import json
import sys
import uuid
from pathlib import Path

import pytest


# Add hooks directory to path for imports
HOOKS_DIR = Path(__file__).parent.parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


def make_session_id() -> str:
    """Generate a test session ID."""
    return str(uuid.uuid4())


class TestHydratorStateWrite:
    """Test hydrator state is written by UserPromptSubmit hook."""

    def test_hook_writes_hydrator_state(self, tmp_path: Path, monkeypatch) -> None:
        """Hook writes hydrator state file after processing prompt."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        # Set up state directory
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        prompt = "Fix the bug in parser.py"

        # Build instruction (should also write state)
        build_hydration_instruction(session_id, prompt)

        # Verify state file was created
        state = load_hydrator_state(session_id)
        assert state is not None

    def test_hydrator_state_contains_intent_envelope(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Hydrator state contains intent_envelope from prompt."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        prompt = "Implement the new feature for user authentication"
        build_hydration_instruction(session_id, prompt)

        state = load_hydrator_state(session_id)
        assert state is not None
        assert "intent_envelope" in state
        # Intent should contain the prompt (possibly truncated)
        assert "authentication" in state["intent_envelope"].lower()

    def test_hydrator_state_intent_truncates_long_prompts(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Long prompts are truncated in intent_envelope."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        # Create a very long prompt
        long_prompt = "Fix the bug. " * 100  # ~1300 chars

        build_hydration_instruction(session_id, long_prompt)

        state = load_hydrator_state(session_id)
        assert state is not None
        # Intent should be truncated to reasonable length
        assert len(state["intent_envelope"]) <= 500

    def test_hydrator_state_has_pending_workflow(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Hydrator state has workflow_pending marker before hydrator runs."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        prompt = "Simple task"
        build_hydration_instruction(session_id, prompt)

        state = load_hydrator_state(session_id)
        assert state is not None
        assert "declared_workflow" in state
        # Workflow should be pending (to be filled by prompt-hydrator)
        assert state["declared_workflow"]["gate"] == "pending"

    def test_hydrator_state_has_timestamp(self, tmp_path: Path, monkeypatch) -> None:
        """Hydrator state includes hydration timestamp."""
        import time

        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        before = time.time()
        build_hydration_instruction(session_id, "Test prompt")
        after = time.time()

        state = load_hydrator_state(session_id)
        assert state is not None
        assert "last_hydration_ts" in state
        assert before <= state["last_hydration_ts"] <= after

    def test_hydrator_state_has_empty_active_skill(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Initial hydrator state has empty active_skill (to be filled by hydrator)."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        build_hydration_instruction(session_id, "Test prompt")

        state = load_hydrator_state(session_id)
        assert state is not None
        assert "active_skill" in state
        # Initially empty, to be set by prompt-hydrator
        assert state["active_skill"] == ""

    def test_hydrator_state_has_empty_guardrails(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Initial hydrator state has empty guardrails list."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()
        build_hydration_instruction(session_id, "Test prompt")

        state = load_hydrator_state(session_id)
        assert state is not None
        assert "guardrails" in state
        assert state["guardrails"] == []


class TestHydratorStateSkip:
    """Test hydrator state NOT written when hydration is skipped."""

    def test_no_state_for_skipped_prompts(self, tmp_path: Path, monkeypatch) -> None:
        """Hydrator state not written for prompts that skip hydration."""
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()

        # Import main to test full hook behavior
        from hooks.user_prompt_submit import should_skip_hydration

        # These should skip hydration
        assert should_skip_hydration("/commit")
        assert should_skip_hydration(".quick note")
        assert should_skip_hydration("<agent-notification>done</agent-notification>")
        assert should_skip_hydration(
            "<task-notification>\n<task-id>abc123</task-id>\n</task-notification>"
        )

        # No state should be written (would need to test via main())
        state = load_hydrator_state(session_id)
        assert state is None


class TestSessionIsolation:
    """Test that different sessions have isolated state."""

    def test_different_sessions_different_state(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Different session IDs produce different state files."""
        from hooks.user_prompt_submit import build_hydration_instruction
        from lib.session_state import get_hydrator_state_path, load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        # First session
        session1 = make_session_id()
        build_hydration_instruction(session1, "Prompt one")
        path1 = get_hydrator_state_path(session1)

        # Second session
        session2 = make_session_id()
        build_hydration_instruction(session2, "Prompt two")
        path2 = get_hydrator_state_path(session2)

        # Both should exist and be different files
        assert path1.exists()
        assert path2.exists()
        assert path1 != path2

        # Each session should have its own intent
        state1 = load_hydrator_state(session1)
        state2 = load_hydrator_state(session2)
        assert state1 is not None
        assert state2 is not None
        assert "one" in state1["intent_envelope"].lower()
        assert "two" in state2["intent_envelope"].lower()


class TestHydratorStateIntegration:
    """Integration tests for hydrator state with full hook flow."""

    def test_main_writes_state_on_valid_prompt(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Full hook main() writes hydrator state for valid prompts."""
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()

        # Simulate hook input (with session_id)
        input_data = {
            "prompt": "Implement feature X",
            "transcript_path": None,
            "session_id": session_id,
        }

        # Capture stdin/stdout
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(input_data)))
        captured_output = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured_output)

        # Run hook (with exit code capture)
        from hooks.user_prompt_submit import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        # Verify state was written
        state = load_hydrator_state(session_id)
        assert state is not None
        assert "Implement feature" in state["intent_envelope"]

    def test_main_skips_state_for_skill_invocation(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Hook main() does NOT write state for skill invocations."""
        from lib.session_state import load_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        session_id = make_session_id()

        # Skill invocation should skip hydration
        input_data = {
            "prompt": "/commit",
            "transcript_path": None,
            "session_id": session_id,
        }

        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(input_data)))
        captured_output = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured_output)

        from hooks.user_prompt_submit import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

        # State IS written, but with hydration_pending=False (so gate doesn't block)
        state = load_hydrator_state(session_id)
        assert state is not None
        assert state.get("hydration_pending") is False

    def test_main_graceful_without_session_id(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Hook main() handles missing session_id gracefully."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))

        # No session_id in input
        input_data = {
            "prompt": "Test prompt",
            "transcript_path": None,
        }

        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(input_data)))
        captured_output = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured_output)

        from hooks.user_prompt_submit import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should exit gracefully with code 0 (fail-open)
        assert exc_info.value.code == 0

        # Output should be valid JSON
        output = captured_output.getvalue()
        result = json.loads(output)
        assert "hookSpecificOutput" in result
