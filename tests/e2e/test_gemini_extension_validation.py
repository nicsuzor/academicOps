"""End-to-end validation of the built Gemini extension.

This file is the release-certification gate for `dist/aops-gemini/`. It covers
every codepath the Gemini CLI exercises when it loads our extension, so that
`gemini --list-extensions` prints a clean banner on a freshly installed
`aops-core` — no `[ExtensionManager] Error`, no `Validation failed`, no
`Policy file warning`.

Two tiers, side-by-side in one file so contributors can see the whole picture:

* **Fast tier** (no Gemini binary required) — pure-Python parses of the built
  artefacts under `dist/aops-gemini/`. Runs every PR.
  - `TestDistStructure`: required files present, `contextFileName` resolves.
  - `TestAgentSchema`: agent frontmatter keys ⊆ Gemini schema; tools are
    builtin or `mcp_*`; no Claude-only leakage (`skills`, `subagents`,
    `mcpServers`, `disallowedTools`, `permissionMode`, `maxTurns`, `effort`,
    `background`, `isolation`).
  - `TestPolicyTomls`: every `toolName` in every shipped TOML policy is a
    known Gemini tool (catches the `complete_tasks` → `complete_task` typo).
  - `TestRouterToolNames`: hook router literals don't reference unknown tools
    that would leak into Gemini's auto-saved policy.

* **Slow tier** (`-m slow`, requires the `gemini` binary on `PATH`) —
  `TestGeminiCliValidate` delegates to `gemini extensions validate`, the
  CLI's own purpose-built linter. This is the ground-truth gate: whatever
  Gemini rejects is what users will see on install. Parses stderr and the
  `Validation failed with the following errors:` block.

Why `gemini extensions validate` is the right probe:

* Non-interactive. No auth, no network, no Docker.
* Exercises the same schema loader used on extension install.
* Prints structured `[ExtensionManager] Error ...` / `Validation failed ...`
  stderr that is stable enough to grep against.

Known quirk (as of gemini 0.38.2): `gemini extensions validate` exits 0 even
when it prints `Extension validation failed.` Tests must grep stderr,
**not** rely on the exit code.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST = REPO_ROOT / "dist" / "aops-gemini"

# Gemini agent frontmatter schema (from scripts/build.py::validate_gemini_agent_schema).
# Keys outside this set cause `Unrecognized key(s) in object: ...` on load.
GEMINI_AGENT_ALLOWED_KEYS = frozenset(
    {
        "name",
        "description",
        "kind",
        "tools",
        "model",
        "temperature",
        "max_turns",
        "timeout_mins",
    }
)

# Claude-Code-only keys that have historically leaked into the Gemini build.
# Listing them explicitly (rather than just negating the allow-list) gives
# better failure messages and acts as a regression ledger.
CLAUDE_ONLY_LEAK_KEYS = frozenset(
    {
        "skills",
        "subagents",
        "mcpServers",
        "disallowedTools",
        "permissionMode",
        "maxTurns",
        "effort",
        "background",
        "isolation",
        "color",
    }
)

# Gemini CLI built-in tool names. Anything else in an agent's `tools:` array
# must be an MCP tool prefixed with `mcp_`.
GEMINI_BUILTIN_TOOLS = frozenset(
    {
        "read_file",
        "write_file",
        "replace",
        "list_directory",
        "glob",
        "grep_search",
        "run_shell_command",
        "web_fetch",
        "google_web_search",
        "save_memory",
        "activate_skill",
        "ask_user",
        "enter_plan_mode",
        "complete_task",
        "write_todos",
        "update_topic",
    }
)

# Stderr patterns that indicate a real regression. Any match fails the test,
# with the offending lines echoed back in the assertion message so CI logs
# are self-explanatory.
CLI_ERROR_PATTERNS = (
    re.compile(r"\[ExtensionManager\] Error"),
    re.compile(r"Validation failed: Agent Definition"),
    re.compile(r"Unrecognized key\(s\) in object"),
    re.compile(r"tools\.\d+: Invalid tool name"),
    re.compile(r"Policy file warning"),
    re.compile(r"Extension validation failed\."),
    re.compile(r"context files .* are missing"),
)


# Source directories whose content determines the dist build output.
# Used by _check_dist_not_stale() to detect a forgotten local rebuild.
_DIST_SOURCE_DIRS = (
    REPO_ROOT / "scripts",
    REPO_ROOT / "templates",
    REPO_ROOT / "aops-core",
)


def _check_dist_not_stale() -> None:
    """Skip with an actionable message if dist is older than any source input.

    Approach: skip-with-warning (not auto-rebuild) so the check is fast,
    transparent, and safe in read-only or CI environments.
    """
    build_stamp = DIST / "gemini-extension.json"
    if not build_stamp.exists():
        return  # Malformed dist — let structural tests fail instead
    dist_mtime = build_stamp.stat().st_mtime

    newest_source: Path | None = None
    newest_mtime = 0.0
    for src_dir in _DIST_SOURCE_DIRS:
        if not src_dir.exists():
            continue
        for p in src_dir.rglob("*"):
            if p.is_file():
                if any(
                    part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
                    for part in p.parts
                ) or p.suffix in (".pyc", ".pyo", ".DS_Store"):
                    continue
                mt = p.stat().st_mtime
                if mt > newest_mtime:
                    newest_mtime = mt
                    newest_source = p

    if newest_source is not None and newest_mtime > dist_mtime:
        rel = newest_source.relative_to(REPO_ROOT)
        pytest.skip(
            f"dist/ is stale: {rel} is newer than {build_stamp.relative_to(REPO_ROOT)}. "
            "Run `make build-dev` to rebuild before running these tests."
        )


def _require_dist() -> None:
    """Skip the test cleanly if the extension has not been built yet or is stale."""
    if not DIST.exists():
        pytest.skip(
            f"{DIST} not built. Run `make build-dev` (or `uv run python scripts/build.py`) first."
        )
    _check_dist_not_stale()


def _gemini_available() -> bool:
    return shutil.which("gemini") is not None


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
# Fast tier — runs on every PR, no Gemini binary required.
# ---------------------------------------------------------------------------


class TestSourceManifestMcpConfig:
    """Source-level pin: gemini-extension.json MCP config is wired for PKB access.

    Validates the source ``gemini-extension.json`` (repo root, not the built dist)
    before any build step. This catches the 2026-04-28 regression where the pkb
    MCP server env block had ``RUST_LOG: warn`` instead of
    ``PKB_MCP_URL: ${PKB_MCP_URL}`` — causing every Gemini polecat to launch
    ``run-mcp.sh`` without a URL, fall back to a broken local stdio path, and
    have zero PKB tools. The silent result: spike polecat output was lost and
    required manual supervisor transcription. Fixed in PR #784.

    Why source *and* dist: the dist is built from the source. A corrupted source
    means every subsequent dist build ships the regression. These tests run on
    every PR without any build step.
    """

    _SOURCE = REPO_ROOT / "templates" / "aops-core.gemini-extension.json"

    @pytest.fixture(autouse=True)
    def _require_source(self):
        if not self._SOURCE.is_file():
            pytest.skip(f"Source gemini-extension.json not found at {self._SOURCE}")

    def _manifest(self) -> dict:
        import json

        return json.loads(self._SOURCE.read_text())

    def test_pkb_mcp_server_registered(self):
        """'pkb' must be registered as an MCP server in the source manifest."""
        m = self._manifest()
        assert "pkb" in m.get("mcpServers", {}), (
            "gemini-extension.json: 'pkb' MCP server not registered. "
            "Gemini polecats need this server to call release_task and persist results. "
            "Regression ledger: PR #784 (2026-04-28)."
        )

    def test_pkb_mcp_url_in_env(self):
        """PKB_MCP_URL must appear in the pkb MCP server env block.

        Regression: 2026-04-28 — the env block had ``RUST_LOG: warn`` instead.
        Without PKB_MCP_URL, run-mcp.sh cannot connect to the remote PKB server
        and falls back to a broken local stdio path. The Gemini session then has
        zero PKB tools — no release_task, no get_task, nothing. Fixed in PR #784.
        """
        m = self._manifest()
        env = m.get("mcpServers", {}).get("pkb", {}).get("env", {})
        assert "PKB_MCP_URL" in env, (
            "gemini-extension.json: PKB_MCP_URL missing from pkb MCP server env. "
            "Without this, run-mcp.sh has no URL and PKB MCP falls back to broken stdio. "
            "Regression ledger: PR #784 (2026-04-28)."
        )

    def test_pkb_mcp_url_is_template(self):
        """PKB_MCP_URL value must expand from the host env, not be hardcoded."""
        m = self._manifest()
        env = m.get("mcpServers", {}).get("pkb", {}).get("env", {})
        val = env.get("PKB_MCP_URL", "")
        assert "${PKB_MCP_URL}" in val, (
            f"gemini-extension.json: PKB_MCP_URL value should be '${{PKB_MCP_URL}}' "
            f"(Gemini extension template substitution), got {val!r}. "
            "The extension must propagate the host env var into the MCP subprocess."
        )

    def test_no_rust_log_in_pkb_env(self):
        """RUST_LOG must not be in the pkb MCP server env (regression guard).

        The 2026-04-28 regression had ``RUST_LOG: warn`` in the env block where
        ``PKB_MCP_URL`` should have been. This test pins the absence of that
        specific misconfig. See PR #784.
        """
        m = self._manifest()
        env = m.get("mcpServers", {}).get("pkb", {}).get("env", {})
        assert "RUST_LOG" not in env, (
            "gemini-extension.json: RUST_LOG found in pkb MCP server env. "
            "This was the root cause of the 2026-04-28 regression (PR #784). "
            "Remove it — RUST_LOG does not belong in the MCP server env block."
        )

    def test_playwright_mcp_server_registered(self):
        """'playwright' must be registered as an MCP server in the source manifest.

        Regression: 2026-05 — playwright MCP server was absent from the manifest.
        Marsha (Gemini version) lists mcp_playwright_browser_* tools, but without
        a registered playwright MCP server every call fails with
        "Tool execution for ... denied by policy." Fixed in PR #<N>.
        """
        m = self._manifest()
        assert "playwright" in m.get("mcpServers", {}), (
            "gemini-extension.json: 'playwright' MCP server not registered. "
            "Gemini polecats running marsha need this server for browser verification. "
            "Regression ledger: 2026-05 (task aops-f7c1a64e)."
        )

    def test_playwright_mcp_command_is_npx(self):
        """playwright MCP server must launch via npx so it works without a
        global npm install in non-Docker environments."""
        m = self._manifest()
        pw = m.get("mcpServers", {}).get("playwright", {})
        assert pw.get("command") == "npx", (
            "gemini-extension.json: playwright MCP server command should be 'npx', "
            f"got {pw.get('command')!r}. Use npx so the package can be resolved "
            "from the npx cache or npm registry without requiring a global install."
        )

    def test_playwright_mcp_uses_headless_flag(self):
        """playwright MCP must run headless — no display available in worker containers."""
        m = self._manifest()
        args = m.get("mcpServers", {}).get("playwright", {}).get("args", [])
        assert "--headless" in args, (
            "gemini-extension.json: playwright MCP server args missing '--headless'. "
            "Worker containers have no display server; headed Chromium will crash."
        )

    def test_playwright_mcp_propagates_browsers_path(self):
        """playwright MCP must propagate PLAYWRIGHT_BROWSERS_PATH so it finds
        the Chromium binary baked into the worker Docker image at /ms-playwright."""
        m = self._manifest()
        env = m.get("mcpServers", {}).get("playwright", {}).get("env", {})
        assert "PLAYWRIGHT_BROWSERS_PATH" in env, (
            "gemini-extension.json: PLAYWRIGHT_BROWSERS_PATH missing from playwright "
            "MCP server env. Without this the MCP server uses the default browser "
            "cache location (~/.cache/ms-playwright) which may not exist in the "
            "container, causing 'browser not found' at session start."
        )


class TestPolechatPlaywrightPolicy:
    """Polecat's playwright ALLOW policy exists and contains the right toolNames.

    This policy is staged to the container's adminPolicyPaths at runtime by
    _replicate_gemini_auth so it overrides any auto-saved deny rules the user
    may have accumulated before the fix in 2026-05.
    """

    _POLICY = REPO_ROOT / "polecat" / "defaults" / "playwright-allow.toml"

    @pytest.fixture(autouse=True)
    def _require_policy(self):
        if not self._POLICY.is_file():
            pytest.fail(
                f"playwright-allow.toml missing at {self._POLICY}. "
                "This file provides defense-in-depth ALLOW rules for playwright MCP tools "
                "in polecat admin policies. It must always exist."
            )

    def _rules(self) -> list[dict]:
        data = tomllib.loads(self._POLICY.read_text())
        return [r for r in data.get("rule", []) if isinstance(r, dict)]

    def test_policy_has_allow_rules(self):
        allow_rules = [r for r in self._rules() if r.get("decision") == "allow"]
        assert allow_rules, (
            f"{self._POLICY.name}: no 'decision = \"allow\"' rules found. "
            "The policy must explicitly allow playwright tools."
        )

    def test_policy_covers_navigate_and_screenshot(self):
        """Core playwright tools used by marsha must be explicitly allowed."""
        all_tool_names: set[str] = set()
        for rule in self._rules():
            tn = rule.get("toolName")
            if isinstance(tn, str):
                all_tool_names.add(tn)
            elif isinstance(tn, list):
                all_tool_names.update(tn)
        required = {"mcp_playwright_browser_navigate", "mcp_playwright_browser_take_screenshot"}
        missing = required - all_tool_names
        assert not missing, (
            f"{self._POLICY.name}: required playwright tools not in ALLOW rules: {missing}. "
            "These are the core tools used by marsha for browser verification."
        )

    def test_policy_tool_names_are_gemini_format(self):
        """All toolNames must use the Gemini single-underscore format (mcp_<server>_<tool>).

        The Gemini policy engine uses mcp_playwright_browser_navigate, not the
        Claude double-underscore form mcp__playwright__browser_navigate.
        """
        bad: list[str] = []
        for rule in self._rules():
            tn = rule.get("toolName")
            names = [tn] if isinstance(tn, str) else (tn if isinstance(tn, list) else [])
            for name in names:
                if isinstance(name, str) and "mcp__" in name:
                    bad.append(name)
        assert not bad, (
            f"{self._POLICY.name}: toolNames use Claude double-underscore format: {bad}. "
            "Gemini policy engine requires single-underscore: mcp_playwright_browser_navigate."
        )

    def test_policy_has_high_priority(self):
        """All rules must have priority >= 950 to override auto-saved user deny rules."""
        low_priority: list[dict] = []
        for rule in self._rules():
            if rule.get("decision") == "allow" and rule.get("priority", 0) < 950:
                low_priority.append(rule)
        assert not low_priority, (
            f"{self._POLICY.name}: ALLOW rules with priority < 950: {low_priority}. "
            "Priority must be >= 950 to override auto-saved deny rules (priority varies)."
        )


class TestDistStructure:
    """The built extension has everything `gemini-extension.json` promises."""

    def test_dist_exists(self):
        _require_dist()
        assert (DIST / "gemini-extension.json").is_file(), (
            f"gemini-extension.json missing from {DIST}"
        )

    def test_context_file_present(self):
        """`contextFileName` (usually GEMINI.md) must exist in the extension root.

        Regression: early April 2026 the build shipped `dist/aops-gemini/`
        without `GEMINI.md`, producing `Extension validation failed: context
        files referenced in gemini-extension.json are missing: GEMINI.md`.
        """
        _require_dist()
        import json

        manifest = json.loads((DIST / "gemini-extension.json").read_text())
        ctx_name = manifest.get("contextFileName")
        if not ctx_name:
            pytest.skip("gemini-extension.json has no contextFileName")
        assert (DIST / ctx_name).is_file(), (
            f"{ctx_name} referenced by gemini-extension.json missing from {DIST}"
        )

    def test_gemini_md_imports_resolve(self):
        """@imports in GEMINI.md must point to real files under the extension."""
        _require_dist()
        gemini_md = DIST / "GEMINI.md"
        if not gemini_md.is_file():
            pytest.skip("No GEMINI.md in dist")
        pattern = re.compile(r"^@([a-zA-Z0-9_/.-]+)\b", re.MULTILINE)
        broken = [
            m.group(1)
            for m in pattern.finditer(gemini_md.read_text())
            if not (gemini_md.parent / m.group(1)).exists()
        ]
        assert not broken, f"GEMINI.md references missing files: {broken}"


class TestDistMcpConfig:
    """The built gemini-extension.json preserves MCP env vars from the base template."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    def _manifest(self) -> dict:
        import json

        return json.loads((DIST / "gemini-extension.json").read_text())

    def test_pkb_env_not_empty(self):
        """The build must not wipe env vars from the base template via shallow merge."""
        m = self._manifest()
        env = m.get("mcpServers", {}).get("pkb", {}).get("env", {})
        assert env, (
            "dist gemini-extension.json: pkb MCP server has empty env. "
            "The build's MCP merge wiped env vars from the base template. "
            "PKB_MCP_URL and ACA_DATA should be preserved."
        )

    def test_pkb_mcp_url_in_dist(self):
        m = self._manifest()
        env = m.get("mcpServers", {}).get("pkb", {}).get("env", {})
        assert "PKB_MCP_URL" in env, (
            "dist gemini-extension.json: PKB_MCP_URL missing from pkb env. "
            "The build merge must preserve env vars from the base template."
        )

    def test_playwright_env_in_dist(self):
        m = self._manifest()
        env = m.get("mcpServers", {}).get("playwright", {}).get("env", {})
        assert "PLAYWRIGHT_BROWSERS_PATH" in env, (
            "dist gemini-extension.json: PLAYWRIGHT_BROWSERS_PATH missing from playwright env. "
            "The build merge must preserve env vars from the base template."
        )


