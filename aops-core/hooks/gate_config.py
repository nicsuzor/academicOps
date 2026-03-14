"""
Gate Configuration: Single source of truth for gate behavior.

This module defines:
1. Tool categories (always_available, read_only, write, meta)
2. Compliance subagent types (bypass gate policies)
3. Spawn tool detection (cross-platform agent/skill invocation)
4. Gate modes (block/warn)
5. PKB prefix normalization (handles MCP tool name variants)

"""

import os
import re
import sys
from typing import Any

# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize TOOL NAMES by their side effects. This determines which gates
# must pass before the tool can be used.
#
# IMPORTANT: Only TOOL NAMES go here. Agent/skill names (hydrator,
# custodiet, etc.) are subagent_type values, not tool names. They belong in
# COMPLIANCE_SUBAGENT_TYPES below.
#
# MCP tool names vary by platform and plugin registration method:
#   - mcp__pkb__<op>                         (Claude Code short form)
#   - mcp__plugin_aops-core_pkb__<op>        (Claude Code full plugin prefix)
#   - mcp__pbk__<op>                         (Gemini typo variant)
#   - mcp__plugin_<version>_pkb__<op>        (versioned plugin prefix)
#   - pkb__<op>                              (bare prefix)
#   - <op>                                   (Gemini bare tool name)
#
# All known variants should be listed here. Unknown PKB variants are handled
# by the _PKB_PREFIX_RE fallback in get_tool_category().

