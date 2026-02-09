"""
Gate Registry: Defines the logic for specific gates.

This module contains the "Conditions" that gates evaluate.
"""

import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from lib.gate_model import GateResult, GateVerdict
from lib.paths import get_ntfy_config

from hooks.schemas import HookContext

# Adjust imports to work within the aops-core environment
# These imports are REQUIRED for gate functionality - fail explicitly if missing
_IMPORT_ERROR: str | None = None
try:
    from lib.session_reader import build_rich_session_context, extract_gate_context
    from lib.template_loader import load_template

    from lib import axiom_detector, hook_utils, session_paths, session_state
except ImportError as e:
    _IMPORT_ERROR = str(e)
    # Provide stub implementations that raise clear errors when used
    session_state = None  # type: ignore[assignment]
    session_paths = None  # type: ignore[assignment]
    hook_utils = None  # type: ignore[assignment]
    axiom_detector = None  # type: ignore[assignment]
    load_template = None  # type: ignore[assignment]
    extract_gate_context = None  # type: ignore[assignment]
    build_rich_session_context = None  # type: ignore[assignment]


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
# DEPRECATED: Use TemplateRegistry.instance().render("hydration.block", ...) instead
HYDRATION_BLOCK_TEMPLATE = Path(__file__).parent / "templates" / "hydration-gate-block.md"

# Custodiet
CUSTODIET_TEMP_CATEGORY = "hydrator"
CUSTODIET_DEFAULT_THRESHOLD = 7


# DEPRECATED: Use TemplateRegistry.instance().render("custodiet.context", ...) instead
CUSTODIET_CONTEXT_TEMPLATE_FILE = Path(__file__).parent / "templates" / "custodiet-context.md"
# DEPRECATED: Use TemplateRegistry.instance().render("custodiet.instruction", ...) instead
CUSTODIET_INSTRUCTION_TEMPLATE_FILE = (
    Path(__file__).parent / "templates" / "custodiet-instruction.md"
)
# DEPRECATED: Use TemplateRegistry.instance().render("custodiet.fallback", ...) instead
CUSTODIET_FALLBACK_TEMPLATE = Path(__file__).parent / "templates" / "overdue-enforcement-block.md"
AOPS_ROOT = Path(__file__).parent.parent.parent  # aops-core -> hooks -> gate_registry -> ...
AXIOMS_FILE = AOPS_ROOT / "aops-core" / "AXIOMS.md"
HEURISTICS_FILE = AOPS_ROOT / "aops-core" / "HEURISTICS.md"
SKILLS_FILE = AOPS_ROOT / "aops-core" / "SKILLS.md"

# --- Task Required Gate Constants ---

# Tools that bind/unbind tasks to sessions (for ntfy notifications)
TASK_BINDING_TOOLS = {
    "mcp__plugin_aops-core_task_manager__update_task",
    "mcp__plugin_aops-core_task_manager__claim_next_task",
    "mcp__plugin_aops-core_task_manager__complete_task",
    "mcp__plugin_aops-core_task_manager__complete_tasks",
    # Gemini variants
    "update_task",
    "claim_next_task",
    "complete_task",
    "complete_tasks",
}

# Safe temp directories - writes allowed without task binding
# These are framework-controlled, session-local, not user data
SAFE_TEMP_PREFIXES = [
    str(Path.home() / ".claude" / "tmp"),
    str(Path.home() / ".claude" / "projects"),
    str(Path.home() / ".gemini" / "tmp"),
    str(Path.home() / ".aops" / "tmp"),
]


# Template paths for task gate messages
# DEPRECATED: Use TemplateRegistry.instance().render("task.block", ...) instead
TASK_GATE_BLOCK_TEMPLATE = Path(__file__).parent / "templates" / "task-gate-block.md"
# DEPRECATED: Use TemplateRegistry.instance().render("task.warn", ...) instead
TASK_GATE_WARN_TEMPLATE = Path(__file__).parent / "templates" / "task-gate-warn.md"
DEFAULT_TASK_GATE_MODE = "block"
DEFAULT_CUSTODIET_GATE_MODE = "block"

# DEPRECATED: Use TemplateRegistry.instance().render("hydration.warn", ...) instead
HYDRATION_WARN_TEMPLATE = Path(__file__).parent / "templates" / "hydration-gate-warn.md"

