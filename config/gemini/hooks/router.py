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
    "AfterAgent": "Stop",
    "SessionEnd": "Stop",
    # Gemini-only events (no Claude equivalent - pass through for logging)
    "BeforeModel": None,
    "AfterModel": None,
    "BeforeToolSelection": None,
    "PreCompress": None,
}

# Claude router location (relative to this file)
CLAUDE_ROUTER = Path(__file__).parent.parent.parent.parent / "aops-core" / "hooks" / "router.py"

# Session ID file location
SESSION_ID_FILE = Path.home() / ".gemini" / "tmp" / "current_session_id"


def get_session_id(event_name: str) -> str:
    """
    Get or create a persistent session ID.

    On SessionStart, generates a new ID and saves it.
    On other events, reads the existing ID.
    Fallback: Generates a temporary ID if file is missing.
    """
    # Create dir if needed
    if not SESSION_ID_FILE.parent.exists():
        SESSION_ID_FILE.parent.mkdir(parents=True, exist_ok=True)

    if event_name == "SessionStart":
        # Generate new session ID: YYYYMMDD-HHMMSS-uuid
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"gemini-{timestamp}-{short_uuid}"

        try:
            SESSION_ID_FILE.write_text(session_id)
        except Exception as e:
            print(f"WARNING: Failed to write session ID: {e}", file=sys.stderr)

        return session_id

    # Read existing ID
    if SESSION_ID_FILE.exists():
        try:
            return SESSION_ID_FILE.read_text().strip()
        except Exception:
            pass

    # Fallback if file missing or unreadable
    # Generate and persist a new ID so subsequent events in this session use it
    fallback_id = f"gemini-fallback-{str(uuid.uuid4())[:8]}"
    try:
        SESSION_ID_FILE.write_text(fallback_id)
    except Exception as e:
        print(f"WARNING: Failed to write fallback session ID: {e}", file=sys.stderr)

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

    # Inject session_id if not present
    if "session_id" not in claude_input:
        claude_input["session_id"] = get_session_id(gemini_event)

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


def call_claude_router(claude_input: dict) -> tuple[dict, int]:
    """
    Call the Claude router and return its output.
    """
    if not CLAUDE_ROUTER.exists():
        print(f"ERROR: Claude router not found at {CLAUDE_ROUTER}", file=sys.stderr)
        return {}, 1

    try:
        result = subprocess.run(
            ["python3", str(CLAUDE_ROUTER)],
            input=json.dumps(claude_input),
            capture_output=True,
            text=True,
            timeout=30,
            env={
                **dict(__import__("os").environ),
                "PYTHONPATH": str(CLAUDE_ROUTER.parent.parent),
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

    # Map to Claude format
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
