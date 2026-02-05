import pytest
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add aops-core to path
AOPS_ROOT = Path(__file__).parent.parent.parent
AOPS_CORE_DIR = AOPS_ROOT / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import HookRouter

# --- Simplified Mocking ---


def mock_session_state():
    """Minimal mocks to allow hooks to run."""
    state = {"state": {}, "hydration": {"temp_path": "/tmp/hydrator"}}
    return patch.multiple(
        "lib.session_state",
        is_hydration_pending=MagicMock(return_value=False),
        check_all_gates=MagicMock(
            return_value={
                "task_bound": True,
                "plan_mode_invoked": True,
                "critic_invoked": True,
            }
        ),
        is_hydrator_active=MagicMock(return_value=False),
        get_hydration_temp_path=MagicMock(return_value="/tmp/hydrator"),
        load_session_state=MagicMock(return_value=state),
        get_or_create_session_state=MagicMock(return_value=state),
        save_session_state=MagicMock(return_value=None),
        clear_reflection_output=MagicMock(return_value=None),
        has_file_been_read=MagicMock(return_value=True),
    )


# --- Test Data ---

DEFAULT_INPUT = {
    "session_id": "test-session",
    "transcript_path": "/home/nic/.gemini/tmp/session.json",
    "cwd": "/home/nic/writing",
    "timestamp": "2026-02-05T01:59:58.304Z",
}


def make_input(**overrides):
    """Merge overrides with DEFAULT_INPUT."""
    return {**DEFAULT_INPUT, **overrides}


TEST_CASES = [
    {
        "name": "UserPromptSubmit Example (Gemini)",
        "input": make_input(
            session_id="gemini-test",
            hook_event_name="UserPromptSubmit",
            prompt="test",
        ),
        "expected_decision": "allow",
    },
    {
        "name": "PreToolUse Example (Claude)",
        "input": make_input(
            session_id="claude-test",
            hook_event_name="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "test.txt"},
        ),
        "expected_decision": "allow",
    },
    {
        "name": "UserPromptSubmit invoke subagent (Gemini)",
        "input": make_input(
            client="gemini",
            session_id="claude-test",
            timestamp="2026-02-05T01:59:46.799Z",
            hook_event_name="UserPromptSubmit",
            prompt="@prompt-hydrator read and comment on `/home/nic/.gemini/tmp/97325aa96d9b1e6dce1905b0cdf4f54194df9929d37e09f04fcc3b3b50ca9e84/hydrator/hydrate_gwwqthue.md`\n<system_note>\nThe user has explicitly selected the following agent(s): prompt-hydrator. Please use the 'delegate_to_agent' tool to delegate the task to the selected agent(s).\n</system_note>\n",
        ),
        "expected_decision": "allow",
    },
    {
        "name": "PreToolUse invoke subagent (Gemini)",
        "input": make_input(
            session_id="a4038255-8fdc-4514-a010-f90d969a31f3",
            transcript_path="/home/nic/.gemini/tmp/97325aa96d9b1e6dce1905b0cdf4f54194df9929d37e09f04fcc3b3b50ca9e84/chats/session-2026-02-05T01-50-a4038255.json",
            hook_event_name="PreToolUse",
            tool_name="prompt-hydrator",
            tool_input={
                "query": "Read and comment on /home/nic/.gemini/tmp/97325aa96d9b1e6dce1905b0cdf4f54194df9929d37e09f04fcc3b3b50ca9e84/hydrator/hydrate_gwwqthue.md"
            },
        ),
        "expected_decision": "allow",
    },
]

# --- Test Runner ---


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c["name"])
def test_hook_json_io(case):
    """
    Data-driven test that takes JSON input and verifies JSON output structure.
    """
    raw_input = case["input"]
    expected_decision = case["expected_decision"]

    router = HookRouter()

    with (
        mock_session_state(),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="# Mock Content"),
        patch("pathlib.Path.mkdir"),
        patch.dict(
            os.environ,
            {
                "HYDRATION_GATE_MODE": "block",
                "TASK_GATE_MODE": "block",
                "AOPS_SESSION_STATE_DIR": "/tmp/aops-test",
            },
        ),
    ):
        ctx = router.normalize_input(raw_input)
        result = router.execute_hooks(ctx)

        # Format output
        if raw_input.get("session_id", "").startswith("gemini-") or "gemini" in str(
            raw_input.get("transcript_path", "")
        ):
            output = router.output_for_gemini(result, ctx.hook_event)
            output_dict = json.loads(output.model_dump_json(exclude_none=True))
            assert output_dict.get("decision") == expected_decision
        else:
            output = router.output_for_claude(result, ctx.hook_event)
            output_dict = json.loads(output.model_dump_json(exclude_none=True))
            # Claude PreToolUse puts decision in hookSpecificOutput
            if "hookSpecificOutput" in output_dict:
                assert (
                    output_dict["hookSpecificOutput"].get("permissionDecision")
                    == expected_decision
                )
            else:
                # Stop event
                assert output_dict.get("decision") in ("approve", "block")
                if expected_decision == "allow":
                    assert output_dict.get("decision") == "approve"
                else:
                    assert output_dict.get("decision") == "block"
