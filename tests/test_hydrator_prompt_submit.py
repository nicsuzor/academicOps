from unittest.mock import patch
from hooks.router import HookRouter


@patch("hooks.user_prompt_submit.build_hydration_instruction")
@patch("hooks.user_prompt_submit.write_initial_hydrator_state")
@patch("hooks.user_prompt_submit.should_skip_hydration")
@patch("hooks.gate_registry.session_state")
def test_hydrator_hook_with_specific_input(
    mock_session_state, mock_should_skip, mock_write_state, mock_build_instruction
):
    """
    Test that the hydrator hook handles the specific UserPromptSubmit input correctly.
    It should NOT block (allow), but should inject the hydration instruction.
    """
    # Setup mocks
    mock_should_skip.return_value = False
    mock_build_instruction.return_value = (
        "Run prompt-hydrator with /tmp/hydrator/instruction.md"
    )

    # Specific input from request
    raw_input = {
        "session_id": "da2ab2cf-0d89-4876-8ad7-62c2e2d066d7",
        "transcript_path": "/home/nic/.gemini/tmp/c6ab9cd93f2a7acc2ea832be15a42be8173ea49bb4375fa31e99f9a2f90b5c60/chats/session-2026-02-01T22-43-da2ab2cf.json",
        "cwd": "/home/nic/.aops/crew/stormé",
        "hook_event_name": "BeforeAgent",
        "timestamp": "2026-02-01T22:44:04.922Z",
        "prompt": "fix the stop hook for claude -- it shouldn't output hookSpecificOutput. \n```  ⎿  Stop says: ✓ handover verified\nSessionEnd hook ...```",
    }

    # Initialize Router
    router = HookRouter()

    # Normalize (Gemini event mapping)
    # Note: router.normalize_input handles the mapping from BeforeAgent -> UserPromptSubmit
    ctx = router.normalize_input(raw_input, gemini_event="BeforeAgent")

    assert ctx.hook_event == "UserPromptSubmit"

    # Execute
    result = router.execute_hooks(ctx)

    # Assertions
    # The gate logic returns ALLOW with context_injection
    assert result.verdict == "allow"
    assert (
        result.context_injection
        == "Run prompt-hydrator with /tmp/hydrator/instruction.md"
    )

    # Verify build_hydration_instruction was called with correct args
    mock_build_instruction.assert_called_with(
        "da2ab2cf-0d89-4876-8ad7-62c2e2d066d7",
        raw_input["prompt"],
        raw_input["transcript_path"],
    )
