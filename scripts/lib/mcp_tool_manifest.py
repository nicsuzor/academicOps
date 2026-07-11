"""SSoT snapshot of the "pkb" MCP aggregator's live tool manifest.

Used by scripts/build.py's frontmatter-vs-reality guard (aops_35b7dce7) to catch
the aops_b580e332 defect class before it ships: an agent's `tools:` frontmatter
naming an explicit MCP tool that LOOKS plausible but does not resolve against
what the plugin's MCP server actually exposes at runtime.

SCOPE: the "pkb" server (aops-pkb/mcp.json.template, and aops-core/mcp.json.template's
cowork/gemini blocks — same underlying service, different Claude-Code plugin-slug
prefix) is the only in-repo plugin-provided MCP server today. It is an AGGREGATOR:
Claude Code namespaces its tools as `mcp__plugin_<installed-plugin-slug>_pkb__...`,
and the aggregator itself mounts three inner FastMCP sub-apps (`pkb`, `zotmcp`,
`osbchatmcp`), each contributing its OWN `<name>__` segment, plus a handful of
tools mounted directly at the aggregator's top level (`code-mode`, `mcp-*`). So a
frontmatter author writing `mcp__plugin_aops-pkb_pkb__get_task` (one `pkb__`)
produces a name that looks entirely plausible but is NOT the live, callable tool
— the real name carries the sub-mount's OWN `pkb__` segment too:
`mcp__plugin_aops-pkb_pkb__pkb__get_task` (two). rbg/marsha/ida shipped with the
single-prefix (broken) form for an unknown period before aops_b580e332 caught it
by manual runtime observation, not by any automated gate.

PROVENANCE / HOW TO REFRESH: the pkb MCP server has no source in this repo (it's
an external HTTP service reached via PKB_MCP_URL — see aops-pkb/scripts/run-mcp.sh)
and CI has no network path or credentials to query its live `tools/list`, so this
manifest is a hand-captured snapshot, not something scripts/build.py can
regenerate itself. Captured 2026-07-12 by enumerating the tool manifest a live
Claude Code session negotiated with the installed aops-pkb plugin at session
start (the harness's own runtime tool discovery — the same kind of evidence the
aops_b580e332 incident was diagnosed against, just captured deliberately instead
of by accident). To refresh: start a fresh session with the aops-pkb plugin
installed, list every `mcp__plugin_aops-pkb_pkb__*` tool the harness surfaces,
and replace the sets below.
"""

from __future__ import annotations

import re

# Sub-servers mounted inside the "pkb" aggregator, each contributing a
# `<name>__<verb>` segment to the tool's exposed name.
PKB_SUBSERVER_TOOLS: dict[str, frozenset[str]] = {
    "pkb": frozenset(
        {
            "append",
            "batch_archive",
            "batch_create_epics",
            "batch_merge",
            "batch_reclassify",
            "batch_reparent",
            "batch_update",
            "claim_task",
            "complete_task",
            "create",
            "create_memory",
            "create_task",
            "decompose_task",
            "delete",
            "delete_memory",
            "detect_weight_divergence",
            "find_duplicates",
            "get_dependency_tree",
            "get_document",
            "get_network_metrics",
            "get_semantic_neighbors",
            "get_stats",
            "get_task",
            "get_task_children",
            "graph_json",
            "graph_stats",
            "list_documents",
            "list_memories",
            "list_tasks",
            "merge_node",
            "pkb_context",
            "pkb_orphans",
            "pkb_trace",
            "refresh_graph",
            "release_task",
            "retrieve_memory",
            "search",
            "search_by_tag",
            "status",
            "task_search",
            "task_summary",
            "top_n_by_metric",
            "update_body",
            "update_task",
        }
    ),
    "zotmcp": frozenset(
        {
            "add_note",
            "add_tags",
            "create_item",
            "get_collection_info",
            "get_item",
            "get_paper_citations",
            "get_paper_details",
            "get_referenced_works",
            "get_similar_items",
            "get_version_info",
            "import_attachment",
            "link_attachment",
            "resolve_and_create",
            "search",
            "search_by_citation_key",
            "search_by_doi",
            "search_library_by_author",
            "search_openalex_author",
            "search_papers",
        }
    ),
    "osbchatmcp": frozenset(
        {
            "get_case_summary",
            "get_collection_info",
            "get_document",
            "get_similar_documents",
            "ping",
            "search",
        }
    ),
}

# Tools mounted directly at the aggregator's top level (no sub-server segment).
PKB_TOP_LEVEL_TOOLS: frozenset[str] = frozenset(
    {
        "code-mode",
        "mcp-activate-profile",
        "mcp-add",
        "mcp-config-set",
        "mcp-create-profile",
        "mcp-exec",
        "mcp-find",
        "mcp-remove",
    }
)


def _pkb_manifest_suffixes() -> frozenset[str]:
    """Every valid `mcp__plugin_<slug>_pkb__<suffix>` suffix, sub-server-qualified."""
    suffixes = set(PKB_TOP_LEVEL_TOOLS)
    for sub_server, tools in PKB_SUBSERVER_TOOLS.items():
        suffixes.update(f"{sub_server}__{tool}" for tool in tools)
    return frozenset(suffixes)


PKB_MANIFEST_SUFFIXES: frozenset[str] = _pkb_manifest_suffixes()

# Matches an explicit (non-wildcard) frontmatter grant into the "pkb"
# aggregator's namespace under ANY installed plugin slug. Every TRACKED source
# file uses the "aops-pkb" slug; "aops-cowork" only appears in BUILD OUTPUT
# (scripts/build.py's _AOPS_CORE_MCP_PREFIX -> _AOPS_COWORK_MCP_PREFIX rewrite
# pass), which this guard does not scan (it runs against source, see
# scripts/build.py's _assert_agent_frontmatter_mcp_tools_resolve).
_PKB_PLUGIN_TOOL_RE = re.compile(r"^mcp__plugin_[a-z0-9-]+_pkb__(?P<suffix>.+)$")


def classify_explicit_mcp_tool(tool_name: str) -> str | None:
    """Return an error message if `tool_name` is a known-aggregator explicit
    grant whose suffix is NOT in the live-verified manifest; ``None`` if it
    resolves, is a wildcard grant, or names a tool this module has no manifest
    for (a different MCP server entirely — out of scope, see module docstring).
    """
    if tool_name.endswith("*"):
        return None  # wildcard — prefix-matches at runtime, unaffected by the bug
    match = _PKB_PLUGIN_TOOL_RE.match(tool_name)
    if not match:
        return None  # not a "pkb" aggregator grant — no manifest to check it against
    suffix = match.group("suffix")
    if suffix in PKB_MANIFEST_SUFFIXES:
        return None
    return (
        f"'{tool_name}' does not resolve against the live 'pkb' MCP aggregator "
        f"manifest (checked suffix '{suffix}' against {len(PKB_MANIFEST_SUFFIXES)} "
        "known tools — see scripts/lib/mcp_tool_manifest.py for provenance/refresh "
        "instructions; this is the aops_b580e332 single-/double-`pkb__`-prefix "
        "defect class)"
    )
