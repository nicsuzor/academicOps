"""
Gate Registry: Defines the logic for specific gates.

This module contains the "Conditions" that gates evaluate.
"""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import sys
import os

# Adjust imports to work within the aops-core environment
# These imports are REQUIRED for gate functionality - fail explicitly if missing
_IMPORT_ERROR: str | None = None
try:
    from lib import session_state
    from lib import hook_utils
    from lib.template_loader import load_template
    from lib.session_reader import extract_gate_context
except ImportError as e:
    _IMPORT_ERROR = str(e)
    # Provide stub implementations that raise clear errors when used
    session_state = None  # type: ignore[assignment]
    hook_utils = None  # type: ignore[assignment]
    load_template = None  # type: ignore[assignment]
    extract_gate_context = None  # type: ignore[assignment]


def _check_imports() -> None:
    """Verify required imports are available. Raises RuntimeError if not."""
    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            f"gate_registry: Required imports failed: {_IMPORT_ERROR}. "
            "Ensure PYTHONPATH includes aops-core directory."
        )


# --- Constants & Configuration ---

# Hydration
HYDRATION_TEMP_CATEGORY = "hydrator"
HYDRATION_BLOCK_TEMPLATE = (
    Path(__file__).parent / "templates" / "hydration-gate-block.md"
)

# Custodiet
CUSTODIET_TEMP_CATEGORY = "compliance"
CUSTODIET_TOOL_CALL_THRESHOLD = 7
CUSTODIET_CONTEXT_TEMPLATE_FILE = (
    Path(__file__).parent / "templates" / "custodiet-context.md"
)
CUSTODIET_INSTRUCTION_TEMPLATE_FILE = (
    Path(__file__).parent / "templates" / "custodiet-instruction.md"
)
AOPS_ROOT = Path(
    __file__
).parent.parent.parent  # aops-core -> hooks -> gate_registry -> ...
AXIOMS_FILE = AOPS_ROOT / "aops-core" / "AXIOMS.md"
HEURISTICS_FILE = AOPS_ROOT / "aops-core" / "HEURISTICS.md"
SKILLS_FILE = AOPS_ROOT / "aops-core" / "SKILLS.md"


class GateContext:
    """Context passed to gate evaluators."""

    def __init__(self, session_id: str, event_name: str, input_data: Dict[str, Any]):
        self.session_id = session_id
        self.event_name = event_name
        self.input_data = input_data
        self.tool_name = input_data.get("tool_name")
        self.tool_input = input_data.get("tool_input", {})
        self.transcript_path = input_data.get("transcript_path")


# --- Hydration Logic ---

# MCP tools that should bypass hydration gate (infrastructure operations)
# These tools need to work even before hydration so the agent can:
# - Create/update/list tasks (task binding for other gates)
# - Store/retrieve memories (context persistence)
# - Other infrastructure operations
MCP_TOOLS_EXEMPT_FROM_HYDRATION = {
    # Task manager MCP tools (Claude format)
    "mcp__plugin_aops-tools_task_manager__create_task",
    "mcp__plugin_aops-tools_task_manager__update_task",
    "mcp__plugin_aops-tools_task_manager__complete_task",
    "mcp__plugin_aops-tools_task_manager__get_task",
    "mcp__plugin_aops-tools_task_manager__list_tasks",
    "mcp__plugin_aops-tools_task_manager__search_tasks",
    "mcp__plugin_aops-tools_task_manager__claim_next_task",
    "mcp__plugin_aops-tools_task_manager__get_task_tree",
    "mcp__plugin_aops-tools_task_manager__get_children",
    "mcp__plugin_aops-tools_task_manager__decompose_task",
    "mcp__plugin_aops-tools_task_manager__get_blocked_tasks",
    "mcp__plugin_aops-tools_task_manager__get_review_tasks",
    "mcp__plugin_aops-tools_task_manager__get_dependencies",
    "mcp__plugin_aops-tools_task_manager__rebuild_index",
    "mcp__plugin_aops-tools_task_manager__get_index_stats",
    # Memory MCP tools (Claude format)
    "mcp__plugin_aops-core_memory__store_memory",
    "mcp__plugin_aops-core_memory__retrieve_memory",
    "mcp__plugin_aops-core_memory__recall_memory",
    "mcp__plugin_aops-core_memory__search_by_tag",
    "mcp__plugin_aops-core_memory__list_memories",
    "mcp__plugin_aops-core_memory__check_database_health",
    # Gemini / Short names (used by Gemini CLI)
    "create_task",
    "update_task",
    "complete_task",
    "get_task",
    "list_tasks",
    "search_tasks",
    "claim_next_task",
    "get_task_tree",
    "get_children",
    "decompose_task",
    "store_memory",
    "retrieve_memory",
    "recall_memory",
    "search_by_tag",
    "list_memories",
}


