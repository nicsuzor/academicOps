"""Tool categorization for gate routing.

Categorizes tool *names* by their side-effect class (always_available,
infrastructure, spawn, read_only, write). Gates consult `get_tool_category()`
to decide whether a tool call must pass the gate, bypass it, or be
unconditionally protected from blocking (`is_never_block()`).

`hooks/gate_config.py` re-exports these names for backward compatibility.

Lives in `lib/` because gate-engine code (`lib/gates/*`) needs to consume it
without importing upward from `hooks/`.

PKB op coverage:
    `_PKB_OPERATIONS` is the single source of truth for which PKB MCP
    operations exist. The full set of prefixed variants
    (`mcp__pkb__<op>`, `mcp__plugin_aops-core_pkb__<op>`, `mcp__pbk__<op>`,
    `mcp_pkb_<op>`, `mcp_pbk_<op>`, `pkb__<op>`, and bare `<op>`) is
    generated mechanically at module load and injected into the
    `infrastructure` set. This eliminates the previous divergence between
    the hand-maintained set and the `_PKB_OPERATIONS` fallback (16 ops
    were only in the fallback, 1 only in the static set).

Lookup performance:
    A reverse `{tool_name: category}` index is built once at module load,
    so `get_tool_category()` runs in O(1) for known names. The PKB prefix
    regex is consulted only as a fallback for unknown prefix variants.
"""

import re
from typing import Any

from lib import tool_registry

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
# Skill/activate_skill), not as a separate subagent.

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
    # Antigravity (agy): spawn tool. The type is NESTED under
    # ``Subagents: [{TypeName: ...}]`` (not a flat param), so the flat lookup here
    # returns nothing and ``extract_subagent_type`` falls back to
    # ``tool_registry.agy_subagents_type``. Registered so agy spawns are recognised
    # as spawn tools at all (previously unknown -> defaulted to ``write``).
    "invoke_subagent": ((), False),
    # Gemini: bare agent tools (Strategy 2)
    "aops_core_enforcer": ((), False),
    "aops_core_rbg": ((), False),
    "aops_core_marsha": ((), False),
}


# =============================================================================
# PKB OPERATION REGISTRY (single source of truth)
# =============================================================================
# Every PKB MCP operation lives here. All known prefix variants are generated
# mechanically below — no hand-maintained per-prefix sets to drift from this.

_PKB_OPERATIONS: dict[str, str] = {
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
    "save_memory": "infrastructure",
}

# Prefix variants that PKB ops can appear under. Generated mechanically into the
# static infrastructure set at module load, so no per-prefix list drifts from
# _PKB_OPERATIONS. The fallback regex below still covers unknown variants
# (e.g. future versioned plugin prefixes).
_PKB_PREFIX_VARIANTS: tuple[str, ...] = (
    "mcp__pkb__",  # Claude Code short form
    "mcp__plugin_aops-core_pkb__",  # Claude Code full plugin prefix
    "mcp__pbk__",  # Gemini typo variant (double underscore)
    "mcp_pkb_",  # Gemini single-underscore form
    "mcp_pbk_",  # Gemini single-underscore typo variant
    "pkb__",  # Bare double-underscore
    "",  # Gemini bare tool name (no prefix)
)

# Regex to match any PKB MCP prefix variant and extract the operation name.
# Used as fallback for unknown prefix variants (e.g. versioned plugin prefixes
# not enumerated in _PKB_PREFIX_VARIANTS).
_PKB_PREFIX_RE = re.compile(
    r"^(?:"
    r"mcp__(?:plugin_(?:aops-core_|[\w.]+_))?(?:pkb|pbk)__"  # Claude double-underscore
    r"|mcp_(?:plugin_(?:aops-core_|[\w.]+_))?(?:pkb|pbk)_"  # Gemini single-underscore
    r"|pkb__"  # bare double-underscore
    r")(.+)$"
)


def _generate_pkb_variants() -> dict[str, set[str]]:
    """Generate per-category sets of every (prefix, op) PKB tool name variant."""
    variants: dict[str, set[str]] = {}
    for op, category in _PKB_OPERATIONS.items():
        bucket = variants.setdefault(category, set())
        for prefix in _PKB_PREFIX_VARIANTS:
            bucket.add(f"{prefix}{op}")
    return variants


# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize TOOL NAMES by their side effects. This determines which gates
# must pass before the tool can be used.
#
# IMPORTANT: Only TOOL NAMES go here. Agent/skill names (enforcer, etc.)
# are subagent_type values, not tool names. They belong in
# COMPLIANCE_SUBAGENT_TYPES above.
#
# PKB MCP operations are NOT listed individually — they are generated
# mechanically from `_PKB_OPERATIONS` × `_PKB_PREFIX_VARIANTS` at module
# load. To add a new PKB op, add it once to `_PKB_OPERATIONS`.

