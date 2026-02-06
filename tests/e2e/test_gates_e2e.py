import pytest
import uuid
import json
from pathlib import Path

# NOTE: These tests use the `cli_headless` fixture from tests/conftest.py
# which supports both 'claude' and 'gemini' params.

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("gate, instruction, expected_behavior", [
    ("hydration", "Run shell command: ls /etc/hosts", "blocked"),
    # ("task", "Write a file named 'test.txt' with content 'hello'", "blocked"), # Task gate might be warn-only in default config
])
def test_gate_enforcement_e2e(cli_headless, gate, instruction, expected_behavior):
    """
    End-to-End test for gate enforcement using real CLI agents.
    
    This test runs the actual agent against the actual hooks installed in the environment.
    It expects the agent to report being blocked or to fail to execute the command.
    """
    runner, platform = cli_headless
    
    # We use a unique session ID logic handled by the runner or the framework
    # For Gemini, it's automatic. For Claude, the fixture handles it.
    
    print(f"\n--- Running E2E Gate Test: {platform} | {gate} ---")
    
    # 1. Run the instruction
    # We expect a successful CLI run (exit code 0), but the *content* of the response
    # should indicate a block or the tool output should contain the block message.
    
    # Note: For Gemini, we might need to specify the model to ensure function calling capability
    model = "gemini-2.0-flash" if platform == "gemini" else "haiku"
    
    if platform == "gemini" and expected_behavior == "blocked":
        pytest.xfail("Gemini CLI hooks (PreToolUse) not triggering for native tools in headless mode (known gap)")

    result = runner(instruction, model=model)
    
    assert result["success"], f"CLI execution failed: {result.get('error')}"
    
    # 2. Analyze the response/logs to verify enforcement
    # The output format depends on the CLI.
    # We look for specific keywords in the output that indicate the gate fired.
    
    output_text = json.dumps(result["result"])
    
    if expected_behavior == "blocked":
        # Look for standard block templates
        block_indicators = [
            "Hydration Required",
            "This session is not hydrated",
            "Access Denied",
            "Gate Blocked",
            "BLOCKED"
        ]
        
        # Check if any block indicator is present in the output
        is_blocked = any(indicator in output_text for indicator in block_indicators)
        
        # Also check if the tool execution actually happened (it shouldn't have)
        # This is harder to check without session logs, but if blocked, 
        # the model usually complains about it.
        
        if not is_blocked:
             # Fallback: check if the model says "I cannot" or "blocked"
             is_blocked = "block" in output_text.lower() or "denied" in output_text.lower()

        if not is_blocked:
            print(f"DEBUG: Full Output:\n{result['output']}")
            print(f"DEBUG: Parsed Result:\n{result['result']}")
            
        assert is_blocked, f"Expected {gate} gate to block, but no block message found in output. Platform: {platform}"

    elif expected_behavior == "allowed":
        # Ensure NO block message
        assert "BLOCKED" not in output_text
        assert "Hydration Required" not in output_text

@pytest.mark.integration
@pytest.mark.slow
def test_hydrator_bypass_e2e(cli_headless):
    """
    Test that the Hydrator agent (simulated via skill) can bypass the hydration gate.
    """
    runner, platform = cli_headless
    model = "gemini-2.0-flash" if platform == "gemini" else "haiku"
    
    # Instruction: Activate the prompt-hydrator skill
    instruction = "activate_skill name='prompt-hydrator' prompt='test plan'"
    if platform == "claude":
         instruction = "Use the Skill tool to activate 'aops-core:prompt-hydrator' with prompt 'test plan'"

    result = runner(instruction, model=model)
    
    assert result["success"]
    output_text = json.dumps(result["result"])
    
    # Should NOT be blocked
    assert "Hydration Required" not in output_text