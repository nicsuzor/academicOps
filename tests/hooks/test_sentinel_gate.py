"""Tests for the sentinel gate — destructive env-op protection.

Covers:
  - Shell tools blocked when command contains destructive verb + protected path
  - Write-file tools blocked when target is a protected path
  - Safe operations allowed (wrong tool, safe path, non-destructive cmd)
  - Case-insensitive matching for both commands and paths
  - Word-boundary enforcement (rmdir doesn't match as rm; truncate as truncat)
  - All covered tool names: Bash, run_shell_command, Edit, Write, write_file, replace
  - Mode switching: block / warn / off
  - `truncate` command coverage (parity with Gemini TOML policy)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.router import HookRouter
from lib.gate_model import GateResult, GateVerdict
from lib.gate_types import GateState
from lib.gates.custom_conditions import (
    _DESTRUCTIVE_CMD_RE,
    _PROTECTED_PATH_RE,
    check_custom_condition,
)
from lib.gates.registry import GateRegistry
from lib.hook_context import HookContext
from lib.session_state import SessionState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state() -> SessionState:
    return SessionState.create("test-sentinel")


def _make_ctx(tool_name: str, tool_input: dict | None = None, **kwargs) -> HookContext:
    return HookContext(
        session_id="test-sentinel",
        hook_event="PreToolUse",
        tool_name=tool_name,
        tool_input=tool_input or {},
        **kwargs,
    )


def _dispatch(router: HookRouter, tool_name: str, tool_input: dict) -> GateResult | None:
    ctx = _make_ctx(tool_name, tool_input)
    state = _make_state()
    return router._dispatch_gates(ctx, state)


def _sentinel_result(result: GateResult | None) -> GateResult | None:
    """Return the gate result only if it came from the sentinel gate."""
    if result is not None and getattr(result, "gate_name", None) == "sentinel":
        return result
    return result  # return whatever the router decided — caller checks verdict


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reinit_gates(monkeypatch):
    """Stamp deterministic gate modes and reinitialise the registry."""
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    monkeypatch.setenv("QA_GATE_MODE", "warn")
    monkeypatch.setenv("ENFORCER_GATE_MODE", "warn")
    monkeypatch.setenv("HYDRATION_GATE_MODE", "off")
    monkeypatch.setenv("IDA_GATE_MODE", "off")
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", "50")
    monkeypatch.setenv("SENTINEL_GATE_MODE", "block")

    if "hooks.gate_config" in sys.modules:
        importlib.reload(sys.modules["hooks.gate_config"])
    if "lib.gates.definitions" in sys.modules:
        importlib.reload(sys.modules["lib.gates.definitions"])
    GateRegistry._initialized = False
    GateRegistry.initialize()


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


# ---------------------------------------------------------------------------
# Unit tests: regex correctness
# ---------------------------------------------------------------------------


class TestProtectedPathRegex:
    """_PROTECTED_PATH_RE matches protected paths in all expected forms."""

    @pytest.mark.parametrize(
        "path",
        [
            # tilde-expanded forms
            "~/.gemini/extensions/my-ext/index.js",
            "~/.gemini/settings.json",
            "~/.claude/plugins/",
            "~/.claude/settings.json",
            "~/.claude/settings.local.json",
            "~/.config/gemini/",
            # absolute home dir (Linux)
            "/home/user/.gemini/extensions/my-ext/",
            "/home/debian/.claude/settings.json",
            "/home/worker/.claude/plugins/",
            "/home/user/.gemini/settings.json",
            "/home/user/.config/gemini/config.json",
            # absolute home dir (macOS)
            "/Users/alice/.gemini/extensions/ext/",
            "/Users/alice/.claude/settings.json",
            # path embedded in a shell command
            "rm -rf ~/.gemini/extensions/old-ext/",
            "mv ~/.claude/settings.json ~/.claude/settings.json.bak",
        ],
    )
    def test_matches_protected_path(self, path: str):
        assert _PROTECTED_PATH_RE.search(path), f"Should match: {path!r}"

    @pytest.mark.parametrize(
        "path",
        [
            "/workspace/src/main.py",
            "~/.bashrc",
            "/tmp/my-ext/index.js",
            "/home/user/projects/gemini/extensions/",
            "~/.gemini/tmp/logs/session.md",  # tmp subdir not protected
            "/home/user/.claude_backup/settings.json",
        ],
    )
    def test_does_not_match_safe_path(self, path: str):
        assert not _PROTECTED_PATH_RE.search(path), f"Should NOT match: {path!r}"

    def test_case_insensitive(self):
        """Path regex is case-insensitive (for macOS case-folded paths)."""
        assert _PROTECTED_PATH_RE.search("~/.GEMINI/EXTENSIONS/ext/")
        assert _PROTECTED_PATH_RE.search("/HOME/USER/.CLAUDE/SETTINGS.JSON")


class TestDestructiveCmdRegex:
    """_DESTRUCTIVE_CMD_RE matches destructive verbs with word boundaries."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf ~/.claude/settings.json",
            "rmdir ~/.gemini/extensions/old/",
            "mv ~/.claude/settings.json /tmp/",
            "unlink ~/.gemini/settings.json",
            "truncate -s 0 ~/.claude/settings.json",
            # uppercase — case-insensitive
            "RM -rf ~/.gemini/",
            "TRUNCATE -s 0 ~/.claude/settings.json",
            "Rm -f ~/.gemini/settings.json",
        ],
    )
    def test_matches_destructive_verbs(self, cmd: str):
        assert _DESTRUCTIVE_CMD_RE.search(cmd), f"Should match: {cmd!r}"

    @pytest.mark.parametrize(
        "cmd",
        [
            # safe commands
            "ls ~/.gemini/extensions/",
            "cat ~/.claude/settings.json",
            "cp ~/.gemini/settings.json /tmp/backup.json",
            "echo ~/.claude/settings.json",
            "chmod 644 ~/.gemini/settings.json",
            # word-boundary enforcement: partial matches must NOT fire
            "rmdirfoo ~/.gemini/extensions/",  # rm not a standalone word
        ],
    )
    def test_does_not_match_safe_commands(self, cmd: str):
        assert not _DESTRUCTIVE_CMD_RE.search(cmd), f"Should NOT match: {cmd!r}"

    def test_word_boundary_rm_vs_rmdir(self):
        """rm must not match inside rmdir — word boundaries enforce this."""
        import re

        cmd = "rmdir ~/.claude/plugins/"
        # rm\b should not match at position 0 of 'rmdir'
        rm_only = re.compile(r"\brm\b", re.IGNORECASE)
        assert not rm_only.search(cmd), "rm\\b must not fire inside rmdir"
        # But the combined regex (which includes rmdir as an alternative) should match
        assert _DESTRUCTIVE_CMD_RE.search(cmd)

    def test_truncate_is_included(self):
        """truncate must be in the regex (parity with Gemini TOML policy)."""
        assert _DESTRUCTIVE_CMD_RE.search("truncate -s 0 somefile")

    def test_case_insensitive(self):
        """Destructive verb match is case-insensitive."""
        assert _DESTRUCTIVE_CMD_RE.search("RM -rf /tmp/x")
        assert _DESTRUCTIVE_CMD_RE.search("RMDIR /tmp/x")
        assert _DESTRUCTIVE_CMD_RE.search("TRUNCATE -s 0 /tmp/x")


