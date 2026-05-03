"""Regression test: rbg agent tool list must include PKB read tools.

Prevents accidental removal of tools that rbg (The Judge) needs to read
PKB context before issuing a verdict.

PR #895 removed the PKB write tools (append, complete_task) that were added
in #891 for the combined-lenses verdict-filing approach. RBG is now
axiom-compliance only and returns verdicts to its caller rather than filing
them to tasks directly.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RBG_MD = REPO_ROOT / "aops-core" / "agents" / "rbg.md"

REQUIRED_TOOLS = [
    "mcp__plugin_aops-core_pkb__search",
    "mcp__plugin_aops-core_pkb__get_task",
    "mcp__plugin_aops-core_pkb__get_document",
    "mcp__plugin_aops-core_pkb__pkb_context",
]


def _parse_rbg_tools() -> list[str]:
    text = RBG_MD.read_text()
    parts = text.split("---")
    fm = yaml.safe_load(parts[1])
    return fm.get("tools", [])


def test_rbg_tool_list_parses():
    tools = _parse_rbg_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_rbg_includes_pkb_read_tools():
    tools = _parse_rbg_tools()
    missing = [t for t in REQUIRED_TOOLS if t not in tools]
    assert not missing, f"rbg is missing PKB read tools: {missing}"


def test_rbg_excludes_pkb_write_tools():
    """After PR #895 reverted the combined-lenses approach, rbg must NOT include
    the PKB write tools that were used for verdict filing under that approach."""
    tools = _parse_rbg_tools()
    write_tools = [
        "mcp__plugin_aops-core_pkb__append",
        "mcp__plugin_aops-core_pkb__complete_task",
    ]
    unexpected = [t for t in write_tools if t in tools]
    assert not unexpected, (
        f"rbg has PKB write tools that should have been removed in PR #895 "
        f"(combined-lenses verdict filing reverted): {unexpected}"
    )
