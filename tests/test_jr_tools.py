"""Regression test: jr agent tool list must be a superset of planner-required PKB tools.

Prevents accidental removal of tools that planner/remember/sleep/aops skills depend on.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
JR_MD = REPO_ROOT / "aops-core" / "agents" / "jr.md"

# Tools required by the skills jr drives (from planner/remember/sleep/aops allowlists).
REQUIRED_TOOLS = [
    "mcp__plugin_aops-core_pkb__get_task_children",
    "mcp__plugin_aops-core_pkb__decompose_task",
    "mcp__plugin_aops-core_pkb__list_documents",
    "mcp__plugin_aops-core_pkb__search_by_tag",
    "mcp__plugin_aops-core_pkb__delete_memory",
    "mcp__plugin_aops-core_pkb__get_dependency_tree",
    "mcp__plugin_aops-core_pkb__pkb_trace",
    "mcp__plugin_aops-core_pkb__pkb_orphans",
    "mcp__plugin_aops-core_pkb__bulk_reparent",
    "mcp__plugin_aops-core_pkb__find_duplicates",
    "mcp__plugin_aops-core_pkb__batch_merge",
    "mcp__plugin_aops-core_pkb__merge_node",
    "mcp__plugin_aops-core_pkb__batch_reclassify",
    "mcp__plugin_aops-core_pkb__batch_archive",
    "mcp__plugin_aops-core_pkb__batch_update",
]


def _parse_jr_tools() -> list[str]:
    text = JR_MD.read_text()
    parts = text.split("---")
    fm = yaml.safe_load(parts[1])
    return fm.get("tools", [])


def test_jr_tool_list_parses():
    tools = _parse_jr_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_jr_includes_planner_required_tools():
    tools = _parse_jr_tools()
    missing = [t for t in REQUIRED_TOOLS if t not in tools]
    assert not missing, f"jr is missing tools required by planner/skills: {missing}"
