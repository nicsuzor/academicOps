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


def _require_dist() -> None:
    """Skip the test cleanly if the extension has not been built yet."""
    if not DIST.exists():
        pytest.skip(
            f"{DIST} not built. Run `make build` (or `uv run python scripts/build.py`) first."
        )


def _gemini_available() -> bool:
    return shutil.which("gemini") is not None


def _iter_agent_files() -> list[Path]:
    return sorted((DIST / "agents").glob("*.md")) if (DIST / "agents").exists() else []


def _parse_frontmatter(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm) or {}


# ---------------------------------------------------------------------------
# Fast tier — runs on every PR, no Gemini binary required.
# ---------------------------------------------------------------------------


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
        """Each tool is a Gemini builtin or MCP-prefixed."""
        fm = _parse_frontmatter(agent_file)
        tools = fm.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]
        bad = [
            t
            for t in tools
            if t not in GEMINI_BUILTIN_TOOLS and not t.startswith(("mcp_", "mcp__"))
        ]
        assert not bad, (
            f"{agent_file.name}: invalid tool names {bad}. "
            f"Gemini will reject with 'tools.N: Invalid tool name'. "
            f"Add to the GEMINI_TOOL_NAME_MAP in scripts/build.py or drop from source."
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
                    and not name.startswith(("mcp_", "mcp__"))
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
        offenders = {bad: good for bad, good in known_typos.items() if bad in text}
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
    """Post-install smoke test: `gemini --list-extensions` prints no load errors.

    This is the exact codepath a user hits after running the install. We
    install `dist/aops-gemini` into a disposable `$HOME/.gemini/extensions`
    via HOME override, then assert stderr is clean.
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

        env = {"HOME": str(fake_home), "PATH": __import__("os").environ["PATH"]}
        return subprocess.run(
            [shutil.which("gemini") or "gemini", "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            check=False,
        )

    def test_stderr_is_clean(self, list_output):
        """Every CLI_ERROR_PATTERN must be absent from stderr."""
        offenders = {
            pat.pattern: [ln for ln in list_output.stderr.splitlines() if pat.search(ln)]
            for pat in CLI_ERROR_PATTERNS
        }
        offenders = {k: v for k, v in offenders.items() if v}
        assert not offenders, "gemini --list-extensions emitted regressions:\n" + "\n\n".join(
            f"[{k}]\n  " + "\n  ".join(v) for k, v in offenders.items()
        )

    def test_extension_listed(self, list_output):
        assert "aops-core" in list_output.stdout, (
            f"aops-core not listed by Gemini. stdout:\n{list_output.stdout}\n"
            f"stderr:\n{list_output.stderr}"
        )
