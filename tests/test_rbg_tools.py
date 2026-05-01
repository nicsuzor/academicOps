"""Regression test: rbg agent tool list must include PKB write tools.

Prevents accidental removal of tools that rbg (The Judge) needs to write
verdicts back to tasks instead of bouncing them to the caller.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RBG_MD = REPO_ROOT / "aops-core" / "agents" / "rbg.md"

REQUIRED_TOOLS = [
    "mcp__plugin_aops-core_pkb__append",
    "mcp__plugin_aops-core_pkb__complete_task",
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


def test_rbg_includes_pkb_write_tools():
    tools = _parse_rbg_tools()
    missing = [t for t in REQUIRED_TOOLS if t not in tools]
    assert not missing, f"rbg is missing PKB write tools: {missing}"
