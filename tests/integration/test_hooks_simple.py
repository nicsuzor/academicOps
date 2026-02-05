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
    "client": "gemini",
}


def make_input(**overrides):
    """Merge overrides with DEFAULT_INPUT."""
    return {**DEFAULT_INPUT, **overrides}


# Expected field semantics:
#   None = don't check this field
#   value = check exact match (for expected_system_message)
#   True/False = check existence (for expected_injection_exists)
#   string = check substring (for *_contains fields)

TEST_CASES = [
    {
        "name": "UserPromptSubmit Example (Gemini)",
        "input": make_input(
            session_id="gemini-test",
            hook_event_name="UserPromptSubmit",
            prompt="test",
        ),
        "expected_decision": "allow",
        "expected_system_message": None,
        "expected_system_message_contains": None,
        "expected_injection_exists": None,
        "expected_injection_contains": None,
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
        "expected_system_message": None,
        "expected_system_message_contains": None,
        "expected_injection_exists": None,
        "expected_injection_contains": None,
    },
    {
        "name": "UserPromptSubmit invoke subagent (Gemini)",
        "input": make_input(
            hook_event_name="UserPromptSubmit",
            prompt="@prompt-hydrator read and comment on `/tmp/file.md`\n<system_note>\nThe user has explicitly selected the following agent(s): prompt-hydrator. Please use the 'delegate_to_agent' tool to delegate the task to the selected agent(s).\n</system_note>\n",
        ),
        "expected_decision": "allow",
        "expected_system_message": None,
        "expected_system_message_contains": None,
        "expected_injection_exists": None,
        "expected_injection_contains": None,
    },
    {
        "name": "PreToolUse invoke subagent (Gemini)",
        "input": make_input(
            hook_event_name="PreToolUse",
            tool_name="prompt-hydrator",
            tool_input={"query": "Read and comment on /tmp/file.md"},
        ),
        "expected_decision": "allow",
        "expected_system_message": None,
        "expected_system_message_contains": None,
        "expected_injection_exists": None,
        "expected_injection_contains": None,
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

        # --- Additional assertions for system_message and injection ---
        system_message = output_dict.get("systemMessage")
        injection = None
        if "hookSpecificOutput" in output_dict:
            injection = output_dict["hookSpecificOutput"].get("additionalContext")

        # Check expected_system_message (exact match)
        if case.get("expected_system_message") is not None:
            assert system_message == case["expected_system_message"], (
                f"Expected systemMessage={case['expected_system_message']!r}, got {system_message!r}"
            )

        # Check expected_system_message_contains (substring)
        if case.get("expected_system_message_contains") is not None:
            assert system_message is not None, "Expected systemMessage but got None"
            assert case["expected_system_message_contains"] in system_message, (
                f"Expected systemMessage to contain {case['expected_system_message_contains']!r}, got {system_message!r}"
            )

        # Check expected_injection_exists (True = must exist, False = must not exist)
        if case.get("expected_injection_exists") is not None:
            if case["expected_injection_exists"]:
                assert injection is not None, "Expected injection to exist but got None"
            else:
                assert injection is None, f"Expected no injection but got {injection!r}"

        # Check expected_injection_contains (substring)
        if case.get("expected_injection_contains") is not None:
            assert injection is not None, "Expected injection but got None"
            assert case["expected_injection_contains"] in injection, (
                f"Expected injection to contain {case['expected_injection_contains']!r}, got {injection!r}"
            )
