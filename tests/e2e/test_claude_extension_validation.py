"""End-to-end validation of the built Claude Code extension.

This file is the release-certification gate for `dist/aops-claude/`. It covers
every codepath Claude Code exercises when it loads our extension, so that
`claude agent list` prints a clean list on a freshly installed `aops-core` —
no schema errors, no bad tool names, no variable leakage from the Gemini build.

Two tiers, side-by-side in one file so contributors can see the whole picture:

* **Fast tier** (no Claude binary required) — pure-Python parses of the built
  artefacts under `dist/aops-claude/`. Runs every PR.
  - `TestDistStructure`: required files present (plugin.json, .mcp.json, hooks.json).
  - `TestPluginJson`: manifest has required fields; no Gemini variable leakage.
  - `TestMcpJson`: valid MCP server config; `${CLAUDE_PLUGIN_ROOT}` used throughout.
  - `TestHooksJson`: hook event names are valid Claude Code events; no Gemini leakage.
  - `TestAgentSchema`: `tools:` value is comma-separated string with PascalCase or
    `mcp__` names; no Gemini-only tool names leak through the build transform.
  - `TestRouterToolNames`: hook router literals don't reference nonexistent tools.

* **Slow tier** (`-m slow`, requires the `claude` binary on `PATH`) —
  `TestClaudeCliSmoke` confirms the binary can start and sees the extension.
  Note: Claude Code has no `claude extensions validate` equivalent, so the
  fast-tier static analysis is the primary correctness gate.

Analogous to `test_gemini_extension_validation.py`; the key structural
difference is that the Gemini build uses snake_case tool names and a YAML list
for `tools:`, while the Claude build uses PascalCase and a comma-separated
string.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST = REPO_ROOT / "dist" / "aops-claude"

# Claude Code built-in tool names. Anything else in an agent's `tools:` string
# must be an MCP tool prefixed with `mcp__`.
CLAUDE_BUILTIN_TOOLS = frozenset(
    {
        # File operations
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        # Shell
        "Bash",
        # Skills / Agents
        "Skill",
        "Task",
        "Agent",
        # Web
        "WebFetch",
        "WebSearch",
        # Notebook
        "NotebookEdit",
        "NotebookRead",
        # Task management
        "TodoWrite",
        "TodoRead",
        # Interaction
        "AskUserQuestion",
        "ExitPlanMode",
        "ToolSearch",
        # Browser/Playwright passthrough (lowercase, not remapped by build)
        "browser_navigate",
        "browser_snapshot",
        "browser_take_screenshot",
        "browser_click",
        "browser_wait_for",
        "browser_evaluate",
        "browser_type",
        "browser_resize",
    }
)

# Gemini-only tool names that should NOT appear in the Claude build.
# If any of these appear in a built agent's `tools:` field, the build transform
# in `scripts/build.py::transform_agent_for_platform` failed to remap them.
GEMINI_ONLY_TOOLS = frozenset(
    {
        "read_file",
        "write_file",
        "replace",
        "run_shell_command",
        "grep_search",
        "web_fetch",
        "google_web_search",
        "save_memory",
        "ask_user",
        "enter_plan_mode",
        "complete_task",
        "write_todos",
        "update_topic",
        "activate_skill",
        "list_directory",
    }
)

# Valid Claude Code hook event names (from the Claude Code hooks schema).
CLAUDE_HOOK_EVENTS = frozenset(
    {
        "SessionStart",
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "SessionEnd",
        "PreCompact",
        "Notification",
    }
)

# Gemini path variable that must NOT appear in any Claude build artifact.
GEMINI_PATH_VAR = "${extensionPath}"
CLAUDE_PATH_VAR = "${CLAUDE_PLUGIN_ROOT}"


def _require_dist() -> None:
    """Skip the test cleanly if the extension has not been built yet."""
    if not DIST.exists():
        pytest.skip(
            f"{DIST} not built. Run `make build` (or `uv run python scripts/build.py`) first."
        )


def _claude_available() -> bool:
    return shutil.which("claude") is not None


def _iter_agent_files() -> list[Path]:
    return sorted((DIST / "agents").glob("*.md")) if (DIST / "agents").exists() else []


def _parse_frontmatter(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    _, fm, _ = parts
    return yaml.safe_load(fm) or {}


# ---------------------------------------------------------------------------
# Fast tier — runs on every PR, no Claude binary required.
# ---------------------------------------------------------------------------


class TestDistStructure:
    """The built extension has every file Claude Code needs to load it."""

    def test_dist_exists(self):
        _require_dist()
        assert DIST.is_dir(), "dist/aops-claude/ missing — run `make build` first"

    def test_plugin_json_present(self):
        _require_dist()
        assert (DIST / ".claude-plugin" / "plugin.json").is_file(), (
            ".claude-plugin/plugin.json missing from dist/aops-claude/. "
            "Claude Code will not recognise the extension."
        )

    def test_mcp_json_present(self):
        _require_dist()
        assert (DIST / ".mcp.json").is_file(), (
            ".mcp.json missing from dist/aops-claude/. "
            "MCP servers declared in plugin.json will not be registered."
        )

    def test_hooks_json_present(self):
        _require_dist()
        assert (DIST / "hooks" / "hooks.json").is_file(), (
            "hooks/hooks.json missing from dist/aops-claude/. "
            "No lifecycle hooks will fire after install."
        )

    def test_agents_directory_present(self):
        _require_dist()
        assert (DIST / "agents").is_dir(), "agents/ directory missing from dist/aops-claude/."

    def test_claude_md_imports_resolve(self):
        """@import lines in CLAUDE.md must point to real files under the extension."""
        _require_dist()
        claude_md = DIST / "CLAUDE.md"
        if not claude_md.is_file():
            pytest.skip("No CLAUDE.md in dist/aops-claude/")
        pattern = re.compile(r"^@([a-zA-Z0-9_/.-]+)\b", re.MULTILINE)
        broken = [
            m.group(1)
            for m in pattern.finditer(claude_md.read_text())
            if not (claude_md.parent / m.group(1)).exists()
        ]
        assert not broken, f"CLAUDE.md references missing files: {broken}"


class TestPluginJson:
    """`.claude-plugin/plugin.json` is well-formed and correct for Claude Code."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    def _load(self) -> dict:
        path = DIST / ".claude-plugin" / "plugin.json"
        if not path.is_file():
            pytest.skip("plugin.json not built")
        return json.loads(path.read_text())

    def test_valid_json(self):
        self._load()

    def test_required_fields(self):
        manifest = self._load()
        for field in ("name", "version", "description"):
            assert manifest.get(field), (
                f"plugin.json missing required field {field!r}. "
                f"Claude Code will reject the extension on install."
            )

    def test_mcp_servers_field_present(self):
        manifest = self._load()
        assert "mcpServers" in manifest, (
            "plugin.json missing 'mcpServers' field. "
            "MCP servers will not be auto-registered on install."
        )

    def test_no_gemini_variable_leakage(self):
        """`${extensionPath}` must not appear; Claude Code uses `${CLAUDE_PLUGIN_ROOT}`."""
        text = (DIST / ".claude-plugin" / "plugin.json").read_text()
        assert GEMINI_PATH_VAR not in text, (
            f"plugin.json contains Gemini path variable '{GEMINI_PATH_VAR}'. "
            f"Replace with '{CLAUDE_PATH_VAR}'."
        )


