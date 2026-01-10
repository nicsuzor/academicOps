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

from lib.session_reader import extract_gate_context
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


def build_audit_instruction(
    transcript_path: str | None, tool_name: str, cwd: str
) -> str:
    """Build instruction for compliance audit.

    Writes full context to temp file, returns short instruction.

    Context includes:
    - Original user intent (from hydrator state or first prompt)
    - Recent prompts (less truncated)
    - Full TodoWrite plan (not just counts)
    - Tool errors (for Type A reactive helpfulness detection)
    - Files modified (for scope assessment)
    - Recent tools and agent responses
    """
    cleanup_old_temp_files()

    # Extract rich session context
    session_context = _build_session_context(transcript_path, cwd)

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


def _build_session_context(transcript_path: str | None, cwd: str) -> str:
    """Build rich session context for custodiet analysis.

    Extracts all signals needed for compliance checking:
    - Original intent (critical for drift detection)
    - Full todo plan (critical for scope checking)
    - Tool errors (critical for Type A detection)
    - Files modified (for scope assessment)
    """
    lines: list[str] = []

    # 1. Get intent envelope from hydrator state (primary source of authority)
    hydrator_state = load_hydrator_state(cwd)
    if hydrator_state:
        intent = hydrator_state.get("intent_envelope")
        if intent:
            lines.append("**Original User Request** (from hydrator):")
            # Show full intent, not truncated - this is the authority baseline
            lines.append(f"> {intent}")
            lines.append("")

        workflow = hydrator_state.get("declared_workflow")
        if workflow:
            lines.append(f"**Declared Workflow**: {workflow.get('gate', 'unknown')}")
            if workflow.get("approach"):
                lines.append(f"**Approach**: {workflow.get('approach')}")
            lines.append("")

        guardrails = hydrator_state.get("guardrails")
        if guardrails:
            lines.append(f"**Active Guardrails**: {', '.join(guardrails)}")
            lines.append("")

    # 2. Extract from transcript
    if transcript_path:
        ctx = extract_gate_context(
            Path(transcript_path),
            include={
                "intent",
                "prompts",
                "todos",
                "errors",
                "tools",
                "files",
                "conversation",
            },
            max_turns=10,  # More context than default 5
        )

        # Show original intent from transcript if not from hydrator
        if not hydrator_state or not hydrator_state.get("intent_envelope"):
            intent = ctx.get("intent")
            if intent:
                lines.append("**Original User Request** (first prompt):")
                # Full text, not truncated
                lines.append(f"> {intent}")
                lines.append("")

        # Recent prompts (for context, less truncated)
        prompts = ctx.get("prompts", [])
        if prompts:
            lines.append("**Recent User Prompts**:")
            for i, prompt in enumerate(prompts[-5:], 1):
                # Truncate at 300 chars instead of 100
                display = prompt[:300] + "..." if len(prompt) > 300 else prompt
                lines.append(f"{i}. {display}")
            lines.append("")

        # Full TodoWrite plan (critical for scope checking)
        todos = ctx.get("todos")
        if todos:
            todo_list = todos.get("todos", [])
            counts = todos.get("counts", {})
            lines.append(
                f"**TodoWrite Plan** ({counts.get('pending', 0)} pending, "
                f"{counts.get('in_progress', 0)} in_progress, "
                f"{counts.get('completed', 0)} completed):"
            )
            for todo in todo_list:
                status = todo.get("status", "pending")
                content = todo.get("content", "")
                symbol = {
                    "completed": "[x]",
                    "in_progress": "[>]",
                    "pending": "[ ]",
                }.get(status, "[ ]")
                lines.append(f"  {symbol} {content}")
            lines.append("")

        # Tool errors (critical for Type A detection)
        errors = ctx.get("errors", [])
        if errors:
            lines.append("**Tool Errors** (watch for reactive helpfulness):")
            for error in errors[-5:]:
                tool_name = error.get("tool_name", "unknown")
                input_summary = error.get("input_summary", "")
                error_msg = error.get("error", "")[:150]
                if input_summary:
                    lines.append(f"  - {tool_name}({input_summary}): {error_msg}")
                else:
                    lines.append(f"  - {tool_name}: {error_msg}")
            lines.append("")

        # Files modified (for scope assessment)
        files = ctx.get("files", [])
        if files:
            lines.append("**Files Modified**:")
            for f in files:
                # Show just filename for readability
                short = f.split("/")[-1] if "/" in f else f
                lines.append(f"  - {short}")
            lines.append("")

        # Recent tools (for activity tracking)
        tools = ctx.get("tools", [])
        if tools:
            lines.append("**Recent Tools**:")
            for tool in tools[-10:]:
                name = tool.get("name", "unknown")
                args = tool.get("args", {})
                # Compact display
                if name in ("Read", "Write", "Edit"):
                    path = args.get("file_path", "")
                    short = path.split("/")[-1] if "/" in path else path
                    lines.append(f"  - {name}({short})")
                elif name == "Bash":
                    cmd = str(args.get("command", ""))[:50]
                    lines.append(f"  - Bash({cmd}...)")
                else:
                    lines.append(f"  - {name}")
            lines.append("")

        # Recent conversation (critical for understanding agent reasoning)
        conversation = ctx.get("conversation", [])
        if conversation:
            lines.append("**Recent Conversation** (last 5 turns):")
            for turn in conversation[-5:]:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
                prefix = "User" if role == "user" else "Agent"
                lines.append(f"  [{prefix}]: {content}")
            lines.append("")

    if not lines:
        return "(No session context available)"

    return "\n".join(lines)


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
            instruction = build_audit_instruction(transcript_path, tool_name, cwd)
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
