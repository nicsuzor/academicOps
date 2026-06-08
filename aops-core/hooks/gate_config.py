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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Declared here so type checkers see precise types for PEP 562 lazy attrs.
    # At runtime these names come from __getattr__ below.
    ENFORCER_GATE_MODE: str
    HANDOVER_GATE_MODE: str
    QA_GATE_MODE: str
    IDA_GATE_MODE: str
    HYDRATION_GATE_MODE: str
    SENTINEL_GATE_MODE: str
    ENFORCER_TOOL_CALL_THRESHOLD: int

# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize TOOL NAMES by their side effects. This determines which gates
# must pass before the tool can be used.
#
# IMPORTANT: Only TOOL NAMES go here. Agent/skill names (enforcer, etc.)
# are subagent_type values, not tool names. They belong in
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
    # Always available: bypass ALL gates.
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
    # Infrastructure: bypass ALL gates.
    # These are tools required for the framework itself to function (PKB ops).
    "infrastructure": {
        # --- PKB task management: mcp__pkb__* (Claude Code short form) ---
        "mcp__pkb__get_task",
        "mcp__pkb__create_task",
        "mcp__pkb__update_task",
        "mcp__pkb__complete_task",
        "mcp__pkb__release_task",
        "mcp__pkb__manage_task",
        "mcp__pkb__reindex",
        "mcp__pkb__delete_document",
        # --- PKB task management: mcp__plugin_aops-core_pkb__* (Claude Code full plugin) ---
        "mcp__plugin_aops-core_pkb__get_task",
        "mcp__plugin_aops-core_pkb__create_task",
        "mcp__plugin_aops-core_pkb__update_task",
        "mcp__plugin_aops-core_pkb__complete_task",
        "mcp__plugin_aops-core_pkb__release_task",
        "mcp__plugin_aops-core_pkb__manage_task",
        "mcp__plugin_aops-core_pkb__reindex",
        # --- PKB task management: mcp__pbk__* (Gemini typo variant) ---
        "mcp__pbk__get_task",
        "mcp__pbk__create_task",
        "mcp__pbk__update_task",
        "mcp__pbk__complete_task",
        "mcp__pbk__release_task",
        "mcp__pbk__manage_task",
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
        "mcp__pkb__create_subtask",
        "mcp__pkb__merge_node",
        "mcp__pkb__bulk_reparent",
        "mcp__pkb__batch_update",
        "mcp__pkb__batch_reparent",
        "mcp__pkb__batch_archive",
        "mcp__pkb__batch_merge",
        "mcp__pkb__batch_create_epics",
        "mcp__pkb__batch_reclassify",
        "mcp__pkb__graph_stats",
        "mcp__pkb__get_stats",
        "mcp__pkb__create_document",
        "mcp__pkb__find_duplicates",
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
        "mcp__plugin_aops-core_pkb__create_subtask",
        "mcp__plugin_aops-core_pkb__append",
        "mcp__plugin_aops-core_pkb__create_memory",
        "mcp__plugin_aops-core_pkb__create",
        "mcp__plugin_aops-core_pkb__delete",
        "mcp__plugin_aops-core_pkb__delete_memory",
        "mcp__plugin_aops-core_pkb__create_document",
        "mcp__plugin_aops-core_pkb__batch_update",
        "mcp__plugin_aops-core_pkb__batch_reparent",
        "mcp__plugin_aops-core_pkb__batch_merge",
        "mcp__plugin_aops-core_pkb__merge_node",
        "mcp__plugin_aops-core_pkb__graph_stats",
        "mcp__plugin_aops-core_pkb__get_stats",
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
        "release_task",
        "manage_task",
        "get_task",
        "list_tasks",
        "task_search",
        "search",
        "get_task_children",
        "pkb_orphans",
        "create_memory",
        "decompose_task",
        "create_subtask",
        "merge_node",
        "bulk_reparent",
        "batch_update",
        "batch_reparent",
        "batch_archive",
        "batch_merge",
        "batch_create_epics",
        "batch_reclassify",
        "create_document",
        "find_duplicates",
        "delete",
        "delete_memory",
        "pkb_stats",
        "pkb_explore",
        "pkb_batch",
        "pkb_tool_help",
        "pkb_task_summary",
        "pkb_graph_stats",
        "graph_stats",
        "get_stats",
        "pkb_graph_json",
        "tool_stats",
        "append",
        "save_memory",
    },
    # Spawn: tools that invoke subagents or skills.
    # Always allowed if the target subagent is a compliance agent (enforcer, etc).
    "spawn": {
        "Agent",  # Claude Code: spawn subagent (current tool name)
        "Task",  # Claude Code: spawn subagent (legacy/alias)
        "Skill",  # Claude Code: invoke skill in-session
        "delegate_to_agent",  # Gemini CLI: spawn subagent (legacy)
        "invoke_agent",  # Gemini CLI >= ~0.40: spawn subagent
        "activate_skill",  # Gemini CLI: invoke skill in-session
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
        "aops_core_rbg",
        "aops_core_marsha",
        "aops_core_enforcer",
        "aops_core_qa",
        "aops_core_audit",
        "aops_core_butler",
    },
    # Read-only tools: no side effects. Exempt from enforcer gate.
    # Enforcer gate exempts them because compliance only tracks write operations.
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
        # enforcer — Haiku-class narrow compliance agent (periodic gate review).
        "enforcer",
        "aops-core:enforcer",
        "aops_core_enforcer",
        # rbg (The Judge) — sonnet-class ad-hoc axiom review.
        "rbg",
        "aops-core:rbg",
        "aops_core_rbg",
        # marsha (The QA Reviewer).
        "marsha",
        "aops-core:marsha",
        "aops_core_marsha",
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
    "invoke_agent": (
        ("agent_name", "name", "subagent_type", "agent", "agent_type"),
        False,
    ),  # Gemini CLI >= ~0.40
    "activate_skill": (("skill", "name"), True),
    # Gemini: bare agent tools (Strategy 2)
    "aops_core_enforcer": ((), False),
    "aops_core_rbg": ((), False),
    "aops_core_marsha": ((), False),
    # Codex: add entries when tool names are known
    # GitHub Copilot: add entries when tool names are known
}