# ---------------------------------------------------------------------------
# Unit tests: check_custom_condition("is_destructive_env_op")
# ---------------------------------------------------------------------------


class TestIsDestructiveEnvOp:
    """check_custom_condition correctly classifies ops as destructive or safe."""

    def _ctx(self, tool_name: str, tool_input: dict) -> HookContext:
        return HookContext(
            session_id="test-sentinel",
            hook_event="PreToolUse",
            tool_name=tool_name,
            tool_input=tool_input,
        )

    def _state(self) -> GateState:
        return GateState()

    def _session(self) -> SessionState:
        return _make_state()

    def _check(self, tool_name: str, tool_input: dict) -> bool:
        ctx = self._ctx(tool_name, tool_input)
        return check_custom_condition("is_destructive_env_op", ctx, self._state(), self._session())

    # -- Shell tools: should block when destructive cmd + protected path --

    def test_bash_rm_on_gemini_extensions(self):
        assert self._check("Bash", {"command": "rm -rf ~/.gemini/extensions/old-ext/"})

    def test_bash_rmdir_on_claude_plugins(self):
        assert self._check("Bash", {"command": "rmdir ~/.claude/plugins/legacy/"})

    def test_bash_mv_on_claude_settings(self):
        assert self._check("Bash", {"command": "mv ~/.claude/settings.json /tmp/bak.json"})

    def test_bash_unlink_on_gemini_settings(self):
        assert self._check("Bash", {"command": "unlink ~/.gemini/settings.json"})

    def test_bash_truncate_on_claude_settings(self):
        """truncate is covered (parity with Gemini TOML)."""
        assert self._check("Bash", {"command": "truncate -s 0 ~/.claude/settings.json"})

    def test_run_shell_command_rm_on_protected(self):
        assert self._check(
            "run_shell_command",
            {"command": "rm ~/.gemini/extensions/ext/manifest.json"},
        )

    def test_bash_case_insensitive_rm(self):
        """RM (uppercase) must be caught (bypass attempt via mixed case)."""
        assert self._check("Bash", {"command": "RM -rf ~/.gemini/extensions/"})

    def test_bash_case_insensitive_truncate(self):
        assert self._check("Bash", {"command": "TRUNCATE -s 0 ~/.claude/settings.json"})

    # -- Shell tools: should allow when path is safe or cmd is safe --

    def test_bash_rm_on_safe_path_allowed(self):
        """rm on non-protected path should be allowed."""
        assert not self._check("Bash", {"command": "rm -rf /tmp/old-build/"})

    def test_bash_ls_on_protected_path_allowed(self):
        """ls on protected path is not destructive — should be allowed."""
        assert not self._check("Bash", {"command": "ls ~/.gemini/extensions/"})

    def test_bash_cat_on_protected_path_allowed(self):
        """cat (read) on protected path is not destructive."""
        assert not self._check("Bash", {"command": "cat ~/.claude/settings.json"})

    def test_bash_cp_on_protected_path_allowed(self):
        """cp is not in the destructive verb list."""
        assert not self._check(
            "Bash",
            {"command": "cp ~/.claude/settings.json /tmp/backup.json"},
        )

    # -- Write-file tools: should block when target is a protected path --

    def test_edit_on_claude_settings(self):
        assert self._check(
            "Edit",
            {"file_path": "/home/user/.claude/settings.json", "old_string": "x", "new_string": "y"},
        )

    def test_write_on_gemini_extensions(self):
        assert self._check(
            "Write",
            {
                "file_path": "~/.gemini/extensions/my-ext/index.js",
                "content": "// modified",
            },
        )

    def test_write_file_on_claude_plugins(self):
        """write_file uses 'path' field (Gemini tool)."""
        assert self._check(
            "write_file",
            {"path": "~/.claude/plugins/my-plugin/plugin.json", "content": "{}"},
        )

    def test_replace_on_gemini_settings(self):
        assert self._check(
            "replace",
            {
                "path": "/home/debian/.gemini/settings.json",
                "old_string": "oldVal",
                "new_string": "newVal",
            },
        )

    def test_write_on_config_gemini(self):
        assert self._check(
            "Write",
            {"file_path": "~/.config/gemini/config.json", "content": "{}"},
        )

    # -- Write-file tools: should allow when target is a safe path --

    def test_edit_on_workspace_file_allowed(self):
        assert not self._check(
            "Edit",
            {
                "file_path": "/workspace/aops-core/lib/gates/definitions.py",
                "old_string": "x",
                "new_string": "y",
            },
        )

    def test_write_on_tmp_file_allowed(self):
        assert not self._check("Write", {"file_path": "/tmp/report.md", "content": "# Report"})

    def test_write_file_gemini_tmp_allowed(self):
        """~/.gemini/tmp/ is NOT a protected subpath."""
        assert not self._check(
            "write_file",
            {"path": "~/.gemini/tmp/session.md", "content": "data"},
        )

    # -- Other tools: non-covered tools should not trigger sentinel --

    def test_read_tool_never_triggers(self):
        assert not self._check("Read", {"file_path": "~/.gemini/extensions/"})

    def test_glob_never_triggers(self):
        assert not self._check("Glob", {"pattern": "~/.claude/*.json"})

    def test_unknown_tool_never_triggers(self):
        assert not self._check("SomeFutureTool", {"command": "rm ~/.claude/settings.json"})