# --- Stop Gate Constants ---

# DEPRECATED: Use TemplateRegistry.instance().render("stop.critic", ...) instead
STOP_GATE_CRITIC_TEMPLATE = Path(__file__).parent / "templates" / "stop-gate-critic.md"
# DEPRECATED: Use TemplateRegistry.instance().render("stop.handover_block", ...) instead
STOP_GATE_HANDOVER_BLOCK_TEMPLATE = (
    Path(__file__).parent / "templates" / "stop-gate-handover-block.md"
)


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
    """Check if a bash command is destructive (modifies state).

    Read-only commands (git status, ls, cat, etc.) return False.
    State-modifying commands (git commit, rm, etc.) return True.

    Args:
        command: The bash command string

    Returns:
        True if the command modifies state, False if read-only
    """
    # Normalize command for pattern matching
    cmd = command.strip().lower()

    # Read-only command patterns (safe, don't require task binding)
    readonly_patterns = [
        "git status",
        "git diff",
        "git log",
        "git show",
        "git branch",
        "git remote",
        "git fetch",
        "ls ",
        "ls\n",
        "ls$",
        "cat ",
        "head ",
        "tail ",
        "grep ",
        "rg ",
        "find ",
        "which ",
        "type ",
        "echo ",
        "pwd",
        "env",
        "printenv",
        "uname",
        "whoami",
        "date",
        "uptime",
    ]

    for pattern in readonly_patterns:
        if pattern.endswith("$"):
            if cmd == pattern[:-1]:
                return False
        elif cmd.startswith(pattern) or f" {pattern}" in cmd:
            return False

    # Destructive command patterns
    destructive_patterns = [
        "git commit",
        "git push",
        "git merge",
        "git rebase",
        "git reset",
        "git checkout",
        "git restore",
        "git clean",
        "git stash",
        "rm ",
        "rm\n",
        "rmdir",
        "mv ",
        "cp ",
        "mkdir",
        "touch ",
        "chmod ",
        "chown ",
        "> ",  # redirect (overwrites)
        ">>",  # append
        "tee ",
        "sed -i",
        "npm install",
        "npm run",
        "yarn ",
        "pip install",
        "uv pip",
        "uv sync",
        "uv run",
    ]

    for pattern in destructive_patterns:
        if cmd.startswith(pattern) or f" {pattern}" in cmd or f"&& {pattern}" in cmd:
            return True

    # Default: assume destructive (fail-closed)
    return True


def _is_actually_destructive(tool_name: str, tool_input: dict[str, Any]) -> bool:
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
        "write_file",
        "replace_file_content",
        "replace",
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


def _is_skill_invocation(
    tool_name: str, tool_input: dict[str, Any], skill_names: tuple[str, ...]
) -> bool:
    """Check if this is an invocation of a specific skill/agent.

    Handles all invocation patterns:
    - Direct MCP tool invocation (Gemini): tool_name matches skill name
    - Claude Skill tool: tool_input["skill"] matches
    - Gemini activate_skill: tool_input["name"] matches
    - Gemini delegate_to_agent: tool_input["agent_name"] matches
    - Claude Task tool: tool_input["subagent_type"] matches

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters
        skill_names: Tuple of valid skill names (e.g., ("custodiet", "aops-core:custodiet"))

    Returns:
        True if this is an invocation of one of the skill_names
    """
    # Direct MCP tool invocation (Gemini MCP pattern)
    if tool_name in skill_names:
        return True

    # Claude Skill tool
    if tool_name == "Skill":
        skill_name = tool_input.get("skill", "")
        if skill_name in skill_names:
            return True

    # Gemini activate_skill tool
    if tool_name == "activate_skill":
        name = tool_input.get("name", "")
        if name in skill_names:
            return True

    # Gemini delegate_to_agent
    if tool_name == "delegate_to_agent":
        agent_name = tool_input.get("agent_name", "")
        if agent_name in skill_names:
            return True

    # Claude Task tool with subagent_type
    if tool_name == "Task":
        subagent_type = tool_input.get("subagent_type", "")
        if subagent_type in skill_names:
            return True

    return False


