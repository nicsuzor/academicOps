import json
import pytest
from pathlib import Path

def extract_tool_calls_from_events(events):
    """Parse tool calls from Claude JSON event stream."""
    calls = []
    for e in events:
        if e.get("type") == "assistant" and "message" in e:
            content = e["message"].get("content", [])
            for part in content:
                if part.get("type") == "tool_use":
                    calls.append({
                        "name": part.get("name"),
                        "input": part.get("input")
                    })
    return calls

@pytest.mark.integration
@pytest.mark.slow
def test_hydration_gate_preemptive_unblock(claude_headless_tracked):
    """
    Verify that the hydration gate unblocks pre-emptively when the hydrator is dispatched.
    """
    prompt = "List all files in the current directory, but you MUST follow the project guidelines in the context file. Analyze the context first."
    result, session_id, _ = claude_headless_tracked(
        prompt, 
        permission_mode="bypassPermissions",
        fail_on_error=False
    )
    
    # Write raw output to file for debugging
    log_path = Path("claude_output.json")
    log_path.write_text(result["output"])
    print(f"DEBUG: Raw output written to {log_path.absolute()}")
    
    # Parse events from result
    events = result.get("result", [])
    if not isinstance(events, list):
        try:
            events = json.loads(result["output"])
        except (json.JSONDecodeError, TypeError):
            events = []

    tool_calls = extract_tool_calls_from_events(events)
    
    # 1. Verify hydrator was dispatched
    task_calls = [c for c in tool_calls if "hydrator" in str(c)]
    assert len(task_calls) > 0, f"Agent should have dispatched the prompt-hydrator. Tool calls: {tool_calls}"
    
    # 2. Verify icon change in the hook stream
    hook_responses = [e for e in events if e.get("type") == "system" and e.get("subtype") == "hook_response"]
    
    # Find PreToolUse:Task icons - should be unblocked
    unblocked = False
    for hr in hook_responses:
        event = hr.get("hook_event")
        if event == "PreToolUse":
            try:
                data = json.loads(hr.get("output", "{}"))
                sys_msg = data.get("systemMessage", "")
                print(f"DEBUG: Hook {event} icons: {sys_msg}")
                # Hydration icon is 🫗 (\ud83d\udeb1)
                # If hydration icon is NOT in sys_msg but WAS in start_msg (or we know it starts closed)
                # We check for the absence of the "needs hydration" indicator.
                if "🫗" not in sys_msg and "\ud83d\udeb1" not in sys_msg:
                    unblocked = True
                    break
            except json.JSONDecodeError:
                continue
                
    assert unblocked, "Hydration gate should have unblocked during PreToolUse:Task"

@pytest.mark.integration
@pytest.mark.slow
def test_custodiet_threshold_enforcement(claude_headless_tracked):
    """
    Test that custodiet gate blocks tool calls after threshold (7 ops).
    """
    prompt = (
        "I want you to run exactly 10 separate tool calls. "
        "Each call should be 'ls' on a different subdirectory or file. "
        "Run them one by one. Do not stop until you hit 10. "
        "1. ls . 2. ls .. 3. ls /tmp 4. ls /home 5. ls /etc 6. ls /usr 7. ls /bin 8. ls /lib 9. ls /var 10. ls /opt"
    )
    
    result, session_id, _ = claude_headless_tracked(
        prompt,
        permission_mode="bypassPermissions",
        fail_on_error=False,
        timeout_seconds=240
    )
    
    events = result.get("result", [])
    if not isinstance(events, list):
        try:
            events = json.loads(result["output"])
        except (json.JSONDecodeError, TypeError):
            events = []

    hook_responses = [e for e in events if e.get("type") == "system" and e.get("subtype") == "hook_response"]
    
    # 1. Check for compliance block
    compliance_block_found = False
    for hr in hook_responses:
        try:
            data = json.loads(hr.get("output", "{}"))
            sys_msg = data.get("systemMessage", "")
            if "Compliance check required" in sys_msg:
                compliance_block_found = True
                break
        except json.JSONDecodeError:
            continue
            
    assert compliance_block_found, "Custodiet gate should have blocked tool use after 7 ops"
    
    # 2. Verify custodiet was dispatched
    tool_calls = extract_tool_calls_from_events(events)
    custodiet_calls = [c for c in tool_calls if "custodiet" in str(c)]
    assert len(custodiet_calls) > 0, "Agent should have dispatched custodiet to unblock"

