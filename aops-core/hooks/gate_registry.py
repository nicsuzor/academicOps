"""
Gate Registry: Defines the logic for specific gates.

This module contains the "Conditions" that gates evaluate.
"""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import re
import sys
import os
import json

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

# Shared safe tools for all gates (read-only operations that don't modify state)
# Used by hydration gate, custodiet gate, and other gates for consistency
SAFE_READ_TOOLS = {
    # Claude tools
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    # Gemini tools
    "read_file",
    "view_file",
    "list_dir",
    "find_by_name",
    "grep_search",
    "search_web",
    "read_url_content",
    # MCP tools (memory retrieval)
    "mcp__memory__retrieve_memory",
    "mcp_memory_retrieve_memory",
    "mcp__plugin_aops-core_memory__retrieve_memory",
}

# Hydration
HYDRATION_TEMP_CATEGORY = "hydrator"
HYDRATION_BLOCK_TEMPLATE = (
    Path(__file__).parent / "templates" / "hydration-gate-block.md"
)
# Alias for backward compatibility
HYDRATION_SAFE_TOOLS = SAFE_READ_TOOLS

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

# --- Task Required Gate Constants ---

# Safe temp directories - writes allowed without task binding
# These are framework-controlled, session-local, not user data
SAFE_TEMP_PREFIXES = [
    str(Path.home() / ".claude" / "tmp"),
    str(Path.home() / ".claude" / "projects"),
    str(Path.home() / ".gemini" / "tmp"),
    str(Path.home() / ".aops" / "tmp"),
]

# Task MCP tools that should always be allowed (they establish binding)
TASK_BINDING_TOOLS = {
    "mcp__plugin_aops-tools_task_manager__create_task",
    "mcp__plugin_aops-tools_task_manager__update_task",
    "mcp__plugin_aops-tools_task_manager__complete_task",
    "mcp__plugin_aops-tools_task_manager__decompose_task",
    # Gemini / Short names
    "create_task",
    "update_task",
    "complete_task",
    "decompose_task",
}

# Mutating tools that require task binding
MUTATING_TOOLS = {
    # Claude/Legacy
    "Edit",
    "Write",
    "Bash",
    "NotebookEdit",
    # Gemini
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "run_command",
    "run_shell_command",
}

# Destructive Bash command patterns (require task)
DESTRUCTIVE_BASH_PATTERNS = [
    r"\brm\b",  # remove files
    r"\bmv\b",  # move files
    r"\bcp\b",  # copy files (creates new)
    r"\bmkdir\b",  # create directories
    r"\btouch\b",  # create files
    r"\bchmod\b",  # change permissions
    r"\bchown\b",  # change ownership
    r"\bgit\s+commit\b",  # git commit
    r"\bgit\s+push\b",  # git push
    r"\bgit\s+reset\b",  # git reset
    r"\bgit\s+checkout\b.*--",  # git checkout with file paths
    r"\bnpm\s+install\b",  # npm install
    r"\bpip\s+install\b",  # pip install
    r"\buv\s+add\b",  # uv add
    r"\bsed\s+-i\b",  # sed in-place
    r"\bawk\s+-i\b",  # awk in-place
    r">\s*[^&]",  # redirect to file (but not >& which is fd redirect)
    r">>\s*",  # append to file
]

