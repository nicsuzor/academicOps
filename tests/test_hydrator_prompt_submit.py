from unittest.mock import ANY, patch

from hooks.router import HookRouter


@patch("lib.hydration.build_hydration_instruction")
@patch("hooks.user_prompt_submit.write_initial_hydrator_state")
@patch("lib.hydration.should_skip_hydration")
def test_hydrator_hook_with_specific_input(
    mock_should_skip, mock_write_state, mock_build_instruction, tmp_path
):
    """
    Test that the hydrator hook handles the specific UserPromptSubmit input correctly.
    It should NOT block (allow), but should inject the hydration instruction.

    Arguments must match decorators in REVERSE order (bottom-up):
    1. mock_should_skip -> should_skip_hydration
    2. mock_write_state -> write_initial_hydrator_state
    3. mock_build_instruction -> build_hydration_instruction
    """
    # Setup mocks
    mock_should_skip.return_value = False

    # build_hydration_instruction must set temp_path in metrics via side effect
    def build_side_effect(*args, **kwargs):
        state = kwargs.get("state")
        if state:
            # Ensure hydration gate state exists
            if "hydration" not in state.gates:
                from lib.gate_types import GateState

                state.gates["hydration"] = GateState()
            state.gates["hydration"].metrics["temp_path"] = "/tmp/hydrator/hydrate_da2ab2cf.md"
        return "Run prompt-hydrator with /tmp/hydrator/instruction.md"

    mock_build_instruction.side_effect = build_side_effect

    # Create safe transcript path
    transcript_dir = tmp_path / ".gemini" / "tmp" / "hash123" / "chats"
    transcript_dir.mkdir(parents=True)
    transcript_file = transcript_dir / "session-2026.json"
    transcript_file.write_text("{}")

    # Specific input from request
    raw_input = {
        "session_id": "da2ab2cf-0d89-4876-8ad7-62c2e2d066d7",
        "transcript_path": str(transcript_file),
        "cwd": str(tmp_path),
        "hook_event_name": "BeforeAgent",
        "timestamp": "2026-02-01T22:44:04.922Z",
        "prompt": "fix the stop hook for claude -- it shouldn't output hookSpecificOutput. \n```  ⎿  Stop says: ✓ handover verified\nSessionEnd hook ...```",
    }

    expected_transcript_path = raw_input["transcript_path"]
    expected_prompt = raw_input["prompt"]

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
    assert "Run prompt-hydrator" in result.context_injection

    # Verify build_hydration_instruction was called with correct args
    mock_build_instruction.assert_called_with(
        "da2ab2cf-0d89-4876-8ad7-62c2e2d066d7",
        expected_prompt,
        expected_transcript_path,
        state=ANY,
    )
