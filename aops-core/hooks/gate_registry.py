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
import time

from lib.gate_model import GateResult, GateVerdict
from lib.paths import get_ntfy_config

# Adjust imports to work within the aops-core environment
# These imports are REQUIRED for gate functionality - fail explicitly if missing
_IMPORT_ERROR: str | None = None
try:
    from lib import session_state
    from lib import session_paths
    from lib import hook_utils
    from lib import axiom_detector
    from lib.template_loader import load_template
    from lib.session_reader import extract_gate_context
except ImportError as e:
    _IMPORT_ERROR = str(e)
    # Provide stub implementations that raise clear errors when used
    session_state = None  # type: ignore[assignment]
    session_paths = None  # type: ignore[assignment]
    hook_utils = None  # type: ignore[assignment]
    axiom_detector = None  # type: ignore[assignment]
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
# Strict allow list for Hydration (Blocks reads by default)
HYDRATION_ALLOWED_TOOLS = {
    "list_prompts",  # Allowed to check available prompts? Maybe.
    # Handover needs to run even if hydration blocked (to save/exit safely)
    "handover",
    "aops-core:handover",
    # Skill tool needed for subagent hydration bypass (prevents deadlock when
    # is_hydrator_active() fails to detect subagent context correctly)
    "Skill",
}
# Alias for backward compatibility (Deprecated usage in Hydration Gate)
HYDRATION_SAFE_TOOLS = SAFE_READ_TOOLS

# Custodiet
CUSTODIET_TEMP_CATEGORY = "compliance"
CUSTODIET_DEFAULT_THRESHOLD = 7


def get_custodiet_threshold() -> int:
    """Get custodiet threshold, reading from env at call time for testability."""
    raw = os.environ.get("CUSTODIET_TOOL_CALL_THRESHOLD")
    return int(raw) if raw else CUSTODIET_DEFAULT_THRESHOLD


