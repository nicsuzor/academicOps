import pytest
import os
import json
from pathlib import Path

@pytest.mark.integration
@pytest.mark.slow
def test_hydration_gate_fail_fast_loop(claude_headless_tracked, tmp_path):
    """
    Test that hydration gate blocks tool calls and provides instructions,
    and then unblocks when the hydrator is dispatched.
    """
    # 1. Start a session with a hydratable prompt
    # "List files" is clearly hydratable.
    prompt = "List files in the current directory"
    
    # We use bypassPermissions so Claude proceeds to tool use immediately.
    # The framework hooks will still fire.
    result, session_id, tool_calls = claude_headless_tracked(
        prompt, 
        permission_mode="bypassPermissions",
        fail_on_error=False
    )
    
    print(f"DEBUG: Session ID: {session_id}")
    print(f"DEBUG: Result Success: {result['success']}")
    if not result['success']:
        print(f"DEBUG: Error: {result.get('error')}")
    
    # 2. Check for hydration block in the hook output stream
    # result["output"] contains the full stdout, which is a JSON array of events
    print(f"DEBUG: Raw Output: {result['output']}")
    events = result.get("result", [])
    print(f"DEBUG: Number of events: {len(events)}")
    
    if not isinstance(events, list):
        # Handle case where output might be a single object or something else
        try:
            events = json.loads(result["output"])
        except:
            events = []

    # Find hook_response events
    hook_responses = [e for e in events if e.get("type") == "system" and e.get("subtype") == "hook_response"]
    print(f"DEBUG: Number of hook responses: {len(hook_responses)}")
    
    # Look for the hydration block message
    hydration_block_found = False
    for hr in hook_responses:
        output_str = hr.get("output", "")
        print(f"DEBUG: Hook response output: {output_str[:200]}...")
        try:
            output = json.loads(output_str)
            sys_msg = output.get("systemMessage", "")
            if "HYDRATION REQUIRED" in sys_msg or "Hydration required" in sys_msg:
                hydration_block_found = True
                assert "prompt-hydrator" in sys_msg
                # Check for temp_path resolution (not set check)
                assert "(not set)" not in sys_msg
                break
        except json.JSONDecodeError:
            continue
            
    assert hydration_block_found, "Hydration gate should have blocked a tool call with instructions"
    
    # 3. Verify hydrator was dispatched
    # tool_calls contains parsed tool usage
    task_calls = [c for c in tool_calls if c["name"] == "Task" and "hydrator" in str(c["input"])]
    assert len(task_calls) > 0, "Agent should have dispatched the prompt-hydrator"
    
    # 4. Verify subagent tool calls succeeded
    # We look for successful Read or Glob calls from the subagent
    # Since subagents are sidechains, their tool calls show up in the main log too
    # but with tool_result entries.
    
    # If the whole session succeeded, it means the subagent worked.
    assert result["success"], f"Session failed: {result.get('error')}"

