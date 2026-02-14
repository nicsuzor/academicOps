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
def router():
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