# =============================================================================
# SLASH-COMMAND PROMPT DETECTION
# =============================================================================
# A UserPromptSubmit whose prompt carries one of these markers is a
# slash-command turn — i.e. a skill invocation (`/end-session`, `/dump`,
# `/remember`, `/planner`, ...). Such a turn owns its own finishing format, so
# the per-turn session-end gates (qa, handover, ida) must NOT re-arm (close) on
# it. Re-arming would fire the gate a second time on the Stop that follows the
# skill — e.g. a redundant ida honesty reflection right after /end-session has
# already produced its own reflection blocks.
#
# These patterns are used ONLY as `prompt_exclude_patterns` on the gates'
# UserPromptSubmit -> CLOSED re-arm triggers. They SUPPRESS the close; they
# never open a gate. A gate keeps whatever status it already held.
#
# Surface formats (verified against real transcripts / existing triggers):
#   Claude Code: the prompt carries `<command-name>/foo</command-name>`
#                (with sibling <command-message>/<command-args> tags; tag order
#                varies, so we match the tag anywhere, not anchored).
#   Gemini CLI:  the slash command is injected as `# /foo — ...`.
#
# A BARE leading slash is deliberately NOT matched: real user prompts can be
# bare file paths (e.g. "/home/nic/.../session-enforcer.md"), which must still
# re-arm the gate. Matching `^/` would silently disarm the honesty/handover/qa
# gates on any path-only prompt. The `<command-name>` tag and the Gemini `# /`
# form are unambiguous; a bare path is not.
SLASH_COMMAND_PROMPT_PATTERNS: list[str] = [
    r"<command-name>\s*/[a-zA-Z0-9_-]+\s*</command-name>",  # Claude Code slash command (skill invocation)
    r"^\s*#\s*/(?:end[-_]session|dump|remember|planner)\b",  # Gemini CLI slash-command injection (e.g. "# /dump …")
]