# ---------------------------------------------------------------------------
# Integration tests: router produces correct verdicts
# ---------------------------------------------------------------------------


class TestSentinelGateVerdictsBlock:
    """Sentinel gate in block mode produces DENY for destructive env ops."""

    def test_bash_rm_protected_denied(self, router):
        result = _dispatch(router, "Bash", {"command": "rm -rf ~/.gemini/extensions/old/"})
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_bash_truncate_protected_denied(self, router):
        """truncate on protected path — parity gap from original PR."""
        result = _dispatch(router, "Bash", {"command": "truncate -s 0 ~/.claude/settings.json"})
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_edit_protected_path_denied(self, router):
        """Edit on a protected path is denied — gap fixed in this PR."""
        result = _dispatch(
            router,
            "Edit",
            {"file_path": "~/.claude/settings.json", "old_string": "a", "new_string": "b"},
        )
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_write_protected_path_denied(self, router):
        """Write on a protected path is denied."""
        result = _dispatch(
            router,
            "Write",
            {"file_path": "/home/user/.gemini/extensions/my-ext/index.js", "content": "x"},
        )
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_write_file_gemini_protected_denied(self, router):
        """Gemini write_file on protected path is denied."""
        result = _dispatch(
            router, "write_file", {"path": "~/.gemini/settings.json", "content": "{}"}
        )
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_replace_claude_plugins_denied(self, router):
        """Gemini replace on protected path is denied."""
        result = _dispatch(
            router,
            "replace",
            {"path": "~/.claude/plugins/plugin.json", "old_string": "x", "new_string": "y"},
        )
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_uppercase_rm_denied(self, router):
        """Case-insensitive: RM must be caught (bypass gap from original PR)."""
        result = _dispatch(router, "Bash", {"command": "RM -rf ~/.gemini/extensions/"})
        assert result is not None
        assert result.verdict == GateVerdict.DENY

    def test_run_shell_command_rm_denied(self, router):
        result = _dispatch(
            router,
            "run_shell_command",
            {"command": "rm ~/.gemini/extensions/ext/index.js"},
        )
        assert result is not None
        assert result.verdict == GateVerdict.DENY