class TestMcpJson:
    """`.mcp.json` declares MCP servers with Claude Code-compatible paths."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    def _load(self) -> dict:
        path = DIST / ".mcp.json"
        if not path.is_file():
            pytest.skip(".mcp.json not built")
        return json.loads(path.read_text())

    def test_valid_json(self):
        self._load()

    def test_has_mcp_servers_key(self):
        data = self._load()
        assert "mcpServers" in data, (
            ".mcp.json missing top-level 'mcpServers' key. "
            "Claude Code will not register any MCP servers."
        )

    def test_server_entries_have_required_fields(self):
        servers = self._load().get("mcpServers", {})
        missing = [
            name
            for name, cfg in servers.items()
            if not isinstance(cfg, dict) or "command" not in cfg
        ]
        assert not missing, f"MCP server entries missing 'command' field: {missing}"

    def test_no_gemini_variable_leakage(self):
        """`${extensionPath}` must not appear; Claude Code uses `${CLAUDE_PLUGIN_ROOT}`."""
        text = (DIST / ".mcp.json").read_text()
        assert GEMINI_PATH_VAR not in text, (
            f".mcp.json contains Gemini path variable '{GEMINI_PATH_VAR}'. "
            f"Replace with '{CLAUDE_PATH_VAR}'."
        )


class TestHooksJson:
    """`.hooks/hooks.json` uses valid Claude Code event names and no Gemini artifacts."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    def _load(self) -> dict:
        path = DIST / "hooks" / "hooks.json"
        if not path.is_file():
            pytest.skip("hooks/hooks.json not built")
        return json.loads(path.read_text())

    def test_valid_json(self):
        self._load()

    def test_has_hooks_key(self):
        data = self._load()
        assert "hooks" in data, (
            "hooks.json missing top-level 'hooks' key. "
            "Claude Code will not register any lifecycle hooks."
        )

    def test_event_names_are_known_claude_events(self):
        """All top-level event keys must be valid Claude Code hook events."""
        hooks = self._load().get("hooks", {})
        unknown = [
            ev for ev in hooks if ev not in CLAUDE_HOOK_EVENTS and not ev.endswith("-disabled")
        ]
        assert not unknown, (
            f"hooks.json contains unknown Claude Code event names: {unknown}. "
            f"Valid events: {sorted(CLAUDE_HOOK_EVENTS)}"
        )

    def test_hook_entries_have_type_field(self):
        """Each individual hook entry must have a 'type' field."""
        hooks = self._load().get("hooks", {})
        missing: list[str] = []
        for event, hook_groups in hooks.items():
            if event.endswith("-disabled"):
                continue
            for group in hook_groups if isinstance(hook_groups, list) else []:
                for entry in group.get("hooks", []) if isinstance(group, dict) else []:
                    if "type" not in entry:
                        missing.append(f"{event}: {entry}")
        assert not missing, f"Hook entries missing 'type' field: {missing}"

    def test_no_gemini_variable_leakage(self):
        """`${extensionPath}` must not appear in any hook command string."""
        text = (DIST / "hooks" / "hooks.json").read_text()
        assert GEMINI_PATH_VAR not in text, (
            f"hooks.json contains Gemini path variable '{GEMINI_PATH_VAR}'. "
            f"Replace with '{CLAUDE_PATH_VAR}'."
        )


