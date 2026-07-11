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
            ctx = router.normalize_input(raw, client_type="agy")
        entry = HookLogEntry(
            logged_at="2026-04-30T00:00:00+00:00",
            exit_code=0,
            output=None,
            **ctx.model_dump(exclude={"session_id"}),
            session_id=ctx.session_id,
        )
        dumped = entry.model_dump()
        assert dumped["client_type"] == "agy"


class TestAntigravityEventMapping:
    """Antigravity CLI (agy) uses PreInvocation/PostInvocation event names.

    The router must normalize these to their canonical equivalents so that
    gate logic (which checks hook_event == "UserPromptSubmit" etc.) works
    correctly when agy fires hooks.

    agy sends events via hook_event_name in the JSON payload under
    ``--client agy`` (the build rewrites ``--client claude`` → ``--client agy``
    for the agy assets), so the router resolves them through the agy inbound map.
    """

    def test_pre_invocation_maps_to_user_prompt_submit(self, router):
        """agy PreInvocation → UserPromptSubmit (fires before each agent turn)."""
        raw = {"session_id": "test-session", "hook_event_name": "PreInvocation"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="agy")
        assert ctx.hook_event == "UserPromptSubmit"

    def test_post_invocation_maps_to_stop(self, router):
        """agy PostInvocation → Stop (fires after each agent invocation)."""
        raw = {"session_id": "test-session", "hook_event_name": "PostInvocation"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="agy")
        assert ctx.hook_event == "Stop"

    def test_agy_pre_tool_use_passes_through(self, router):
        """agy PreToolUse uses same event name as Claude Code — no transform needed."""
        raw = {"session_id": "test-session", "hook_event_name": "PreToolUse"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="agy")
        assert ctx.hook_event == "PreToolUse"

    def test_agy_post_tool_use_passes_through(self, router):
        """agy PostToolUse uses same event name as Claude Code — no transform needed."""
        raw = {"session_id": "test-session", "hook_event_name": "PostToolUse"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="agy")
        assert ctx.hook_event == "PostToolUse"


class TestPostToolUseFailurePayload:
    """PostToolUseFailure crashed normalize_input on a legitimate CC payload
    shape (aops_9d3894e3).

    Live during PR #2192 headless verification (2026-07-09): a failed `Agent`
    tool call ("Agent type 'aops-pkb:rbg' not found") produced a
    PostToolUseFailure hook whose tool-result field is the raw error STRING,
    not a dict/list, and whose payload carries no session_id.
    HookContext.tool_output previously required dict/list, so pydantic
    validation raised and normalize_input crashed (exit_code=1) — masked only
    by the PR #2192 fallback log sink, which let the surrounding client run
    still report success while the event itself failed to route.
    """

    def test_string_tool_output_does_not_crash(self, router, monkeypatch):
        monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
        raw = {
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "aops-pkb:rbg"},
            "tool_response": "Agent type 'aops-pkb:rbg' not found",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="claude")
        assert ctx.hook_event == "PostToolUseFailure"
        assert ctx.tool_output == "Agent type 'aops-pkb:rbg' not found"

    def test_missing_session_id_resolves_without_crash(self, router, monkeypatch):
        monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
        raw = {
            "hook_event_name": "PostToolUseFailure",
            "tool_response": "Agent type 'aops-pkb:rbg' not found",
        }
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="claude")
        # Graceful synthetic fallback ("unknown-<uuid8>"), not a crash — and
        # not the bare "unknown" that main()'s exception-path stub produced
        # when normalize_input never returned a context at all.
        assert ctx.session_id
        assert ctx.session_id.startswith("unknown-")
        assert ctx.session_id != "unknown"
