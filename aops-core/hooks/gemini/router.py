#!/usr/bin/env python3
"""
Gemini CLI hook router - thin wrapper around Claude Code hooks.

Maps Gemini event names to Claude event names and delegates to the
existing hook infrastructure. This avoids duplicating hook logic.

Also manages Session ID persistence for Gemini sessions, as Gemini CLI
doesn't natively provide a persistent session ID across hook calls.

Usage (called by Gemini CLI):
    echo '{"tool_name": "write_file", ...}' | python router.py BeforeTool

Event mapping:
    Gemini CLI      -> Claude Code
    SessionStart    -> SessionStart
    BeforeTool      -> PreToolUse
    AfterTool       -> PostToolUse
    BeforeAgent     -> UserPromptSubmit
    AfterAgent      -> Stop
    SessionEnd      -> Stop
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Event name mapping: Gemini -> Claude
EVENT_MAP = {
    "SessionStart": "SessionStart",
    "BeforeTool": "PreToolUse",
    "AfterTool": "PostToolUse",
    "BeforeAgent": "UserPromptSubmit",
    "AfterAgent": "AfterAgent",
    "SessionEnd": "Stop",
    # Gemini-only events (no Claude equivalent - pass through for logging)
    "BeforeModel": None,
    "AfterModel": None,
    "BeforeToolSelection": None,
    "PreCompress": None,
}


# Hook paths (from $AOPS environment variable)
def get_aops_root() -> Path:
    """Get AOPS root path from $AOPS environment variable."""
    aops_root = Path(os.getenv("AOPS", ""))
    if not aops_root.name:
        raise EnvironmentError("$AOPS environment variable not set")
    return aops_root


def get_claude_router() -> Path:
    """Get Claude router path from $AOPS environment variable."""
    return get_aops_root() / "aops-core" / "hooks" / "router.py"


def get_gemini_user_prompt_hook() -> Path:
    """Get Gemini-specific user_prompt_submit hook path."""
    return get_aops_root() / "config" / "gemini" / "hooks" / "user_prompt_submit.py"


# Session ID file location (from $AOPS_SESSIONS environment variable)
def get_session_id_file() -> Path:
    """Get session ID file path from $AOPS_SESSIONS environment variable.

    Uses parent process ID (Gemini CLI) to create unique file per session.
    """
    aops_sessions = Path(os.getenv("AOPS_SESSIONS", ""))
    if not aops_sessions.name:
        raise EnvironmentError("$AOPS_SESSIONS environment variable not set")

    # Create directory if needed
    aops_sessions.mkdir(parents=True, exist_ok=True)

    # Use PARENT process ID (the Gemini CLI process) to anchor the session
    return aops_sessions / f"session-{os.getppid()}.txt"


def persist_session_id(session_id: str) -> None:
    """Write session ID to the fallback file."""
    try:
        session_id_file = get_session_id_file()
        session_id_file.write_text(session_id)
    except Exception as e:
        print(f"WARNING: Failed to write session ID: {e}", file=sys.stderr)


def get_session_id(event_name: str) -> str:
    """
    Get or create a persistent session ID.

    Priority:
    1. GEMINI_SESSION_ID environment variable (native Gemini CLI support)
    2. Persistent file storage (fallback using PPID)
    3. Generate new (SessionStart)
    """
    # Check for native Gemini session ID (available in recent versions)
    env_session_id = os.environ.get("GEMINI_SESSION_ID")
    if env_session_id:
        return env_session_id

    # Read existing ID from fallback file
    try:
        session_id_file = get_session_id_file()
        if session_id_file.exists():
            return session_id_file.read_text().strip()
    except Exception:
        pass

    if event_name == "SessionStart":
        # Generate new session ID: YYYYMMDD-HHMMSS-uuid
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"gemini-{timestamp}-{short_uuid}"
        # Persistence handled by caller (map_gemini_input)
        return session_id

    # Fallback if file missing or unreadable
    fallback_id = f"gemini-fallback-{str(uuid.uuid4())[:8]}"
    return fallback_id


def map_gemini_input(gemini_event: str, gemini_input: dict) -> dict:
    """
    Map Gemini input format to Claude input format.

    Gemini sends: {"tool_name": "...", "tool_input": {...}, ...}
    Claude expects: {"hook_event_name": "...", "tool_name": "...", ...}
    """
    claude_event = EVENT_MAP.get(gemini_event)
    if not claude_event:
        return {}

    claude_input = dict(gemini_input)
    claude_input["hook_event_name"] = claude_event

    # Resolve session_id
    session_id = claude_input.get("session_id")

    # If not in input, try environment or fallback file
    if not session_id:
        session_id = get_session_id(gemini_event)
        claude_input["session_id"] = session_id

    # Always persist on SessionStart (to support fallback for later hooks)
    if gemini_event == "SessionStart" and session_id:
        persist_session_id(session_id)

    # Map Gemini field names to Claude field names if needed
    # (Currently they're similar enough to work directly)

    return claude_input


def map_claude_output(claude_output: dict, gemini_event: str) -> dict:
    """
    Map Claude output format to Gemini output format.

    Claude returns: {"hookSpecificOutput": {...}, "systemMessage": "..."}
    Gemini expects: {"hookSpecificOutput": {...}, "systemMessage": "...", "decision": "..."}
    """
    if not claude_output:
        return {}

    gemini_output = dict(claude_output)

    # Update hookEventName to Gemini event name
    if "hookSpecificOutput" in gemini_output:
        gemini_output["hookSpecificOutput"]["hookEventName"] = gemini_event

        # Map permissionDecision to decision (Gemini field name)
        perm = gemini_output["hookSpecificOutput"].pop("permissionDecision", None)
        if perm:
            gemini_output["decision"] = perm

    return gemini_output


def call_gemini_user_prompt_hook(gemini_input: dict) -> tuple[dict, int]:
    """
    Call Gemini-specific user_prompt_submit hook directly.

    Used for BeforeAgent events instead of delegating to Claude router.
    Returns Gemini-compatible output (no Task subagent instructions).
    """
    try:
        hook_path = get_gemini_user_prompt_hook()
        aops_root = get_aops_root()
    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return {}, 1

    if not hook_path.exists():
        print(f"ERROR: Gemini hook not found at {hook_path}", file=sys.stderr)
        return {}, 1

    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=json.dumps(gemini_input),
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **dict(os.environ),
                "PYTHONPATH": str(aops_root / "aops-core"),
            },
        )

        output = {}
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return output, result.returncode

    except subprocess.TimeoutExpired:
        print("ERROR: Gemini user_prompt hook timed out", file=sys.stderr)
        return {}, 1
    except Exception as e:
        print(f"ERROR: Failed to call Gemini hook: {e}", file=sys.stderr)
        return {}, 1


def call_claude_router(claude_input: dict) -> tuple[dict, int]:
    """
    Call the Claude router and return its output.
    """
    try:
        claude_router = get_claude_router()
        aops_root = get_aops_root()
    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return {}, 1

    if not claude_router.exists():
        print(f"ERROR: Claude router not found at {claude_router}", file=sys.stderr)
        return {}, 1

    try:
        result = subprocess.run(
            ["python3", str(claude_router)],
            input=json.dumps(claude_input),
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **dict(os.environ),
                "PYTHONPATH": str(aops_root / "aops-core"),
            },
        )

        output = {}
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return output, result.returncode

    except subprocess.TimeoutExpired:
        print("ERROR: Claude router timed out", file=sys.stderr)
        return {}, 1
    except Exception as e:
        print(f"ERROR: Failed to call Claude router: {e}", file=sys.stderr)
        return {}, 1


def main():
    """Main entry point."""
    # Get Gemini event name from command line
    if len(sys.argv) < 2:
        print("Usage: router.py <EventName>", file=sys.stderr)
        sys.exit(1)

    gemini_event = sys.argv[1]

    # Check if we handle this event
    if gemini_event not in EVENT_MAP:
        print(f"WARNING: Unknown event: {gemini_event}", file=sys.stderr)
        print("{}")
        sys.exit(0)

    # Check if there's a Claude equivalent
    if EVENT_MAP[gemini_event] is None:
        # Gemini-only event - just acknowledge
        print("{}")
        sys.exit(0)

    # Read Gemini input from stdin
    gemini_input = {}
    try:
        gemini_input = json.load(sys.stdin)
    except Exception:
        pass

    # Special handling for BeforeAgent (UserPromptSubmit)
    # Use Gemini-specific hook that doesn't require Task() subagents
    if gemini_event == "BeforeAgent":
        # Inject session_id if not present
        if "session_id" not in gemini_input:
            gemini_input["session_id"] = get_session_id(gemini_event)

        # Call Gemini-specific hook directly
        gemini_output, exit_code = call_gemini_user_prompt_hook(gemini_input)
        print(json.dumps(gemini_output))
        sys.exit(exit_code)

    # For all other events, delegate to Claude router
    claude_input = map_gemini_input(gemini_event, gemini_input)
    if not claude_input:
        print("{}")
        sys.exit(0)

    # Call Claude router
    claude_output, exit_code = call_claude_router(claude_input)

    # Map output back to Gemini format
    gemini_output = map_claude_output(claude_output, gemini_event)

    # Output JSON
    print(json.dumps(gemini_output))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
