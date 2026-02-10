import json
import re
import pytest
from pathlib import Path

def extract_tool_calls(result, platform):
    """Platform-agnostic tool call extraction."""
    calls = []
    if platform == "claude":
        # 1. Try to find session_id from output
        # Claude output in JSON mode is a list of events.
        # Find 'init' event or any event with session_id.
        events = result.get("result", [])
        if not isinstance(events, list):
            try: events = json.loads(result["output"])
            except: events = []
            
        session_id = next((e.get("session_id") for e in events if e.get("session_id")), None)
        print(f"DEBUG: Claude Session ID: {session_id}")
        
        if session_id:
            # 2. Parse session file (JSONL) for full history
            claude_dir = Path.home() / ".claude" / "projects"
            print(f"DEBUG: Searching for {session_id}.jsonl in {claude_dir}")
            for project_dir in claude_dir.iterdir():
                if not project_dir.is_dir(): continue
                session_file = project_dir / f"{session_id}.jsonl"
                if session_file.exists():
                    print(f"DEBUG: Found session file: {session_file}")
                    with session_file.open() as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                if entry.get("type") == "assistant":
                                    for content in entry.get("message", {}).get("content", []):
                                        if content.get("type") == "tool_use":
                                            print(f"DEBUG: Extracted tool call: {content.get('name')}")
                                            calls.append({"name": content.get("name"), "input": content.get("input", {})})
                            except: continue
                    return calls
                else:
                    # Debug project dir contents
                    pass
            print(f"DEBUG: Session file NOT FOUND for {session_id}")

        # Fallback to events in stream
        for e in events:
            if e.get("type") == "assistant" and "message" in e:
                for part in e["message"].get("content", []):
                    if part.get("type") == "tool_use":
                        calls.append({"name": part.get("name"), "input": part.get("input")})
    else: # gemini
        res = result.get("result", {})
        if isinstance(res, list):
            for turn in res:
                for call in turn.get("toolCalls", []):
                    calls.append(call)
        else:
            for call in res.get("toolCalls", []):
                calls.append(call)
    return calls

@pytest.mark.integration
@pytest.mark.slow
def test_hydration_gate_lifecycle(claude_headless_tracked, gemini_headless):
    """
    Test that hydration gate blocks tool calls and then unblocks when hydrator is dispatched.
    """
    prompt = "List all files in the current directory, but you MUST follow the project guidelines in the context file. Analyze the context first."
    
    # 1. Test Claude
    result, session_id, tool_calls = claude_headless_tracked(prompt, permission_mode="bypassPermissions", timeout_seconds=180)
    assert result["success"], f"Session failed on claude: {result.get('error')}"
    task_calls = [c for c in tool_calls if "hydrator" in str(c)]
    assert len(task_calls) > 0, f"Agent should have dispatched prompt-hydrator on claude. Calls: {tool_calls}"
    
    # 2. Test Gemini (if requested/available)
    # Gemini usually doesn't need session file parsing as much, but we can use the same logic
    # result_gemini = gemini_headless(prompt, permission_mode="yolo", timeout_seconds=180)
    # (Optional: implement Gemini verification here if needed)

@pytest.mark.integration
@pytest.mark.slow
def test_custodiet_gate_lifecycle(claude_headless_tracked):
    """
    Test that custodiet gate enforces periodic compliance checks.
    """
    prompt = (
        "I want you to run exactly 10 separate tool calls. "
        "Each call should be 'ls' on a different subdirectory or file. "
        "Run them one by one. Do not stop until you hit 10. "
        "1. ls . 2. ls .. 3. ls /tmp 4. ls /home 5. ls /etc 6. ls /usr 7. ls /bin 8. ls /lib 9. ls /var 10. ls /opt"
    )
    
    result, session_id, tool_calls = claude_headless_tracked(prompt, permission_mode="bypassPermissions", timeout_seconds=300)
    assert result["success"], f"Session failed on claude: {result.get('error')}"
    
    custodiet_calls = [c for c in tool_calls if "custodiet" in str(c)]
    assert len(custodiet_calls) > 0, f"Agent should have dispatched custodiet after threshold on claude. Calls: {tool_calls}"

