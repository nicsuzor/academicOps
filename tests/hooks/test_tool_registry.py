#!/usr/bin/env python3
"""Tests for lib/tool_registry.py — Table 2 SSoT (RUNTIME tool recognition).

Covers:
- FAITHFULNESS: the registry's generated (name -> category) never disagrees with
  the hand-maintained ``TOOL_CATEGORIES`` (the registry is additive, not a fork).
- agy RUNTIME recognition gap (the P1b correctness payload):
  * agy native tool names categorize correctly (read/write/always/infra).
  * ``invoke_subagent`` is a spawn tool and its NESTED subagent type is extracted.
  * dispatching a compliance agent via ``invoke_subagent`` bypasses gates
    (get_tool_category -> infrastructure) instead of being mis-gated as write.
  * ``call_mcp_tool`` is unwrapped so agy MCP/PKB calls classify by the WRAPPED
    tool (PKB -> infrastructure, Zotero -> read_only) rather than the write default.
  * agy interaction tools (ask_question/ask_permission) are never-block.
"""

import sys
from pathlib import Path

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib import tool_registry  # noqa: E402
from lib.tool_categories import (  # noqa: E402
    TOOL_CATEGORIES,
    extract_subagent_type,
    get_tool_category,
    is_never_block,
)

pytest_plugins: list[str] = []


# ---------------------------------------------------------------------------
# Faithfulness: registry never disagrees with the hand-maintained categories.
# ---------------------------------------------------------------------------
def test_registry_category_index_self_consistent():
    """A tool name appearing on two specs must carry the SAME category."""
    seen: dict[str, str] = {}
    for spec in tool_registry.REGISTRY:
        for name in (spec.claude, spec.gemini, spec.agy):
            if not name:
                continue
            if name in seen:
                assert seen[name] == spec.category, (
                    f"{name!r} categorized as both {seen[name]!r} and {spec.category!r}"
                )
            seen[name] = spec.category


def test_registry_agrees_with_tool_categories():
    """Every registry name already present in TOOL_CATEGORIES must be in the SAME
    category — the merge is additive, never a silent recategorization."""
    reverse = {tool: cat for cat, tools in TOOL_CATEGORIES.items() for tool in tools}
    for name, category in tool_registry.RUNTIME_NAME_TO_CATEGORY.items():
        if name in reverse:
            assert reverse[name] == category, (
                f"registry says {name!r} is {category!r} but TOOL_CATEGORIES says {reverse[name]!r}"
            )


def test_registry_names_merged_into_tool_categories():
    """After the merge, every registry name is resolvable via get_tool_category."""
    for name, category in tool_registry.RUNTIME_NAME_TO_CATEGORY.items():
        assert get_tool_category(name) == category, f"{name!r} did not resolve to {category!r}"


# ---------------------------------------------------------------------------
# agy native vocabulary categorizes correctly (the gap this task closes).
# ---------------------------------------------------------------------------
def test_agy_write_tools():
    for name in (
        "run_command",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ):
        assert get_tool_category(name) == "write", name


def test_agy_read_tools():
    for name in (
        "view_file",
        "grep_search",
        "list_dir",
        "search_web",
        "read_url_content",
        "list_resources",
    ):
        assert get_tool_category(name) == "read_only", name


def test_agy_interaction_tools_never_block():
    for name in ("ask_question", "ask_permission"):
        assert get_tool_category(name) == "always_available", name
        assert is_never_block(name), f"{name} must be never-block"


def test_agy_control_tools_infrastructure():
    for name in ("manage_task", "schedule"):
        assert get_tool_category(name) == "infrastructure", name


# ---------------------------------------------------------------------------
# invoke_subagent: spawn recognition + nested type extraction.
# ---------------------------------------------------------------------------
def test_invoke_subagent_is_spawn():
    # No compliance target -> generic spawn category (not the write default).
    ti = {"Subagents": [{"Prompt": "do x", "Role": "Fetcher", "TypeName": "research"}]}
    assert get_tool_category("invoke_subagent", ti) == "spawn"


def test_invoke_subagent_nested_type_extracted():
    ti = {"Subagents": [{"Prompt": "do x", "Role": "Fetcher", "TypeName": "research"}]}
    sub, is_skill = extract_subagent_type("invoke_subagent", ti)
    assert sub == "research"
    assert is_skill is False


def test_invoke_subagent_nested_type_from_json_string():
    """agy double-encodes args, so Subagents may arrive as a JSON STRING."""
    ti = {"Subagents": '[{"Prompt":"x","Role":"r","TypeName":"marsha"}]'}
    sub, _ = extract_subagent_type("invoke_subagent", ti)
    assert sub == "marsha"


def test_invoke_subagent_compliance_agent_bypasses_gates():
    """Dispatching a compliance agent on agy must be infrastructure (never gated),
    exactly as Agent/Task + compliance subagent_type is on Claude."""
    ti = {"Subagents": [{"Prompt": "review", "Role": "Judge", "TypeName": "rbg"}]}
    assert get_tool_category("invoke_subagent", ti) == "infrastructure"