TOOL_CATEGORIES: dict[str, set[str]] = {
    # Always available: bypass ALL gates, including hydration.
    # These are Claude Code built-in meta/control tools that have no substantive
    # side effects on user data. They must never be blocked — e.g. AskUserQuestion
    # is needed to communicate with the user during any gate state.
    # Distinct from infrastructure (PKB ops) and spawn (subagent dispatch).
    "always_available": {
        "AskUserQuestion",
        "ask_user",
        "TodoWrite",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
    },
    # Infrastructure: bypass ALL gates, including hydration.
    # These are tools required for the framework itself to function (PKB ops).
    "infrastructure": {
        # --- PKB task management: mcp__pkb__* (Claude Code short form) ---
        "mcp__pkb__get_task",
        "mcp__pkb__create_task",
        "mcp__pkb__update_task",
        "mcp__pkb__complete_task",
        "mcp__pkb__reindex",
        "mcp__pkb__delete_document",
        # --- PKB task management: mcp__plugin_aops-core_pkb__* (Claude Code full plugin) ---
        "mcp__plugin_aops-core_pkb__get_task",
        "mcp__plugin_aops-core_pkb__create_task",
        "mcp__plugin_aops-core_pkb__update_task",
        "mcp__plugin_aops-core_pkb__complete_task",
        "mcp__plugin_aops-core_pkb__reindex",
        # --- PKB task management: mcp__pbk__* (Gemini typo variant) ---
        "mcp__pbk__get_task",
        "mcp__pbk__create_task",
        "mcp__pbk__update_task",
        "mcp__pbk__complete_task",
        "mcp__pbk__reindex",
        # --- PKB all ops: mcp__pkb__* (Claude Code short form) ---
        "mcp__pkb__task_search",
        "mcp__pkb__get_task_network",
        "mcp__pkb__list_tasks",
        "mcp__pkb__get_blocked_tasks",
        "mcp__pkb__get_network_metrics",
        "mcp__pkb__semantic_search",
        "mcp__pkb__pkb_search",
        "mcp__pkb__pkb_context",
        "mcp__pkb__get_document",
        "mcp__pkb__list_documents",
        "mcp__pkb__search",
        "mcp__pkb__create",
        "mcp__pkb__append",
        "mcp__pkb__create_memory",
        "mcp__pkb__retrieve_memory",
        "mcp__pkb__list_memories",
        "mcp__pkb__search_by_tag",
        "mcp__pkb__delete_memory",
        "mcp__pkb__decompose_task",
        "mcp__pkb__delete",
        # --- PKB all ops: mcp__plugin_aops-core_pkb__* (Claude Code full plugin) ---
        "mcp__plugin_aops-core_pkb__list_tasks",
        "mcp__plugin_aops-core_pkb__search",
        "mcp__plugin_aops-core_pkb__task_search",
        "mcp__plugin_aops-core_pkb__pkb_orphans",
        "mcp__plugin_aops-core_pkb__get_task_children",
        "mcp__plugin_aops-core_pkb__retrieve_memory",
        "mcp__plugin_aops-core_pkb__search_by_tag",
        "mcp__plugin_aops-core_pkb__decompose_task",
        "mcp__plugin_aops-core_pkb__append",
        "mcp__plugin_aops-core_pkb__create_memory",
        "mcp__plugin_aops-core_pkb__create",
        "mcp__plugin_aops-core_pkb__delete",
        "mcp__plugin_aops-core_pkb__delete_memory",
        # --- PKB all ops: mcp__pbk__* (Gemini typo variant) ---
        "mcp__pbk__list_tasks",
        "mcp__pbk__pkb_context",
        "mcp__pbk__search",
        "mcp__pbk__get_document",
        "mcp__pbk__list_documents",
        "mcp__pbk__pkb_orphans",
        "mcp__pbk__get_network_metrics",
        "mcp__pbk__create",
        "mcp__pbk__append",
        "mcp__pbk__create_memory",
        # --- PKB: bare/versioned variants ---
        "pkb__search",
        "mcp__plugin_0_2_25_pkb__list_tasks",
        # --- Memory MCP ---
        "mcp__plugin_aops-core_memory__retrieve_memory",
        "mcp__plugin_aops-core_memory__store_memory",
        # --- Gemini equivalents (bare tool names, PKB ops) ---
        "create_task",
        "update_task",
        "complete_task",
        "get_task",
        "list_tasks",
        "task_search",
        "search",
        "get_task_children",
        "pkb_orphans",
        "create_memory",
        "decompose_task",
        "append",
        "save_memory",
    },
    # Spawn: tools that invoke subagents or skills.
    # Subject to hydration gate (must hydrate before doing substantive work).
    # Always allowed if the target subagent is a compliance agent (hydrator, custodiet, etc).
    "spawn": {
        "Agent",  # Claude Code: spawn subagent (current tool name)
        "Task",  # Claude Code: spawn subagent (legacy/alias)
        "Skill",  # Claude Code: invoke skill in-session
        "delegate_to_agent",  # Gemini CLI: spawn subagent
        "activate_skill",  # Gemini CLI: invoke skill in-session
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
        "aops_core_custodiet",
        "aops_core_qa",
        "aops_core_audit",
        "aops_core_butler",
    },
    # Read-only tools: no side effects. Exempt from custodiet gate (not hydration).
    # Hydration gate blocks these until hydrator is dispatched (JIT gate open).
    # Custodiet gate exempts them because compliance only tracks write operations.
    "read_only": {
        # --- Claude Code built-in ---
        "Read",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "ListMcpResourcesTool",
        "ReadMcpResourceTool",
        "TaskOutput",
        "TaskStop",
        "ToolSearch",
        # --- Gemini CLI ---
        "read_file",
        "view_file",
        "list_dir",
        "list_directory",
        "find_by_name",
        "grep_search",
        "search_file_content",
        "glob",
        "search_web",
        "google_web_search",
        "web_fetch",
        "read_url_content",
        # --- Gemini bare tool names (non-PKB) ---
        "get_internal_docs",
        "cli_help",
        # --- Context7 MCP (both prefix variants) ---
        "mcp__plugin_context7-plugin_context7__resolve-library-id",
        "mcp__plugin_context7-plugin_context7__query-docs",
        "mcp__context7__resolve-library-id",
        "mcp__context7__query-docs",
        # --- Zotero MCP ---
        "mcp__zot__search",
        "mcp__zot__search_library_by_author",
        "mcp__zot__search_openalex_author",
        # --- Oversight Board MCP ---
        "mcp__osb__search",
        "mcp__osb__get_case_summary",
        "mcp__osb__get_document",
        "mcp__osb__get_collection_info",
        "mcp__osb__get_similar_documents",
        "mcp__osb__ping",
        # --- Outlook MCP: mcp__omcp__* (read) ---
        "mcp__omcp__messages_get",
        "mcp__omcp__messages_list_recent",
        "mcp__omcp__messages_search",
        "mcp__omcp__messages_index",
        "mcp__omcp__messages_list_accounts",
        "mcp__omcp__messages_list_folders",
        "mcp__omcp__calendar_list_today",
        "mcp__omcp__calendar_list_events",
        "mcp__omcp__calendar_get_event",
        "mcp__omcp__calendar_list_upcoming",
        "mcp__omcp__calendar_list_calendars",
        "mcp__omcp__help",
        "mcp__omcp__ping",
        # --- Outlook MCP: mcp__outlook__* (alternate prefix, read) ---
        "mcp__outlook__messages_get",
        "mcp__outlook__messages_list_recent",
        "mcp__outlook__calendar_list_today",
        "mcp__outlook__calendar_list_upcoming",
        # --- Playwright MCP (read) ---
        "mcp__playwright__browser_wait_for",
        "mcp__playwright__browser_take_screenshot",
        "mcp__playwright__browser_snapshot",
        "mcp__playwright__browser_console_messages",
        "mcp__playwright__browser_network_requests",
        "mcp__playwright__browser_tabs",
        # --- Playwright bare names (Gemini, read) ---
        "browser_wait_for",
        "browser_take_screenshot",
        "browser_console_messages",
        "browser_network_requests",
    },
    # Write tools: modify USER files/state. Subject to all gates.
    "write": {
        # --- Claude Code built-in ---
        "Edit",
        "Write",
        "Bash",
        "NotebookEdit",
        "MultiEdit",
        # --- Gemini CLI ---
        "write_file",
        "replace",
        "run_shell_command",
        "execute_code",
        "shell",
        # --- Outlook MCP (write) ---
        "mcp__omcp__messages_reply",
        "mcp__omcp__messages_forward",
        "mcp__omcp__messages_create_draft",
        "mcp__omcp__messages_move",
        "mcp__omcp__messages_archive",
        "mcp__omcp__messages_set_category",
        "mcp__omcp__messages_add_flag",
        "mcp__omcp__messages_download_attachments",
        "mcp__omcp__calendar_create_event",
        "mcp__omcp__calendar_update_event",
        "mcp__omcp__calendar_delete_event",
        "mcp__omcp__calendar_respond_to_meeting",
        "mcp__omcp__calendar_accept_invitation",
        "mcp__omcp__archive_messages_monthly",
        "mcp__omcp__archive_messages_batch",
        # --- Playwright MCP (write) ---
        "mcp__playwright__browser_navigate",
        "mcp__playwright__browser_click",
        "mcp__playwright__browser_install",
        "mcp__playwright__browser_type",
        "mcp__playwright__browser_fill_form",
        "mcp__playwright__browser_press_key",
        "mcp__playwright__browser_evaluate",
        "mcp__playwright__browser_run_code",
        "mcp__playwright__browser_handle_dialog",
        "mcp__playwright__browser_file_upload",
        "mcp__playwright__browser_close",
        "mcp__playwright__browser_resize",
        "mcp__playwright__browser_drag",
        "mcp__playwright__browser_hover",
        "mcp__playwright__browser_select_option",
        # --- Playwright bare names (Gemini, write) ---
        "browser_navigate",
        "browser_click",
        "browser_evaluate",
        "browser_run_code",
    },
    "meta": set(),
}