# Safe Bash command patterns (explicitly allowed without task)
SAFE_BASH_PATTERNS = [
    r"^\s*cat\s",  # cat (read)
    r"^\s*head\s",  # head (read)
    r"^\s*tail\s",  # tail (read)
    r"^\s*less\s",  # less (read)
    r"^\s*more\s",  # more (read)
    r"^\s*ls\b",  # ls (read)
    r"^\s*find\s",  # find (read)
    r"^\s*grep\s",  # grep (read)
    r"^\s*rg\s",  # ripgrep (read)
    r"^\s*echo\s",  # echo (output only, unless redirected)
    r"^\s*pwd\b",  # pwd (read)
    r"^\s*which\s",  # which (read)
    r"^\s*type\s",  # type (read)
    r"^\s*git\s+status\b",  # git status (read)
    r"^\s*git\s+diff\b",  # git diff (read)
    r"^\s*git\s+log\b",  # git log (read)
    r"^\s*git\s+show\b",  # git show (read)
    r"^\s*git\s+branch\b",  # git branch (list)
    r"^\s*npm\s+list\b",  # npm list (read)
    r"^\s*pip\s+list\b",  # pip list (read)
    r"^\s*uv\s+pip\s+list\b",  # uv pip list (read)
]

# Template paths for task gate messages
TASK_GATE_BLOCK_TEMPLATE = Path(__file__).parent / "templates" / "task-gate-block.md"
TASK_GATE_WARN_TEMPLATE = Path(__file__).parent / "templates" / "task-gate-warn.md"
DEFAULT_TASK_GATE_MODE = "block"
DEFAULT_CUSTODIET_GATE_MODE = "block"
# --- Stop Gate Constants ---

STOP_GATE_CRITIC_TEMPLATE = Path(__file__).parent / "templates" / "stop-gate-critic.md"
STOP_GATE_HANDOVER_WARN_TEMPLATE = (
    Path(__file__).parent / "templates" / "stop-gate-handover-warn.md"
)


class GateContext:
    """Context passed to gate evaluators."""

    def __init__(self, session_id: str, event_name: str, input_data: Dict[str, Any]):
        self.session_id = session_id
        self.event_name = event_name
        self.input_data = input_data
        self.tool_name = input_data.get("tool_name")
        self.tool_input = input_data.get("tool_input", {})
        self.transcript_path = input_data.get("transcript_path")


# --- Shared Helper Functions ---


def _is_safe_temp_path(file_path: str | None) -> bool:
    """Check if file path is in a safe temp directory.

    Safe temp directories are framework-controlled, session-local paths
    that don't require task binding for writes. This allows session state
    management, hook logging, and other framework operations to work.

    Args:
        file_path: Target file path from tool_input

    Returns:
        True if path is in a safe temp directory, False otherwise
    """
    if not file_path:
        return False

    # Expand ~ and resolve to absolute path
    try:
        resolved = str(Path(file_path).expanduser().resolve())
    except (OSError, ValueError):
        return False

    # Check if path starts with any safe prefix
    for prefix in SAFE_TEMP_PREFIXES:
        if resolved.startswith(prefix):
            return True

    return False


def _is_destructive_bash(command: str) -> bool:
    """Check if a Bash command is destructive (modifies state).

    Uses a two-pass approach:
    1. Check if command matches safe patterns (allow without task)
    2. Check if command matches destructive patterns (require task)

    Args:
        command: The Bash command string

    Returns:
        True if command is destructive, False if read-only
    """
    # Normalize command for matching
    cmd = command.strip()

    # First check: explicitly safe patterns
    for pattern in SAFE_BASH_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            # But check if there's a redirect that makes it destructive
            if not re.search(r">\s*[^&]|>>\s*", cmd):
                return False

    # Second check: destructive patterns
    for pattern in DESTRUCTIVE_BASH_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True

    # Default: allow (fail-open for unknown commands - they're likely read-only)
    return False