# ---------------------------------------------------------------------------
# call_mcp_tool unwrap: classify by the WRAPPED tool, not the write default.
# ---------------------------------------------------------------------------
def test_call_mcp_tool_pkb_is_infrastructure():
    # double-JSON-encoded values, as agy emits them
    ti = {"ServerName": '"pkb"', "ToolName": '"search"', "Arguments": '"{\\"query\\":\\"x\\"}"'}
    assert get_tool_category("call_mcp_tool", ti) == "infrastructure"


def test_call_mcp_tool_pkb_plain_values():
    ti = {"ServerName": "pkb", "ToolName": "create_task"}
    assert get_tool_category("call_mcp_tool", ti) == "infrastructure"


def test_call_mcp_tool_unwrap_helper():
    assert (
        tool_registry.unwrap_agy_mcp_call(
            "call_mcp_tool", {"ServerName": '"pkb"', "ToolName": '"search"'}
        )
        == "mcp__pkb__search"
    )
    assert tool_registry.unwrap_agy_mcp_call("view_file", {}) is None
    assert tool_registry.unwrap_agy_mcp_call("call_mcp_tool", {}) is None


def test_call_mcp_tool_unknown_server_falls_back_to_write():
    """An unrecognized wrapped MCP tool still gets the conservative write default
    (not a crash) — the unwrap only HELPS recognition, never weakens it."""
    ti = {"ServerName": "totallyunknown", "ToolName": "do_something"}
    assert get_tool_category("call_mcp_tool", ti) == "write"


# ---------------------------------------------------------------------------
# BUILD-NAME PROJECTION faithfulness (§P3b): the build-side tool/agent NAME maps
# were moved out of scripts/build.py into the SSoT here. These frozen literals
# are the regression anchor — the SSoT must keep reproducing EXACTLY what the
# build inline copies produced (deliberately distinct from runtime names: e.g.
# Claude Agent/Task -> activate_skill in build frontmatter).
# ---------------------------------------------------------------------------
_FROZEN_CLAUDE_TO_GEMINI_TOOL = {
    "Read": "read_file",
    "Write": "write_file",
    "Edit": "replace",
    "Glob": "glob",
    "Grep": "grep_search",
    "grep": "grep_search",
    "Bash": "run_shell_command",
    "bash": "run_shell_command",
    "Skill": "activate_skill",
    "Task": "activate_skill",
    "Agent": "activate_skill",
    "AskUserQuestion": "ask_user",
    "ExitPlanMode": "enter_plan_mode",
    "TodoWrite": "write_todos",
    "NotebookEdit": None,
    "WebFetch": "web_fetch",
    "WebSearch": "google_web_search",
    "browser_navigate": "navigate_page",
    "browser_snapshot": "take_snapshot",
    "browser_take_screenshot": "take_screenshot",
    "browser_click": "click",
    "browser_wait_for": "wait_for",
    "browser_evaluate": "evaluate_script",
    "browser_type": "type_text",
    "browser_resize": "resize_page",
}


def test_build_claude_to_gemini_tool_map_frozen():
    assert tool_registry.BUILD_CLAUDE_TO_GEMINI_TOOL == _FROZEN_CLAUDE_TO_GEMINI_TOOL


def test_build_spawn_collapse_distinct_from_runtime():
    """The build collapses Agent/Task to activate_skill, but the RUNTIME registry
    emits invoke_agent/delegate_to_agent — proving the two halves stay distinct."""
    assert tool_registry.BUILD_CLAUDE_TO_GEMINI_TOOL["Agent"] == "activate_skill"
    assert tool_registry.BUILD_CLAUDE_TO_GEMINI_TOOL["Task"] == "activate_skill"
    by_canonical = {s.canonical: s for s in tool_registry.REGISTRY}
    assert by_canonical["Agent"].gemini == "invoke_agent"
    assert by_canonical["Task"].gemini == "delegate_to_agent"


def test_build_to_claude_tool_map_frozen_core():
    m = tool_registry.BUILD_TO_CLAUDE_TOOL
    assert m["read_file"] == "Read"
    assert m["replace"] == "Edit"
    assert m["run_shell_command"] == "Bash"
    assert m["activate_skill"] == "Skill"
    # passthrough identity for already-Claude names
    assert m["Read"] == "Read" and m["Agent"] == "Agent" and m["Task"] == "Task"


def test_build_body_notation_and_spawn_rewrites_frozen():
    gem = tool_registry.BUILD_BODY_TOOL_NOTATION["gemini"]
    assert gem["Read("] == "read_file(" and gem["`Grep`"] == "`grep_search`"
    assert tool_registry.BUILD_BODY_TOOL_NOTATION["claude"] == {}
    assert tool_registry.BUILD_GEMINI_BODY_SPAWN_REWRITES[0] == (
        "Task(subagent_type=",
        "activate_skill(name=",
    )