def _hydration_is_subagent_session() -> bool:
    """Check if this is a subagent session."""
    return hook_utils.is_subagent_session()


def _hydration_is_hydrator_task(tool_input: dict[str, Any]) -> bool:
    """Check if Task/delegate_to_agent invocation is spawning prompt-hydrator."""
    # Claude Task tool uses 'subagent_type'
    target = tool_input.get("subagent_type")

    # Gemini delegate_to_agent uses 'agent_name'
    if not target:
        target = tool_input.get("agent_name")

    if target is None:
        return False
    if target == "prompt-hydrator":
        return True
    if "hydrator" in target.lower():
        return True
    return False


def _hydration_is_gemini_hydration_attempt(
    tool_name: str, tool_input: dict[str, Any]
) -> bool:
    """Check if Gemini is attempting to read hydration context."""
    try:
        temp_dir = str(hook_utils.get_hook_temp_dir(HYDRATION_TEMP_CATEGORY))
    except RuntimeError:
        return False

    if tool_name == "read_file":
        file_path = tool_input.get("file_path")
        if file_path:
            path = str(file_path)
            return path.startswith(temp_dir) or path.startswith("/tmp/claude-hydrator/")

    if tool_name == "run_shell_command":
        command = tool_input.get("command")
        if command:
            cmd = str(command)
            return temp_dir in cmd or "/tmp/claude-hydrator/" in cmd

    return False


