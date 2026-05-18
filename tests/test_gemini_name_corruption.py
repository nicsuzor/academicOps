"""Guard against Gemini-form tool names escaping into source files.

Root cause: build.py transforms canonical Claude-form tool names
(mcp__server__tool, Read, Edit) into Gemini-form names (mcp_server_tool,
read_file, replace) for the Gemini distribution. Gemini polecat workers
see only the Gemini catalog, so when they edit SKILL.md or agent files
they silently write back Gemini-form names into source — corrupting the
canonical forms that Claude workers and the build pipeline depend on.

This test catches the corruption before it merges. See issue #1128.
"""

from pathlib import Path

import pytest

from scripts.audit_agent_compliance import (
    check_gemini_names,
    find_gemini_mcp_names_in_text,
    is_gemini_tool_name,
)

REPO_ROOT = Path(__file__).parent.parent.resolve()


# ── Unit: is_gemini_tool_name ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name,expected",
    [
        # Canonical forms — must NOT trigger
        ("mcp__plugin_aops-core_pkb__get_task", False),
        ("mcp__pkb__search", False),
        ("mcp__playwright__browser_navigate", False),
        ("Read", False),
        ("Edit", False),
        ("Bash", False),
        ("Grep", False),
        ("WebFetch", False),
        # Gemini MCP forms (__ → _) — must trigger
        ("mcp_plugin_aops-core_pkb_get_task", True),
        ("mcp_pkb_search", True),
        ("mcp_pkb_complete_task", True),
        ("mcp_playwright_browser_navigate", True),
        # Gemini built-in aliases — must trigger
        ("read_file", True),
        ("write_file", True),
        ("replace", True),
        ("grep_search", True),
        ("run_shell_command", True),
        ("activate_skill", True),
        ("web_fetch", True),
        ("google_web_search", True),
    ],
)
def test_is_gemini_tool_name(name: str, expected: bool) -> None:
    assert is_gemini_tool_name(name) == expected, (
        f"is_gemini_tool_name({name!r}) should be {expected}"
    )


# ── Unit: find_gemini_mcp_names_in_text ──────────────────────────────────────


def test_find_gemini_mcp_names_in_text_detects_corrupted_name() -> None:
    body = "Call mcp_pkb_complete_task to close the task."
    matches = find_gemini_mcp_names_in_text(body)
    assert "pkb" in matches[0] or "mcp_pkb_complete_task".startswith("mcp_")
    # At least one match returned
    assert len(matches) >= 1


def test_find_gemini_mcp_names_in_text_ignores_canonical() -> None:
    body = "Use mcp__pkb__search and mcp__plugin_aops-core_pkb__get_task."
    assert find_gemini_mcp_names_in_text(body) == []


def test_find_gemini_mcp_names_in_text_ignores_short_mcp_words() -> None:
    # "mcp_servers" is one segment — not a tool name
    body = "The mcpServers config key and mcp_servers field."
    assert find_gemini_mcp_names_in_text(body) == []


# ── Integration: no violations in current source ──────────────────────────────


def test_no_gemini_names_in_source() -> None:
    """Fail the build if any Gemini-form tool names are found in aops-core/**/*.md.

    This is the CI gate for issue #1128. A Gemini polecat worker edits source
    files using its own (Gemini) tool catalog and can silently write back
    names like mcp_pkb_complete_task instead of mcp__pkb__complete_task.
    This test catches that before merge.
    """
    violations = check_gemini_names(REPO_ROOT)
    if violations:
        lines = [
            f"  {file_path} [{location}]: {name!r}" for file_path, location, name in violations
        ]
        pytest.fail(
            f"{len(violations)} Gemini-form tool name(s) found in source "
            f"(build.py transform leaked back into aops-core):\n" + "\n".join(lines)
        )