TOOL_CATEGORIES: dict[str, set[str]] = {
    # Always available: bypass ALL gates.
    # Claude Code built-in meta/control tools with no substantive side effects
    # on user data. They must never be blocked — e.g. AskUserQuestion is needed
    # to communicate with the user during any gate state.
    "always_available": {
        "AskUserQuestion",
        "ask_user",
        "TodoWrite",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
    },
    # Infrastructure: bypass ALL gates.
    # Tools required for the framework itself to function (PKB + memory MCP).
    # PKB op variants are added below from _PKB_OPERATIONS.
    "infrastructure": {
        # --- Memory MCP ---
        "mcp__plugin_aops-core_memory__retrieve_memory",
        "mcp__plugin_aops-core_memory__store_memory",
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
}

# Inject mechanically generated PKB variants. Single source: _PKB_OPERATIONS.
for _category, _variants in _generate_pkb_variants().items():
    TOOL_CATEGORIES.setdefault(_category, set()).update(_variants)
del _category, _variants

# Merge the cross-client tool registry (Table 2 SSoT — lib/tool_registry.py).
# This is the SINGLE source for the core file/shell/web/spawn/interaction tool
# names across Claude, Gemini, and agy — including the agy RUNTIME vocabulary
# (view_file, run_command, write_to_file, replace_file_content, invoke_subagent,
# manage_task, …) that was previously unknown here, so agy tool calls fell through
# to the conservative ``write`` default and broke spawn/enforcer/sentinel matching.
# Server-specific MCP sets (Outlook, Zotero, Playwright, …) stay defined above; the
# registry only owns the cross-client core. The merge is additive and must never
# DISAGREE with an existing entry (asserted by tests/hooks/test_tool_registry.py).
for _category, _reg_names in tool_registry.names_by_category().items():
    TOOL_CATEGORIES.setdefault(_category, set()).update(_reg_names)
del _category, _reg_names


# Build O(1) reverse index. Rebuilt only if TOOL_CATEGORIES is mutated.
_TOOL_CATEGORY_INDEX: dict[str, str] = {
    tool: category for category, tools in TOOL_CATEGORIES.items() for tool in tools
}


# =============================================================================
# NEVER-BLOCK CATEGORIES
# =============================================================================
# Tool categories whose tools must NEVER be denied/warned by any gate policy.
# These are the control-plane tools the framework itself depends on — denying
# them deadlocks the session. AskUserQuestion is the load-bearing case: it is
# the live-attention surface the "Nic is the gate" substitute relies on, so a
# gate that denies it collapses that substitute (#1451, thread 8). Promoting
# always_available + infrastructure to a global, gate-independent never-block
# guarantee is the fix.

NEVER_BLOCK_CATEGORIES: frozenset[str] = frozenset({"always_available", "infrastructure"})


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_tool_category(tool_name: str, tool_input: dict[str, Any] | None = None) -> str:
    """Get the category for a tool.

    Lookup order:
    1. ToolSearch with select: prefix -> infrastructure (tool-loading, not new work)
    2. Compliance agent spawn: spawn tool + compliance subagent_type -> infrastructure
    3. Static TOOL_CATEGORIES reverse index (O(1) for known tool names)
    4. PKB prefix normalization (handles unknown MCP prefix variants)
    5. Structural escape hatch: tool_input names a compliance subagent
    6. Default: 'write' (conservative fallback for truly unknown tools)

    Args:
        tool_name: The tool being called.
        tool_input: Optional tool input dict. Used to:
            - Detect ToolSearch select: queries (infrastructure bypass)
            - Extract subagent_type for compliance-spawn bypass
    """
    # 0. Antigravity (agy) wraps EVERY MCP call in ``call_mcp_tool`` with the real
    # server/tool in ``tool_input`` ({ServerName, ToolName, Arguments}). Unwrap it to
    # the canonical ``mcp__<server>__<tool>`` name and classify THAT — otherwise every
    # agy MCP/PKB call falls through to the ``write`` default and gets gated.
    unwrapped = tool_registry.unwrap_agy_mcp_call(tool_name, tool_input)
    if unwrapped is not None:
        return get_tool_category(unwrapped, None)

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

    # 3. Static reverse index (O(1)).
    category = _TOOL_CATEGORY_INDEX.get(tool_name)
    if category is not None:
        return category

    # 4. Fallback: normalize PKB MCP prefix variants. Covers prefixes not
    # enumerated in _PKB_PREFIX_VARIANTS (e.g. mcp__plugin_<version>_pkb__).
    m = _PKB_PREFIX_RE.match(tool_name)
    if m:
        cat = _PKB_OPERATIONS.get(m.group(1))
        if cat:
            return cat

    # Edge case: compliance subagent names sometimes appear as tool_name
    # (router logs subagent_type as tool_name in some code paths).
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
        # Strategy 2b: agy nests the subagent type under ``Subagents: [{TypeName}]``
        # (invoke_subagent) rather than a flat param. Fall back to the registry's
        # nested extractor for those tools.
        reg = tool_registry.SPAWN_TABLE.get(tool_name)
        if reg and reg[2]:  # agy_subagents
            nested = tool_registry.agy_subagents_type(tool_input)
            if nested:
                return nested, is_skill
        return None, is_skill

    return None, False


def is_never_block(tool_name: str | None, tool_input: dict[str, Any] | None = None) -> bool:
    """Return True if the tool must never be denied/warned by any gate policy.

    Consulted by the gate engine before emitting a deny/block/warn verdict on a
    PreToolUse tool call. AskUserQuestion, ExitPlanMode, and the PKB/spawn
    infrastructure tools are never-block (#1451). Honouring this list is a global
    invariant — individual gates do not get to override it.
    """
    if not tool_name:
        return False
    return get_tool_category(tool_name, tool_input) in NEVER_BLOCK_CATEGORIES