def check_hydration_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check if hydration is required.
    Returns None if allowed, or an output dict if blocked.
    """
    _check_imports()  # Fail fast if imports unavailable

    # Bypass for subagent sessions
    if _hydration_is_subagent_session():
        return None

    # Bypass for MCP infrastructure tools (task manager, memory, etc.)
    # These must work before hydration so agents can bind tasks, persist context, etc.
    if ctx.tool_name in MCP_TOOLS_EXEMPT_FROM_HYDRATION:
        return None

    # Check if hydration is pending
    if not session_state.is_hydration_pending(ctx.session_id):
        return None

    # Check if this is the hydrator being invoked
    is_hydrator_tool = ctx.tool_name in ("Task", "delegate_to_agent")
    is_hydrator = is_hydrator_tool and _hydration_is_hydrator_task(ctx.tool_input)
    is_gemini = _hydration_is_gemini_hydration_attempt(
        ctx.tool_name or "", ctx.tool_input
    )

    if is_hydrator or is_gemini:
        # Clear gate and allow
        session_state.clear_hydration_pending(ctx.session_id)
        return None

    # Block
    block_msg = load_template(HYDRATION_BLOCK_TEMPLATE)
    return hook_utils.make_deny_output(block_msg)


# --- Custodiet Logic ---


def _custodiet_load_framework_content() -> Tuple[str, str, str]:
    """Load framework content."""
    axioms = load_template(AXIOMS_FILE)
    heuristics = load_template(HEURISTICS_FILE)
    skills = load_template(SKILLS_FILE)
    return axioms, heuristics, skills


def _custodiet_build_session_context(
    transcript_path: Optional[str], session_id: str
) -> str:
    """Build rich session context for custodiet compliance checks.

    Extracts recent conversation history, tool usage, files modified,
    and any errors to provide context for compliance evaluation.
    """
    if not transcript_path:
        return "(No transcript path available)"

    lines = []

    # Extract using library
    gate_ctx = extract_gate_context(
        Path(transcript_path),
        include={"prompts", "errors", "tools", "files", "conversation", "skill"},
        max_turns=15,
    )

    # Most recent user request
    prompts = gate_ctx.get("prompts", [])
    if prompts:
        lines.append("**Most Recent User Request**:")
        lines.append(f"> {prompts[-1]}")
        lines.append("")

    # Active skill context (if any)
    skill = gate_ctx.get("skill")
    if skill:
        lines.append(f"**Active Skill**: {skill}")
        lines.append("")

    # Recent tool usage summary
    tools = gate_ctx.get("tools", [])
    if tools:
        lines.append("**Recent Tool Calls**:")
        for tool in tools[-10:]:  # Last 10 tools
            tool_name = tool.get("name", "unknown")
            status = tool.get("status", "")
            lines.append(f"  - {tool_name} ({status})")
        lines.append("")

    # Files modified/read
    files = gate_ctx.get("files", [])
    if files:
        lines.append("**Files Accessed**:")
        for f in files[-10:]:  # Last 10 files
            action = f.get("action", "accessed")
            path = f.get("path", "unknown")
            lines.append(f"  - [{action}] {path}")
        lines.append("")

    # Tool errors (important for compliance)
    errors = gate_ctx.get("errors", [])
    if errors:
        lines.append("**Tool Errors**:")
        for e in errors[-5:]:
            lines.append(f"  - {e.get('tool_name')}: {e.get('error')}")
        lines.append("")

    # Conversation summary
    conversation = gate_ctx.get("conversation", [])
    if conversation:
        lines.append("**Recent Conversation Summary**:")
        # Include last few turns for context
        for turn in conversation[-5:]:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")[:200]  # Truncate long content
            if content:
                lines.append(f"  [{role}]: {content}...")
        lines.append("")

    if not lines:
        return "(No session context extracted)"

    return "\n".join(lines)


def _custodiet_build_audit_instruction(
    transcript_path: Optional[str], tool_name: str, session_id: str
) -> str:
    """Build instruction for compliance audit."""
    hook_utils.cleanup_old_temp_files(
        hook_utils.get_hook_temp_dir(CUSTODIET_TEMP_CATEGORY), "audit_"
    )

    session_context = _custodiet_build_session_context(transcript_path, session_id)
    axioms, heuristics, skills = _custodiet_load_framework_content()
    custodiet_mode = os.environ.get("CUSTODIET_MODE", "warn").lower()

    context_template = load_template(CUSTODIET_CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        session_context=session_context,
        tool_name=tool_name,
        axioms_content=axioms,
        heuristics_content=heuristics,
        skills_content=skills,
        custodiet_mode=custodiet_mode,
    )

    temp_dir = hook_utils.get_hook_temp_dir(CUSTODIET_TEMP_CATEGORY)
    temp_path = hook_utils.write_temp_file(full_context, temp_dir, "audit_")

    instruction_template = load_template(CUSTODIET_INSTRUCTION_TEMPLATE_FILE)
    return instruction_template.format(temp_path=str(temp_path))


def check_custodiet_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check compliancy via Custodiet.
    Returns None if allowed (or no check needed), or an output dict with instruction if check needed.
    """
    _check_imports()  # Fail fast if imports unavailable

    # Skip for certain tools
    skip_tools = {
        # Claude tools
        "Read",
        "Glob",
        "Grep",
        "mcp__memory__retrieve_memory",
        # Gemini tools
        "view_file",
        "read_file",
        "read_url_content",
        "list_dir",
        "find_by_name",
        "grep_search",
        "search_web",
        "mcp_memory_retrieve_memory",
    }
    if ctx.tool_name in skip_tools:
        return None

    # Track tool calls and trigger compliance check when threshold reached
    loaded = session_state.load_custodiet_state(ctx.session_id)
    state = (
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
    session_state.save_custodiet_state(ctx.session_id, state)
    tool_count = state["tool_calls_since_compliance"]

    if tool_count >= CUSTODIET_TOOL_CALL_THRESHOLD:
        try:
            instruction = _custodiet_build_audit_instruction(
                ctx.transcript_path, ctx.tool_name or "unknown", ctx.session_id
            )
            output = hook_utils.make_context_output(
                instruction, "PostToolUse", wrap_in_reminder=True
            )

            # Reset
            state["tool_calls_since_compliance"] = 0
            session_state.save_custodiet_state(ctx.session_id, state)

            return output
        except (OSError, KeyError, TypeError) as e:
            # Fail-open: compliance checking errors should not block operations.
            # Log the error for debugging but allow the tool call to proceed.
            print(f"WARNING: Custodiet audit failed (fail-open): {e}", file=sys.stderr)
            return None

    return None


# Registry of available gate checks
GATE_CHECKS = {
    "hydration": check_hydration_gate,
    "custodiet": check_custodiet_gate,
}