def _is_handover_skill_invocation(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Check if this is a handover skill invocation."""
    return _is_skill_invocation(tool_name, tool_input, ("handover", "aops-core:handover"))


def _is_custodiet_invocation(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Check if this is a custodiet skill invocation."""
    return _is_skill_invocation(tool_name, tool_input, ("custodiet", "aops-core:custodiet"))


def _check_git_dirty() -> bool:
    """Check if git working directory has uncommitted changes.

    Returns True if there are staged or unstaged changes that would be lost
    if the session ends without commit.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Any output means there are changes
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        # If git fails, assume no changes (fail-open for this check)
        return False


# --- Hydration Logic ---

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
    # NOTE: "pull" removed - it DOES provide task context and satisfies planning intent
    # by binding a task with full context to the session
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


def _hydration_is_hydrator_task(tool_input: dict[str, Any]) -> bool:
    """Check if Task/delegate_to_agent/activate_skill invocation is spawning prompt-hydrator.

    Note: tool_input is pre-normalized by router.py (JSON strings parsed to dicts).
    """
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
    tool_name: str, tool_input: dict[str, Any], input_data: dict[str, Any]
) -> bool:
    """Check if Gemini is attempting to read hydration context.

    Note: tool_input is pre-normalized by router.py (JSON strings parsed to dicts).
    """
    if not isinstance(tool_input, dict):
        return False

    try:
        temp_dir = str(hook_utils.get_hook_temp_dir(HYDRATION_TEMP_CATEGORY, input_data))
    except RuntimeError:
        return False

    if tool_name == "read_file":
        file_path = tool_input.get("file_path")
        if file_path:
            path = str(file_path)
            return path.startswith(temp_dir)

    if tool_name == "write_to_file":
        target_file = tool_input.get("TargetFile") or tool_input.get("file_path")
        if target_file:
            path = str(target_file)
            return path.startswith(temp_dir)

    if tool_name == "run_shell_command":
        command = tool_input.get("command")
        if command:
            cmd = str(command)
            return temp_dir in cmd

    return False


# --- Custodiet Logic ---

# <!-- NS: delete these helpers and ensure codebase only uses the correct functions -->
def _custodiet_load_framework_content() -> tuple[str, str, str]:
    """Load framework content."""
    return hook_utils.load_framework_content()


def _custodiet_build_session_context(transcript_path: str | None, session_id: str) -> str:
    """Build rich session context for custodiet compliance checks."""
    if not transcript_path:
        return "(No transcript path available)"
    return build_rich_session_context(transcript_path)


def _custodiet_build_audit_instruction(
    transcript_path: str | None, tool_name: str, session_id: str
) -> str:
    """Build instruction for compliance audit."""
    # Build minimal input_data for hook_utils resolution
    input_data = {"transcript_path": transcript_path} if transcript_path else None

    hook_utils.cleanup_old_temp_files(
        hook_utils.get_hook_temp_dir(CUSTODIET_TEMP_CATEGORY, input_data), "audit_"
    )

    session_context = _custodiet_build_session_context(transcript_path, session_id)
    axioms, heuristics, skills = _custodiet_load_framework_content()
    # <!-- NS: no magic literals. -->
    # <!-- @claude 2026-02-07: DEFAULT_CUSTODIET_GATE_MODE is defined at module level (line ~50). This usage is correct - it references the constant. The env var name "CUSTODIET_MODE" could be extracted to CUSTODIET_MODE_ENV_VAR constant for consistency. -->
    custodiet_mode = os.environ.get("CUSTODIET_MODE", DEFAULT_CUSTODIET_GATE_MODE).lower()

    from lib.template_registry import TemplateRegistry

    registry = TemplateRegistry.instance()
    full_context = registry.render(
        "custodiet.context",
        {
            "session_context": session_context,
            "tool_name": tool_name,
            "axioms_content": axioms,
            "heuristics_content": heuristics,
            "skills_content": skills,
            "custodiet_mode": custodiet_mode,
        },
    )

    temp_dir = hook_utils.get_hook_temp_dir(CUSTODIET_TEMP_CATEGORY, input_data)
    temp_path = hook_utils.write_temp_file(full_context, temp_dir, "audit_")

    return registry.render("custodiet.instruction", {"temp_path": str(temp_path)})


# --- Accountant Logic (Post-Tool State Updates) ---


def run_accountant(ctx: HookContext) -> GateResult | None:
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
    if ctx.hook_event != "PostToolUse":
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
    # Also include direct MCP agent calls (Gemini pattern: tool_name IS the agent).
    if (
        ctx.tool_name in ("Task", "delegate_to_agent", "activate_skill", "Skill")
        or "hydrator" in (ctx.tool_name or "").lower()
    ):
        if (
            _hydration_is_hydrator_task(ctx.tool_input)
            or "hydrator" in (ctx.tool_name or "").lower()
        ):
            session_state.clear_hydrator_active(ctx.session_id)

        # Track subagent invocations for stop gate (checks has_run_subagents)
        subagent_type = (
            ctx.tool_input.get("subagent_type")
            or ctx.tool_input.get("agent_name")
            or ctx.tool_input.get("skill")
            or ctx.tool_input.get("name")
        )
        # Gemini direct MCP: tool_name IS the agent
        if not subagent_type and ctx.tool_name not in (
            "Task",
            "Skill",
            "delegate_to_agent",
            "activate_skill",
        ):
            subagent_type = ctx.tool_name
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
    # Count ALL tool calls (not just mutating) for visibility into total session activity.
    # Blocking is still gated on MUTATING_TOOLS in check_custodiet_gate.
    sess = session_state.get_or_create_session_state(ctx.session_id)
    state = sess.setdefault("state", {})

    # Initialize fields
    state.setdefault("tool_calls_since_compliance", 0)
    state.setdefault("last_compliance_ts", 0.0)

    # Check for reset (custodiet invoked) or increment
    if _is_custodiet_invocation(ctx.tool_name or "", ctx.tool_input):
        state["tool_calls_since_compliance"] = 0
        state["last_compliance_ts"] = time.time()
        system_messages.append("🛡️ [Gate] Compliance verified. Custodiet gate reset.")

    else:
        state["tool_calls_since_compliance"] += 1
        system_messages.append(
            f"🛡️ [Gate] Tool calls since last Custodiet check: {state['tool_calls_since_compliance']}."
        )

    session_state.save_session_state(ctx.session_id, sess)

    # 3. Update Handover State
    # Handover gate starts OPEN (handover_skill_invoked=True).
    # Reset to False when DESTRUCTIVE tools are used (requiring handover again).
    # Read-only tools (including read-only Bash commands) do NOT reset the gate.
    if _is_handover_skill_invocation(ctx.tool_name or "", ctx.tool_input):
        try:
            session_state.set_handover_skill_invoked(ctx.session_id)
            system_messages.append(
                "🤝 [Gate] Handover tool recorded. Stop gate will open once repo is clean and reflection message printed."
            )
        except Exception as e:
            print(f"WARNING: Accountant failed to set handover flag: {e}", file=sys.stderr)
    elif _is_actually_destructive(ctx.tool_name or "", ctx.tool_input):
        # Destructive tool used - require handover before stop
        # Only show warning on status change (gate was open, now closing)
        try:
            was_open = session_state.is_handover_skill_invoked(ctx.session_id)
            session_state.clear_handover_skill_invoked(ctx.session_id)
            if was_open:
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


def check_stop_gate(ctx: HookContext) -> GateResult | None:
    """
    Check if the agent is allowed to stop (Stop / AfterAgent Enforcement).
    Returns None if allowed, or GateResult if blocked/warned.

    Rules:
    0. Bypass Check: If gates_bypassed flag is set in session state, skip all checks.
    1. Critic Check: If turns_since_hydration == 0, deny stop and demand Critic.
    2. Handover Check: If handover skill not invoked (with valid reflection format), deny stop.
    3. QA Check: If hydration occurred and not streamlined workflow, require QA verification.
    """
    _check_imports()

    # Only applies to Stop event
    if ctx.hook_event != "Stop":
        return None

    state = session_state.load_session_state(ctx.session_id)
    if not state:
        return None

    # Check if gates are bypassed (. prefix) - user is in interactive mode
    if state.get("state", {}).get("gates_bypassed"):
        return None

    # --- 1. Critic Check (turns_since_hydration == 0) ---
    # We estimate turns since hydration by checking if hydrated_intent is set
    # but no subagents have been recorded yet.
    hydration_data = state.get("hydration", {})
    subagents = state.get("subagents", {})
    state_data = state.get("state", {})
    current_workflow = state_data.get("current_workflow")

    # Only consider "hydrated" if the hydrator actually ran and produced intent.
    # original_prompt being set alone just means a prompt was submitted, not that
    # hydration was needed or performed.
    is_hydrated = hydration_data.get("hydrated_intent") is not None
    has_run_subagents = len(subagents) > 0
    is_streamlined = current_workflow in (
        "interactive-followup",
        "simple-question",
        "direct-skill",
    )
    # If hydration_pending is False but hydrated_intent is None, the session
    # was a trivial query that didn't require hydration (e.g., "what time is it?")
    hydration_pending = state_data.get("hydration_pending", False)
    is_trivial_session = not hydration_pending and not is_hydrated

    # Only require critic if hydration actually occurred and no work was done yet
    if is_hydrated and not has_run_subagents and not is_streamlined and not is_trivial_session:
        # User explicitly asked for turns_since_hydration == 0 logic
        # This implies the agent is trying to stop immediately after the hydrator finished.
        from lib.template_registry import TemplateRegistry

        msg = TemplateRegistry.instance().render("stop.critic", {})
        # <!-- NS: please add a brief system_message to ALL GateResult() calls to provide user feedback. -->
        return GateResult(verdict=GateVerdict.DENY, context_injection=msg)

    # --- 2. Handover Check ---
    # Only enforce handover if there's work at risk (uncommitted changes or active task)
    # Otherwise, allow stop - don't block normal conversation turns
    if not session_state.is_handover_skill_invoked(ctx.session_id):
        # Check if there's work at risk
        has_uncommitted = _check_git_dirty()
        current_task = session_state.get_current_task(ctx.session_id)

        if has_uncommitted or current_task:
            # Work at risk - block stop until handover
            from lib.template_registry import TemplateRegistry

            msg = TemplateRegistry.instance().render("stop.handover_block", {})
            return GateResult(verdict=GateVerdict.DENY, context_injection=msg)
        # No work at risk - allow stop without handover

    # --- 3. QA Verification Check ---
    # If hydration occurred (intent was set), require QA verification
    # Streamlined workflows are exempt (same pattern as critic check)
    if is_hydrated and not is_streamlined:
        if not session_state.is_qa_invoked(ctx.session_id):
            return GateResult(
                verdict=GateVerdict.DENY,
                context_injection=(
                    "⛔ **BLOCKED: QA Verification Required**\n"
                    "**Action Required**: Invoke QA agent to verify your work.\n"
                    "After QA passes, invoke `/handover` again to end the session."
                ),
                metadata={"source": "stop_gate_qa_check"},
            )

    return None


def check_agent_response_listener(ctx: HookContext) -> GateResult | None:
    """
    AfterAgent: Listen to agent response for state updates and optional enforcement.

    Checks:
    1. Hydration result in text -> clear pending flag
    2. Handover reflection in text -> set handover flag
    3. Task claimed in text -> set task_bound flag
    4. Task completion in text -> clear task_bound flag
    """
    _check_imports()

    if ctx.hook_event != "AfterAgent":
        return None

    response_text = ctx.raw_input.get("prompt_response", "")

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

        # Parse workflow ID (supports both **Workflow**: and **Workflows**: formats)
        workflow_match = re.search(
            r"\*\*Workflows?\*\*:\s*\[\[workflows/([^\]]+)\]\]", response_text
        )
        workflow_id = workflow_match.group(1) if workflow_match else None

        if workflow_id:
            state = session_state.get_or_create_session_state(ctx.session_id)
            state["state"]["current_workflow"] = workflow_id
            session_state.save_session_state(ctx.session_id, state)

        # Detect streamlined workflows that skip critic
        is_streamlined = workflow_id in (
            "interactive-followup",
            "simple-question",
            "direct-skill",
        )

        if is_streamlined:
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"[Gate] Hydration complete (workflow: {workflow_id}). Streamlined mode enabled.",
                metadata={
                    "source": "agent_response_hydration",
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
            metadata={"source": "agent_response_hydration"},
        )

    # 2. Update Handover State - validate Framework Reflection format
    if "## Framework Reflection" in response_text:
        # Required fields for a valid Framework Reflection (per P#65, session completion rules)
        required_fields = [
            r"\*\*Prompts\*\*:",
            r"\*\*Guidance received\*\*:",
            r"\*\*Followed\*\*:",
            r"\*\*Outcome\*\*:",
            r"\*\*Accomplishments\*\*:",
            r"\*\*Friction points\*\*:",
            r"\*\*Proposed changes\*\*:",
            r"\*\*Next step\*\*:",
        ]

        missing_fields = []
        for field_pattern in required_fields:
            if not re.search(field_pattern, response_text, re.IGNORECASE):
                # Extract field name for error message
                field_name = field_pattern.replace(r"\*\*", "").replace(":", "")
                missing_fields.append(field_name)

        if missing_fields:
            # Reflection present but malformed - issue warning, don't set flag
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"⚠️ [Gate] Framework Reflection found but missing required fields: {', '.join(missing_fields)}. Handover gate remains closed.",
                context_injection=(
                    "<system-reminder>\n"
                    "Your Framework Reflection is missing required fields. The correct format is:\n\n"
                    "## Framework Reflection\n\n"
                    "**Prompts**: [Original request in brief]\n"
                    '**Guidance received**: [Hydrator advice, or "N/A"]\n'
                    "**Followed**: [Yes/No/Partial - explain]\n"
                    "**Outcome**: success | partial | failure\n"
                    "**Accomplishments**: [What was completed]\n"
                    '**Friction points**: [Issues encountered, or "none"]\n'
                    '**Proposed changes**: [Framework improvements, or "none"]\n'
                    '**Next step**: [Follow-up needed, or "none"]\n\n'
                    f"Missing: {', '.join(missing_fields)}\n"
                    "</system-reminder>"
                ),
                metadata={
                    "source": "agent_response_listener",
                    "missing_fields": missing_fields,
                },
            )

        # All required fields present - set handover flag
        session_state.set_handover_skill_invoked(ctx.session_id)
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message="🧠 [Gate] Framework Reflection validated. Handover gate open.",
        )

    return None


def check_session_start_gate(ctx: HookContext) -> GateResult | None:
    """
    Handle SessionStart event.
    Creates the session state file and returns startup info to USER.

    FAIL-FAST (P#8): If state file cannot be created, session is DENIED.
    """
    _check_imports()

    if ctx.hook_event != "SessionStart":
        return None

    from hooks.unified_logger import get_hook_log_path

    short_hash = session_paths.get_session_short_hash(ctx.session_id)

    # Get hook log path for this session (full absolute path)
    hook_log_path = get_hook_log_path(ctx.session_id, ctx.raw_input)

    # Get actual state file path (not a glob pattern)
    state_file_path = session_paths.get_session_file_path(ctx.session_id, input_data=ctx.raw_input)

    # FAIL-FAST: Actually create the state file, don't just report the path
    # If this fails, the session should not proceed
    try:
        state = session_state.get_or_create_session_state(ctx.session_id)
        session_state.save_session_state(ctx.session_id, state)

        # Verify the file was actually written
        if not state_file_path.exists():
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"FAIL-FAST: State file not created at expected path.\n"
                    f"Expected: {state_file_path}\n"
                    f"Check AOPS_SESSION_STATE_DIR env var and directory permissions.\n\n"
                ),
                metadata={"source": "session_start", "error": "state_file_not_created"},
            )
    except OSError as e:
        return GateResult(
            verdict=GateVerdict.DENY,
            system_message=(
                f"FAIL-FAST: Cannot write session state file.\n"
                f"Path: {state_file_path}\n"
                f"Error: {e}\n"
                f"Fix: Check directory permissions and disk space."
            ),
            metadata={"source": "session_start", "error": str(e)},
        )

    # GEMINI-SPECIFIC: Validate hydration temp path infrastructure at session start
    # Per P#8 (Fail-Fast), catch temp directory problems early, not at PreToolUse
    transcript_path = ctx.raw_input.get("transcript_path", "") if ctx.raw_input else ""
    if transcript_path and ".gemini" in str(transcript_path):
        try:
            # Validate hydration temp directory can be created/accessed
            hydration_temp_dir = hook_utils.get_hook_temp_dir("hydrator", ctx.raw_input)
            if not hydration_temp_dir.exists():
                hydration_temp_dir.mkdir(parents=True, exist_ok=True)
        except RuntimeError as e:
            # Loud, clear error message for Gemini temp infrastructure failure
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"⛔ **STATE ERROR**: Hydration temp path missing from session state.\n\n"
                    f"This indicates framework state corruption. Cannot proceed safely.\n\n"
                    f"Details: {e}\n\n"
                    f"Fix: Ensure Gemini CLI has initialized the project directory.\n"
                    f"Try running a simple Gemini command first to create ~/.gemini/tmp/{{hash}}/"
                ),
                metadata={
                    "source": "session_start",
                    "error": "gemini_temp_dir_missing",
                },
            )
        except OSError as e:
            return GateResult(
                verdict=GateVerdict.DENY,
                system_message=(
                    f"⛔ **STATE ERROR**: Cannot create hydration temp directory.\n\n"
                    f"Error: {e}\n\n"
                    f"Fix: Check directory permissions for ~/.gemini/tmp/"
                ),
                metadata={
                    "source": "session_start",
                    "error": "gemini_temp_dir_permission",
                },
            )

    # Build startup message for USER display (system_message, not context_injection)
    msg_lines = [
        f"🚀 Session Started: {ctx.session_id} ({short_hash})",
        f"State File: {state_file_path}",
        f"Hooks log: {hook_log_path}",
        f"Transcript: {transcript_path}",
    ]

    return GateResult(
        verdict=GateVerdict.ALLOW,
        system_message="\n".join(msg_lines),
        metadata={"source": "session_start"},
    )


# --- Unified Logger Gate (formerly unified_logger.py) ---


def run_unified_logger(ctx: HookContext) -> GateResult | None:
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
        return log_event_to_session(ctx.session_id, ctx.hook_event, ctx.raw_input)
    except Exception as e:
        print(f"WARNING: unified_logger error: {e}", file=sys.stderr)

    return None


# --- User Prompt Submit Gate (formerly user_prompt_submit.py) ---


def run_user_prompt_submit(ctx: HookContext) -> GateResult | None:
    """
    UserPromptSubmit: Build hydration context and return instruction.
    """
    _check_imports()

    if ctx.hook_event != "UserPromptSubmit":
        return None

    try:
        from lib.session_state import (
            clear_reflection_output,
            set_gates_bypassed,
        )

        from hooks.user_prompt_submit import (
            build_hydration_instruction,
            should_skip_hydration,
            write_initial_hydrator_state,
        )
    except ImportError as e:
        print(f"WARNING: user_prompt_submit import failed: {e}", file=sys.stderr)
        return None

    prompt = ctx.raw_input.get("prompt", "")
    transcript_path = ctx.raw_input.get("transcript_path")
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
            hydration_instruction = build_hydration_instruction(session_id, prompt, transcript_path)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                context_injection=hydration_instruction,
                metadata={"source": "user_prompt_submit"},
            )
    except Exception as e:
        import traceback

        error_msg = f"user_prompt_submit error: {type(e).__name__}: {e}"
        print(f"WARNING: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # FAIL-FAST: Return error in metadata so it's visible in hook logs
        return GateResult(
            verdict=GateVerdict.ALLOW,
            context_injection=f"⛔ **HYDRATION ERROR**: {error_msg}\n\nCannot proceed with hydration.",
            metadata={"source": "user_prompt_submit", "error": error_msg},
        )

    return None


# --- Task Binding Gate (formerly task_binding.py) ---


def run_task_binding(ctx: HookContext) -> GateResult | None:
    """
    PostToolUse: Bind/unbind task to session when task MCP operations occur.
    """
    _check_imports()

    if ctx.hook_event != "PostToolUse":
        return None

    from lib.event_detector import StateChange, detect_tool_state_changes
    from lib.hook_utils import get_task_id_from_result

    # Support both Claude (snake_case) and Gemini (camelCase) field names
    tool_name = ctx.tool_name or ctx.raw_input.get("tool_name") or ctx.raw_input.get("toolName", "")
    tool_input = (
        ctx.tool_input or ctx.raw_input.get("tool_input") or ctx.raw_input.get("toolInput", {})
    )
    tool_result = ctx.tool_output

    changes = detect_tool_state_changes(tool_name, tool_input, tool_result)

    if StateChange.PLAN_MODE in changes:
        from lib.session_state import is_plan_mode_invoked, set_plan_mode_invoked

        if not is_plan_mode_invoked(ctx.session_id):
            set_plan_mode_invoked(ctx.session_id)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message="Plan mode gate passed ✓",
            )
        return None

    if StateChange.UNBIND_TASK in changes:
        from lib.session_state import clear_current_task, get_current_task

        current = get_current_task(ctx.session_id)
        if current:
            clear_current_task(ctx.session_id)
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"Task completed and unbound from session: {current}",
            )
        return None

    if StateChange.BIND_TASK in changes:
        task_id = get_task_id_from_result(tool_result)
        if not task_id:
            return None

        source = "claim"
        from lib.session_state import get_current_task, set_current_task

        current = get_current_task(ctx.session_id)
        if current and current != task_id:
            return GateResult(
                verdict=GateVerdict.ALLOW,
                system_message=f"Note: Session already bound to task {current}, ignoring {task_id}",
            )

        set_current_task(ctx.session_id, task_id, source=source)
        return GateResult(
            verdict=GateVerdict.ALLOW,
            system_message=f"Task bound to session: {task_id}",
        )

    return None


# --- Session End Commit Check Gate (formerly session_end_commit_check.py) ---


def run_session_end_commit_check(ctx: HookContext) -> GateResult | None:
    """
    Stop: Check for uncommitted work and perform session cleanup.
    """
    _check_imports()

    if ctx.hook_event != "Stop":
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
    transcript_path = ctx.raw_input.get("transcript_path")

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


def run_generate_transcript(ctx: HookContext) -> GateResult | None:
    """
    Stop: Run transcript.py on session end.
    """
    if ctx.hook_event != "Stop":
        return None

    transcript_path = ctx.raw_input.get("transcript_path")
    if not transcript_path:
        return None

    try:
        import subprocess
        from pathlib import Path

        root_dir = Path(__file__).parent.parent
        script_path = root_dir / "scripts" / "transcript_push.py"

        if not script_path.exists():
            # Fallback to original transcript.py
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


def run_ntfy_notifier(ctx: HookContext) -> GateResult | None:
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
    if ctx.hook_event == "SessionStart":
        notify_session_start(config, ctx.session_id)
        return None

    # Stop notification
    if ctx.hook_event == "Stop":
        # Get current task if any
        try:
            current_task = session_state.get_current_task(ctx.session_id)
        except Exception:
            current_task = None
        notify_session_stop(config, ctx.session_id, current_task)
        return None

    # PostToolUse: task binding and subagent completion
    if ctx.hook_event == "PostToolUse":
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
            # Note: tool_result/toolResult are pre-normalized by router.py
            verdict = None
            if tool_result := ctx.tool_output:
                if isinstance(tool_result, dict) and "verdict" in tool_result:
                    verdict = tool_result["verdict"]

            notify_subagent_stop(config, ctx.session_id, agent_type, verdict)

    return None


def run_session_env_setup(ctx: HookContext) -> GateResult | None:
    """
    Persist environment variables for Claude Code sessions.
    """
    _check_imports()

    try:
        from hooks.session_env_setup import run_session_env_setup as setup_func
    except ImportError as e:
        print(f"WARNING: session_env_setup import failed: {e}", file=sys.stderr)
        return None

    return setup_func(ctx)


# Import unified gate functions from gates.py
from hooks.gates import (
    check_tool_gate as _check_tool_gate,
)
from hooks.gates import (
    on_session_start as _on_session_start,
)
from hooks.gates import (
    on_user_prompt as _on_user_prompt,
)
from hooks.gates import (
    update_gate_state as _update_gate_state,
)

# Registry of available gate checks
GATE_CHECKS = {
    # Universal gates
    "unified_logger": run_unified_logger,
    "ntfy_notifier": run_ntfy_notifier,
    "session_env_setup": run_session_env_setup,
    # SessionStart gates
    "session_start": check_session_start_gate,
    "gate_init": _on_session_start,  # Initialize gate states
    # UserPromptSubmit gates
    "user_prompt_submit": run_user_prompt_submit,
    "gate_reset": _on_user_prompt,  # Close gates that reset on new prompt
    # PreToolUse gates
    "tool_gate": _check_tool_gate,  # Unified tool gating from gates.py
    # PostToolUse gates
    "task_binding": run_task_binding,
    "accountant": run_accountant,
    "gate_update": _update_gate_state,  # Open/close gates based on conditions
    # AfterAgent gates
    "agent_response": check_agent_response_listener,
    # Stop gates
    "stop_gate": check_stop_gate,
    # "session_end_commit": run_session_end_commit_check,
    "generate_transcript": run_generate_transcript,
}