# Legacy alias for backward compatibility
CUSTODIET_TOOL_CALL_THRESHOLD: int = CUSTODIET_DEFAULT_THRESHOLD
CUSTODIET_CONTEXT_TEMPLATE_FILE = (
    Path(__file__).parent / "templates" / "custodiet-context.md"
)
CUSTODIET_INSTRUCTION_TEMPLATE_FILE = (
    Path(__file__).parent / "templates" / "custodiet-instruction.md"
)
CUSTODIET_FALLBACK_TEMPLATE = (
    Path(__file__).parent / "templates" / "overdue-enforcement-block.md"
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
    "mcp__plugin_aops-core_task_manager__create_task",
    "mcp__plugin_aops-core_task_manager__update_task",
    "mcp__plugin_aops-core_task_manager__complete_task",
    "mcp__plugin_aops-core_task_manager__decompose_task",
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

# Git operations that are safe to allow through hydration gate
# These don't corrupt history or affect other branches, and are commonly
# needed during handover/session-end workflows
HYDRATION_SAFE_GIT_PATTERNS = [
    r"^\s*git\s+status\b",  # Check repo state
    r"^\s*git\s+diff\b",  # View changes
    r"^\s*git\s+log\b",  # View history
    r"^\s*git\s+show\b",  # View commits
    r"^\s*git\s+branch\b(?!\s+-[dD])",  # List branches (not delete)
    r"^\s*git\s+add\b",  # Stage files
    r"^\s*git\s+commit\b",  # Create commit
    r"^\s*git\s+fetch\b",  # Download from remote (no merge)
    r"^\s*git\s+pull\b(?!.*--force)",  # Pull (no force)
    r"^\s*git\s+push\b(?!.*--force)",  # Push (no force) - safe for current branch
    r"^\s*git\s+stash\b",  # Stash changes
    r"^\s*git\s+remote\b",  # List/manage remotes
    r"^\s*git\s+worktree\s+list\b",  # List worktrees
    r"^\s*git\s+cherry\b",  # Check cherry-pick status
]

# Read-only file operations safe to allow through hydration gate
# These enable agents to re-read tool results and other cached data
# without requiring full hydration (aops-2bbce5b0)
HYDRATION_SAFE_READ_PATTERNS = [
    r"^\s*cat\s",  # Read file contents
    r"^\s*head\s",  # Read first N lines
    r"^\s*tail\s",  # Read last N lines
    r"^\s*less\s",  # View file (pager)
    r"^\s*more\s",  # View file (pager)
    r"^\s*jq\s",  # JSON query (read-only)
    r"^\s*wc\s",  # Word/line count
    r"^\s*file\s",  # File type detection
    r"^\s*stat\s",  # File stats
    r"^\s*ls\b",  # List directory
    r"^\s*find\s",  # Find files
    r"^\s*grep\s",  # Search file contents
    r"^\s*rg\s",  # Ripgrep search
    r"^\s*pwd\b",  # Print working directory
    r"^\s*which\s",  # Locate command
    r"^\s*type\s",  # Command type
    r"^\s*echo\s",  # Echo (no redirect)
]

# Template paths for task gate messages
TASK_GATE_BLOCK_TEMPLATE = Path(__file__).parent / "templates" / "task-gate-block.md"
TASK_GATE_WARN_TEMPLATE = Path(__file__).parent / "templates" / "task-gate-warn.md"
DEFAULT_TASK_GATE_MODE = "warn"
DEFAULT_CUSTODIET_GATE_MODE = "warn"

# Hydration gate mode: "block" (default) or "warn"
HYDRATION_WARN_TEMPLATE = Path(__file__).parent / "templates" / "hydration-gate-warn.md"
DEFAULT_HYDRATION_GATE_MODE = "warn"
# --- Stop Gate Constants ---

STOP_GATE_CRITIC_TEMPLATE = Path(__file__).parent / "templates" / "stop-gate-critic.md"
STOP_GATE_HANDOVER_BLOCK_TEMPLATE = (
    Path(__file__).parent / "templates" / "stop-gate-handover-block.md"
)


class GateContext:
    """Context passed to gate evaluators."""

    def __init__(self, session_id: str, event_name: str, input_data: Dict[str, Any]):
        self.session_id = session_id
        self.event_name = event_name
        self.input_data = input_data
        # Support both Claude (snake_case) and Gemini (camelCase) field names
        self.tool_name = input_data.get("tool_name") or input_data.get("toolName")
        self.tool_input = input_data.get("tool_input") or input_data.get("toolInput", {})
        self.transcript_path = input_data.get("transcript_path")


# --- Subagent Tool Restrictions ---


def check_subagent_tool_restrictions(ctx: GateContext) -> Optional[GateResult]:
    """Block mutating tools for restricted subagents like prompt-hydrator.

    The prompt-hydrator agent should ONLY return a plan, never execute work.
    This gate enforces that by blocking Edit/Write/Bash for hydrator sessions.

    Args:
        ctx: Gate context with tool and session information

    Returns:
        GateResult with DENY if blocked, None if allowed
    """
    if ctx.event_name != "PreToolUse":
        return None

    # Check if we're in a restricted subagent session
    subagent_type = os.environ.get("CLAUDE_SUBAGENT_TYPE", "")

    # Check for hydrator session via env var OR session state for robustness
    is_hydrator_session = (
        subagent_type == "aops-core:prompt-hydrator"
        or "hydrator" in subagent_type.lower()
        or session_state.is_hydrator_active(ctx.session_id)
    )

    # prompt-hydrator should only have Read + memory tools
    if is_hydrator_session:
        if ctx.tool_name in MUTATING_TOOLS:
            return GateResult(
                verdict=GateVerdict.DENY,
                context_injection=(
                    "⛔ **BLOCKED: prompt-hydrator cannot use mutating tools**\n\n"
                    "The hydrator agent is read-only. It must return a hydration plan, "
                    "not execute the work directly.\n\n"
                    "**Action Required**: Return your `## HYDRATION RESULT` section with:\n"
                    "- Intent summary\n"
                    "- Execution path\n"
                    "- Acceptance criteria\n"
                    "- Execution steps\n\n"
                    "Do NOT attempt to Edit, Write, or run Bash commands."
                ),
                metadata={
                    "source": "subagent_tool_restriction",
                    "blocked_tool": ctx.tool_name,
                },
            )

    return None


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


def _is_hydration_safe_bash(command: str) -> bool:
    """Check if a Bash command is safe to allow through hydration gate.

    Safe commands include:
    - Git operations that don't corrupt history or affect other branches
    - Read-only file operations (cat, jq, head, tail, etc.)

    These are commonly needed during handover and for re-reading cached data.

    Args:
        command: The Bash command string

    Returns:
        True if command is safe for hydration bypass, False otherwise
    """
    cmd = command.strip()

    # Check git patterns
    for pattern in HYDRATION_SAFE_GIT_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True

    # Check read-only file patterns (but not if they redirect to files)
    # A redirect like "cat foo > bar" or "cat foo >> bar" makes it destructive
    has_redirect = re.search(r">\s*[^&]|>>\s*", cmd)
    if not has_redirect:
        for pattern in HYDRATION_SAFE_READ_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
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


def _is_actually_destructive(tool_name: str, tool_input: Dict[str, Any]) -> bool:
    """Check if this tool call is actually destructive (modifies state).

    For most mutating tools (Edit, Write), this returns True.
    For Bash commands, checks if the command is actually destructive
    (e.g., git commit) vs read-only (e.g., git status).

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if the operation is destructive, False if read-only
    """
    # Non-Bash mutating tools are always destructive
    if tool_name in (
        "Edit",
        "Write",
        "NotebookEdit",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ):
        return True

    # Bash commands: check if actually destructive
    if tool_name in ("Bash", "run_shell_command", "run_command"):
        command = tool_input.get("command") or tool_input.get("CommandLine")
        if command is None:
            return True  # Fail-closed: no command = assume destructive
        return _is_destructive_bash(command)

    # All other tools are not destructive
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

    # Claude Task tool with subagent_type
    if tool_name == "Task":
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type in ("custodiet", "aops-core:custodiet"):
            return True

    return False


# --- Hydration Logic ---

# MCP tools that should bypass hydration gate (infrastructure operations)
# These tools need to work even before hydration so the agent can:
# - Create/update/list tasks (task binding for other gates)
# - Store/retrieve memories (context persistence)
# - Other infrastructure operations
MCP_TOOLS_EXEMPT_FROM_HYDRATION = {
    # Task manager MCP tools (Claude format) - NOTE: task_manager is in aops-core, not aops-tools
    "mcp__plugin_aops-core_task_manager__create_task",
    "mcp__plugin_aops-core_task_manager__update_task",
    "mcp__plugin_aops-core_task_manager__complete_task",
    "mcp__plugin_aops-core_task_manager__complete_tasks",
    "mcp__plugin_aops-core_task_manager__get_task",
    "mcp__plugin_aops-core_task_manager__list_tasks",
    "mcp__plugin_aops-core_task_manager__search_tasks",
    "mcp__plugin_aops-core_task_manager__get_task_tree",
    "mcp__plugin_aops-core_task_manager__get_children",
    "mcp__plugin_aops-core_task_manager__decompose_task",
    "mcp__plugin_aops-core_task_manager__get_blocked_tasks",
    "mcp__plugin_aops-core_task_manager__get_review_tasks",
    "mcp__plugin_aops-core_task_manager__get_dependencies",
    "mcp__plugin_aops-core_task_manager__rebuild_index",
    "mcp__plugin_aops-core_task_manager__get_index_stats",
    "mcp__plugin_aops-core_task_manager__reorder_children",
    "mcp__plugin_aops-core_task_manager__dedup_tasks",
    "mcp__plugin_aops-core_task_manager__delete_task",
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

# Infrastructure skills that should NOT clear hydration_pending when activated.
# These are utility/navigation commands that don't satisfy the "provide context" intent.
# Hydration should only be cleared by actual hydration-completing skills (prompt-hydrator).
INFRASTRUCTURE_SKILLS_NO_HYDRATION_CLEAR = {
    # Simple commands (navigation/utility)
    "bump",
    "aops-core:bump",
    "diag",
    "aops-core:diag",
    "dump",
    "aops-core:dump",
    "aops",
    "aops-core:aops",
    "log",
    "aops-core:log",
    "q",
    "aops-core:q",
    "email",
    "aops-core:email",
    "learn",
    "aops-core:learn",
    "pull",
    "aops-core:pull",
    # Infrastructure skills (don't complete hydration)
    "task-viz",
    "aops-core:task-viz",
    "remember",
    "aops-core:remember",
    "handover",
    "aops-core:handover",
    "garden",
    "aops-core:garden",
    "audit",
    "aops-core:audit",
    "annotations",
    "aops-core:annotations",
    "session-insights",
    "aops-core:session-insights",
    "hypervisor",
    "aops-core:hypervisor",
    # Hydrator is an infrastructure skill that should not clear hydration
    "prompt-hydrator",
    "aops-core:prompt-hydrator",
}


def _hydration_is_subagent_session(input_data: dict[str, Any] | None = None) -> bool:
    """Check if this is a subagent session."""
    return hook_utils.is_subagent_session(input_data)


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

    if tool_name == "write_to_file":
        target_file = tool_input.get("TargetFile") or tool_input.get("file_path")
        if target_file:
            path = str(target_file)
            return path.startswith(temp_dir) or path.startswith("/tmp/claude-hydrator/")

    if tool_name == "run_shell_command":
        command = tool_input.get("command")
        if command:
            cmd = str(command)
            return temp_dir in cmd or "/tmp/claude-hydrator/" in cmd

    return False


def check_hydration_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Check if hydration is required (Pre-Tool Enforcement).
    Returns None if allowed, or GateResult if blocked.
    """
    _check_imports()  # Fail fast if imports unavailable

    # DEBUG: Log to fixed file for subagent visibility
    from datetime import datetime

    debug_file = Path("/tmp/hydration-gate-debug.jsonl")
    try:
        with open(debug_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": str(datetime.now()),
                        "event": ctx.event_name,
                        "tool": ctx.tool_name,
                        "session_id": ctx.session_id,
                        "transcript_path": ctx.input_data.get("transcript_path")
                        if ctx.input_data
                        else None,
                        "env_agent_type": os.environ.get("CLAUDE_AGENT_TYPE"),
                        "env_subagent_type": os.environ.get("CLAUDE_SUBAGENT_TYPE"),
                        "input_keys": list(ctx.input_data.keys())
                        if ctx.input_data
                        else [],
                    }
                )
                + "\n"
            )
    except Exception:
        pass  # Don't fail on debug logging
    # END DEBUG

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Bypass for subagent sessions
    if _hydration_is_subagent_session(ctx.input_data):
        return None

    # BELT & SUSPENDERS: Additional detection for hydrator subagent
    # Check env var that might be set for subagent processes
    subagent_type = os.environ.get("CLAUDE_SUBAGENT_TYPE", "")
    if subagent_type and "hydrator" in subagent_type.lower():
        return None

    # Also check transcript path directly (redundant but catches edge cases)
    if ctx.input_data:
        transcript_path = str(ctx.input_data.get("transcript_path", ""))
        if "/subagents/" in transcript_path or "/agent-" in transcript_path:
            return None

    # STATEFUL BYPASS: Check if hydrator is currently active (set when Task(hydrator) starts)
    # This is the reliable way to detect subagent tool calls since Claude Code
    # passes the main session's context to hooks, not the subagent's context.
    if session_state.is_hydrator_active(ctx.session_id):
        return None

    # Bypass for accepted tools (Strict List)
    if ctx.tool_name in HYDRATION_ALLOWED_TOOLS:
        return None

    # Bypass for MCP infrastructure tools (task manager, memory, etc.)
    if ctx.tool_name in MCP_TOOLS_EXEMPT_FROM_HYDRATION:
        return None

    # Bypass for safe git operations (add, commit, fetch, pull, status, etc.)
    # These are commonly needed during handover and don't corrupt history
    if ctx.tool_name in ("Bash", "run_shell_command", "run_command"):
        command = (
            ctx.tool_input.get("command") or ctx.tool_input.get("CommandLine") or ""
        )
        if _is_hydration_safe_bash(command):
            return None

    # Check if a skill is being activated (allow ANY skill to bypass hydration check)
    # If the user explicitly activates a skill, they are providing a plan/context.
    is_skill_activation = ctx.tool_name in ("activate_skill", "Skill")
    # Legacy: prompt-hydrator specific check (kept for robust detection context)
    is_hydrator_tool_or_agent = _hydration_is_hydrator_task(ctx.tool_input)
    is_gemini = _hydration_is_gemini_hydration_attempt(
        ctx.tool_name or "", ctx.tool_input, ctx.input_data
    )

    if is_skill_activation or is_hydrator_tool_or_agent or is_gemini:
        # Allow hydrator invocation but DO NOT clear hydration_pending here.
        # hydration_pending is cleared by SubagentStop handler when hydrator
        # completes with a valid ## HYDRATION RESULT output.
        # Subagent sessions bypass this gate at line 577, so hydrator can use
        # Read tools. The main agent's gates stay closed until hydrator completes.
        #
        # SET hydrator_active flag so the hydrator's own tool calls bypass this gate.
        if is_hydrator_tool_or_agent:
            session_state.set_hydrator_active(ctx.session_id)
        return None

    # Check if hydration is pending
    if not session_state.is_hydration_pending(ctx.session_id):
        return None

    # If we reach here, hydration is pending and not bypassed.
    # Check mode: "block" (default) or "warn"
    hydration_mode = os.environ.get("HYDRATION_MODE", DEFAULT_HYDRATION_GATE_MODE)

    # Get temp_path from session state to include in message
    temp_path = session_state.get_hydration_temp_path(ctx.session_id)
    if not temp_path:
        temp_path = "(temp file not found - check session state)"

    if hydration_mode == "warn":
        # Warn mode: allow but inject warning context
        warn_msg = load_template(HYDRATION_WARN_TEMPLATE, {"temp_path": temp_path})
        return GateResult(
            verdict=GateVerdict.WARN,
            system_message=None,
            context_injection=warn_msg,
        )

    # Block mode (default): deny with formatted message
    block_msg = load_template(HYDRATION_BLOCK_TEMPLATE, {"temp_path": temp_path})
    return GateResult(
        verdict=GateVerdict.DENY,
        system_message=None,
        context_injection=block_msg,
    )


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

    Enhanced (aops-226ccba2): Now includes:
    - All user requests (chronological) for scope drift detection
    - Tool arguments (truncated at 200 chars) for action verification
    - Full agent responses (last 3, up to 1000 chars each) for phrase pattern detection
    """
    if not transcript_path:
        return "(No transcript path available)"

    lines: list[str] = []

    # Extract using library
    gate_ctx = extract_gate_context(
        Path(transcript_path),
        include={"prompts", "errors", "tools", "files", "conversation", "skill"},
        max_turns=15,
    )

    # ALL user requests (chronological) - enables scope drift detection
    prompts = gate_ctx.get("prompts", [])
    if prompts:
        lines.append("**All User Requests** (chronological):")
        for i, prompt in enumerate(prompts, 1):
            # Truncate very long prompts but preserve enough for scope checking
            truncated = prompt[:500] + "..." if len(prompt) > 500 else prompt
            lines.append(f"  {i}. {truncated}")
        lines.append("")
        # Also highlight the most recent for quick reference
        lines.append("**Most Recent User Request**:")
        lines.append(f"> {prompts[-1][:500]}")
        lines.append("")

    # Active skill context (if any)
    skill = gate_ctx.get("skill")
    if skill:
        lines.append(f"**Active Skill**: {skill}")
        lines.append("")

    # Recent tool usage WITH ARGUMENTS - enables action verification
    tools = gate_ctx.get("tools", [])
    if tools:
        lines.append("**Recent Tool Calls** (with arguments):")
        for tool in tools[-10:]:  # Last 10 tools
            tool_name = tool["name"]  # Required field - fail if missing
            tool_input = tool.get("input") or {}
            # Format tool arguments, truncate at 200 chars
            if tool_input:
                # Summarize key arguments
                arg_parts = []
                for k, v in list(tool_input.items())[:5]:  # Max 5 args shown
                    v_str = str(v)
                    if len(v_str) > 50:
                        v_str = v_str[:50] + "..."
                    arg_parts.append(f"{k}={v_str}")
                args_str = ", ".join(arg_parts)
                if len(args_str) > 200:
                    args_str = args_str[:200] + "..."
                lines.append(f"  - {tool_name}({args_str})")
            else:
                lines.append(f"  - {tool_name}()")
        lines.append("")

    # Files modified/read
    files = gate_ctx.get("files", [])
    if files:
        lines.append("**Files Accessed**:")
        for f in files[-10:]:  # Last 10 files
            # These fields are required by extract_gate_context contract
            lines.append(f"  - [{f['action']}] {f['path']}")
        lines.append("")

    # Tool errors (important for compliance - Type A detection)
    errors = gate_ctx.get("errors", [])
    if errors:
        lines.append("**Tool Errors** (check for workaround attempts after these):")
        for e in errors[-5:]:
            lines.append(f"  - {e['tool_name']}: {e['error']}")
        lines.append("")

    # FULL agent responses for last 3 turns - enables phrase pattern detection
    # ("I'll just...", "While I'm at it...", etc.)
    conversation = gate_ctx.get("conversation", [])
    if conversation:
        lines.append("**Recent Agent Responses** (full text for phrase detection):")
        # Extract only agent responses, show last 3 with more content
        agent_responses = [
            turn
            for turn in conversation
            if (isinstance(turn, str) and turn.startswith("[Agent]:"))
        ]
        for turn in agent_responses[-3:]:  # Last 3 agent responses
            # String format: "[Agent]: content"
            content = turn[8:] if turn.startswith("[Agent]:") else turn
            # Allow up to 1000 chars per response for phrase detection
            if len(content) > 1000:
                content = content[:1000] + "..."
            if content.strip():
                lines.append(f"  {content.strip()}")
                lines.append("")

        # Also show recent conversation flow (condensed)
        lines.append("**Recent Conversation Summary**:")
        for turn in conversation[-5:]:
            # Handle both string and dict formats for backward compatibility
            if isinstance(turn, dict):
                role = turn["role"]  # Required - fail if missing
                content = turn["content"][:200]  # Required - fail if missing
                lines.append(f"  [{role}]: {content}...")
            else:
                # String format - prepend [unknown] for legacy compatibility
                content = str(turn)[:200]
                if content:
                    lines.append(f"  [unknown]: {content}...")
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


# --- Axiom Enforcer Logic ---


def check_axiom_enforcer_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Real-time axiom violation detection for Edit/Write operations.

    Blocks tool calls that contain code patterns violating framework axioms:
    - P#8: Fail-fast violations (fallbacks, silent exception handling)
    - P#12: DRY violations (future)
    - P#26: Verify-first violations (future)

    This gate runs BEFORE custodiet threshold checks to catch violations
    immediately, regardless of compliance counter state.

    Returns None if allowed, or GateResult with DENY if violation detected.
    """
    _check_imports()

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Only check code-modifying tools
    if ctx.tool_name not in (
        "Write",
        "Edit",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ):
        return None

    # Extract code/content for analysis
    code = ""
    if ctx.tool_name in ("Write", "write_to_file"):
        code = ctx.tool_input.get("content", "")
    elif ctx.tool_name in ("Edit", "replace_file_content"):
        code = ctx.tool_input.get("new_string", "")
    elif ctx.tool_name == "multi_replace_file_content":
        replacements = ctx.tool_input.get("replacements", [])
        code = "\n".join([r.get("new_string", "") for r in replacements])

    if not code:
        return None

    # Detect violations
    violations = axiom_detector.detect_all_violations(code)

    if not violations:
        return None

    # Format violation messages
    msg_lines = ["⛔ **AXIOM ENFORCEMENT BLOCKED**", ""]
    for v in violations:
        msg_lines.append(f"- **{v.axiom}**: {v.message}")
        if v.line_number:
            msg_lines.append(f"  Line {v.line_number}: `{v.context}`")

    msg_lines.append("")
    msg_lines.append(
        "Please fix these violations before submitting. No fallbacks, no workarounds."
    )

    return GateResult(
        verdict=GateVerdict.DENY,
        context_injection="\n".join(msg_lines),
        metadata={
            "source": "axiom_enforcer",
            "violations": [
                {"axiom": v.axiom, "pattern": v.pattern_name, "line": v.line_number}
                for v in violations
            ],
        },
    )


def check_custodiet_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Check if compliance is overdue (The Bouncer).
    Returns None if allowed, or GateResult if blocked.

    Only runs on PreToolUse events. Blocks mutating tools when too many
    tool calls have occurred without a compliance check.
    """
    _check_imports()

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Only block mutating tools (DRY: use shared definition)
    if ctx.tool_name not in MUTATING_TOOLS:
        return None

    # Track tool calls and trigger compliance check when threshold reached
    # Use unified SessionState API directly (no backwards compat wrappers)
    sess = session_state.get_or_create_session_state(ctx.session_id)
    state = sess.get("state", {})

    # Initialize custodiet fields if not present
    state.setdefault("tool_calls_since_compliance", 0)
    state.setdefault("last_compliance_ts", 0.0)

    # NOTE: Counter is incremented by run_accountant in PostToolUse, not here
    # We only READ the counter here to check if we should block
    tool_calls = state["tool_calls_since_compliance"]

    # NOTE: Axiom enforcement is now handled by dedicated check_axiom_enforcer_gate
    # which runs before custodiet in the PreToolUse gate chain.

    # Check compliance threshold
    threshold = get_custodiet_threshold()
    if tool_calls < threshold:
        return None

    # At or over threshold - block mutating tool with full instruction
    try:
        # Build the instruction using the full context logic
        # (This creates the temp file and formats the custodiet-instruction.md template)
        instruction = _custodiet_build_audit_instruction(
            ctx.transcript_path, ctx.tool_name or "unknown", ctx.session_id
        )

        # Return as a deny/block
        return GateResult(
            verdict=GateVerdict.DENY,
            context_injection=instruction,
            metadata={"source": "custodiet", "tool_calls": tool_calls},
        )

    except (OSError, KeyError, TypeError) as e:
        # Fail-open: if instruction generation fails, fall back to simple block
        print(f"WARNING: Custodiet audit generation failed: {e}", file=sys.stderr)
        block_msg = load_template(
            CUSTODIET_FALLBACK_TEMPLATE, {"tool_calls": str(tool_calls)}
        )
        return GateResult(
            verdict=GateVerdict.DENY,
            context_injection=block_msg,
            metadata={"source": "custodiet_fallback", "error": str(e)},
        )


def _task_gate_status(passed: bool) -> str:
    """Return gate status indicator."""
    return "\u2713" if passed else "\u2717"


def _build_task_block_message(gates: Dict[str, bool]) -> str:
    """Build a detailed block message showing which gates are missing."""
    missing = []
    if not gates["task_bound"]:
        missing.append(
            '(a) Claim a task: `mcp__plugin_aops-core_task_manager__update_task(id="...", status="in_progress")`'
        )
    # Check for hydration (using hydrated_intent or hydrator_invoked equivalent)
    # We map "plan_mode_invoked" to "hydrator_invoked" in the template
    if not gates["plan_mode_invoked"]:
        missing.append(
            '(b) Hydrate prompt: invoke the **aops-core:prompt-hydrator** agent or skill (Claude: `activate_skill(name="aops-core:prompt-hydrator", ...)` | Gemini: `activate_skill(name="prompt-hydrator", ...)`) to transform your prompt into a plan.'
        )
    if not gates["critic_invoked"]:
        missing.append(
            '(c) Invoke critic: `activate_skill(name="critic", prompt="Review this plan: ...")`'
        )

    return load_template(
        TASK_GATE_BLOCK_TEMPLATE,
        {
            "task_bound_status": _task_gate_status(gates["task_bound"]),
            "hydrator_invoked_status": _task_gate_status(gates["plan_mode_invoked"]),
            "critic_invoked_status": _task_gate_status(gates["critic_invoked"]),
            "missing_gates": "\n".join(missing),
        },
    )


def _build_task_warn_message(gates: Dict[str, bool]) -> str:
    """Build a warning message for warn-only mode."""
    return load_template(
        TASK_GATE_WARN_TEMPLATE,
        {
            "task_bound_status": _task_gate_status(gates["task_bound"]),
            "hydrator_invoked_status": _task_gate_status(gates["plan_mode_invoked"]),
            "critic_invoked_status": _task_gate_status(gates["critic_invoked"]),
        },
    )


def _get_task_gate_mode() -> str:
    """Get TASK_GATE_MODE from environment, defaulting to warn mode.

    Uses explicit check for env var presence to comply with fail-fast axiom
    while still providing a sensible default for optional configuration.
    """
    if "TASK_GATE_MODE" in os.environ:
        return os.environ["TASK_GATE_MODE"].lower()
    return DEFAULT_TASK_GATE_MODE


def _is_full_gate_enforcement_enabled() -> bool:
    """Check if full three-gate enforcement is enabled.

    Returns True if TASK_GATE_ENFORCE_ALL is set to a truthy value.
    """
    if "TASK_GATE_ENFORCE_ALL" not in os.environ:
        return False
    return os.environ["TASK_GATE_ENFORCE_ALL"].lower() in ("1", "true", "yes")


def check_task_required_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    TASK GATE: Unified enforcement for destructive operations.
    Returns None if allowed, or GateResult if blocked/warned.

    Only runs on PreToolUse events. Enforces three-gate requirement:
    (a) Task bound - session has an active task claimed
    (b) Hydrator invoked - prompt-hydrator or plan mode completed
    (c) Critic invoked - critic agent reviewed the plan

    This gate consolidates the former separate hydration and task-required gates
    into a single enforcement point for all destructive operations.
    """
    _check_imports()

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Bypass for subagent sessions
    if hook_utils.is_subagent_session(ctx.input_data):
        return None

    # Bypass for handover skill invocation (needs to run git/etc for closure)
    if _is_handover_skill_invocation(ctx.tool_name or "", ctx.tool_input):
        return None

    # Check if operation requires task binding (destructive operations only)
    if not _should_require_task(ctx.tool_name or "", ctx.tool_input):
        return None

    # Check if gates are bypassed (. prefix)
    state = session_state.load_session_state(ctx.session_id)
    if state is not None:
        state_dict = state.get("state")
        if state_dict is not None and state_dict.get("gates_bypassed"):
            return None

    # Check all gate statuses
    gates = session_state.check_all_gates(ctx.session_id)

    # Enforce task_bound gate (the primary gate for destructive operations)
    # The other gates (plan_mode_invoked, critic_invoked) are tracked but
    # enforcement is configurable via TASK_GATE_ENFORCE_ALL env var
    if _is_full_gate_enforcement_enabled():
        # Full three-gate enforcement
        if gates["task_bound"] and gates["plan_mode_invoked"] and gates["critic_invoked"]:
            return None
    else:
        # Default: only enforce task_bound (other gates for observability)
        if gates["task_bound"]:
            return None

    # Gates not passed - enforce based on mode
    gate_mode = _get_task_gate_mode()
    if gate_mode == "block":
        block_msg = _build_task_block_message(gates)
        return GateResult(verdict=GateVerdict.DENY, context_injection=block_msg)
    else:
        # Warn mode: allow but inject warning as context
        warn_msg = _build_task_warn_message(gates)
        return GateResult(verdict=GateVerdict.WARN, context_injection=warn_msg)


# --- Accountant Logic (Post-Tool State Updates) ---


def run_accountant(ctx: GateContext) -> Optional[GateResult]:
    """
    The Accountant: General state tracking for all components.
    Runs on PostToolUse. Never blocks, only updates state.

    Components tracked:
    1. Hydration: Clears pending flag if hydrator ran; increments turns_since_hydration.
    2. Custodiet: Increments tool count or resets if custodiet ran.
    3. Handover: Sets handover flag if handover skill ran; clears on mutating tools.
    """
    _check_imports()

    # Only applies to PostToolUse
    if ctx.event_name != "PostToolUse":
        return None

    system_messages: list[str] = []

    # 1. Hydration State Update
    # NOTE: Do NOT clear hydration_pending here. PostToolUse fires when the
    # Task tool call completes, but the subagent hasn't returned yet.
    # hydration_pending is cleared by SubagentStop handler when the hydrator
    # actually completes with a valid ## HYDRATION RESULT output.
    #
    # BUT we DO clear hydrator_active here because the Task tool has completed,
    # meaning the hydrator subagent has finished running.
    # Include Skill/activate_skill for Claude/Gemini which may use them to spawn hydrator.
    if ctx.tool_name in ("Task", "delegate_to_agent", "activate_skill", "Skill"):
        if _hydration_is_hydrator_task(ctx.tool_input):
            session_state.clear_hydrator_active(ctx.session_id)

        # Track subagent invocations for stop gate (checks has_run_subagents)
        subagent_type = (
            ctx.tool_input.get("subagent_type")
            or ctx.tool_input.get("agent_name")
            or ctx.tool_input.get("skill")
            or ctx.tool_input.get("name")
        )
        if subagent_type:
            sess = session_state.get_or_create_session_state(ctx.session_id)
            subagents = sess.setdefault("subagents", {})
            subagents[subagent_type] = subagents.get(subagent_type, 0) + 1
            session_state.save_session_state(ctx.session_id, sess)

    # 1b. Increment turns_since_hydration for non-read-only tool calls.
    # This tracks how many actions have occurred since hydration completed.
    # The counter semantics:
    #   -1 = never hydrated (new prompt needs hydration)
    #    0 = just hydrated, no actions yet
    #   >0 = N actions since hydration
    # Only increment for non-safe tools to avoid inflating count on reads.
    if ctx.tool_name not in SAFE_READ_TOOLS:
        sess = session_state.get_or_create_session_state(ctx.session_id)
        hydration_state = sess.setdefault("hydration", {})
        hydration_state.setdefault("turns_since_hydration", -1)
        turns_since = hydration_state["turns_since_hydration"]
        if turns_since >= 0:
            hydration_state["turns_since_hydration"] = turns_since + 1
            session_state.save_session_state(ctx.session_id, sess)

    # 2. Update Custodiet State
    # Skip for safe read-only tools to avoid noise
    if ctx.tool_name not in SAFE_READ_TOOLS:
        sess = session_state.get_or_create_session_state(ctx.session_id)
        state = sess.setdefault("state", {})

        # Initialize fields
        state.setdefault("tool_calls_since_compliance", 0)
        state.setdefault("last_compliance_ts", 0.0)

        # Check for reset (custodiet invoked) or increment
        if _is_custodiet_invocation(ctx.tool_name or "", ctx.tool_input):
            state["tool_calls_since_compliance"] = 0
            state["last_compliance_ts"] = time.time()
            system_messages.append(
                "🛡️ [Gate] Compliance verified. Custodiet gate reset."
            )

        else:
            state["tool_calls_since_compliance"] += 1

        session_state.save_session_state(ctx.session_id, sess)

    # 3. Update Handover State
    # Handover gate starts OPEN (handover_skill_invoked=True).
    # Reset to False when DESTRUCTIVE tools are used (requiring handover again).
    # Read-only tools (including read-only Bash commands) do NOT reset the gate.
    if _is_handover_skill_invocation(ctx.tool_name or "", ctx.tool_input):
        try:
            session_state.set_handover_skill_invoked(ctx.session_id)
            system_messages.append("🤝 [Gate] Handover recorded. Stop gate open.")
        except Exception as e:
            print(
                f"WARNING: Accountant failed to set handover flag: {e}", file=sys.stderr
            )
    elif _is_actually_destructive(ctx.tool_name or "", ctx.tool_input):
        # Destructive tool used - require handover before stop
        try:
            session_state.clear_handover_skill_invoked(ctx.session_id)
            system_messages.append(
                "⚠️ [Gate] Destructive tool used. Handover required before stop."
            )
        except Exception as e:
            print(
                f"WARNING: Accountant failed to clear handover flag: {e}",
                file=sys.stderr,
            )

    if system_messages:
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="\n".join(system_messages),
        )

    return None


def check_stop_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Check if the agent is allowed to stop (Stop / AfterAgent Enforcement).
    Returns None if allowed, or GateResult if blocked/warned.

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
    current_workflow = state.get("state", {}).get("current_workflow")

    is_hydrated = (
        hydration_data.get("hydrated_intent") is not None
        or hydration_data.get("original_prompt") is not None
    )
    has_run_subagents = len(subagents) > 0
    is_streamlined = current_workflow in ("interactive-followup", "simple-question", "direct-skill")

    if is_hydrated and not has_run_subagents and not is_streamlined:
        # User explicitly asked for turns_since_hydration == 0 logic
        # This implies the agent is trying to stop immediately after the hydrator finished.
        msg = load_template(STOP_GATE_CRITIC_TEMPLATE)
        return GateResult(verdict=GateVerdict.DENY, context_injection=msg)

    # --- 2. Handover Check ---
    if not session_state.is_handover_skill_invoked(ctx.session_id):
        # Issue warning but allow stop
        msg = load_template(STOP_GATE_HANDOVER_BLOCK_TEMPLATE)
        return GateResult(verdict=GateVerdict.DENY, context_injection=msg)

    return None


def check_hydration_recency_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Stop hook: Block exit if turns since hydration == 0.
    This ensures the agent doesn't hydrate then immediately exit.
    """
    _check_imports()

    # Load session state to check turns since hydration
    # Note: We need to load full state to check this tracker
    state = session_state.get_or_create_session_state(ctx.session_id)
    hydration_state = state.get("hydration", {})

    turns_since = hydration_state.get("turns_since_hydration")
    current_workflow = state.get("state", {}).get("current_workflow")
    is_streamlined = current_workflow in ("interactive-followup", "simple-question", "direct-skill")

    if turns_since == 0 and not is_streamlined:
        return GateResult(
            verdict=GateVerdict.DENY,
            context_injection="You just completed hydration. Please execute the plan before ending the session.",
        )

    return None


def post_hydration_trigger(ctx: GateContext) -> Optional[GateResult]:
    """
    PostToolUse: Detect successful hydration and inject next step.
    """
    _check_imports()

    # Check if this was a successful hydration
    # We re-use logic from check_hydration_gate to identify hydrator tools
    is_hydrator_tool = ctx.tool_name in (
        "Task",
        "delegate_to_agent",
        "activate_skill",
        "Skill",
    )
    is_hydrator = is_hydrator_tool and _hydration_is_hydrator_task(ctx.tool_input)
    is_gemini = _hydration_is_gemini_hydration_attempt(
        ctx.tool_name or "", ctx.tool_input, ctx.input_data
    )

    if is_hydrator or is_gemini:
        # Reset trackers
        session_state.update_hydration_metrics(ctx.session_id, turns_since_hydration=0)
        session_state.clear_hydration_pending(ctx.session_id)

        # User-facing output + agent context injection
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="💧 [Gate] Hydration complete. Critic required next.",
            context_injection="<system-reminder>\nNext, invoke the critic and revise your plan.\n</system-reminder>",
        )

    return None


def post_critic_trigger(ctx: GateContext) -> Optional[GateResult]:
    """
    PostToolUse: Detect successful critic invocation and update state.
    """
    _check_imports()

    # Check if this was a critic invocation
    is_delegate = ctx.tool_name == "delegate_to_agent"
    is_critic = is_delegate and ctx.tool_input.get("agent_name") == "critic"

    # Also check Task tool (Claude)
    is_task = ctx.tool_name == "Task"
    subagent_type = ctx.tool_input.get("subagent_type", "")
    is_critic_task = is_task and (
        subagent_type == "critic"
        or subagent_type == "aops-core:critic"
        or "critic" in subagent_type.lower()
    )

    # Also check Skill/activate_skill
    is_skill = ctx.tool_name in ("activate_skill", "Skill")
    skill_input = ctx.tool_input or {}
    skill_name = skill_input.get("name") or skill_input.get("skill")
    is_critic_skill = is_skill and skill_name == "critic"

    if is_critic or is_critic_task or is_critic_skill:
        # Set flags
        session_state.set_critic_invoked(
            ctx.session_id, "INVOKED"
        )  # Generic verdict for now
        session_state.update_hydration_metrics(ctx.session_id, turns_since_critic=0)

        # User-facing output for gate state change
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="🔍 [Gate] Critic invoked. Gate satisfied.",
        )

    return None