# =============================================================================
# COMPLIANCE SUBAGENT TYPES
# =============================================================================
# Subagent types that are part of the compliance framework itself.
# When detected as the active subagent, their tool calls bypass gate
# POLICIES (but triggers still run to update gate state correctly).
#
# This is conceptually different from tool categories: these are
# subagent_type values (passed via Task/delegate_to_agent params),
# not tool names.

COMPLIANCE_SUBAGENT_TYPES: frozenset[str] = frozenset(
    {
        "hydrator",
        "aops-core:hydrator",
        "aops_core_hydrator",
        "custodiet",
        "aops-core:custodiet",
        "aops_core_custodiet",
        "audit",
        "aops-core:audit",
        "aops_core_audit",
        "qa",
        "aops-core:qa",
        "aops_core_qa",
        # Curia alias: "auditor" is the Curia name for the custodiet/audit role.
        # Other Curia roles (Assessor/Critic, Advocate) are not compliance agents
        # and must not bypass gate enforcement.
        "auditor",
    }
)

# =============================================================================
# SPAWN TOOLS — Cross-platform agent/skill detection
# =============================================================================
# Maps tool_name -> (parameter_names_to_check, is_skill)
#
# When a hook event carries one of these tool names, the router extracts
# the subagent_type from the first matching parameter in tool_input.
#
# is_skill=True means the tool runs in the MAIN agent's session (like
# Skill/activate_skill), not as a separate subagent. This prevents
# misclassifying skill invocations as subagent sessions.
#
# To add a new platform: add its agent-spawning and skill-invoking tools
# here with the parameter names they use for the agent/skill identifier.

