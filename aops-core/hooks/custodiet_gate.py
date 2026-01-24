#!/usr/bin/env python3
"""
PostToolUse custodiet hook (ultra vires detector).

Runs a periodic compliance check every N tool calls by:
1. Tracking tool call count in state file (keyed by session_id)
2. When threshold reached, writing context to temp file
3. Returning instruction to spawn custodiet subagent

Uses same pattern as prompt hydration: temp file + short instruction.

State is keyed by session_id for proper isolation - each Claude client session
is independent, even when running from the same project directory.

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

from lib.session_reader import extract_gate_context, load_skill_scope
from lib.session_state import (
    CustodietState,
    load_custodiet_state,
    load_hydrator_state,
    save_custodiet_state,
)
from lib.template_loader import load_template
from lib.transcript_parser import SessionProcessor

# Paths
HOOK_DIR = Path(__file__).parent
AOPS_ROOT = HOOK_DIR.parent.parent  # aops-core -> academicOps
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "custodiet-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "custodiet-instruction.md"
REMINDERS_FILE = HOOK_DIR / "data" / "reminders.txt"
AXIOMS_FILE = AOPS_ROOT / "AXIOMS.md"
HEURISTICS_FILE = AOPS_ROOT / "HEURISTICS.md"
SKILLS_FILE = AOPS_ROOT / "SKILLS.md"
# Use /tmp like hydrator - subagents can reliably access /tmp but not project dirs
TEMP_DIR = Path("/tmp/claude-compliance")

# Configuration
TOOL_CALL_THRESHOLD = 7  # Check every ~7 tool calls

# Random reminders: DORMANT (set to 0.0)
# This mechanism is preserved as a potential enforcement tool if evidence shows
# agents are forgetting instructions. Until then, avoid unnecessary injection noise.
# To activate: set to 0.3 (30% probability) when behavioral data justifies it.
REMINDER_PROBABILITY = 0.0
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


# ============================================================================
# Shared State API Functions (for cross-gate coordination)
# ============================================================================


def increment_tool_count(session_id: str) -> int:
    """Increment tool_calls_since_compliance counter using shared state.

    Args:
        session_id: Claude Code session ID

    Returns:
        New tool call count after increment
    """
    loaded = load_custodiet_state(session_id)
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
    save_custodiet_state(session_id, state)
    return state["tool_calls_since_compliance"]


def reset_compliance_state(session_id: str) -> None:
    """Reset tool counter after compliance check runs.

    Args:
        session_id: Claude Code session ID
    """
    loaded = load_custodiet_state(session_id)
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
    save_custodiet_state(session_id, state)


def get_intent_from_hydrator(session_id: str) -> str | None:
    """Read intent_envelope from hydrator state.

    Args:
        session_id: Claude Code session ID

    Returns:
        Intent envelope string or None if not found
    """
    state = load_hydrator_state(session_id)
    if state is None:
        return None
    return state.get("intent_envelope")


def get_workflow_from_hydrator(session_id: str) -> dict[str, str] | None:
    """Read declared_workflow from hydrator state.

    Args:
        session_id: Claude Code session ID

    Returns:
        Workflow dict or None if not found
    """
    state = load_hydrator_state(session_id)
    if state is None:
        return None
    return state.get("declared_workflow")


def set_drift_warning(session_id: str, warning: str) -> None:
    """Store drift warning in custodiet state.

    Args:
        session_id: Claude Code session ID
        warning: Drift warning message to store
    """
    loaded = load_custodiet_state(session_id)
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
    save_custodiet_state(session_id, state)


def load_framework_content() -> tuple[str, str, str]:
    """Load AXIOMS.md, HEURISTICS.md, and SKILLS.md content for custodiet.

    Returns:
        Tuple of (axioms_content, heuristics_content, skills_content) with frontmatter stripped.

    Raises:
        FileNotFoundError: If any file is missing (fail-fast).
    """
    axioms = load_template(AXIOMS_FILE)
    heuristics = load_template(HEURISTICS_FILE)
    skills = load_template(SKILLS_FILE)
    return axioms, heuristics, skills


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
    transcript_path: str | None, tool_name: str, session_id: str
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
    session_context = _build_session_context(transcript_path, session_id)

    # Load framework principles (fail-fast if missing)
    axioms_content, heuristics_content, skills_content = load_framework_content()

    # Build full context
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        session_context=session_context,
        tool_name=tool_name,
        axioms_content=axioms_content,
        heuristics_content=heuristics_content,
        skills_content=skills_content,
    )

    # Write to temp file
    temp_path = write_temp_file(full_context)

    # Build short instruction
    instruction_template = load_template(INSTRUCTION_TEMPLATE_FILE)
    instruction = instruction_template.format(temp_path=str(temp_path))

    return instruction


def _build_session_context(transcript_path: str | None, session_id: str) -> str:
    """Build rich session context for custodiet analysis.

    Extracts all signals needed for compliance checking:
    - Most recent user prompt (CRITICAL - this is the active request)
    - Original intent from hydrator (may be stale if new command invoked)
    - Full todo plan (critical for scope checking)
    - Tool errors (critical for Type A detection)
    - Files modified (for scope assessment)
    """
    lines: list[str] = []

    # 1. Extract MOST RECENT user prompt first (this is the active request)
    # Commands like /learn are injected by Claude Code and don't update hydrator state,
    # so we need the raw prompt to detect when a NEW command has been invoked.
    most_recent_prompt = None
    if transcript_path:
        ctx = extract_gate_context(
            Path(transcript_path),
            include={"prompts"},
            max_turns=5,
        )
        prompts = ctx.get("prompts", [])
        if prompts:
            most_recent_prompt = prompts[-1]
            lines.append("**Most Recent User Request** (active intent):")
            lines.append(f"> {most_recent_prompt}")
            lines.append("")

    # 2. Get intent envelope from hydrator state (may be stale if new command invoked)
    hydrator_state = load_hydrator_state(session_id)
    if hydrator_state:
        intent = hydrator_state.get("intent_envelope")
        # Only show if different from most recent prompt (avoids duplication)
        if intent and intent != most_recent_prompt:
            lines.append("**Original Session Intent** (from hydrator, may be stale):")
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

    # 3. Extract from transcript
    if transcript_path:
        ctx = extract_gate_context(
            Path(transcript_path),
            include={
                "prompts",
                "todos",
                "errors",
                "tools",
                "files",
                "conversation",
                "skill",  # Active skill for Type B detection
            },
            max_turns=15,  # Expanded for long-session drift detection
        )

        # NOTE: Verbatim first prompt is now extracted earlier (before hydrator state),
        # ensuring it ALWAYS appears regardless of hydrator state.
        # This gives custodiet the raw user intent for scope creep detection.

        # Previous prompts (for context, excludes most recent which is the user request)
        prompts = ctx.get("prompts", [])
        previous_prompts = prompts[:-1] if len(prompts) > 1 else []
        if previous_prompts:
            lines.append("**Previous User Prompts**:")
            for i, prompt in enumerate(previous_prompts[-5:], 1):
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

        # Active skill (critical for Type B - distinguishes legitimate multi-step from scope creep)
        skill = ctx.get("skill")
        if skill:
            lines.append(f"**Active Skill**: `/{skill}`")
            # Load skill's authorized scope so custodiet knows what's legitimate
            skill_scope = load_skill_scope(skill)
            if skill_scope:
                lines.append("**Skill Authorized Scope**:")
                for scope_line in skill_scope.split("\n"):
                    lines.append(f"  {scope_line}")
                lines.append(
                    "  ⚠️ Activities matching this workflow are NOT scope creep"
                )
            else:
                lines.append(
                    "  (Activities within the skill's documented workflow are NOT scope creep)"
                )
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

        # Recent conversation (critical for understanding agent reasoning and drift detection)
        conversation = ctx.get("conversation", [])
        if conversation:
            lines.append(f"**Recent Conversation** (last {len(conversation)} entries):")
            # Conversation is list[str] from session_reader (formatted [User]/[Agent]/[Tool] log)
            # max_turns controls extraction; no additional slicing here to preserve context
            for item in conversation:
                if isinstance(item, dict):
                    # Legacy fallback
                    role = item.get("role", "unknown")
                    content = item.get("content", "")
                    prefix = "User" if role == "user" else "Agent"
                    lines.append(f"  [{prefix}]: {content}")
                else:
                    # New formatted string
                    lines.append(f"  {item}")
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

    # Get session_id and tool info
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path")
    tool_name = input_data.get("tool_name", "unknown")

    # Skip for certain tools that shouldn't count toward threshold
    skip_tools = {"Read", "Glob", "Grep", "mcp__memory__retrieve_memory"}
    if tool_name in skip_tools:
        print(json.dumps({}))
        sys.exit(0)

    # Require session_id for state tracking (fail-open if missing)
    if not session_id:
        print(json.dumps({}))
        sys.exit(0)

    # Increment shared tool counter (syncs with overdue_enforcement.py)
    tool_count = increment_tool_count(session_id)

    output_data: dict[str, Any] = {}

    # Check if threshold reached
    if tool_count >= TOOL_CALL_THRESHOLD:
        try:
            instruction = build_audit_instruction(
                transcript_path, tool_name, session_id
            )
            # Use hookSpecificOutput.additionalContext - the only format router passes through
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": f"<system-reminder>\n{instruction}\n</system-reminder>",
                }
            }
            # Reset shared counter (syncs with overdue_enforcement.py)
            reset_compliance_state(session_id)
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

    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