def post_qa_trigger(ctx: GateContext) -> Optional[GateResult]:
    """
    PostToolUse: Detect successful QA invocation and update state.
    """
    _check_imports()

    # Check if this was a QA invocation
    is_delegate = ctx.tool_name == "delegate_to_agent"
    is_qa = is_delegate and ctx.tool_input.get("agent_name") == "qa"

    # Also check Task tool (Claude)
    is_task = ctx.tool_name == "Task"
    subagent_type = ctx.tool_input.get("subagent_type", "")
    is_qa_task = is_task and (
        subagent_type == "qa"
        or subagent_type == "aops-core:qa"
        or "qa" in subagent_type.lower()
    )

    # Also check Skill/activate_skill
    is_skill = ctx.tool_name in ("activate_skill", "Skill")
    skill_input = ctx.tool_input or {}
    skill_name = skill_input.get("name") or skill_input.get("skill")
    is_qa_skill = is_skill and skill_name == "qa"

    if is_qa or is_qa_task or is_qa_skill:
        # Set flags
        session_state.set_qa_invoked(ctx.session_id)

        # User-facing output for gate state change
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="🧪 [Gate] QA verified. Gate satisfied.",
        )

    return None


def check_agent_response_listener(ctx: GateContext) -> Optional[GateResult]:
    """
    AfterAgent: Listen to agent response for state updates and optional enforcement.

    Checks:
    1. Hydration result in text -> clear pending flag
    2. Handover reflection in text -> set handover flag
    """
    _check_imports()

    if ctx.event_name != "AfterAgent":
        return None

    response_text = ctx.input_data.get("prompt_response", "")

    # 1. Update Hydration State
    # Check for "HYDRATION RESULT" or "Execution Plan" (agent may vary format)
    if re.search(
        r"(?:##\s*|\*\*)?(?:HYDRATION RESULT|Execution Plan|Execution Steps)",
        response_text,
        re.IGNORECASE,
    ):
        session_state.clear_hydration_pending(ctx.session_id)
        # Reset turns counter since hydration just happened
        session_state.update_hydration_metrics(ctx.session_id, turns_since_hydration=0)

        # Parse workflow ID
        workflow_match = re.search(
            r"\*\*Workflow\*\*:\s*\[\[workflows/([^\]]+)\]\]", response_text
        )
        workflow_id = workflow_match.group(1) if workflow_match else None

        if workflow_id:
            state = session_state.get_or_create_session_state(ctx.session_id)
            state["state"]["current_workflow"] = workflow_id
            session_state.save_session_state(ctx.session_id, state)

        # Detect streamlined workflows that skip critic
        is_streamlined = workflow_id in ("interactive-followup", "simple-question", "direct-skill")

        if is_streamlined:
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"[Gate] Hydration complete (workflow: {workflow_id}). Streamlined mode enabled.",
                metadata={
                    "source": "post_hydration_trigger",
                    "streamlined": True,
                    "workflow": workflow_id,
                },
            )

        # Inject instruction to invoke critic
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="💧 [Gate] Hydration plan detected. Gate satisfied.",
            context_injection=(
                "<system-reminder>\n"
                "Hydration plan detected. Next step: Invoke the critic to review this plan.\n"
                "Use: `activate_skill(name='critic', prompt='Review this plan...')`\n"
                "</system-reminder>"
            ),
            metadata={"source": "post_hydration_trigger"},
        )

    # 2. Update Handover State
    if "## Framework Reflection" in response_text:
        session_state.set_handover_skill_invoked(ctx.session_id)
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="🧠 [Gate] Framework Reflection detected. Handover gate open.",
        )

    return None


