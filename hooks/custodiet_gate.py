#!/usr/bin/env python3
"""
PostToolUse custodiet hook (ultra vires detector).

Runs a periodic compliance check every N tool calls by:
1. Tracking tool call count in state file (keyed by project cwd, not session_id)
2. When threshold reached, writing context to temp file
3. Returning instruction to spawn custodiet subagent

Uses same pattern as prompt hydration: temp file + short instruction.

NOTE: State is keyed by cwd (project directory), NOT session_id, because:
- Subagents get their own session_id (no parent_session_id available)
- We want tool calls from main session AND subagents to count together
- cwd is stable across all agents within the same project

Exit codes:
    0: Success (no check needed or check instruction returned)
    1: Infrastructure failure (fail-fast)
"""

import json
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from lib.session_reader import extract_router_context
from lib.session_state import (
    CustodietState,
    load_custodiet_state,
    load_hydrator_state,
    save_custodiet_state,
)

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "custodiet-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "custodiet-instruction.md"
REMINDERS_FILE = HOOK_DIR / "data" / "reminders.txt"
# Use /tmp like hydrator - subagents can reliably access /tmp but not project dirs
TEMP_DIR = Path("/tmp/claude-compliance")

# Configuration
TOOL_CALL_THRESHOLD = 5  # Check every ~5 tool calls
REMINDER_PROBABILITY = 0.3  # 30% chance of injecting a reminder on non-threshold calls
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