class TestAgentSchema:
    """Every built agent loads cleanly under the Gemini schema."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_frontmatter_keys_are_allowed(self, agent_file: Path):
        """Reject Claude-only keys that leak through
        `scripts/build.py::validate_gemini_agent_schema`.
        """
        fm = _parse_frontmatter(agent_file)
        disallowed = set(fm) - GEMINI_AGENT_ALLOWED_KEYS
        assert not disallowed, (
            f"{agent_file.name}: disallowed frontmatter keys {sorted(disallowed)}. "
            f"Gemini will reject with: Unrecognized key(s) in object: {sorted(disallowed)}. "
            f"Fix scripts/build.py::validate_gemini_agent_schema to whitelist-and-drop."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_no_claude_only_leak(self, agent_file: Path):
        """Explicit regression guard for each historically-leaked key."""
        fm = _parse_frontmatter(agent_file)
        leaks = set(fm) & CLAUDE_ONLY_LEAK_KEYS
        assert not leaks, (
            f"{agent_file.name}: Claude-only keys present in Gemini build: {sorted(leaks)}"
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_tool_names_valid(self, agent_file: Path):
        """Each tool is a Gemini builtin or MCP-prefixed (single underscore only)."""
        fm = _parse_frontmatter(agent_file)
        tools = fm.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]
        bad = [t for t in tools if t not in GEMINI_BUILTIN_TOOLS and not t.startswith("mcp_")]
        assert not bad, (
            f"{agent_file.name}: invalid tool names {bad}. "
            f"Gemini will reject with 'tools.N: Invalid tool name'. "
            f"Add to the GEMINI_TOOL_NAME_MAP in scripts/build.py or drop from source."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_no_double_underscores_in_tool_names(self, agent_file: Path):
        """Double underscores are Claude's MCP delimiter and must not appear in Gemini builds."""
        fm = _parse_frontmatter(agent_file)
        tools = fm.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]
        bad = [t for t in tools if "__" in t]
        assert not bad, (
            f"{agent_file.name}: tool names contain double underscores (Claude format): {bad}. "
            f"The build transform should convert mcp__plugin_aops-core_pkb__<tool> "
            f"to mcp_pkb_<tool>."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_no_plugin_namespace_in_tool_names(self, agent_file: Path):
        """Claude plugin namespace prefix must be stripped from Gemini tool names."""
        fm = _parse_frontmatter(agent_file)
        tools = fm.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]
        bad = [t for t in tools if "plugin_" in t]
        assert not bad, (
            f"{agent_file.name}: tool names contain Claude plugin namespace: {bad}. "
            f"Gemini registers MCP servers by bare name (e.g. 'pkb'), not the Claude "
            f"plugin-namespaced form (e.g. 'plugin_aops-core_pkb')."
        )

    @pytest.mark.parametrize("agent_file", _iter_agent_files(), ids=lambda p: p.name)
    def test_required_fields(self, agent_file: Path):
        fm = _parse_frontmatter(agent_file)
        for field in ("name", "description"):
            assert fm.get(field), f"{agent_file.name}: missing required field {field!r}"


