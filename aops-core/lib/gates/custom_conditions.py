import os
import re

from hooks.schemas import HookContext

from lib.gate_types import GateState
from lib.session_state import SessionState

# =============================================================================
# SENTINEL GATE — destructive-env-op detection
# =============================================================================
# Protected user-environment paths. Matches both tilde-expanded (~) and
# absolute home-dir forms (/home/user or /Users/user on macOS). Case-
# insensitive so macOS case-folded paths and adversarial mixed-case commands
# are caught.
_PROTECTED_PATH_RE = re.compile(
    r"(?:~|(?:/home|/Users)/[^/\s]+)"
    r"/\."
    r"(?:"
    r"gemini/extensions"  # ~/.gemini/extensions/
    r"|gemini/settings\.json"  # ~/.gemini/settings.json
    r"|claude/plugins"  # ~/.claude/plugins/
    r"|claude/[^/\s]+\.json"  # ~/.claude/*.json (e.g. settings.json)
    r"|config/gemini"  # ~/.config/gemini/
    r")",
    re.IGNORECASE,
)

# Destructive shell commands. Word-bounded so rm doesn't match inside rmdir
# and vice versa; case-insensitive to block RM, Rm, TRUNCATE, etc.
_DESTRUCTIVE_CMD_RE = re.compile(
    r"\b(?:rm|mv|rmdir|unlink|truncate)\b",
    re.IGNORECASE,
)

# Tool name sets for sentinel gate dispatch.
_SENTINEL_SHELL_TOOLS: frozenset[str] = frozenset(
    {"Bash", "run_shell_command", "shell", "execute_code"}
)
_SENTINEL_WRITE_FILE_TOOLS: frozenset[str] = frozenset({"Edit", "Write", "write_file", "replace"})


def check_custom_condition(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "is_destructive_env_op":
        # Sentinel gate: block destructive ops on protected user-env paths.
        # Shell tools: command must contain BOTH a destructive verb AND a
        # protected path reference (and-logic to reduce false positives).
        # Write-file tools: ANY write to a protected path is blocked —
        # no destructive-verb check needed because the write itself is the
        # destructive op (Edit/Write will overwrite or truncate the file).
        tool_name = ctx.tool_name or ""
        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}

        if tool_name in _SENTINEL_SHELL_TOOLS:
            command = tool_input.get("command", "")
            if not isinstance(command, str):
                return False
            return bool(_DESTRUCTIVE_CMD_RE.search(command) and _PROTECTED_PATH_RE.search(command))

        if tool_name in _SENTINEL_WRITE_FILE_TOOLS:
            # file_path is Claude Code field; path is Gemini write_file field
            file_path = tool_input.get("file_path") or tool_input.get("path") or ""
            if not isinstance(file_path, str):
                return False
            return bool(_PROTECTED_PATH_RE.search(file_path))

        return False

    if name == "is_destructive_or_irreversible_op":
        from hooks.gate_config import is_destructive_or_irreversible_op

        tool_name = ctx.tool_name or ""  # allow-fallback: default empty tool name
        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}
        return is_destructive_or_irreversible_op(tool_name, tool_input)

    if name == "is_not_safe_toolsearch":
        # Returns False ONLY if ToolSearch is loading specific tools by name (select:*)
        # Returns True for everything else (including discovery ToolSearch)
        if ctx.tool_name == "ToolSearch":
            tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}
            query = tool_input.get("query", "")
            if isinstance(query, str) and "select:" in query:
                return False
        return True

    if name == "is_write_tool":
        from hooks.gate_config import get_tool_category

        # Treat shell tools as read-only when the handover gate is sticky
        # (post-skill) or no task is bound — prevents gates from re-closing
        # on discovery/status commands (e.g. git status after /end-session).
        handover_state = session_state.gates.get("handover")
        if (handover_state and handover_state.sticky) or not session_state.main_agent.current_task:
            if ctx.tool_name in ("Bash", "run_shell_command", "shell", "execute_code"):
                return False

        tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else None
        return ctx.tool_name is not None and get_tool_category(ctx.tool_name, tool_input) == "write"

    if name == "not_mid_edit":
        # Defer enforcer block while agent has an in-progress todo item.
        # The enforcer trigger on TodoWrite PostToolUse keeps this metric
        # up to date. False (condition not met) when mid-edit, deferring the
        # block until the agent has finished its current sub-task. (#319)
        return not state.metrics.get("has_in_progress_todo", False)

    if name == "is_ida_block_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        return os.environ.get("IDA_GATE_MODE", "warn") in ("block", "deny")

    if name == "is_ida_warn_mode":
        # IDA gate policy: active only when IDA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        return os.environ.get("IDA_GATE_MODE", "warn") == "warn"

    if name == "is_qa_block_mode":
        # QA gate policy: active only when QA_GATE_MODE is blocking.
        # Separating block vs warn into distinct policies lets each choose
        # appropriate message channels (context_key vs message_key) so
        # warn mode doesn't inadvertently upgrade Stop to decision=block.
        return os.environ.get("QA_GATE_MODE", "warn") in ("block", "deny")

    if name == "is_qa_warn_mode":
        # QA gate policy: active only when QA_GATE_MODE is warn.
        # Warn mode delivers the advisory via system_message only (user-visible)
        # rather than context_injection, so output_for_claude does not upgrade
        # the WARN verdict to decision=block for the Stop hook.
        return os.environ.get("QA_GATE_MODE", "warn") == "warn"

    if name == "is_handover_block_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is blocking
        # AND the session did real work (write tool or task claim).
        # Read-only sessions (session_did_work=False) are exempt — they need no
        # structured handover (aops-16a15a05).
        if not session_state.session_did_work:
            return False
        from hooks.gate_config import HANDOVER_GATE_MODE

        return HANDOVER_GATE_MODE in ("block", "deny")

    if name == "is_handover_warn_mode":
        # Handover gate policy: active only when HANDOVER_GATE_MODE is warn
        # AND the session did real work. Same read-only exemption as block mode.
        if not session_state.session_did_work:
            return False
        from hooks.gate_config import HANDOVER_GATE_MODE

        return HANDOVER_GATE_MODE == "warn"

    if name == "has_bound_task":
        return bool(session_state.main_agent.current_task)

    if name == "session_did_work":
        # True if the session has used a write tool or claimed a task.
        # Used directly in triggers/conditions that need this signal without
        # combining it with a gate-mode check (aops-16a15a05).
        return session_state.session_did_work

    return False