def _should_require_task(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Determine if this tool call requires task binding.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if task binding required, False otherwise
    """
    # Task binding tools always allowed (they establish binding)
    if tool_name in TASK_BINDING_TOOLS:
        return False

    # File modification tools require task, EXCEPT for safe temp directories
    if tool_name in (
        "Write",
        "Edit",
        "NotebookEdit",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ):
        # Check if target path is in safe temp directory (framework-controlled)
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if _is_safe_temp_path(file_path):
            return False  # Allow writes to temp dirs without task
        return True

    # Bash commands: check for destructive patterns
    if tool_name in ("Bash", "run_shell_command"):
        command = tool_input.get("command")
        if command is None:
            return True  # Fail-closed: no command = require task
        return _is_destructive_bash(command)

    # Gemini run_command (checks CommandLine)
    if tool_name == "run_command":
        command = tool_input.get("CommandLine") or tool_input.get("command")
        if command is None:
            return True  # Fail-closed: no command = require task
        return _is_destructive_bash(command)

    # All other tools (Read, Glob, Grep, Task, MCP reads, etc.) don't require task
    return False


def _is_handover_skill_invocation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if this is a handover skill invocation.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if this is a handover skill invocation
    """
    # Claude Skill tool
    if tool_name == "Skill":
        skill_name = tool_input.get("skill", "")
        if skill_name in ("handover", "aops-core:handover"):
            return True

    # Gemini activate_skill tool
    if tool_name == "activate_skill":
        name = tool_input.get("name", "")
        if name in ("handover", "aops-core:handover"):
            return True

    # Gemini delegate_to_agent (unlikely for handover, but supported)
    if tool_name == "delegate_to_agent":
        agent_name = tool_input.get("agent_name", "")
        if agent_name in ("handover", "aops-core:handover"):
            return True

    # Direct tool name
    if tool_name == "handover":
        return True

    return False


def _is_custodiet_invocation(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if this is a custodiet skill invocation.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if this is a custodiet invocation
    """
    # Claude Skill tool
    if tool_name == "Skill":
        skill_name = tool_input.get("skill", "")
        if skill_name in ("custodiet", "aops-core:custodiet"):
            return True

    # Gemini activate_skill tool
    if tool_name == "activate_skill":
        name = tool_input.get("name", "")
        if name in ("custodiet", "aops-core:custodiet"):
            return True

    # Gemini delegate_to_agent
    if tool_name == "delegate_to_agent":
        agent_name = tool_input.get("agent_name", "")
        if agent_name in ("custodiet", "aops-core:custodiet"):
            return True

    return False


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


def _hydration_is_hydrator_task(tool_input: dict[str, Any] | str) -> bool:
    """Check if Task/delegate_to_agent/activate_skill invocation is spawning prompt-hydrator."""
    # Ensure tool_input is a dictionary before calling .get()
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            return False

    if not isinstance(tool_input, dict):
        return False

    # Claude Task tool uses 'subagent_type'
    target = tool_input.get("subagent_type")

    # Gemini delegate_to_agent uses 'agent_name'
    if not target:
        target = tool_input.get("agent_name")

    # Gemini activate_skill uses 'name'
    if not target:
        target = tool_input.get("name")

    if target is None:
        return False
    if target == "prompt-hydrator":
        return True
    if "hydrator" in target.lower():
        return True
    return False


def _hydration_is_gemini_hydration_attempt(
    tool_name: str, tool_input: dict[str, Any] | str, input_data: dict[str, Any]
) -> bool:
    """Check if Gemini is attempting to read hydration context."""
    # Ensure tool_input is a dictionary before calling .get()
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            return False

    if not isinstance(tool_input, dict):
        return False

    try:
        temp_dir = str(
            hook_utils.get_hook_temp_dir(HYDRATION_TEMP_CATEGORY, input_data)
        )
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
    Check if hydration is required (Pre-Tool Enforcement).
    Returns None if allowed, or an output dict if blocked.
    """
    _check_imports()  # Fail fast if imports unavailable

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Bypass for subagent sessions
    if _hydration_is_subagent_session():
        return None

    # Bypass for safe read-only tools (context gathering shouldn't be blocked)
    if ctx.tool_name in HYDRATION_SAFE_TOOLS:
        return None

    # Bypass for MCP infrastructure tools (task manager, memory, etc.)
    if ctx.tool_name in MCP_TOOLS_EXEMPT_FROM_HYDRATION:
        return None

    # Check if this is the hydrator being invoked (allow it to run)
    is_hydrator_tool = ctx.tool_name in ("Task", "delegate_to_agent", "activate_skill")
    is_hydrator = is_hydrator_tool and _hydration_is_hydrator_task(ctx.tool_input)
    is_gemini = _hydration_is_gemini_hydration_attempt(
        ctx.tool_name or "", ctx.tool_input, ctx.input_data
    )

    if is_hydrator or is_gemini:
        return None

    # Check if hydration is pending
    if not session_state.is_hydration_pending(ctx.session_id):
        return None

    # Block
    block_msg = load_template(HYDRATION_BLOCK_TEMPLATE)
    return dict(hook_utils.make_deny_output(block_msg))


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
            if isinstance(turn, dict):
                role = turn.get("role", "unknown")
                content = turn.get("content", "")[:200]  # Truncate long content
            else:
                # Handle string turns (legacy or other formats)
                role = "unknown"
                content = str(turn)[:200]

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
    # Build minimal input_data for hook_utils resolution
    input_data = {"transcript_path": transcript_path} if transcript_path else None

    hook_utils.cleanup_old_temp_files(
        hook_utils.get_hook_temp_dir(CUSTODIET_TEMP_CATEGORY, input_data), "audit_"
    )

    session_context = _custodiet_build_session_context(transcript_path, session_id)
    axioms, heuristics, skills = _custodiet_load_framework_content()
    custodiet_mode = os.environ.get(
        "CUSTODIET_MODE", DEFAULT_CUSTODIET_GATE_MODE
    ).lower()

    context_template = load_template(CUSTODIET_CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        session_context=session_context,
        tool_name=tool_name,
        axioms_content=axioms,
        heuristics_content=heuristics,
        skills_content=skills,
        custodiet_mode=custodiet_mode,
    )

    temp_dir = hook_utils.get_hook_temp_dir(CUSTODIET_TEMP_CATEGORY, input_data)
    temp_path = hook_utils.write_temp_file(full_context, temp_dir, "audit_")

    instruction_template = load_template(CUSTODIET_INSTRUCTION_TEMPLATE_FILE)
    return instruction_template.format(temp_path=str(temp_path))


def check_custodiet_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check if compliance is overdue (The Bouncer).
    Returns None if allowed, or an output dict if blocked.

    Only runs on PreToolUse events. Blocks mutating tools when too many
    tool calls have occurred without a compliance check.
    """
    _check_imports()

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Only block mutating tools
    if ctx.tool_name not in MUTATING_TOOLS:
        return None

    # Track tool calls and trigger compliance check when threshold reached
    # Use unified SessionState API directly (no backwards compat wrappers)
    sess = session_state.get_or_create_session_state(ctx.session_id)
    state = sess.get("state", {})

    # Initialize custodiet fields if not present
    state.setdefault("tool_calls_since_compliance", 0)
    state.setdefault("last_compliance_ts", 0.0)

    state["tool_calls_since_compliance"] += 1
    session_state.save_session_state(ctx.session_id, sess)
    tool_calls = state["tool_calls_since_compliance"]

    # Under threshold - allow everything
    if tool_calls < OVERDUE_THRESHOLD:
        return None

    # At or over threshold - block mutating tool with full instruction
    try:
        # Build the instruction using the full context logic
        # (This creates the temp file and formats the custodiet-instruction.md template)
        instruction = _custodiet_build_audit_instruction(
            ctx.transcript_path, ctx.tool_name or "unknown", ctx.session_id
        )

        # Return as a deny/block
        return dict(hook_utils.make_deny_output(instruction, "PreToolUse"))

    except (OSError, KeyError, TypeError) as e:
        # Fail-open: if instruction generation fails, fall back to simple block
        print(f"WARNING: Custodiet audit generation failed: {e}", file=sys.stderr)
        block_msg = load_template(
            OVERDUE_BLOCK_TEMPLATE, {"tool_calls": str(tool_calls)}
        )
        return dict(hook_utils.make_deny_output(block_msg, "PreToolUse"))


def _task_gate_status(passed: bool) -> str:
    """Return gate status indicator."""
    return "\u2713" if passed else "\u2717"


def _build_task_block_message(gates: Dict[str, bool]) -> str:
    """Build a detailed block message showing which gates are missing."""
    missing = []
    if not gates["task_bound"]:
        missing.append(
            '(a) Claim a task: `mcp__plugin_aops-tools_task_manager__update_task(id="...", status="active")`'
        )
    if not gates["plan_mode_invoked"]:
        missing.append(
            "(b) Enter plan mode: `EnterPlanMode()` - design your implementation approach first"
        )
    if not gates["critic_invoked"]:
        missing.append(
            '(c) Invoke critic: `Task(subagent_type="aops-core:critic", prompt="Review this plan: ...")`'
        )

    return load_template(
        TASK_GATE_BLOCK_TEMPLATE,
        {
            "task_bound_status": _task_gate_status(gates["task_bound"]),
            "plan_mode_invoked_status": _task_gate_status(gates["plan_mode_invoked"]),
            "critic_invoked_status": _task_gate_status(gates["critic_invoked"]),
            "todo_with_handover_status": "\u2713",  # Deprecated - always pass
            "missing_gates": "\n".join(missing),
        },
    )


def _build_task_warn_message(gates: Dict[str, bool]) -> str:
    """Build a warning message for warn-only mode."""
    return load_template(
        TASK_GATE_WARN_TEMPLATE,
        {
            "task_bound_status": _task_gate_status(gates["task_bound"]),
            "plan_mode_invoked_status": _task_gate_status(gates["plan_mode_invoked"]),
            "critic_invoked_status": _task_gate_status(gates["critic_invoked"]),
            "todo_with_handover_status": "\u2713",  # Deprecated - always pass
        },
    )


def check_task_required_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check if task binding is required for this operation.
    Returns None if allowed, or an output dict if blocked/warned.

    Only runs on PreToolUse events. Enforces task-gated permissions model
    where destructive operations require task binding.
    """
    _check_imports()

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Bypass for subagent sessions
    if hook_utils.is_subagent_session():
        return None

    # Check if operation requires task binding
    if not _should_require_task(ctx.tool_name or "", ctx.tool_input):
        return None

    # Check if gates are bypassed (. prefix)
    state = session_state.load_session_state(ctx.session_id)
    if state and state.get("state", {}).get("gates_bypassed"):
        return None

    # Check gate status
    gates = session_state.check_all_gates(ctx.session_id)

    # Currently only enforce task_bound gate (others disabled for validation)
    if gates["task_bound"]:
        return None

    # Gates not passed - enforce based on mode
    gate_mode = os.environ.get("TASK_GATE_MODE", DEFAULT_TASK_GATE_MODE).lower()
    if gate_mode == "block":
        block_msg = _build_task_block_message(gates)
        return dict(hook_utils.make_deny_output(block_msg, "PreToolUse"))
    else:
        # Warn mode: allow but inject warning as context
        warn_msg = _build_task_warn_message(gates)
        return dict(hook_utils.make_allow_output(warn_msg, "PreToolUse"))


# --- Accountant Logic (Post-Tool State Updates) ---


def run_accountant(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    The Accountant: General state tracking for all components.
    Runs on PostToolUse. Never blocks, only updates state.

    Components tracked:
    1. Hydration: Clears pending flag if hydrator ran.
    2. Custodiet: Increments tool count or resets if custodiet ran.
    3. Handover: Sets handover flag if handover skill ran.
    """
    _check_imports()

    # Only applies to PostToolUse
    if ctx.event_name != "PostToolUse":
        return None

    # 1. Update Hydration State
    # Check if this is the hydrator being completed
    is_hydrator_tool = ctx.tool_name in ("Task", "delegate_to_agent", "activate_skill")
    is_hydrator = is_hydrator_tool and _hydration_is_hydrator_task(ctx.tool_input)
    is_gemini = _hydration_is_gemini_hydration_attempt(
        ctx.tool_name or "", ctx.tool_input, ctx.input_data
    )

    if is_hydrator or is_gemini:
        session_state.clear_hydration_pending(ctx.session_id)

    # 2. Update Custodiet State
    # Skip for safe read-only tools to avoid noise
    if ctx.tool_name not in SAFE_READ_TOOLS:
        sess = session_state.get_or_create_session_state(ctx.session_id)
        state = sess.get("state", {})

        # Initialize fields
        state.setdefault("tool_calls_since_compliance", 0)
        state.setdefault("last_compliance_ts", 0.0)

        # Check for reset (custodiet invoked) or increment
        if _is_custodiet_invocation(ctx.tool_name or "", ctx.tool_input):
            state["tool_calls_since_compliance"] = 0
            state["last_compliance_ts"] = (
                0.0  # update TS? PR didn't show TS update logic here but resetting implies compliance.
            )
            # Actually, if custodiet runs, we should probably update the timestamp too.
            # But adhering to strict rebase logic:
            # HEAD had: else: state["tool_calls_since_compliance"] += 1
            # PR had: save_session_state...

        else:
            state["tool_calls_since_compliance"] += 1

        session_state.save_session_state(ctx.session_id, sess)

    # 3. Update Handover State
    if _is_handover_skill_invocation(ctx.tool_name or "", ctx.tool_input):
        try:
            session_state.set_handover_skill_invoked(ctx.session_id)
            # Return a system message to acknowledge
            return {
                "systemMessage": "[Accountant] Handover recorded. Stop gate cleared."
            }
        except Exception as e:
            print(
                f"WARNING: Accountant failed to set handover flag: {e}", file=sys.stderr
            )

    return None


def check_stop_gate(ctx: GateContext) -> Optional[Dict[str, Any]]:
    """
    Check if the agent is allowed to stop (Stop / AfterAgent Enforcement).
    Returns None if allowed, or an output dict if blocked/warned.

    Rules:
    1. Critic Check: If turns_since_hydration == 0, deny stop and demand Critic.
    2. Handover Check: If handover skill not invoked, issue warning but allow stop.
    """
    _check_imports()

    # Only applies to Stop event
    if ctx.event_name != "Stop":
        return None

    state = session_state.load_session_state(ctx.session_id)
    if not state:
        return None

    # --- 1. Critic Check (turns_since_hydration == 0) ---
    # We estimate turns since hydration by checking if hydrated_intent is set
    # but no subagents have been recorded yet.
    hydration_data = state.get("hydration", {})
    subagents = state.get("subagents", {})

    is_hydrated = hydration_data.get("hydrated_intent") is not None
    has_run_subagents = len(subagents) > 0

    if is_hydrated and not has_run_subagents:
        # User explicitly asked for turns_since_hydration == 0 logic
        # This implies the agent is trying to stop immediately after the hydrator finished.
        msg = load_template(STOP_GATE_CRITIC_TEMPLATE)
        return dict(hook_utils.make_deny_output(msg, "Stop"))

    # --- 2. Handover Check ---
    if not session_state.is_handover_skill_invoked(ctx.session_id):
        # Issue warning but allow stop
        msg = load_template(STOP_GATE_HANDOVER_WARN_TEMPLATE)
        return dict(hook_utils.make_allow_output(msg, "Stop"))

    return None


# Registry of available gate checks
GATE_CHECKS = {
    "hydration": check_hydration_gate,
    "custodiet": check_custodiet_gate,
    "task_required": check_task_required_gate,
    "accountant": run_accountant,
    "stop_gate": check_stop_gate,
}
