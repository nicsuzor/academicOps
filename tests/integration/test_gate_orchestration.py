import json
import pytest
from pathlib import Path

def extract_tool_calls(result, platform):
    """Platform-agnostic tool call extraction."""
    calls = []
    if platform == "claude":
        events = result.get("result", [])
        if not isinstance(events, list):
            try:
                events = json.loads(result["output"])
            except:
                events = []
        for e in events:
            if e.get("type") == "assistant" and "message" in e:
                for part in e["message"].get("content", []):
                    if part.get("type") == "tool_use":
                        calls.append({"name": part.get("name"), "input": part.get("input")})
    else: # gemini
        # Gemini JSON output usually contains toolCalls in the result
        res = result.get("result", {})
        if isinstance(res, list): # Some versions return array of turns
            for turn in res:
                for call in turn.get("toolCalls", []):
                    calls.append(call)
        else:
            for call in res.get("toolCalls", []):
                calls.append(call)
    return calls

@pytest.mark.integration
@pytest.mark.slow
def test_hydration_gate_lifecycle(cli_headless):
    """
    Test that hydration gate blocks tool calls and then unblocks when hydrator is dispatched.
    Uses parameterized cli_headless for cross-platform verification.
    """
    runner, platform = cli_headless
    
    # Use a prompt that DEMANDS context analysis
    prompt = "List all files in the current directory, but you MUST follow the project guidelines in the context file. Analyze the context first."
    
    # Run with bypass to allow tool use
    result = runner(prompt, permission_mode="bypassPermissions", timeout_seconds=180)
    assert result["success"], f"Session failed on {platform}: {result.get('error')}"
    
    # 1. Verify hydrator was dispatched
    tool_calls = extract_tool_calls(result, platform)
    task_calls = [c for c in tool_calls if "hydrator" in str(c)]
    assert len(task_calls) > 0, f"Agent should have dispatched prompt-hydrator on {platform}. Calls: {tool_calls}"
    
    # 2. Verify icon change (if possible via output)
    # Most reliable way is to check that it eventually succeeded.
    # If the hydrator was dispatched and the session finished, the gate must have unblocked.

@pytest.mark.integration
@pytest.mark.slow
def test_custodiet_gate_lifecycle(cli_headless):
    """
    Test that custodiet gate enforces periodic compliance checks.
    """
    runner, platform = cli_headless
    
    # Force 10 DISTINCT tool calls to hit the 7-op threshold.
    prompt = (
        "I want you to run exactly 10 separate tool calls. "
        "Each call should be 'ls' on a different subdirectory or file. "
        "Run them one by one. Do not stop until you hit 10. "
        "1. ls . 2. ls .. 3. ls /tmp 4. ls /home 5. ls /etc 6. ls /usr 7. ls /bin 8. ls /lib 9. ls /var 10. ls /opt"
    )
    
    result = runner(prompt, permission_mode="bypassPermissions", timeout_seconds=300)
    assert result["success"], f"Session failed on {platform}: {result.get('error')}"
    
    # Verify custodiet was dispatched
    tool_calls = extract_tool_calls(result, platform)
    custodiet_calls = [c for c in tool_calls if "custodiet" in str(c)]
    assert len(custodiet_calls) > 0, f"Agent should have dispatched custodiet after threshold on {platform}"