# =============================================================================
# GATE MODES
# =============================================================================
# Gate enforcement modes are read directly from environment variables. The
# polecat launcher (polecat/cli.py) resolves the per-mode posture from
# polecat.yaml on the host and stages the values into the container as env
# vars. Hooks never read polecat.yaml; they only read these env vars.
#
# When no env var is set (e.g. host orchestrator chat, fresh-install dev
# machine), defaults below apply: warn for human-facing gates, off for
# hydration. These match the previous BUILTIN_GATES posture.

_GATE_MODE_DEFAULTS = {
    # Handover defaults to block: a session that did real work (write tool or
    # task claim) must hand over before Stop. Read-only sessions are exempt via
    # session_did_work=False in custom_conditions (the policy returns no verdict).
    "HANDOVER_GATE_MODE": "block",
    "QA_GATE_MODE": "warn",
    "ENFORCER_GATE_MODE": "warn",
    "HYDRATION_GATE_MODE": "off",
    "IDA_GATE_MODE": "warn",
    # Sentinel defaults to block — this is a safety gate protecting user
    # environment files from destructive ops, not just an advisory.
    "SENTINEL_GATE_MODE": "block",
}
_ENFORCER_THRESHOLD_DEFAULT = 50


def __getattr__(name: str):  # PEP 562 module-level lazy attrs
    if name in _GATE_MODE_DEFAULTS:
        return os.environ.get(name, _GATE_MODE_DEFAULTS[name])
    if name == "ENFORCER_TOOL_CALL_THRESHOLD":
        raw = os.environ.get("ENFORCER_TOOL_CALL_THRESHOLD")
        if raw is None:
            return _ENFORCER_THRESHOLD_DEFAULT
        try:
            return int(raw)
        except ValueError:
            return _ENFORCER_THRESHOLD_DEFAULT
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "release_task": "infrastructure",
    "manage_task": "infrastructure",
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
    "create_subtask": "infrastructure",
    "merge_node": "infrastructure",
    "bulk_reparent": "infrastructure",
    "batch_update": "infrastructure",
    "batch_reparent": "infrastructure",
    "batch_archive": "infrastructure",
    "batch_merge": "infrastructure",
    "batch_create_epics": "infrastructure",
    "batch_reclassify": "infrastructure",
    "create_document": "infrastructure",
    "find_duplicates": "infrastructure",
    "delete": "infrastructure",
    "delete_memory": "infrastructure",
    "pkb_stats": "infrastructure",
    "pkb_explore": "infrastructure",
    "pkb_batch": "infrastructure",
    "pkb_tool_help": "infrastructure",
    "pkb_task_summary": "infrastructure",
    "pkb_graph_stats": "infrastructure",
    "graph_stats": "infrastructure",
    "get_stats": "infrastructure",
    "pkb_graph_json": "infrastructure",
    "tool_stats": "infrastructure",
}

