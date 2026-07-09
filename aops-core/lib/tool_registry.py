"""Tool registry SSoT — Table 2 of specs/hooks/CLIENT-TRANSLATION.md (RUNTIME half).

One record per ABSTRACT tool: a canonical name, the side-effect ``category``, and
the RUNTIME-emitted concrete tool name on each client (Claude Code, Antigravity
"agy"). This is the SINGLE source of truth for RUNTIME tool
recognition: it generates the per-client ``(name -> category)`` entries, the
spawn table, and the agy ``call_mcp_tool`` unwrap / nested-subagent extraction
consumed by ``lib/tool_categories.py`` — and through it the gate engine, the
sentinel, and the rbg.

SCOPE — RUNTIME names only: what each client EMITS in a hook event. A client's
BUILD-frontmatter tool name can DIFFER from its runtime name. For example, Claude
``Agent`` is rewritten to ``activate_skill`` inside a Gemini agent's frontmatter
by the build, but the Gemini *runtime* emits ``invoke_agent`` / ``delegate_to_agent``;
agy agent bodies keep Claude tool names (invariant #11) yet the agy runtime emits
``invoke_subagent``. The build-side frontmatter/body name projection is a SEPARATE
concern handled in ``scripts/build.py`` (CLIENT-TRANSLATION.md §P3) — do NOT fold
build names into this table or recognition will diverge from reality.

The agy column is the previously-missing half: agy agent bodies reuse Claude tool
names, so the build never needed agy names, but the agy runtime emits its own
vocabulary (``view_file``, ``run_command``, ``invoke_subagent``, ``call_mcp_tool``,
…). Those names were unknown to the runtime, so spawn / rbg / sentinel
matching silently failed on agy. The vocabulary here is EMPIRICAL — mined from real
``~/.gemini/antigravity-cli/brain/*.jsonl`` transcripts (see PKB ref mem-689f170f).

DESIGN CONSTRAINT: stdlib-only (no pydantic, no project imports) so
``scripts/build.py`` can import the canonical/category data without pulling in the
hook runtime's dependency tree — the same constraint as ``client_spec.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

CLIENTS = ("claude", "agy")

# Category labels — MUST match the keys of ``lib.tool_categories.TOOL_CATEGORIES``.
READ_ONLY = "read_only"
WRITE = "write"
SPAWN = "spawn"
ALWAYS = "always_available"
INFRASTRUCTURE = "infrastructure"


@dataclass(frozen=True)
class ToolSpec:
    """One abstract tool and its RUNTIME name on each client.

    ``claude`` / ``agy`` are the names that client EMITS in a hook
    event (``None`` = the tool is not available / not distinct on that client).
    Several abstract tools may share a client name; that is fine — reverse lookups
    resolve to ``category`` which is identical for them, and ``canonical`` is only
    needed where it is unambiguous.
    """

    canonical: str
    category: str
    claude: str | None = None
    agy: str | None = None
    # Spawn-only: flat tool_input param names that carry the subagent type
    # (Claude ``subagent_type`` …).
    spawn_flat_params: tuple[str, ...] = ()
    # Spawn-only: agy nests the type under ``Subagents: [{TypeName: ...}]`` — set
    # this so ``extract_subagent_type`` reaches it.
    spawn_agy_subagents: bool = False
    # Skill-like spawn that runs in the MAIN agent's session (Skill)
    # rather than as a separate subagent.
    is_skill: bool = False


# =============================================================================
# THE REGISTRY
# =============================================================================
# Canonical name == Claude's tool name where one exists; otherwise the client's
# own name (agy-native tools that have no Claude equivalent).
REGISTRY: tuple[ToolSpec, ...] = (
    # ---- File reads -------------------------------------------------------
    ToolSpec("Read", READ_ONLY, claude="Read", agy="view_file"),
    ToolSpec("Glob", READ_ONLY, claude="Glob", agy="list_dir"),
    ToolSpec("Grep", READ_ONLY, claude="Grep", agy="grep_search"),
    # ---- File writes / shell ---------------------------------------------
    ToolSpec("Write", WRITE, claude="Write", agy="write_to_file"),
    ToolSpec("Edit", WRITE, claude="Edit", agy="replace_file_content"),
    ToolSpec("MultiEdit", WRITE, claude="MultiEdit", agy="multi_replace_file_content"),
    ToolSpec("Bash", WRITE, claude="Bash", agy="run_command"),
    ToolSpec("NotebookEdit", WRITE, claude="NotebookEdit"),  # no agy equivalent
    # ---- Web --------------------------------------------------------------
    ToolSpec("WebFetch", READ_ONLY, claude="WebFetch", agy="read_url_content"),
    ToolSpec("WebSearch", READ_ONLY, claude="WebSearch", agy="search_web"),
    # ---- Spawn (subagents / skills) --------------------------------------
    # Agent / Task: distinct Claude names, surface as agy ``invoke_subagent``
    # (type nested under Subagents[].TypeName).
    ToolSpec(
        "Agent",
        SPAWN,
        claude="Agent",
        agy="invoke_subagent",
        spawn_flat_params=("subagent_type", "agent_name", "name", "agent", "agent_type"),
        spawn_agy_subagents=True,
    ),
    ToolSpec(
        "Task",
        SPAWN,
        claude="Task",
        agy="invoke_subagent",
        spawn_flat_params=("subagent_type", "name", "agent_name"),
        spawn_agy_subagents=True,
    ),
    ToolSpec(
        "Skill",
        SPAWN,
        claude="Skill",
        agy=None,
        spawn_flat_params=("skill", "name"),
        is_skill=True,
    ),
    # ---- User interaction / control (NEVER block) -------------------------
    ToolSpec("AskUserQuestion", ALWAYS, claude="AskUserQuestion", agy="ask_question"),
    # agy ask_permission: agy's own permission prompt — a control-plane surface,
    # must never be gate-blocked (blocking it deadlocks the agy permission flow).
    ToolSpec("ask_permission", ALWAYS, agy="ask_permission"),
    # ---- agy-native infrastructure / control -----------------------------
    # manage_task: agy's task CRUD. schedule: agy's wait/timer. Both
    # are framework control-plane, not user-data mutations — bypass gates.
    ToolSpec("manage_task", INFRASTRUCTURE, agy="manage_task"),
    ToolSpec("schedule", INFRASTRUCTURE, agy="schedule"),
    # ---- agy-native reads -------------------------------------------------
    ToolSpec("list_resources", READ_ONLY, agy="list_resources"),
    ToolSpec("list_permissions", READ_ONLY, agy="list_permissions"),
)

# agy wraps EVERY MCP call in this tool: args = {ServerName, ToolName, Arguments}.
# It is NOT a fixed category — the real category depends on the wrapped MCP tool,
# so recognition UNWRAPS it (see ``unwrap_agy_mcp_call``) and re-looks-up the
# reconstructed ``mcp__<server>__<tool>`` name. Without this, every agy MCP/PKB
# call fell through to the conservative ``write`` default and got gated.
AGY_MCP_WRAPPER_TOOL = "call_mcp_tool"


# =============================================================================
# BUILD-NAME PROJECTION (Table 2, BUILD half — CLIENT-TRANSLATION.md §P3b)
# =============================================================================
# DISTINCT from the RUNTIME registry above. These maps are what the BUILD writes
# into a client's agent FRONTMATTER / body text when generating dist — and a
# client's build-frontmatter tool name DELIBERATELY differs from its runtime name.
# This is the SSoT that ``scripts/build.py`` reads (replacing its inline
# ``TOOL_NAME_MAP`` copies), EXACTLY mirroring how P3a moved the event maps into
# ``client_spec``.

# Claude-source frontmatter tool name -> Antigravity frontmatter tool name.
# A value of ``None`` means "drop the tool" (no Antigravity equivalent).
BUILD_CLAUDE_TO_AGY_TOOL: dict[str, str | None] = {
    # File operations (Claude Code -> Antigravity)
    "Read": "view_file",
    "Write": "write_to_file",
    "Edit": "replace_file_content",
    "MultiEdit": "multi_replace_file_content",
    "Glob": "list_dir",
    "Grep": "grep_search",
    "grep": "grep_search",  # lowercase variant
    # Shell execution
    "Bash": "run_command",
    "bash": "run_command",  # lowercase variant
    # Skills/Agents
    "Skill": "invoke_subagent",
    "Task": "invoke_subagent",
    "Agent": "invoke_subagent",
    # User interaction / planning / todos (Claude built-ins -> agy native)
    "AskUserQuestion": "ask_question",
    "ExitPlanMode": None,
    "TodoWrite": None,
    "NotebookEdit": None,
    # Web operations
    "WebFetch": "read_url_content",
    "WebSearch": "search_web",
}


# Generic/Gemini frontmatter tool name -> Claude Code frontmatter tool name.
# Used when projecting a (possibly Gemini-named) source agent INTO a Claude
# artifact; unknown names pass through unchanged at the call site.
BUILD_TO_CLAUDE_TOOL: dict[str, str] = {
    # File operations (both Gemini and Antigravity)
    "read_file": "Read",
    "view_file": "Read",
    "write_file": "Write",
    "write_to_file": "Write",
    "replace": "Edit",
    "replace_file_content": "Edit",
    "multi_replace_file_content": "MultiEdit",
    "list_directory": "Glob",
    "list_dir": "Glob",
    "glob": "Glob",
    "grep": "Grep",
    "grep_search": "Grep",
    "search_file_content": "Grep",
    # Shell execution
    "bash": "Bash",
    "run_shell_command": "Bash",
    "run_command": "Bash",
    # Skills/Agents
    "activate_skill": "Skill",
    "invoke_subagent": "Agent",
    # Web operations
    "web_fetch": "WebFetch",
    "read_url_content": "WebFetch",
    "web_search": "WebSearch",
    "search_web": "WebSearch",
    # User interaction
    "ask_question": "AskUserQuestion",
    # Already correct names (passthrough)
    "Read": "Read",
    "Write": "Write",
    "Edit": "Edit",
    "Glob": "Glob",
    "Grep": "Grep",
    "Bash": "Bash",
    "Skill": "Skill",
    "Task": "Task",
    "Agent": "Agent",
    "WebFetch": "WebFetch",
    "WebSearch": "WebSearch",
    "TodoWrite": "TodoWrite",
    "AskUserQuestion": "AskUserQuestion",
    "NotebookEdit": "NotebookEdit",
    # Browser/Playwright (Gemini chrome-devtools-mcp -> Claude Code)
    "navigate_page": "browser_navigate",
    "take_snapshot": "browser_snapshot",
    "take_screenshot": "browser_take_screenshot",
    "click": "browser_click",
    "wait_for": "browser_wait_for",
    "evaluate_script": "browser_evaluate",
    "type_text": "browser_type",
    "resize_page": "browser_resize",
    # Passthrough for browser_* names (already canonical)
    "browser_navigate": "browser_navigate",
    "browser_snapshot": "browser_snapshot",
    "browser_take_screenshot": "browser_take_screenshot",
    "browser_click": "browser_click",
    "browser_wait_for": "browser_wait_for",
    "browser_evaluate": "browser_evaluate",
    "browser_type": "browser_type",
    "browser_resize": "browser_resize",
}

# Body-text tool-call NOTATION rewrites the build applies to a client's prose
# (call notation, descriptive notation, backticked notation). Keyed by build
# platform name (``claude`` / ``antigravity``).
BUILD_BODY_TOOL_NOTATION: dict[str, dict[str, str]] = {
    "antigravity": {
        "Read(": "view_file(",
        "Write(": "write_to_file(",
        "Edit(": "replace_file_content(",
        "ls(": "list_dir(",
        "Glob(": "list_dir(",
        "Grep(": "grep_search(",
        "Read tool": "view_file tool",
        "Write tool": "write_to_file tool",
        "Edit tool": "replace_file_content tool",
        "`Read`": "`view_file`",
        "`Write`": "`write_to_file`",
        "`Edit`": "`replace_file_content`",
        "`ls`": "`list_dir`",
        "`Glob`": "`list_dir`",
        "`Grep`": "`grep_search`",
        "Read or Grep": "view_file or grep_search",
    },
    "claude": {},
}


# =============================================================================
# Derived lookups (built once)
# =============================================================================
def _runtime_name_to_category() -> dict[str, str]:
    """{runtime tool name -> category} across all clients, generated from REGISTRY."""
    index: dict[str, str] = {}
    for spec in REGISTRY:
        for name in (spec.claude, spec.agy):
            if name:
                # Same name on two specs must agree on category (asserted by tests).
                index[name] = spec.category
    return index


RUNTIME_NAME_TO_CATEGORY: dict[str, str] = _runtime_name_to_category()


def _spawn_table() -> dict[str, tuple[tuple[str, ...], bool, bool]]:
    """{spawn runtime name -> (flat_params, is_skill, agy_subagents)}."""
    table: dict[str, tuple[tuple[str, ...], bool, bool]] = {}
    for spec in REGISTRY:
        if spec.category != SPAWN:
            continue
        for name in (spec.claude, spec.agy):
            if name:
                table[name] = (spec.spawn_flat_params, spec.is_skill, spec.spawn_agy_subagents)
    return table


SPAWN_TABLE: dict[str, tuple[tuple[str, ...], bool, bool]] = _spawn_table()


def category_for_runtime_name(tool_name: str | None) -> str | None:
    """Category for a RUNTIME-emitted tool name, or None if not in the registry."""
    if not tool_name:
        return None
    return RUNTIME_NAME_TO_CATEGORY.get(tool_name)


def names_by_category() -> dict[str, set[str]]:
    """{category -> {every runtime name in that category}}."""
    out: dict[str, set[str]] = {}
    for spec in REGISTRY:
        bucket = out.setdefault(spec.category, set())
        for name in (spec.claude, spec.agy):
            if name:
                bucket.add(name)
    return out


def _unwrap_double_json(value):
    """agy double-JSON-encodes scalar arg values (e.g. ``"\\"pkb\\""`` / ``"60"``).

    Strip ONE layer of JSON string-encoding if present so ``"\\"pkb\\""`` -> ``pkb``.
    Returns the value unchanged if it is not a JSON-encoded string.
    """
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            import json

            try:
                return json.loads(s)
            except (ValueError, TypeError):
                return s
        return s
    return value


def unwrap_agy_mcp_call(tool_name: str | None, tool_input) -> str | None:
    """Reconstruct the canonical ``mcp__<server>__<tool>`` name of an agy-wrapped
    MCP call so the normal category lookup (which already knows PKB ops, Zotero,
    Outlook, …) can classify it. Returns None if this is not an agy MCP wrapper or
    the fields are absent.

    agy args shape: ``{"ServerName": "pkb", "ToolName": "search", "Arguments": "{…}"}``
    with values double-JSON-encoded. We reconstruct ``mcp__pkb__search``.
    """
    if tool_name != AGY_MCP_WRAPPER_TOOL or not isinstance(tool_input, dict):
        return None
    server = _unwrap_double_json(tool_input.get("ServerName"))
    tool = _unwrap_double_json(tool_input.get("ToolName"))
    if not isinstance(server, str) or not isinstance(tool, str) or not server or not tool:
        return None
    return f"mcp__{server}__{tool}"


def agy_subagents_type(tool_input) -> str | None:
    """Extract the subagent type from agy ``invoke_subagent`` input.

    agy nests it: ``{"Subagents": [{"Prompt": …, "Role": …, "TypeName": "research"}]}``.
    The ``Subagents`` value may itself be a JSON string (agy double-encodes args),
    so decode it if needed. Returns the first ``TypeName`` found, else None.
    """
    if not isinstance(tool_input, dict):
        return None
    subagents = tool_input.get("Subagents")
    if isinstance(subagents, str):
        import json

        try:
            subagents = json.loads(subagents)
        except (ValueError, TypeError):
            return None  # allow-fallback: malformed agy Subagents JSON -> no type found; a hook must not crash on a garbled wire payload, and "unrecognized spawn" is the safe degradation
    if isinstance(subagents, list):
        for entry in subagents:
            if isinstance(entry, dict):
                type_name = entry.get("TypeName")
                if isinstance(type_name, str) and type_name.strip():
                    return type_name.strip().lstrip("/")
    return None