SPAWN_TOOLS: dict[str, tuple[tuple[str, ...], bool]] = {
    # Claude Code
    "Agent": (("subagent_type",), False),  # Current tool name
    "Task": (("subagent_type",), False),  # Legacy/alias
    "Skill": (("skill",), True),
    # Gemini CLI
    "delegate_to_agent": (("name", "agent_name"), False),
    "activate_skill": (("skill", "name"), True),
    # Gemini: bare agent tools (Strategy 2)
    # Note: hydrator is a skill — invoked via activate_skill(name='aops-core:hydrator')
    "aops_core_custodiet": ((), False),
    "aops_core_qa": ((), False),
    "aops_core_audit": ((), False),
    "aops_core_butler": ((), False),
    # Codex: add entries when tool names are known
    # GitHub Copilot: add entries when tool names are known
}

# =============================================================================
# GATE MODES
# =============================================================================
# Gate enforcement modes from environment variables. Defaults to "warn" when
# not set (e.g. Claude macOS app, Cowork) so the router can boot and
# session_env_setup can persist values via CLAUDE_ENV_FILE.
#
# NOTE: Missing vars emit a stderr warning so misconfigured deployments remain
# visible even though the router does not crash. Set vars in ~/.env.local for
# production to suppress these warnings.


def _gate_mode(var: str, default: str = "warn") -> str:
    """Return env var value, warning on stderr when falling back to default."""
    value = os.environ.get(var)
    if value is None:
        print(
            f"WARNING: {var} not set; defaulting to '{default}'. "
            "Set in ~/.env.local for production.",
            file=sys.stderr,
        )
        return default
    return value


HANDOVER_GATE_MODE = _gate_mode("HANDOVER_GATE_MODE")
QA_GATE_MODE = _gate_mode("QA_GATE_MODE")
CUSTODIET_GATE_MODE = _gate_mode("CUSTODIET_GATE_MODE")
CUSTODIET_TOOL_CALL_THRESHOLD = int(os.environ.get("CUSTODIET_TOOL_CALL_THRESHOLD", "50"))
HYDRATION_GATE_MODE = _gate_mode("HYDRATION_GATE_MODE")
COMMIT_GATE_MODE = _gate_mode("COMMIT_GATE_MODE")

# =============================================================================
# PKB PREFIX NORMALIZATION
# =============================================================================
# MCP tool names for PKB come in many prefix variants depending on how the
# server is registered. This normalization handles unknown prefix variants
# as a fallback when the tool name isn't found in the static TOOL_CATEGORIES.
#
# Known prefix patterns:
#   mcp__plugin_aops-core_pkb__<op>    (Claude Code full plugin prefix)
#   mcp__pkb__<op>                     (Claude Code short form)
#   mcp__pbk__<op>                     (Gemini typo variant)
#   mcp__plugin_<version>_pkb__<op>    (versioned plugin prefix)
#   pkb__<op>                          (bare prefix)

_PKB_OPERATIONS: dict[str, str] = {
    # All PKB operations are infrastructure — the PKB is framework
    # infrastructure, not user files. Gates should never block PKB access.
    "get_task": "infrastructure",
    "create_task": "infrastructure",
    "update_task": "infrastructure",
    "complete_task": "infrastructure",
    "reindex": "infrastructure",
    "delete_document": "infrastructure",
    "list_tasks": "infrastructure",
    "task_search": "infrastructure",
    "search": "infrastructure",
    "pkb_context": "infrastructure",
    "pkb_orphans": "infrastructure",
    "get_document": "infrastructure",
    "list_documents": "infrastructure",
    "get_network_metrics": "infrastructure",
    "get_task_children": "infrastructure",
    "retrieve_memory": "infrastructure",
    "search_by_tag": "infrastructure",
    "list_memories": "infrastructure",
    "pkb_trace": "infrastructure",
    "get_task_network": "infrastructure",
    "get_blocked_tasks": "infrastructure",
    "semantic_search": "infrastructure",
    "pkb_search": "infrastructure",
    "get_dependency_tree": "infrastructure",
    "create": "infrastructure",
    "append": "infrastructure",
    "create_memory": "infrastructure",
    "decompose_task": "infrastructure",
    "delete": "infrastructure",
    "delete_memory": "infrastructure",
}