def check_session_start_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Handle SessionStart event.
    Returns GateResult with startup information displayed to USER (system_message).
    """
    _check_imports()

    if ctx.event_name != "SessionStart":
        return None

    try:
        from hooks.unified_logger import get_hook_log_path

        status_dir = session_paths.get_session_status_dir(
            ctx.session_id, ctx.input_data
        )
        short_hash = session_paths.get_session_short_hash(ctx.session_id)

        # Get hook log path for this session (full absolute path)
        hook_log_path = get_hook_log_path(ctx.session_id, ctx.input_data)

        # Get actual state file path (not a glob pattern)
        state_file_path = session_paths.get_session_file_path(
            ctx.session_id, input_data=ctx.input_data
        )

        # Build startup message for USER display (system_message, not context_injection)
        msg_lines = [
            f"🚀 Session Started: {ctx.session_id} ({short_hash})",
            f"State File: {state_file_path}",
            f"Hooks log: {hook_log_path}",
        ]

        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="\n".join(msg_lines),
            metadata={"source": "session_start"},
        )

    except Exception as e:
        # Fallback if session state access fails
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message=f"Session Started: {ctx.session_id}\n(Error loading details: {e})",
            metadata={"source": "session_start", "error": str(e)},
        )


def check_skill_activation_listener(ctx: GateContext) -> Optional[GateResult]:
    """
    Listener: Clear hydration pending if a non-infrastructure skill was activated.

    Infrastructure skills (like /bump, /diag, /log) do NOT clear hydration state
    because they are utility/navigation commands, not hydration-completing actions.
    Only skills that provide meaningful context should clear the hydration gate.
    """
    _check_imports()

    if ctx.event_name != "PostToolUse":
        return None

    # Handle both Claude Code (Skill) and Gemini (activate_skill) tool names
    if ctx.tool_name not in ("activate_skill", "Skill"):
        return None

    # Extract skill name from tool input
    # Claude Skill tool uses 'skill', Gemini activate_skill uses 'name'
    tool_input = ctx.tool_input or {}
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}

    skill_name = tool_input.get("skill") or tool_input.get("name") or ""

    # Fail-safe: Empty/unknown skill names should NOT clear hydration
    # We require a known substantive skill to clear the hydration gate
    if not skill_name:
        return GateResult(
            verdict=GateVerdict.ALLOW,
            metadata={"source": "skill_activation_unknown", "skill": ""},
        )

    # Infrastructure skills should NOT clear hydration pending
    # These are utility/navigation commands that don't satisfy the hydration intent
    if skill_name in INFRASTRUCTURE_SKILLS_NO_HYDRATION_CLEAR:
        return GateResult(
            verdict=GateVerdict.ALLOW,
            metadata={"source": "skill_activation_infrastructure", "skill": skill_name},
        )

    # Non-infrastructure skill activated - clear hydration pending
    # The user intent "run this skill" with a substantive skill satisfies hydration.
    session_state.clear_hydration_pending(ctx.session_id)

    return GateResult(
        verdict=GateVerdict.ALLOW,
        metadata={"source": "skill_activation_bypass", "skill": skill_name},
        system_message=f"⚡ [Gate] Skill '{skill_name}' activated. Hydration gate cleared.",
    )


def check_qa_enforcement_gate(ctx: GateContext) -> Optional[GateResult]:
    """
    Check if QA verification is required before task completion.
    """
    _check_imports()

    # Only applies to PreToolUse
    if ctx.event_name != "PreToolUse":
        return None

    # Only applies to complete_task
    if ctx.tool_name not in (
        "complete_task",
        "mcp__plugin_aops-core_task_manager__complete_task",
    ):
        return None

    # Check if QA is required
    # Requirement: If prompt-hydrator was used (hydrated_intent exists), QA is mandatory.
    state = session_state.load_session_state(ctx.session_id)
    if not state:
        return None

    hydration = state.get("hydration", {})
    hydrated_intent = hydration.get("hydrated_intent")

    if not hydrated_intent:
        # No hydration occurred, so strictly speaking QA might not be mandated by hydrator.
        return None

    # Check if QA was invoked
    if session_state.is_qa_invoked(ctx.session_id):
        return None

    # Block
    return GateResult(
        verdict=GateVerdict.DENY,
        context_injection=(
            "⛔ **BLOCKED: QA Verification Required**\n\n"
            "This task was planned via `prompt-hydrator`, which mandates a QA step.\n"
            "You have not invoked the QA skill yet.\n\n"
            "**Action Required**: Run `activate_skill(name='qa')` to verify your work before completion."
        ),
        metadata={"source": "qa_enforcement"},
    )


# --- Unified Logger Gate (formerly unified_logger.py) ---


def run_unified_logger(ctx: GateContext) -> Optional[GateResult]:
    """
    Log hook events to session file and handle SubagentStop/Stop state updates.
    Never blocks, only updates state and returns context for SessionStart.
    """
    _check_imports()

    try:
        from hooks.unified_logger import log_event_to_session
    except ImportError as e:
        print(f"WARNING: unified_logger import failed: {e}", file=sys.stderr)
        return None

    try:
        # log_event_to_session now returns GateResult directly (no dict conversion)
        return log_event_to_session(ctx.session_id, ctx.event_name, ctx.input_data)
    except Exception as e:
        print(f"WARNING: unified_logger error: {e}", file=sys.stderr)

    return None


# --- User Prompt Submit Gate (formerly user_prompt_submit.py) ---


def run_user_prompt_submit(ctx: GateContext) -> Optional[GateResult]:
    """
    UserPromptSubmit: Build hydration context and return instruction.
    """
    _check_imports()

    if ctx.event_name != "UserPromptSubmit":
        return None

    try:
        from hooks.user_prompt_submit import (
            build_hydration_instruction,
            should_skip_hydration,
            write_initial_hydrator_state,
        )
        from lib.session_state import (
            get_or_create_session_state,
            save_session_state,
            set_gates_bypassed,
            clear_reflection_output,
        )
    except ImportError as e:
        print(f"WARNING: user_prompt_submit import failed: {e}", file=sys.stderr)
        return None

    prompt = ctx.input_data.get("prompt", "")
    transcript_path = ctx.input_data.get("transcript_path")
    session_id = ctx.session_id

    if not session_id:
        return None

    try:
        clear_reflection_output(session_id)

        # Check for skip patterns FIRST before any state changes
        if should_skip_hydration(prompt):
            write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
            if prompt.strip().startswith("."):
                set_gates_bypassed(session_id, True)
            return None

        if prompt:
            hydration_instruction = build_hydration_instruction(
                session_id, prompt, transcript_path
            )
            return GateResult(
                verdict=GateVerdict.ALLOW,
                context_injection=hydration_instruction,
                metadata={"source": "user_prompt_submit"},
            )
    except Exception as e:
        import traceback

        print(f"WARNING: user_prompt_submit error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    return None


# --- Task Binding Gate (formerly task_binding.py) ---


def run_task_binding(ctx: GateContext) -> Optional[GateResult]:
    """
    PostToolUse: Bind/unbind task to session when task MCP operations occur.
    """
    _check_imports()

    if ctx.event_name != "PostToolUse":
        return None

    try:
        from lib.hook_utils import get_task_id_from_result
        from lib.event_detector import detect_tool_state_changes, StateChange
    except ImportError as e:
        print(f"WARNING: task_binding import failed: {e}", file=sys.stderr)
        return None

    # Support both Claude (snake_case) and Gemini (camelCase) field names
    tool_name = ctx.tool_name or ctx.input_data.get("tool_name") or ctx.input_data.get("toolName", "")
    tool_input = ctx.tool_input or ctx.input_data.get("tool_input") or ctx.input_data.get("toolInput", {})
    tool_result = (
        ctx.input_data.get("tool_result")
        or ctx.input_data.get("toolResult")
        or ctx.input_data.get("tool_response", {})
    )

    try:
        changes = detect_tool_state_changes(tool_name, tool_input, tool_result)
    except Exception as e:
        print(f"WARNING: event_detector error: {e}", file=sys.stderr)
        return None

    if StateChange.PLAN_MODE in changes:
        try:
            if not session_state.is_plan_mode_invoked(ctx.session_id):
                session_state.set_plan_mode_invoked(ctx.session_id)
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message="🗺️ [Gate] Plan mode invoked. Gate satisfied.",
                )
        except Exception as e:
            print(f"WARNING: task_binding plan_mode error: {e}", file=sys.stderr)

    if StateChange.UNBIND_TASK in changes:
        try:
            current = session_state.get_current_task(ctx.session_id)
            if current:
                session_state.clear_current_task(ctx.session_id)
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"🔓 [Gate] Task unbound: {current}",
                )
        except Exception as e:
            print(f"WARNING: task_binding unbind error: {e}", file=sys.stderr)

    if StateChange.BIND_TASK in changes:
        task_id = get_task_id_from_result(tool_result)
        if task_id:
            try:
                current = session_state.get_current_task(ctx.session_id)
                if current and current != task_id:
                    return GateResult(
                        verdict=GateVerdict.ALLOW,
                        system_message=f"ℹ️ [Gate] Already bound to {current}, ignoring {task_id}",
                    )
                session_state.set_current_task(ctx.session_id, task_id, source="claim")
                return GateResult(
                    verdict=GateVerdict.ALLOW,
                    system_message=f"📌 [Gate] Task bound: {task_id}",
                )
            except Exception as e:
                print(f"WARNING: task_binding bind error: {e}", file=sys.stderr)

    return None


# --- Session End Commit Check Gate (formerly session_end_commit_check.py) ---


def run_session_end_commit_check(ctx: GateContext) -> Optional[GateResult]:
    """
    Stop: Check for uncommitted work and perform session cleanup.
    """
    _check_imports()

    if ctx.event_name != "Stop":
        return None

    try:
        from hooks.session_end_commit_check import (
            check_uncommitted_work,
            perform_session_cleanup,
        )
    except ImportError as e:
        print(f"WARNING: session_end_commit_check import failed: {e}", file=sys.stderr)
        return None

    session_id = ctx.session_id
    transcript_path = ctx.input_data.get("transcript_path")

    # Check for active task
    try:
        current_task = session_state.get_current_task(session_id)
        if current_task:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=f"⛔ Active task bound: {current_task}. Complete or unbind first.",
            )
    except Exception as e:
        print(f"WARNING: task check failed: {e}", file=sys.stderr)

    # Check for uncommitted work
    try:
        check_result = check_uncommitted_work(session_id, transcript_path)
        if check_result.should_block:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=check_result.message,
            )
    except Exception as e:
        print(f"WARNING: uncommitted work check failed: {e}", file=sys.stderr)

    # Perform cleanup
    try:
        perform_session_cleanup(session_id, transcript_path)
    except Exception as e:
        print(f"WARNING: session cleanup failed: {e}", file=sys.stderr)

    return GateResult(
        verdict=GateVerdict.ALLOW,
        system_message="✅ handover verified",
    )


# --- Generate Transcript Gate (formerly generate_transcript.py) ---


def run_generate_transcript(ctx: GateContext) -> Optional[GateResult]:
    """
    Stop: Run transcript.py on session end.
    """
    if ctx.event_name != "Stop":
        return None

    transcript_path = ctx.input_data.get("transcript_path")
    if not transcript_path:
        return None

    try:
        import subprocess
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        script_path = root_dir / "scripts" / "transcript.py"

        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), transcript_path],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 and result.returncode != 2:
                print(
                    f"WARNING: Transcript generation failed: {result.stderr}",
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"WARNING: generate_transcript error: {e}", file=sys.stderr)

    return None


# --- ntfy Push Notification Gate ---


def run_ntfy_notifier(ctx: GateContext) -> Optional[GateResult]:
    """
    Send push notifications for key session events via ntfy.

    Non-blocking: notification failures are logged but don't affect execution.
    Only runs if ntfy is configured (NTFY_TOPIC env var set).

    Events:
    - SessionStart: Notify session began
    - Stop: Notify session ended
    - PostToolUse: Notify task bind/unbind, subagent completion
    """
    # Check if ntfy is configured (returns None if disabled)
    try:
        config = get_ntfy_config()
    except RuntimeError as e:
        # Configuration error - log and continue (don't block)
        print(f"WARNING: ntfy config error: {e}", file=sys.stderr)
        return None

    if not config:
        # ntfy not configured - silently skip
        return None

    try:
        from hooks.ntfy_notifier import (
            notify_session_start,
            notify_session_stop,
            notify_subagent_stop,
            notify_task_bound,
            notify_task_completed,
        )
    except ImportError as e:
        print(f"WARNING: ntfy_notifier import failed: {e}", file=sys.stderr)
        return None

    # SessionStart notification
    if ctx.event_name == "SessionStart":
        notify_session_start(config, ctx.session_id)
        return None

    # Stop notification
    if ctx.event_name == "Stop":
        # Get current task if any
        try:
            current_task = session_state.get_current_task(ctx.session_id)
        except Exception:
            current_task = None
        notify_session_stop(config, ctx.session_id, current_task)
        return None

    # PostToolUse: task binding and subagent completion
    if ctx.event_name == "PostToolUse":
        # Check for task binding
        if ctx.tool_name in TASK_BINDING_TOOLS:
            tool_input = ctx.tool_input
            # Use 'in' check instead of .get() for fail-fast compliance
            if "status" in tool_input and "id" in tool_input:
                status = tool_input["status"]
                task_id = tool_input["id"]

                if status == "in_progress":
                    notify_task_bound(config, ctx.session_id, task_id)
                elif status == "done":
                    notify_task_completed(config, ctx.session_id, task_id)

        # Check for subagent completion (Task tool)
        if ctx.tool_name in ("Task", "delegate_to_agent"):
            # Extract agent type - try both field names
            agent_type = "unknown"
            if "subagent_type" in ctx.tool_input:
                agent_type = ctx.tool_input["subagent_type"]
            elif "agent_name" in ctx.tool_input:
                agent_type = ctx.tool_input["agent_name"]

            # Try to extract verdict from tool result
            verdict = None
            if "tool_result" in ctx.input_data:
                tool_result = ctx.input_data["tool_result"]
                if isinstance(tool_result, dict) and "verdict" in tool_result:
                    verdict = tool_result["verdict"]
                elif isinstance(tool_result, str):
                    try:
                        parsed = json.loads(tool_result)
                        if isinstance(parsed, dict) and "verdict" in parsed:
                            verdict = parsed["verdict"]
                    except (json.JSONDecodeError, AttributeError):
                        pass
            elif "toolResult" in ctx.input_data:
                tool_result = ctx.input_data["toolResult"]
                if isinstance(tool_result, dict) and "verdict" in tool_result:
                    verdict = tool_result["verdict"]

            notify_subagent_stop(config, ctx.session_id, agent_type, verdict)

    return None


# Registry of available gate checks
GATE_CHECKS = {
    # Universal gates
    "unified_logger": run_unified_logger,
    "ntfy_notifier": run_ntfy_notifier,
    # UserPromptSubmit
    "user_prompt_submit": run_user_prompt_submit,
    # PreToolUse gates (order matters)
    "subagent_restrictions": check_subagent_tool_restrictions,
    "session_start": check_session_start_gate,
    "hydration": check_hydration_gate,
    "task_required": check_task_required_gate,
    "axiom_enforcer": check_axiom_enforcer_gate,
    "custodiet": check_custodiet_gate,
    "qa_enforcement": check_qa_enforcement_gate,
    # PostToolUse gates
    "task_binding": run_task_binding,
    "accountant": run_accountant,
    "post_hydration": post_hydration_trigger,
    "post_critic": post_critic_trigger,
    "post_qa": post_qa_trigger,
    "skill_activation": check_skill_activation_listener,
    # AfterAgent gates
    "agent_response": check_agent_response_listener,
    # Stop gates
    "stop_gate": check_stop_gate,
    # "hydration_recency": check_hydration_recency_gate,  # Disabled: too restrictive for direct questions/skills
    "session_end_commit": run_session_end_commit_check,
    "generate_transcript": run_generate_transcript,
}