# Regex to match any PKB MCP prefix variant and extract the operation name.
# Handles both Claude double-underscore (mcp__pkb__) and Gemini single-underscore
# (mcp_pkb_) forms, plus bare pkb__ prefix.
_PKB_PREFIX_RE = re.compile(
    r"^(?:"
    r"mcp__(?:plugin_(?:aops-core_|[\w.]+_))?(?:pkb|pbk)__"  # Claude double-underscore
    r"|mcp_(?:plugin_(?:aops-core_|[\w.]+_))?(?:pkb|pbk)_"  # Gemini single-underscore
    r"|pkb__"  # bare double-underscore
    r")(.+)$"
)

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
    # tools, but ToolSearch is sometimes blocked.
    if tool_name == "ToolSearch" and tool_input:
        query = tool_input.get("query", "")  # allow-fallback: optional input
        if isinstance(query, str) and query.startswith("select:"):
            return "infrastructure"

    # 2. Compliance agent spawns (Agent/Task + compliance subagent_type, or tool_name
    # is the compliance agent name directly) are infrastructure.
    # This ensures dispatching the enforcer is never blocked by any gate,
    # including the enforcer's own ops-threshold policy.
    extracted_st, _ = extract_subagent_type(tool_name, tool_input)
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

    # Structural escape hatch: if tool_input names a compliance subagent, treat as
    # infrastructure regardless of tool_name. Guards against future CLI tool-name
    # renames (e.g. invoke_agent successors) leaving the framework deadlocked.
    if isinstance(tool_input, dict):
        for key in ("agent_name", "name", "subagent_type", "agent", "agent_type"):
            v = tool_input.get(key)
            if isinstance(v, str) and v.strip().lstrip("/") in COMPLIANCE_SUBAGENT_TYPES:
                return "infrastructure"

    # Default: treat unknown tools as write (conservative)
    return "write"