class TestAgentSchema:
    """Every built agent uses Claude Code tool format (comma-separated PascalCase string)."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_tools_field_is_string(self, agent_file: Path):
        """Claude Code requires `tools:` to be a comma-separated string, not a YAML list.

        Regression: if `scripts/build.py::transform_agent_for_platform` is not
        called during the Claude build, tools stays as a YAML list and Claude Code
        silently ignores the tool declarations.
        """
        fm = _parse_frontmatter(agent_file)
        tools = fm.get("tools")
        if tools is None:
            return
        assert isinstance(tools, str), (
            f"{agent_file.name}: 'tools:' is a {type(tools).__name__}, not a string. "
            f"The build transform in scripts/build.py::transform_agent_for_platform "
            f"was not applied. Claude Code requires a comma-separated string."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_tool_names_are_valid_claude_format(self, agent_file: Path):
        """Each tool is a Claude builtin (PascalCase) or MCP tool (`mcp__` prefix)."""
        fm = _parse_frontmatter(agent_file)
        tools_raw = fm.get("tools", "")
        if not tools_raw:
            return
        tools = [t.strip() for t in str(tools_raw).split(",") if t.strip()]
        bad = [t for t in tools if t not in CLAUDE_BUILTIN_TOOLS and not t.startswith("mcp__")]
        assert not bad, (
            f"{agent_file.name}: tool names not in Claude Code format: {bad}. "
            f"Each tool must be a PascalCase builtin or 'mcp__server__tool' format. "
            f"Fix scripts/build.py::transform_agent_for_platform."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_no_gemini_tool_names_leaked(self, agent_file: Path):
        """Gemini-only snake_case tool names must not appear in the Claude build.

        Regression guard: if the build accidentally uses the Gemini code path,
        tool names like `read_file` or `activate_skill` end up in agents and
        Claude Code rejects them with 'Invalid tool name'.
        """
        fm = _parse_frontmatter(agent_file)
        tools_raw = fm.get("tools", "")
        if not tools_raw:
            return
        tools = {t.strip() for t in str(tools_raw).split(",") if t.strip()}
        leaks = tools & GEMINI_ONLY_TOOLS
        assert not leaks, (
            f"{agent_file.name}: Gemini-only tool names present in Claude build: "
            f"{sorted(leaks)}. Fix scripts/build.py::transform_agent_for_platform."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_no_gemini_variable_in_body(self, agent_file: Path):
        """`${extensionPath}` must not appear in agent body (Claude uses `${CLAUDE_PLUGIN_ROOT}`)."""
        text = agent_file.read_text(encoding="utf-8")
        assert GEMINI_PATH_VAR not in text, (
            f"{agent_file.name}: contains Gemini path variable '{GEMINI_PATH_VAR}'. "
            f"The build translate_tool_calls() step was not applied."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_required_fields(self, agent_file: Path):
        fm = _parse_frontmatter(agent_file)
        for field in ("name", "description"):
            assert fm.get(field), f"{agent_file.name}: missing required frontmatter field {field!r}"


class TestRouterToolNames:
    """Hook router literals don't reference nonexistent tool names.

    Claude Code records tool calls in its internal logs. If our hooks emit
    a tool name that doesn't exist, downstream tooling that parses those logs
    (policy checkers, audit scripts) will see spurious unknown-tool entries.
    """

    def test_router_has_no_known_typos(self):
        _require_dist()
        router = DIST / "hooks" / "router.py"
        if not router.is_file():
            pytest.skip("no router.py in dist/aops-claude/hooks/")
        text = router.read_text()
        known_typos = {
            "complete_tasks": "complete_task",
            "mcp__pkb__complete_tasks": "mcp__pkb__complete_task",
        }
        offenders = {
            bad: good
            for bad, good in known_typos.items()
            if re.search(r"\b" + re.escape(bad) + r"\b", text)
        }
        assert not offenders, (
            f"Router contains tool-name typos: {offenders}. "
            f"These will produce unknown-tool warnings in Claude Code logs."
        )


# ---------------------------------------------------------------------------
# Slow tier — requires the claude CLI.
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
class TestClaudePluginValidate:
    """Ground truth: `claude plugin validate --strict` passes on the built dist.

    This is the Claude Code equivalent of `gemini extensions validate` — it
    validates the plugin manifest, agent schemas, skill metadata, and rejects
    unknown fields under --strict. This is the definitive gate: whatever Claude
    Code rejects at install time, this catches before release.
    """

    @pytest.fixture(scope="class")
    def validate_output(self) -> subprocess.CompletedProcess[str]:
        _require_dist()
        if not _claude_available():
            pytest.skip("claude CLI not on PATH")
        return subprocess.run(
            [shutil.which("claude") or "claude", "plugin", "validate", "--strict", str(DIST)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_exits_cleanly(self, validate_output):
        assert validate_output.returncode == 0, (
            f"`claude plugin validate --strict` exited {validate_output.returncode}.\n"
            f"stdout: {validate_output.stdout}\n"
            f"stderr: {validate_output.stderr}"
        )

    def test_no_validation_failed(self, validate_output):
        combined = validate_output.stdout + validate_output.stderr
        assert "Validation failed" not in combined, (
            f"`claude plugin validate --strict` reported failure:\n{combined}"
        )