def load_reminders() -> list[str]:
    """Load reminder lines from soft-tissue file.

    Returns empty list if file missing or empty (graceful degradation).
    """
    if not REMINDERS_FILE.exists():
        return []

    try:
        lines = REMINDERS_FILE.read_text().splitlines()
        # Filter out comments and blank lines
        return [
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
    except OSError:
        return []


def get_random_reminder() -> str | None:
    """Get a random reminder with probability q.

    Returns None if no reminder should be shown (probability check failed or no reminders).
    """
    if random.random() > REMINDER_PROBABILITY:
        return None

    reminders = load_reminders()
    if not reminders:
        return None

    return random.choice(reminders)


def get_state_file(cwd: str) -> Path:
    """Get the state file path for a given project cwd.

    State is per-project (hashed cwd) to track tool counts across sessions.
    """
    import hashlib

    project_key = hashlib.sha256(cwd.encode()).hexdigest()[:12]
    return TEMP_DIR / f"state-{project_key}.json"


def load_state(cwd: str) -> dict[str, Any]:
    """Load state for current project (by cwd), or create fresh state."""
    state_file = get_state_file(cwd)
    try:
        if state_file.exists():
            return json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        pass

    # Fresh state for new project
    return {
        "tool_count": 0,
        "last_check_ts": time.time(),
    }


def save_state(cwd: str, state: dict[str, Any]) -> None:
    """Save state to file."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    state_file = get_state_file(cwd)
    state_file.write_text(json.dumps(state))


# ============================================================================
# Shared State API Functions (for cross-gate coordination)
# ============================================================================


def increment_tool_count(cwd: str) -> int:
    """Increment tool_calls_since_compliance counter using shared state.

    Args:
        cwd: Current working directory for project hash

    Returns:
        New tool call count after increment
    """
    loaded = load_custodiet_state(cwd)
    state: CustodietState = (
        loaded
        if loaded is not None
        else {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
            "error_flag": None,
        }
    )

    state["tool_calls_since_compliance"] += 1
    save_custodiet_state(cwd, state)
    return state["tool_calls_since_compliance"]


def reset_compliance_state(cwd: str) -> None:
    """Reset tool counter after compliance check runs.

    Args:
        cwd: Current working directory for project hash
    """
    loaded = load_custodiet_state(cwd)
    state: CustodietState = (
        loaded
        if loaded is not None
        else {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
            "error_flag": None,
        }
    )

    state["tool_calls_since_compliance"] = 0
    state["last_compliance_ts"] = time.time()
    state["last_drift_warning"] = None  # Clear drift warning on reset
    save_custodiet_state(cwd, state)


def get_intent_from_hydrator(cwd: str) -> str | None:
    """Read intent_envelope from hydrator state.

    Args:
        cwd: Current working directory for project hash

    Returns:
        Intent envelope string or None if not found
    """
    state = load_hydrator_state(cwd)
    if state is None:
        return None
    return state.get("intent_envelope")


def get_workflow_from_hydrator(cwd: str) -> dict[str, str] | None:
    """Read declared_workflow from hydrator state.

    Args:
        cwd: Current working directory for project hash

    Returns:
        Workflow dict or None if not found
    """
    state = load_hydrator_state(cwd)
    if state is None:
        return None
    return state.get("declared_workflow")


def set_drift_warning(cwd: str, warning: str) -> None:
    """Store drift warning in custodiet state.

    Args:
        cwd: Current working directory for project hash
        warning: Drift warning message to store
    """
    loaded = load_custodiet_state(cwd)
    state: CustodietState = (
        loaded
        if loaded is not None
        else {
            "last_compliance_ts": 0.0,
            "tool_calls_since_compliance": 0,
            "last_drift_warning": None,
            "error_flag": None,
        }
    )

    state["last_drift_warning"] = warning
    save_custodiet_state(cwd, state)


def load_template(template_path: Path) -> str:
    """Load template, extracting content after YAML frontmatter.

    Only strips the YAML frontmatter block (first --- to closing ---).
    Preserves any --- horizontal rules in content.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text()
    # Handle YAML frontmatter: ---\nmetadata\n---\ncontent
    if content.startswith("---\n"):
        # Find ONLY the closing frontmatter --- (first occurrence after opening)
        # Split once to get frontmatter + rest, preserving any --- in content
        first_newline = content.index("\n")  # Skip opening ---
        rest = content[first_newline + 1 :]
        if "\n---\n" in rest:
            # Take everything after the closing frontmatter delimiter
            closing_idx = rest.index("\n---\n")
            content = rest[closing_idx + 5 :]  # Skip \n---\n (5 chars)
        elif "\n---" in rest and rest.rstrip().endswith("---"):
            # Edge case: frontmatter only, no content after
            content = ""
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

    # Extract session context (FAIL-FAST: no silent failures)
    session_context = ""
    if transcript_path:
        ctx = extract_router_context(Path(transcript_path))
        if ctx:
            # extract_router_context already includes "## Session Context" header
            # Template also has the header, so strip it from ctx to avoid duplication
            ctx_lines = ctx.split("\n")
            if ctx_lines and ctx_lines[0].strip() == "## Session Context":
                ctx = "\n".join(ctx_lines[1:]).lstrip("\n")
            session_context = ctx

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

    # Get project cwd and tool info
    # NOTE: We use cwd (not session_id) because subagents get their own session_id
    # but share the same cwd. This ensures tool counts persist across subagent calls.
    cwd = input_data.get("cwd", "")
    transcript_path = input_data.get("transcript_path")
    tool_name = input_data.get("tool_name", "unknown")

    # Skip for certain tools that shouldn't count toward threshold
    skip_tools = {"Read", "Glob", "Grep", "mcp__memory__retrieve_memory"}
    if tool_name in skip_tools:
        print(json.dumps({}))
        sys.exit(0)

    # Require cwd for state tracking (fail-closed)
    if not cwd:
        print(json.dumps({}))
        sys.exit(0)

    # Load and update state
    state = load_state(cwd)
    state["tool_count"] += 1

    output_data: dict[str, Any] = {}

    # Check if threshold reached
    if state["tool_count"] >= TOOL_CALL_THRESHOLD:
        try:
            instruction = build_audit_instruction(transcript_path, tool_name)
            # Use hookSpecificOutput.additionalContext - the only format router passes through
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"<system-reminder>\n{instruction}\n</system-reminder>",
                }
            }
            # Reset counter
            state["tool_count"] = 0
            state["last_check_ts"] = time.time()
        except (IOError, OSError) as e:
            # Fail-fast on infrastructure errors
            output_data = {
                "decision": "block",
                "reason": f"Custodiet infrastructure error: {e}. Fix before continuing.",
            }
            print(json.dumps(output_data))
            sys.exit(1)
    else:
        # On non-threshold calls, maybe inject a random reminder (passive, not blocking)
        reminder = get_random_reminder()
        if reminder:
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"<system-reminder>\n{reminder}\n</system-reminder>",
                }
            }

    # Save state
    save_state(cwd, state)

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