def extract_subagent_type(
    tool_name: str | None, tool_input: dict[str, Any] | None
) -> tuple[str | None, bool]:
    """Extract subagent_type from a tool invocation.

    Two extraction strategies:
    1. Direct match: tool_name IS the agent name (e.g. Gemini reports
       tool_name="enforcer" rather than "delegate_to_agent").
       Matched against COMPLIANCE_SUBAGENT_TYPES.
    2. SPAWN_TOOLS table: tool_name is a spawning tool (e.g. "Agent",
       "delegate_to_agent") and the agent name is in tool_input.

    Args:
        tool_name: The tool being called (e.g. "Task", "delegate_to_agent",
            or the agent name directly like "enforcer").
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
        if tool_input is None:
            return None, is_skill
        for param in param_names:
            value = tool_input.get(param)
            if isinstance(value, str):
                stripped = value.strip().lstrip("/")
                if stripped:
                    return stripped, is_skill
        return None, is_skill

    return None, False


# =============================================================================
# WS7 — GATE HYGIENE: never-block, precedence, register-scaling, enforcer channel
# =============================================================================
# Composition primitives for WS7 (gate composition & exit semantics). They do
# NOT add gates — they make the EXISTING gates compose deterministically and stop
# the field-validated mis-routings (no new forcing functions; gate hygiene only):
#   - AskUserQuestion denied by a blocking gate (#1451)
#   - the enforcer instruction read as a prompt injection (#1315)
#   - undefined precedence when >=2 gates fire
#   - review-grade ceremony mis-firing on capture/personal work (retro MF4)

# --- Item 5: never-block list (#1451) -----------------------------------------
# The tool categories whose tools must NEVER be denied/warned by any gate policy.
# These are the control-plane tools the framework itself depends on — denying
# them deadlocks the session. AskUserQuestion is the load-bearing case: it is the
# live-attention surface the "Nic is the gate" substitute relies on, so a gate
# that denies it collapses that substitute (#1451, thread 8). Promoting the
# always_available + infrastructure categories to a global, gate-independent
# never-block guarantee is the fix.
NEVER_BLOCK_CATEGORIES: frozenset[str] = frozenset({"always_available", "infrastructure"})


def is_destructive_or_irreversible_op(
    tool_name: str | None, tool_input: dict[str, Any] | None = None
) -> bool:
    """Return True if the tool invocation represents a destructive or irreversible operation.

    Includes PKB reindexing with force, or destructive shell commands targeting PKB reindexing with force.
    """
    if not tool_name:
        return False

    # Check for reindex --force (issue #1497) in shell commands
    if tool_name in ("Bash", "run_shell_command", "shell", "execute_code"):
        inp = tool_input if isinstance(tool_input, dict) else {}
        command = inp.get("command", "")  # allow-fallback: optional shell command input
        if isinstance(command, str):
            cmd_lower = command.lower()
            if "reindex" in cmd_lower and (
                "force" in cmd_lower or "-f" in cmd_lower or "--force" in cmd_lower
            ):
                return True

    # Check for direct PKB reindex tool call with force
    # e.g., mcp__pkb__reindex, mcp__plugin_aops-core_pkb__reindex, etc.
    if "reindex" in tool_name.lower() and (
        "pkb" in tool_name.lower() or "pbk" in tool_name.lower()
    ):
        if tool_input and isinstance(tool_input, dict):
            force_val = tool_input.get("force")
            if force_val:
                return True
            if "force" in tool_input and tool_input["force"]:
                return True

    return False


def is_never_block(tool_name: str | None, tool_input: dict[str, Any] | None = None) -> bool:
    """Return True if the tool must never be denied/warned by any gate policy.

    Consulted by the gate engine before emitting a deny/block/warn verdict on a
    PreToolUse tool call. AskUserQuestion, ExitPlanMode, and the PKB/spawn
    infrastructure tools are never-block (#1451). Honouring this list is a global
    invariant — individual gates do not get to override it.
    """
    if not tool_name:
        return False

    # Destructive or irreversible operations carry a strict carve-out and never
    # qualify as never-block/defensible-defaults.
    if is_destructive_or_irreversible_op(tool_name, tool_input):
        return False

    return get_tool_category(tool_name, tool_input) in NEVER_BLOCK_CATEGORIES


# --- Item 4: enforcer channel sentinel (#1315) --------------------------------
# The enforcer gate injects an instruction telling the main agent to invoke rbg
# with a session-log path. In the field this read as a prompt injection — an
# instruction arriving mid-stream that says "now go invoke this agent" looks
# exactly like smuggled content, so the agent correctly-but-wrongly ignored a
# real gate (#1315, thread 1). The fix is a stable first-party marker on the
# enforcer's own channel: text carrying this sentinel is framework-issued, not
# untrusted input. The marker is the trust boundary — identical text WITHOUT it
# is still treated as untrusted.
ENFORCER_CHANNEL_SENTINEL = "<!-- aops:enforcer-channel -->"


def is_enforcer_channel(text: str | None) -> bool:
    """Return True if text carries the first-party enforcer-channel sentinel.

    The injection defence uses this to distinguish a real enforcer-gate
    instruction (first-party, trusted) from a look-alike smuggled instruction
    (untrusted). Only text the framework wrapped with the sentinel passes.
    """
    return bool(text) and ENFORCER_CHANNEL_SENTINEL in text


# --- Item 1: gate precedence (reviewable composition order) -------------------
# When two or more gates fire on the same event, the outcome must be reviewable.
# This constant makes the EXISTING composition order explicit rather than leaving
# it an emergent property of list position. It is DESCRIPTIVE of the runtime, not
# a redesign:
#
#   1. Verdict tier dominates first. The router (HookRouter._dispatch_gates) and
#      the engine merge results DENY > WARN > ALLOW — a deny from any gate beats
#      a warn from any other, regardless of position. "First deny wins": the
#      first gate (in iteration order) that denies sets the verdict and the loop
#      stops; later gates cannot downgrade it.
#   2. Within a tier, iteration order breaks ties — and iteration order is the
#      registration order, which is the GATE_CONFIGS list order. So the gate
#      earlier in this tuple wins a same-tier collision.
#
# This tuple MUST equal the order of GATE_CONFIGS in lib/gates/definitions.py (a
# test asserts it) so the documented precedence cannot silently drift from the
# runtime. Earlier = higher precedence.
#
# The order and its rationale (highest precedence first):
#   sentinel  — PreToolUse destructive-op safety block; protects the user's
#               environment, never advisory. Highest-stakes forcing function.
#   enforcer  — periodic compliance self-check (PreToolUse threshold block).
#   qa        — verification-before-exit (Stop); ahead of handover so a missing
#               verifier surfaces before the handover reminder.
#   handover  — structured-handover-before-exit (Stop): prevents work loss.
#   ida       — honesty reminder (Stop); advisory, lowest precedence.
GATE_PRECEDENCE: tuple[str, ...] = (
    "sentinel",
    "enforcer",
    "qa",
    "handover",
    "ida",
)


# --- Item 6: register-scaling (capture/personal) ------------------------------
# WS6 defined three registers (capture/personal, working, review-grade) as
# doctrine in junior.md; the enforcement is WS7's lane. The register is selected
# per-session from the AOPS_SESSION_REGISTER env var. In the capture/personal
# register the review-grade gates (enforcer self-check, ida honesty reminder, qa
# verification) are suppressed — a "vacuum the garage" capture must not draw a
# compliance audit or an honesty loop (thread 10, retro MF4). The handover and
# sentinel gates are NOT suppressed: losing a capture or running a destructive
# op is still real harm.
#
# ida (honesty) is suppressed as a *gate* here, but its injected instructions
# are TIERED (hooks/templates/ida-reminder.md, updated 2026-05-30): the honesty
# floor (don't claim inferred as observed; flag substitutions/skips/unverified
# subagent results; no relayed menus) is woven into the template and applied by
# the agent's judgment on every turn — only the heavyweight evidence ceremony
# (confidence %, competing hypotheses, artifact manifest) is gate-suppressed in
# capture. This is the "instructions first" approach: improve guidance before
# escalating to harder enforcement. If instruction tiering proves insufficient,
# we can remove ida from the suppressed set to hard-enforce later.
#
# NOT YET WIRED (reader-side only): this is the *reader* half. Nothing in the
# repo *sets* AOPS_SESSION_REGISTER yet — no launcher, slash-command, or
# SessionStart hook writes it — so get_session_register() always resolves to
# 'working' in the running system and register-scaling is dormant (fail-closed:
# dormant means full ceremony, never less). Activating it (deciding *when* a
# session is capture/personal and writing the var) is a separate follow-up, not
# something this code assumes is live. The reader + engine wiring + tests are
# correct and safe to ship ahead of the writer.
REGISTER_ENV_VAR = "AOPS_SESSION_REGISTER"
CAPTURE_REGISTER_VALUES: frozenset[str] = frozenset({"capture", "personal"})

# Gates suppressed in the capture/personal register (the review-grade ceremony).
# ida's gate fires are suppressed here — the honesty floor is enforced via
# tiered instructions in ida-reminder.md, not by hard gate enforcement.
GATES_SUPPRESSED_IN_CAPTURE: frozenset[str] = frozenset({"enforcer", "ida", "qa"})


def get_session_register() -> str:
    """Return the active session register, defaulting to 'working'.

    Read from AOPS_SESSION_REGISTER. Recognised values: 'capture'/'personal'
    (lightest), 'working' (default), 'review' (review-grade). Unknown values fall
    back to 'working' — register-scaling never fails open onto a *lighter*
    register, only onto the working default.
    """
    # os.environ.get with no default returns None when unset; we normalise that
    # to the 'working' register explicitly (no silent empty-string fallback).
    raw_env = os.environ.get(REGISTER_ENV_VAR)
    raw = (raw_env or "working").strip().lower()
    if raw in CAPTURE_REGISTER_VALUES:
        return raw
    if raw == "review":
        return "review"
    return "working"


def is_capture_register() -> bool:
    """Return True if the session is in the capture/personal register."""
    return get_session_register() in CAPTURE_REGISTER_VALUES


def is_gate_suppressed_in_register(gate_name: str) -> bool:
    """Return True if this gate's ceremony is dropped in the current register.

    In the capture/personal register the review-grade gates (enforcer, ida, qa)
    are suppressed so low-stakes capture work drops below review-grade ceremony
    (WS6 register model, WS7 enforcement). Sentinel and handover always fire.
    """
    return is_capture_register() and gate_name in GATES_SUPPRESSED_IN_CAPTURE