# Regex to match any PKB MCP prefix variant and extract the operation name.
_PKB_PREFIX_RE = re.compile(r"^(?:mcp__(?:plugin_(?:aops-core_|[\w.]+_))?(?:pkb|pbk)__|pkb__)(.+)$")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_tool_category(tool_name: str, tool_input: dict[str, Any] | None = None) -> str:
    """Get the category for a tool.

    Lookup order:
    1. ToolSearch with select: prefix -> infrastructure (tool-loading, not new work)
    2. Compliance agent spawn: spawn tool + compliance subagent_type -> infrastructure
    3. Static TOOL_CATEGORIES sets (O(1) for known tool names)
    4. PKB prefix normalization (handles unknown MCP prefix variants)
    5. Default: 'write' (conservative fallback for truly unknown tools)

    Args:
        tool_name: The tool being called.
        tool_input: Optional tool input dict. Used to:
            - Detect ToolSearch select: queries (infrastructure bypass)
            - Extract subagent_type for compliance-spawn bypass
    """
    # 1. ToolSearch with select: prefix is a pure tool-loading operation (infrastructure).
    # Blocking it creates an unresolvable loop: the agent needs ToolSearch to load
    # tools, but ToolSearch is blocked until hydration, which also requires tools.
    if tool_name == "ToolSearch" and tool_input:
        query = tool_input.get("query", "")
        if isinstance(query, str) and query.startswith("select:"):
            return "infrastructure"

    # 2. Compliance agent spawns (Agent/Task + compliance subagent_type, or tool_name
    # is the compliance agent name directly) are infrastructure.
    # This ensures dispatching the hydrator or custodiet is never blocked by any gate,
    # including custodiet's own ops-threshold policy.
    extracted_st, _ = extract_subagent_type(tool_name, tool_input or {})
    if extracted_st and extracted_st in COMPLIANCE_SUBAGENT_TYPES:
        return "infrastructure"

    # 3. Static categories
    for category, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            return category

    # Fallback: normalize PKB MCP prefix variants
    m = _PKB_PREFIX_RE.match(tool_name)
    if m:
        cat = _PKB_OPERATIONS.get(m.group(1))
        if cat:
            return cat

    # Edge case: compliance subagent names sometimes appear as tool_name
    # (router logs subagent_type as tool_name in some code paths).
    # Treat them as infrastructure so they bypass gates.
    if tool_name in COMPLIANCE_SUBAGENT_TYPES:
        return "infrastructure"

    # Default: treat unknown tools as write (conservative)
    return "write"


def extract_subagent_type(
    tool_name: str | None, tool_input: dict[str, Any]
) -> tuple[str | None, bool]:
    """Extract subagent_type from a tool invocation.

    Two extraction strategies:
    1. Direct match: tool_name IS the agent name (e.g. Gemini reports
       tool_name="hydrator" rather than "delegate_to_agent").
       Matched against COMPLIANCE_SUBAGENT_TYPES.
    2. SPAWN_TOOLS table: tool_name is a spawning tool (e.g. "Agent",
       "delegate_to_agent") and the agent name is in tool_input.

    Args:
        tool_name: The tool being called (e.g. "Task", "delegate_to_agent",
            or the agent name directly like "hydrator").
        tool_input: The tool's input parameters.

    Returns:
        (subagent_type, is_skill) tuple.
        subagent_type is None if this is not a spawn/agent tool.
        is_skill is True for skill-like tools that run in the main session.
    """
    if not tool_name:
        return None, False

    # Strategy 1: tool_name IS the agent name (Gemini bare agent pattern)
    # Checked first so compliance agent names as tool_name take precedence
    # even if they are also registered in SPAWN_TOOLS.
    if tool_name in COMPLIANCE_SUBAGENT_TYPES:
        return tool_name, False

    # Strategy 2: SPAWN_TOOLS lookup (Claude Agent/Task, Gemini delegate_to_agent)
    spec = SPAWN_TOOLS.get(tool_name)
    if spec:
        param_names, is_skill = spec
        for param in param_names:
            value = tool_input.get(param)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped, is_skill
        return None, is_skill

    return None, False
