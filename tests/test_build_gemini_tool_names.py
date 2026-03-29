"""Test that Gemini dist has no double-underscore MCP tool names.

Gemini CLI rejects tool names containing double underscores (mcp__server__tool).
The build must translate these to single underscores (mcp_server_tool) everywhere:
agents, skills, commands, lib, and all markdown files.

This runs the actual build_aops_core() and scans the output — no mocks.
"""

import re
from pathlib import Path

import pytest

# Pattern: mcp__<anything>__<anything> — the invalid double-underscore form
# Negative lookbehind for backtick-fence or code-comment context isn't needed;
# if the string appears anywhere in the dist, Gemini will try to resolve it.
MCP_DOUBLE_UNDERSCORE = re.compile(r"mcp__[a-zA-Z0-9_-]+__[a-zA-Z0-9_-]+")

AOPS_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def gemini_dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the real build and return the Gemini dist directory."""
    from scripts.build import build_aops_core

    dist_root = tmp_path_factory.mktemp("dist")
    build_aops_core(
        aops_root=AOPS_ROOT,
        dist_root=dist_root,
        aca_data_path="/tmp/fake-aca-data",
        platform="gemini",
        version="0.0.0-test",
    )
    dist_dir = dist_root / "aops-gemini"
    assert dist_dir.exists(), f"Build did not produce {dist_dir}"
    return dist_dir


def _collect_md_files(dist_dir: Path) -> list[Path]:
    """Collect all .md files in the dist."""
    return sorted(dist_dir.rglob("*.md"))


def _collect_py_files(dist_dir: Path) -> list[Path]:
    """Collect all .py files in the dist."""
    return sorted(dist_dir.rglob("*.py"))


def _find_violations(filepath: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, matched_tool_name, line_text) for violations."""
    violations = []
    text = filepath.read_text()
    for i, line in enumerate(text.splitlines(), 1):
        for match in MCP_DOUBLE_UNDERSCORE.finditer(line):
            violations.append((i, match.group(), line.strip()))
    return violations


class TestGeminiDistToolNames:
    """All .md files in the Gemini dist must use single-underscore MCP tool names."""

    def test_no_double_underscore_mcp_in_markdown(self, gemini_dist: Path) -> None:
        """No .md file in the Gemini dist should contain mcp__*__* tool names."""
        md_files = _collect_md_files(gemini_dist)
        assert md_files, "No .md files found in Gemini dist — build may have failed"

        all_violations: dict[str, list[tuple[int, str, str]]] = {}
        for md_file in md_files:
            violations = _find_violations(md_file)
            if violations:
                rel = md_file.relative_to(gemini_dist)
                all_violations[str(rel)] = violations

        if all_violations:
            report_lines = ["Gemini dist contains invalid double-underscore MCP tool names:\n"]
            for filepath, violations in sorted(all_violations.items()):
                report_lines.append(f"  {filepath}:")
                for line_no, tool_name, _line_text in violations[:3]:
                    report_lines.append(f"    L{line_no}: {tool_name}")
                if len(violations) > 3:
                    report_lines.append(f"    ... and {len(violations) - 3} more")
            total = sum(len(v) for v in all_violations.values())
            report_lines.append(
                f"\n{total} violations across {len(all_violations)} files. "
                "translate_tool_calls() must be applied to all Gemini dist .md files, not just agents."
            )
            pytest.fail("\n".join(report_lines))

    def test_no_double_underscore_mcp_in_python(self, gemini_dist: Path) -> None:
        """Python files (hooks, lib) are platform-shared — just flag if present."""
        py_files = _collect_py_files(gemini_dist)
        if not py_files:
            pytest.skip("No .py files in Gemini dist")

        # Python files like gate_config.py legitimately list both formats for matching
        # (e.g. a translation table that maps double→single). Only flag a .py file if
        # it contains double-underscore MCP names but ZERO Gemini-format equivalents
        # — that indicates an untranslated file, not a legitimate dual-format reference.
        # Gemini equivalents: mcp_server_tool (single-underscore), pkb:tool (colon
        # format), bare tool names, normalization infra (_PKB_PREFIX_RE), or
        # conceptual_terms (reference strings in audit scripts, not tool invocations).
        gemini_or_reference = re.compile(
            r"mcp_(?!_)[a-zA-Z0-9-]+_[a-zA-Z0-9_-]+"  # mcp_server_tool
            r"|pkb:[a-zA-Z0-9_-]+"  # pkb:tool colon format
            r"|_PKB_PREFIX"  # normalization infrastructure
            r"|conceptual_terms"  # exclusion list context (audit scripts)
            r'|"(?:update_task|complete_task|complete_tasks|create_task|list_tasks|reindex)"'
        )

        flagged: list[str] = []
        for py_file in py_files:
            text = py_file.read_text()
            has_double = bool(MCP_DOUBLE_UNDERSCORE.search(text))
            has_context = bool(gemini_or_reference.search(text))
            if has_double and not has_context:
                rel = py_file.relative_to(gemini_dist)
                flagged.append(str(rel))

        assert not flagged, (
            "Python files contain double-underscore MCP tool names with no single-underscore "
            "equivalents (likely untranslated):\n" + "\n".join(f"  {f}" for f in flagged)
        )

    def test_agents_have_valid_tool_names(self, gemini_dist: Path) -> None:
        """Agent frontmatter tools must not contain double underscores."""
        import yaml

        agents_dir = gemini_dist / "agents"
        if not agents_dir.exists():
            pytest.skip("No agents directory in dist")

        bad_agents: dict[str, list[str]] = {}
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            frontmatter = yaml.safe_load(parts[1])
            if not frontmatter:
                continue
            tools = frontmatter.get("tools", [])
            if isinstance(tools, str):
                tools = [t.strip() for t in tools.split(",")]
            bad_tools = [t for t in tools if MCP_DOUBLE_UNDERSCORE.search(t)]
            if bad_tools:
                bad_agents[agent_file.name] = bad_tools

        assert not bad_agents, (
            f"Agent frontmatter contains double-underscore tool names: {bad_agents}"
        )

    def test_skills_have_translated_tool_references(self, gemini_dist: Path) -> None:
        """Skill .md files must have translated tool names — this is the main regression."""
        skills_dir = gemini_dist / "skills"
        if not skills_dir.exists():
            pytest.skip("No skills directory in dist")

        skill_files = sorted(skills_dir.rglob("*.md"))
        assert skill_files, "No .md files in skills directory"

        violations_by_file: dict[str, int] = {}
        for md_file in skill_files:
            violations = _find_violations(md_file)
            if violations:
                rel = md_file.relative_to(gemini_dist)
                violations_by_file[str(rel)] = len(violations)

        if violations_by_file:
            summary = "\n".join(
                f"  {f}: {n} violations" for f, n in sorted(violations_by_file.items())
            )
            total = sum(violations_by_file.values())
            pytest.fail(
                f"Skills contain {total} double-underscore MCP tool names "
                f"across {len(violations_by_file)} files:\n{summary}\n\n"
                "build.py applies translate_tool_calls() to agents but not skills."
            )