class TestPolicyTomls:
    """Shipped policy TOMLs reference only real Gemini tools."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        _require_dist()

    def _policy_files(self) -> list[Path]:
        pol_dir = DIST / "policies"
        return sorted(pol_dir.rglob("*.toml")) if pol_dir.exists() else []

    def test_tool_names_valid(self):
        """`toolName = ...` entries in policy TOMLs resolve to real Gemini tools.

        Regression: `router.py` emitted literal `complete_tasks` (should be
        `complete_task`); Gemini captured it into `auto-saved.toml` and warned
        at every invocation: `Rule #39: Unrecognized tool name "complete_tasks"`.
        """
        offenders: list[tuple[Path, str]] = []
        for toml_path in self._policy_files():
            data = tomllib.loads(toml_path.read_text())
            rules = data.get("rules", []) if isinstance(data, dict) else []
            for rule in rules if isinstance(rules, list) else []:
                name = rule.get("toolName") if isinstance(rule, dict) else None
                if (
                    isinstance(name, str)
                    and name not in GEMINI_BUILTIN_TOOLS
                    and not name.startswith("mcp_")
                ):
                    offenders.append((toml_path.relative_to(DIST), name))
        assert not offenders, (
            "Policy TOML tool-name typos (Gemini will warn at every invocation):\n  "
            + "\n  ".join(f"{p}: {n}" for p, n in offenders)
        )


class TestRouterToolNames:
    """Hook router literals don't seed `auto-saved.toml` with bad tool names.

    Gemini persists observed tool names into `~/.gemini/policies/auto-saved.toml`.
    When our hooks reference a nonexistent tool (`complete_tasks`), that typo
    ends up in every user's policy file, producing a perpetual stderr warning.
    """

    def test_router_has_no_known_typos(self):
        _require_dist()
        router = DIST / "hooks" / "router.py"
        if not router.is_file():
            pytest.skip("no router.py in dist")
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
            f"Router contains tool-name typos that leak into auto-saved.toml: {offenders}"
        )


# ---------------------------------------------------------------------------
# Slow tier — requires the gemini CLI. Delegates to gemini's own validator.
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
class TestGeminiCliValidate:
    """Ground truth: `gemini extensions validate dist/aops-gemini` is clean."""

    @pytest.fixture(scope="class")
    def validate_output(self) -> subprocess.CompletedProcess[str]:
        _require_dist()
        if not _gemini_available():
            pytest.skip("gemini CLI not on PATH")
        # Use `command gemini` equivalent by bypassing any shell function.
        return subprocess.run(
            [shutil.which("gemini") or "gemini", "extensions", "validate", str(DIST)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_no_extension_manager_errors(self, validate_output):
        hits = [
            ln for ln in validate_output.stderr.splitlines() if "[ExtensionManager] Error" in ln
        ]
        assert not hits, (
            f"`gemini extensions validate` emitted {len(hits)} ExtensionManager errors:\n"
            + "\n".join(hits)
        )

    def test_no_schema_validation_failures(self, validate_output):
        hits = [
            ln
            for ln in validate_output.stderr.splitlines()
            if "Validation failed: Agent Definition" in ln
        ]
        assert not hits, "Agent frontmatter schema failures:\n" + "\n".join(hits)

    def test_no_unrecognized_keys(self, validate_output):
        hits = [ln for ln in validate_output.stderr.splitlines() if "Unrecognized key(s)" in ln]
        assert not hits, "Unrecognized frontmatter keys leaked:\n" + "\n".join(hits)

    def test_no_invalid_tool_names(self, validate_output):
        hits = [
            ln
            for ln in validate_output.stderr.splitlines()
            if re.search(r"tools\.\d+: Invalid tool name", ln)
        ]
        assert not hits, "Invalid tool names in agent frontmatter:\n" + "\n".join(hits)

    def test_no_policy_warnings(self, validate_output):
        hits = [ln for ln in validate_output.stderr.splitlines() if "Policy file warning" in ln]
        assert not hits, "Shipped policy TOMLs contain unknown tool names:\n" + "\n".join(hits)

    def test_no_missing_context_files(self, validate_output):
        stderr = validate_output.stderr
        m = re.search(r"context files .*? are missing: (.*)", stderr)
        assert not m, f"Extension manifest references missing files: {m.group(1) if m else ''}"

    def test_validator_reports_success(self, validate_output):
        """Final verdict line. Gemini prints `Extension validation failed.`
        when anything went wrong. Its exit code is 0 either way (as of 0.38.2)."""
        assert "Extension validation failed." not in validate_output.stderr, (
            "`gemini extensions validate` reported failure. Full stderr:\n" + validate_output.stderr
        )


@pytest.mark.slow
@pytest.mark.integration
class TestGeminiCliListExtensions:
    """Post-install smoke test: `gemini extensions list` prints no load errors.

    This is the exact codepath a user hits after running the install. We
    install `dist/aops-gemini` into a disposable `$HOME/.gemini/extensions`
    via HOME override, then assert stderr is clean.

    Uses the ``extensions list`` subcommand rather than the legacy
    ``--list-extensions`` flag — the latter prints nothing on
    gemini-cli ≥ 0.41 (silent return-zero), so it can no longer detect
    whether the install registered an extension at all.
    """

    @pytest.fixture(scope="class")
    def list_output(self, tmp_path_factory) -> subprocess.CompletedProcess[str]:
        _require_dist()
        if not _gemini_available():
            pytest.skip("gemini CLI not on PATH")

        fake_home = tmp_path_factory.mktemp("gemini_home")
        ext_root = fake_home / ".gemini" / "extensions" / "aops-core"
        ext_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(DIST, ext_root)

        # Replicate the host's gemini auth state into the fake HOME so
        # gemini doesn't refuse to start with "Please set an Auth method...".
        # Skip silently when the host has nothing — CI runners typically set
        # GEMINI_API_KEY instead.
        host_gemini = Path(os.path.expanduser("~/.gemini"))
        if host_gemini.is_dir():
            for filename in (
                "settings.json",
                "google_accounts.json",
                "oauth_creds.json",
                "installation_id",
            ):
                src = host_gemini / filename
                if src.exists():
                    shutil.copy2(src, fake_home / ".gemini" / filename)

        # Enable the extension for any working directory. Without this gemini
        # treats the extension as installed-but-not-enabled and `extensions
        # list` returns a stub line that won't include the extension's name
        # in any easily-greppable form.
        import json as _json

        (fake_home / ".gemini" / "extensions" / "extension-enablement.json").write_text(
            _json.dumps({"aops-core": {"overrides": ["*"]}})
        )

        # Trust both the fake home and the extension dir so gemini doesn't
        # refuse to load extensions ("Approval mode overridden to default
        # because the current folder is not trusted"). Gemini's trust list
        # is keyed by absolute path.
        (fake_home / ".gemini" / "trustedFolders.json").write_text(
            _json.dumps(
                {
                    str(fake_home): "TRUST_FOLDER",
                    str(fake_home / ".gemini"): "TRUST_FOLDER",
                    str(ext_root): "TRUST_FOLDER",
                    str(Path.cwd()): "TRUST_FOLDER",
                }
            )
        )

        # Override HOME *and* GEMINI_CLI_HOME — the latter is set in
        # agent-env-map.conf to /home/worker (the container path) and may
        # leak from the host shell. If left set the gemini CLI tries to
        # mkdir /home/worker/.gemini and fails with EACCES, never reaches
        # extension discovery, and the listing comes back empty.
        env = {**os.environ, "HOME": str(fake_home), "GEMINI_CLI_HOME": str(fake_home)}
        return subprocess.run(
            [shutil.which("gemini") or "gemini", "extensions", "list"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            check=False,
            cwd=str(fake_home),
        )

    def test_stderr_is_clean(self, list_output):
        """Every CLI_ERROR_PATTERN must be absent from stderr."""
        offenders = {
            pat.pattern: [ln for ln in list_output.stderr.splitlines() if pat.search(ln)]
            for pat in CLI_ERROR_PATTERNS
        }
        offenders = {k: v for k, v in offenders.items() if v}
        assert not offenders, "gemini extensions list emitted regressions:\n" + "\n\n".join(
            f"[{k}]\n  " + "\n  ".join(v) for k, v in offenders.items()
        )

    def test_extension_listed(self, list_output):
        # gemini-cli ≥ 0.41 writes the extension listing to stderr (alongside
        # the `[SAFETY] Registering Conseca Safety Checker` banner). Earlier
        # versions wrote to stdout. Accept either.
        combined = (list_output.stdout or "") + (list_output.stderr or "")
        assert "aops-core" in combined, (
            f"aops-core not listed by Gemini. stdout:\n{list_output.stdout}\n"
            f"stderr:\n{list_output.stderr}"
        )
