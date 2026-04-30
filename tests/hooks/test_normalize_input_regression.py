import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Setup path to include aops-core
AOPS_CORE_DIR = Path(__file__).parent.parent.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import HookRouter


@pytest.fixture
def router(monkeypatch):
    # Mock get_session_data to avoid reading shared PID session map during xdist tests
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


class TestGeminiEventMapping:
    """Test regression cases for Gemini event mapping."""

    def test_gemini_before_tool_maps_to_pre_tool_use(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="BeforeTool")
        assert ctx.hook_event == "PreToolUse"

    def test_gemini_after_tool_maps_to_post_tool_use(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="AfterTool")
        assert ctx.hook_event == "PostToolUse"

    def test_gemini_before_agent_maps_to_user_prompt_submit(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="BeforeAgent")
        assert ctx.hook_event == "UserPromptSubmit"

    def test_gemini_after_agent_maps_to_stop(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="AfterAgent")
        assert ctx.hook_event == "Stop"

    def test_gemini_session_end_maps_to_stop(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="SessionEnd")
        assert ctx.hook_event == "SessionEnd"

    def test_gemini_event_without_mapping_passes_through(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="UnknownEvent")
        assert ctx.hook_event == "UnknownEvent"


class TestClientTypePropagation:
    """client_type from --client flag should land on HookContext and JSONL.

    Regression: previously hook JSONL showed model=unknown for all sessions
    because client_type wasn't carried through normalize_input.
    """

    def test_client_type_claude_set_on_context(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="claude")
        assert ctx.client_type == "claude"

    def test_client_type_gemini_set_on_context(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, gemini_event="BeforeTool", client_type="gemini")
        assert ctx.client_type == "gemini"
        assert ctx.hook_event == "PreToolUse"

    def test_client_type_defaults_to_none(self, router):
        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw)
        assert ctx.client_type is None

    def test_client_type_serialized_in_log_entry(self, router):
        """HookLogEntry inherits HookContext fields — client_type must round-trip."""
        from hooks.internal_models import HookLogEntry

        raw = {"session_id": "test-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="gemini")
        entry = HookLogEntry(
            logged_at="2026-04-30T00:00:00+00:00",
            exit_code=0,
            output=None,
            **ctx.model_dump(exclude={"session_id"}),
            session_id=ctx.session_id,
        )
        dumped = entry.model_dump()
        assert dumped["client_type"] == "gemini"
