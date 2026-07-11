"""Tests for the agent-frontmatter-vs-live-MCP-manifest guard (aops_35b7dce7).

Catches the aops_b580e332 defect class: an agent's `tools:` frontmatter naming
an explicit MCP tool that LOOKS plausible (e.g. `mcp__plugin_aops-pkb_pkb__get_task`)
but does not resolve against what the plugin's MCP server actually exposes at
runtime (the real, live, callable name carries the aggregator's inner `pkb__`
sub-server segment too: `mcp__plugin_aops-pkb_pkb__pkb__get_task`).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_build():
    """Load scripts/build.py, resolving its internal sys.path setup."""
    for p in (str(SCRIPTS_DIR), str(SCRIPTS_DIR / "lib"), str(REPO_ROOT / "aops-core")):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location("_build_testmodule", SCRIPTS_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_build = _load_build()

sys.path.insert(0, str(SCRIPTS_DIR / "lib"))
import mcp_tool_manifest  # noqa: E402


def _write_agent(agents_dir: Path, name: str, tools_lines: list[str]) -> None:
    agents_dir.mkdir(parents=True, exist_ok=True)
    body = "\n".join(["tools:"] + [f"  - {t}" for t in tools_lines])
    (agents_dir / name).write_text(f"---\n{body}\n---\n\n# {name}\n")


class TestManifestModule:
    def test_known_double_prefix_resolves(self):
        assert (
            mcp_tool_manifest.classify_explicit_mcp_tool("mcp__plugin_aops-pkb_pkb__pkb__get_task")
            is None
        )

    def test_stale_single_prefix_flagged(self):
        error = mcp_tool_manifest.classify_explicit_mcp_tool("mcp__plugin_aops-pkb_pkb__get_task")
        assert error is not None
        assert "get_task" in error

    def test_wildcard_not_flagged(self):
        assert mcp_tool_manifest.classify_explicit_mcp_tool("mcp__plugin_aops-pkb_pkb__*") is None

    def test_unrelated_server_not_flagged(self):
        # No manifest is maintained for outlook/zot/playwright — out of scope,
        # so an explicit grant there must not false-positive.
        assert mcp_tool_manifest.classify_explicit_mcp_tool("mcp__outlook__list_events") is None

    def test_unknown_suffix_under_known_prefix_flagged(self):
        error = mcp_tool_manifest.classify_explicit_mcp_tool(
            "mcp__plugin_aops-pkb_pkb__pkb__totally_made_up_tool"
        )
        assert error is not None


class TestAssertAgentFrontmatterMcpToolsResolve:
    def test_raises_on_stale_single_prefix(self, tmp_path):
        _write_agent(
            tmp_path / "pkg" / "agents",
            "bad.md",
            ["Read", "mcp__plugin_aops-pkb_pkb__get_task"],
        )
        with pytest.raises(RuntimeError) as exc_info:
            _build._assert_agent_frontmatter_mcp_tools_resolve(tmp_path)
        assert "bad.md" in str(exc_info.value)
        assert "get_task" in str(exc_info.value)

    def test_passes_on_correct_double_prefix(self, tmp_path):
        _write_agent(
            tmp_path / "pkg" / "agents",
            "good.md",
            ["Read", "mcp__plugin_aops-pkb_pkb__pkb__get_task"],
        )
        _build._assert_agent_frontmatter_mcp_tools_resolve(tmp_path)  # must not raise

    def test_wildcard_grant_never_flagged(self, tmp_path):
        _write_agent(
            tmp_path / "pkg" / "agents",
            "wild.md",
            ["Read", "mcp__plugin_aops-pkb_pkb__*"],
        )
        _build._assert_agent_frontmatter_mcp_tools_resolve(tmp_path)  # must not raise

    def test_covers_every_package_agents_dir(self, tmp_path):
        """Not just one package — any `<root>/*/agents/*.md` is scanned."""
        _write_agent(
            tmp_path / "aops-core" / "agents",
            "a.md",
            ["mcp__plugin_aops-pkb_pkb__get_task"],
        )
        _write_agent(
            tmp_path / "aops-pkb" / "agents",
            "b.md",
            ["mcp__plugin_aops-pkb_pkb__get_task"],
        )
        with pytest.raises(RuntimeError) as exc_info:
            _build._assert_agent_frontmatter_mcp_tools_resolve(tmp_path)
        assert "aops-core/agents/a.md" in str(exc_info.value)
        assert "aops-pkb/agents/b.md" in str(exc_info.value)

    def test_non_mcp_and_builtin_tools_ignored(self, tmp_path):
        _write_agent(
            tmp_path / "pkg" / "agents",
            "builtins.md",
            ["Read", "Write", "Bash", "Skill", "Agent"],
        )
        _build._assert_agent_frontmatter_mcp_tools_resolve(tmp_path)  # must not raise

    def test_real_repo_tree_is_clean(self):
        """Guards against regression: the real, tracked agent frontmatter across
        every package must resolve against the live manifest right now."""
        _build._assert_agent_frontmatter_mcp_tools_resolve(REPO_ROOT)
