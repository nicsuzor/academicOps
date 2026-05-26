"""Sentinel gate — destructive ops on user environment paths.

Tests that the sentinel gate blocks rm/mv/rmdir/unlink/truncate on
protected paths (~/.gemini/extensions/, ~/.claude/plugins/, etc.) and
respects SENTINEL_GATE_MODE overrides (block / warn / off).

Origin: GitHub issue #106 — agent deleted a working Gemini extension
installation without evidence it was broken.
"""

import pytest

from tests.hooks.gate_helpers import (
    GateVerdict,
    HookContext,
    SessionState,
    reinit_gates_with_defaults,
    set_gate_modes,
)


class TestSentinelBlocksDestructiveOps:
    """Sentinel gate blocks destructive ops on protected user-environment paths."""

    @pytest.mark.parametrize(
        "command,should_block",
        [
            ("rm -rf ~/.gemini/extensions/aops-core/", True),
            ("rm ~/.gemini/extensions/manifest.json", True),
            ("mv ~/.claude/plugins/cache/ /tmp/backup/", True),
            ("rm ~/.gemini/settings.json", True),
            ("rmdir ~/.claude/plugins/old-plugin/", True),
            ("unlink ~/.config/gemini/config.toml", True),
            ("rm ~/.claude/settings.json", True),
            # Safe operations — NOT blocked
            ("cat ~/.gemini/extensions/manifest.json", False),
            ("ls ~/.gemini/extensions/", False),
            ("rm some-other-file.txt", False),
            ("rm -rf /tmp/build/", False),
            ("git status", False),
            ("echo hello", False),
        ],
        ids=[
            "rm-rf-gemini-ext",
            "rm-gemini-ext-file",
            "mv-claude-plugins",
            "rm-gemini-settings",
            "rmdir-claude-plugin",
            "unlink-config-gemini",
            "rm-claude-json",
            "cat-gemini-ext-allowed",
            "ls-gemini-ext-allowed",
            "rm-other-file-allowed",
            "rm-tmp-allowed",
            "git-status-allowed",
            "echo-allowed",
        ],
    )
    def test_sentinel_verdict(self, router, monkeypatch, command, should_block):
        set_gate_modes(monkeypatch, sentinel="block")
        reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel")
        ctx = HookContext(
            session_id="test-sentinel",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": command},
        )

        result = router._dispatch_gates(ctx, state)

        if should_block:
            assert result is not None, f"Sentinel should block: {command!r}"
            assert result.verdict == GateVerdict.DENY, (
                f"Sentinel should DENY destructive op: {command!r}, got {result.verdict.value}"
            )
        else:
            if result is not None:
                assert result.verdict != GateVerdict.DENY, (
                    f"Sentinel should NOT block: {command!r}, got {result.verdict.value}"
                )

    def test_sentinel_off_mode_allows_all(self, router, monkeypatch):
        """SENTINEL_GATE_MODE=off disables the gate entirely."""
        set_gate_modes(monkeypatch, sentinel="off")
        reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-off")
        ctx = HookContext(
            session_id="test-sentinel-off",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "rm -rf ~/.gemini/extensions/"},
        )

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                "Sentinel with mode=off must not block destructive ops"
            )

    def test_sentinel_warn_mode(self, router, monkeypatch):
        """SENTINEL_GATE_MODE=warn produces WARN instead of DENY."""
        set_gate_modes(monkeypatch, sentinel="warn")
        reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-warn")
        ctx = HookContext(
            session_id="test-sentinel-warn",
            hook_event="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "rm -rf ~/.gemini/extensions/aops-core/"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None, "Sentinel warn mode should produce a result"
        assert result.verdict == GateVerdict.WARN, (
            f"Sentinel warn mode should WARN, got {result.verdict.value}"
        )

    def test_sentinel_non_bash_tool_allowed(self, router, monkeypatch):
        """Non-shell tools are not inspected by sentinel."""
        set_gate_modes(monkeypatch, sentinel="block")
        reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-edit")
        ctx = HookContext(
            session_id="test-sentinel-edit",
            hook_event="PreToolUse",
            tool_name="Edit",
            tool_input={"file_path": "~/.gemini/extensions/foo.txt"},
        )

        result = router._dispatch_gates(ctx, state)

        if result is not None:
            assert result.verdict != GateVerdict.DENY, (
                "Sentinel should only inspect Bash/shell tools, not Edit"
            )

    def test_sentinel_gemini_shell_tool(self, router, monkeypatch):
        """Sentinel also catches Gemini's run_shell_command tool."""
        set_gate_modes(monkeypatch, sentinel="block")
        reinit_gates_with_defaults()

        state = SessionState.create("test-sentinel-gemini")
        ctx = HookContext(
            session_id="test-sentinel-gemini",
            hook_event="PreToolUse",
            tool_name="run_shell_command",
            tool_input={"command": "rm -rf ~/.gemini/extensions/"},
        )

        result = router._dispatch_gates(ctx, state)

        assert result is not None and result.verdict == GateVerdict.DENY, (
            "Sentinel must block destructive ops via Gemini's run_shell_command too"
        )