class TestSentinelGateVerdictsAllow:
    """Sentinel gate allows safe operations through."""

    def test_rm_safe_path_allowed(self, router):
        result = _dispatch(router, "Bash", {"command": "rm -rf /tmp/stale-build/"})
        # None means no gate blocked it (allow)
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW

    def test_ls_protected_path_allowed(self, router):
        result = _dispatch(router, "Bash", {"command": "ls ~/.gemini/extensions/"})
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW

    def test_edit_workspace_file_allowed(self, router):
        result = _dispatch(
            router,
            "Edit",
            {
                "file_path": "/workspace/aops-core/lib/gates/definitions.py",
                "old_string": "x",
                "new_string": "y",
            },
        )
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW

    def test_write_tmp_file_allowed(self, router):
        result = _dispatch(router, "Write", {"file_path": "/tmp/report.md", "content": "data"})
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW

    def test_write_file_gemini_tmp_allowed(self, router):
        """~/.gemini/tmp/ is not protected."""
        result = _dispatch(
            router, "write_file", {"path": "~/.gemini/tmp/session.md", "content": "data"}
        )
        if result is not None:
            assert result.verdict == GateVerdict.ALLOW


class TestSentinelGateModes:
    """SENTINEL_GATE_MODE env var controls enforcement level."""

    def test_warn_mode_produces_warn(self, router, monkeypatch):
        monkeypatch.setenv("SENTINEL_GATE_MODE", "warn")
        if "hooks.gate_config" in sys.modules:
            importlib.reload(sys.modules["hooks.gate_config"])
        if "lib.gates.definitions" in sys.modules:
            importlib.reload(sys.modules["lib.gates.definitions"])
        GateRegistry._initialized = False
        GateRegistry.initialize()

        result = _dispatch(router, "Bash", {"command": "rm -rf ~/.gemini/extensions/"})
        assert result is not None
        assert result.verdict == GateVerdict.WARN

    def test_off_mode_allows_destructive_op(self, router, monkeypatch):
        monkeypatch.setenv("SENTINEL_GATE_MODE", "off")
        if "hooks.gate_config" in sys.modules:
            importlib.reload(sys.modules["hooks.gate_config"])
        if "lib.gates.definitions" in sys.modules:
            importlib.reload(sys.modules["lib.gates.definitions"])
        GateRegistry._initialized = False
        GateRegistry.initialize()

        result = _dispatch(router, "Bash", {"command": "rm -rf ~/.gemini/extensions/"})
        # off mode: sentinel should not produce DENY; other gates may still fire
        if result is not None:
            assert result.verdict != GateVerdict.DENY

    def test_block_mode_default(self, router):
        """Default mode is block — confirmed by env fixture."""
        result = _dispatch(
            router, "Write", {"file_path": "~/.claude/settings.json", "content": "{}"}
        )
        assert result is not None
        assert result.verdict == GateVerdict.DENY
