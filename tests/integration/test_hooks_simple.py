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


# Default session state values (can be overridden per test case)
DEFAULT_STATE = {
    "is_hydration_pending": False,
    "is_hydrator_active": False,
    "has_file_been_read": True,
    "gates": {
        "task_bound": True,
        "plan_mode_invoked": True,
        "critic_invoked": True,
    },
}


def mock_session_state(overrides=None):
    """Minimal mocks to allow hooks to run. Accepts per-test overrides."""
    cfg = {**DEFAULT_STATE, **(overrides or {})}
    gates = {**DEFAULT_STATE["gates"], **cfg.get("gates", {})}

    state = {"state": {}, "hydration": {"temp_path": "/tmp/hydrator"}}
    return patch.multiple(
        "lib.session_state",
        is_hydration_pending=MagicMock(return_value=cfg["is_hydration_pending"]),
        check_all_gates=MagicMock(return_value=gates),
        is_hydrator_active=MagicMock(return_value=cfg["is_hydrator_active"]),
        get_hydration_temp_path=MagicMock(return_value="/tmp/hydrator"),
        load_session_state=MagicMock(return_value=state),
        get_or_create_session_state=MagicMock(return_value=state),
        save_session_state=MagicMock(return_value=None),
        clear_reflection_output=MagicMock(return_value=None),
        has_file_been_read=MagicMock(return_value=cfg["has_file_been_read"]),
    )


# --- Test Data ---

DEFAULT_INPUT = {
    "session_id": "test-session",
    "transcript_path": "/home/nic/.gemini/tmp/session.json",
    "cwd": "/home/nic/writing",
    "timestamp": "2026-02-05T01:59:58.304Z",
    "client": "gemini",
}


def make_input(**overrides):
    """Merge overrides with DEFAULT_INPUT."""
    return {**DEFAULT_INPUT, **overrides}


# Expected field semantics (key presence matters):
#   key absent = don't check this field
#   key=None = assert actual is None
#   key=value = assert exact match (for expected_system_message)
#   key=True/False = check existence (for expected_injection_exists)
#   key=string = check substring (for *_contains fields)

TEST_CASES = [
    {
        "name": "UserPromptSubmit Example (Gemini)",
        "input": make_input(
            session_id="gemini-test",
            hook_event_name="UserPromptSubmit",
            prompt="test",
        ),
        "expected_decision": "allow",
        # No expected_* keys = don't check system_message or injection
    },
    {
        "name": "PreToolUse Example (Claude)",
        "input": make_input(
            client="claude",
            session_id="claude-test",
            hook_event_name="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": "test.txt"},
        ),
        "expected_decision": "allow",
    },
    {
        "name": "UserPromptSubmit invoke subagent (Gemini)",
        "description": "Hydrator subagent should not be blocked by hydration gate on UserPromptSubmit because user explicitly invoked it",
        "input": make_input(
            hook_event_name="UserPromptSubmit",
            prompt="@prompt-hydrator read and comment on `/tmp/file.md`\n<system_note>\nThe user has explicitly selected the following agent(s): prompt-hydrator. Please use the 'delegate_to_agent' tool to delegate the task to the selected agent(s).\n</system_note>\n",
        ),
        "expected_decision": "allow",
        "state_overrides": {"is_hydration_pending": True},
        "expected_status": {"is_hydration_pending": True},
    },
    {
        "name": "PreToolUse invoke subagent (Gemini)",
        "description": "Hydrator subagent should not be blocked by hydration gate",
        "input": make_input(
            hook_event_name="PreToolUse",
            tool_name="prompt-hydrator",
            tool_input={"query": "Read and comment on /tmp/file.md"},
        ),
        # For this case, we want to allow the tool call, because this
        # is the hydrator being invoked as a subagent in Gemini.
        # The subagent invocation should be allowed to proceed so
        # that the hydrator can do its job.
        "expected_decision": "allow",
        "state_overrides": {"is_hydration_pending": True},
    },
    {
        "name": "PostToolUse recognise hydator subagent (Gemini)",
        "description": "Hydrator subagent should clear hydration status after execution",
        "input": make_input(
            hook_event_name="PostToolUse",
            tool_name="prompt-hydrator",
            tool_input={"query": "Read and comment on /tmp/file.md"},
        ),
        "expected_decision": "allow",
        "state_overrides": {"is_hydration_pending": True},
        "expected_status": {"is_hydration_pending": False},
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
    state_overrides = case.get("state_overrides", {})

    router = HookRouter()

    with (
        mock_session_state(state_overrides),
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

        # Format output based on client type
        client = raw_input.get("client", "claude")
        if client == "gemini":
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

        # --- Additional assertions for system_message and injection ---
        # Key presence matters: absent = skip, present = check (even if None)
        system_message = output_dict.get("systemMessage")
        injection = None
        if "hookSpecificOutput" in output_dict:
            injection = output_dict["hookSpecificOutput"].get("additionalContext")

        # Check expected_system_message (exact match, None = assert actual is None)
        if "expected_system_message" in case:
            assert system_message == case["expected_system_message"], (
                f"Expected systemMessage={case['expected_system_message']!r}, got {system_message!r}"
            )

        # Check expected_system_message_contains (substring)
        if "expected_system_message_contains" in case:
            expected = case["expected_system_message_contains"]
            if expected is None:
                assert system_message is None, f"Expected no systemMessage but got {system_message!r}"
            else:
                assert system_message is not None, "Expected systemMessage but got None"
                assert expected in system_message, (
                    f"Expected systemMessage to contain {expected!r}, got {system_message!r}"
                )

        # Check expected_injection_exists (True = must exist, False/None = must not exist)
        if "expected_injection_exists" in case:
            expected = case["expected_injection_exists"]
            if expected:
                assert injection is not None, "Expected injection to exist but got None"
            else:
                assert injection is None, f"Expected no injection but got {injection!r}"

        # Check expected_injection_contains (substring)
        if "expected_injection_contains" in case:
            expected = case["expected_injection_contains"]
            if expected is None:
                assert injection is None, f"Expected no injection but got {injection!r}"
            else:
                assert injection is not None, "Expected injection but got None"
                assert expected in injection, (
                    f"Expected injection to contain {expected!r}, got {injection!r}"
                )
