#!/usr/bin/env python3
"""
PostToolUse custodiet hook (ultra vires detector).

Runs a periodic compliance check every N tool calls by:
1. Tracking tool call count in state file
2. When threshold reached, writing context to temp file
3. Returning instruction to spawn custodiet subagent

Uses same pattern as prompt hydration: temp file + short instruction.

Exit codes:
    0: Success (no check needed or check instruction returned)
    1: Infrastructure failure (fail-fast)
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from lib.session_reader import extract_router_context

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "custodiet-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "custodiet-instruction.md"
TEMP_DIR = Path("/tmp/claude-compliance")
STATE_FILE = TEMP_DIR / "state.json"

# Configuration
TOOL_CALL_THRESHOLD = 7  # Check every ~7 tool calls
CLEANUP_AGE_SECONDS = 60 * 60  # 1 hour


def cleanup_old_temp_files() -> None:
    """Delete temp files older than 1 hour."""
    if not TEMP_DIR.exists():
        return

    cutoff = time.time() - CLEANUP_AGE_SECONDS
    for f in TEMP_DIR.glob("audit_*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass


def load_state(session_id: str) -> dict[str, Any]:
    """Load state for current session, or create fresh state."""
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
            # Check if same session
            if state.get("session_id") == session_id:
                return state
    except (json.JSONDecodeError, OSError):
        pass

    # Fresh state for new session
    return {
        "session_id": session_id,
        "tool_count": 0,
        "last_check_ts": time.time(),
    }


def save_state(state: dict[str, Any]) -> None:
    """Save state to file."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def load_template(template_path: Path) -> str:
    """Load template, extracting content after --- separator."""
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text()
    if "\n---\n" in content:
        content = content.split("\n---\n", 1)[1]
    return content.strip()


def write_temp_file(content: str) -> Path:
    """Write content to temp file, return path."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="audit_",
        suffix=".md",
        dir=TEMP_DIR,
        delete=False,
    ) as f:
        f.write(content)
        return Path(f.name)


def build_audit_instruction(transcript_path: str | None, tool_name: str) -> str:
    """Build instruction for compliance audit.

    Writes full context to temp file, returns short instruction.
    """
    cleanup_old_temp_files()

    # Extract session context
    session_context = ""
    if transcript_path:
        try:
            ctx = extract_router_context(Path(transcript_path))
            if ctx:
                session_context = f"\n\n## Session Context\n\n{ctx}"
        except Exception:
            pass

    # Build full context
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        session_context=session_context,
        tool_name=tool_name,
    )

    # Write to temp file
    temp_path = write_temp_file(full_context)

    # Build short instruction
    instruction_template = load_template(INSTRUCTION_TEMPLATE_FILE)
    instruction = instruction_template.format(temp_path=str(temp_path))

    return instruction


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Get session ID and tool info
    session_id = input_data.get("session_id", "unknown")
    transcript_path = input_data.get("transcript_path")
    tool_name = input_data.get("tool_name", "unknown")

    # Skip for certain tools that shouldn't count toward threshold
    skip_tools = {"Read", "Glob", "Grep", "mcp__memory__retrieve_memory"}
    if tool_name in skip_tools:
        print(json.dumps({}))
        sys.exit(0)

    # Load and update state
    state = load_state(session_id)
    state["tool_count"] += 1

    output_data: dict[str, Any] = {}

    # Check if threshold reached
    if state["tool_count"] >= TOOL_CALL_THRESHOLD:
        try:
            instruction = build_audit_instruction(transcript_path, tool_name)
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": instruction,
                }
            }
            # Reset counter
            state["tool_count"] = 0
            state["last_check_ts"] = time.time()
        except (IOError, OSError) as e:
            # Fail-fast on infrastructure errors
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "error": f"Custodiet temp file failed: {e}",
                }
            }
            print(json.dumps(output_data))
            sys.exit(1)

    # Save state
    save_state(state)

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
