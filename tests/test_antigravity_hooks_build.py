"""Tests for the Antigravity (agy) hooks.json build transform.

Verifies that _generate_antigravity_hooks_json correctly:
- Maps Claude Code events to agy event names (UserPromptSubmit → PreInvocation, Stop → PostInvocation)
- Keeps native agy events unchanged (PreToolUse, PostToolUse)
- Transforms ${CLAUDE_PLUGIN_ROOT} → ${extensionPath} in all commands
- Drops events with no agy equivalent
- Skips -disabled suffix entries

Relates to task aops-f69011aa: Verify hooks work in Antigravity (agy CLI target build).
"""

import json
import sys
from pathlib import Path

import pytest

# Setup path to include build script
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
AOPS_CORE_DIR = REPO_ROOT / "aops-core"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_build_module():
    """Load build.py as a module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build", SCRIPTS_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build_mod():
    return load_build_module()


@pytest.fixture(scope="module")
def real_hooks_src():
    return AOPS_CORE_DIR / "hooks" / "hooks.json"


@pytest.fixture
def transform(build_mod, tmp_path):
    """Run the Antigravity build transform and return the resulting hooks dict."""
    src = AOPS_CORE_DIR / "hooks" / "hooks.json"
    dst = tmp_path / "hooks.json"
    build_mod._generate_antigravity_hooks_json(src, dst)
    with open(dst) as f:
        return json.load(f)


class TestAntigravityHooksBuildTransform:
    """End-to-end tests for the Antigravity hooks.json transform."""

    def test_output_has_hooks_key(self, transform):
        """Output must be a JSON object with a 'hooks' key."""
        assert "hooks" in transform

    def test_pre_tool_use_registered(self, transform):
        """PreToolUse must be present — agy supports it natively."""
        assert "PreToolUse" in transform["hooks"]

    def test_post_tool_use_registered(self, transform):
        """PostToolUse must be present — agy supports it natively."""
        assert "PostToolUse" in transform["hooks"]

    def test_user_prompt_submit_mapped_to_pre_invocation(self, transform):
        """UserPromptSubmit from source hooks must appear as PreInvocation in output."""
        hooks = transform["hooks"]
        assert "PreInvocation" in hooks, (
            "PreInvocation not in output — UserPromptSubmit→PreInvocation mapping missing"
        )
        # Must NOT still appear under original name
        assert "UserPromptSubmit" not in hooks

    def test_stop_mapped_to_post_invocation(self, transform):
        """Stop from source hooks must appear as PostInvocation in output."""
        hooks = transform["hooks"]
        assert "PostInvocation" in hooks, (
            "PostInvocation not in output — Stop→PostInvocation mapping missing"
        )
        assert "Stop" not in hooks

    def test_invocation_events_use_flat_handler_list(self, transform):
        """PreInvocation/PostInvocation MUST be a FLAT handler list, not matcher/hooks[].

        Per https://antigravity.google/docs/hooks#supported-events the
        invocation/Stop events require their command handlers DIRECTLY under the
        event key — no matcher/hooks[] wrapper. The wrapped (tool-event) shape
        made agy phantom-log 'executing command' but never spawn the process, so
        the PreInvocation context-injection hook silently never fired.
        """
        hooks = transform["hooks"]
        for event in ("PreInvocation", "PostInvocation"):
            handlers = hooks[event]
            assert isinstance(handlers, list) and handlers, f"{event} must be a non-empty list"
            for handler in handlers:
                assert "hooks" not in handler, (
                    f"{event} must NOT use the matcher/hooks[] wrapper — agy never "
                    f"spawns the process in that shape: {handler}"
                )
                assert handler.get("type") == "command", (
                    f"{event} flat handler must be a command type: {handler}"
                )
                assert "command" in handler, f"{event} flat handler missing 'command': {handler}"

    def test_tool_events_keep_matcher_hooks_wrapper(self, transform):
        """PreToolUse/PostToolUse MUST keep the matcher/hooks[] wrapper shape."""
        hooks = transform["hooks"]
        for event in ("PreToolUse", "PostToolUse"):
            for entry in hooks[event]:
                assert "hooks" in entry, (
                    f"{event} must keep the hooks[] wrapper (tool-event shape): {entry}"
                )

    def test_unsupported_events_dropped(self, transform):
        """SessionStart, SubagentStart, SubagentStop, SessionEnd, PreCompact, Notification
        are not supported by agy and must be absent from the output."""
        unsupported = {
            "SessionStart",
            "SessionEnd",
            "SubagentStart",
            "SubagentStop",
            "PreCompact",
            "Notification",
        }
        found = unsupported & set(transform["hooks"].keys())
        assert not found, f"Unsupported agy events found in output: {found}"

    @staticmethod
    def _iter_commands(hook_entries):
        """Yield every command string across both registration shapes.

        Flat invocation entries carry the command directly; tool entries nest it
        under hooks[].
        """
        for entry in hook_entries:
            if "hooks" in entry:
                for hook in entry["hooks"]:
                    yield hook.get("command", "")
            elif "command" in entry:
                yield entry.get("command", "")

    def test_plugin_root_var_replaced_with_shell_var(self, transform):
        """All commands must use hardcoded $HOME path not ${CLAUDE_PLUGIN_ROOT}."""
        for event, hook_entries in transform["hooks"].items():
            for cmd in self._iter_commands(hook_entries):
                assert "${CLAUDE_PLUGIN_ROOT}" not in cmd, (
                    f"${'{CLAUDE_PLUGIN_ROOT}'} not replaced in {event} hook: {cmd}"
                )
                assert "$HOME/.gemini/antigravity-cli/plugins/aops-core" in cmd, (
                    f"Expected agy install path missing in {event} hook: {cmd}"
                )
                # Verify that quotation marks around the command/path have been removed
                assert '"$HOME/.gemini' not in cmd, (
                    f"Command path has quotation marks in {event} hook: {cmd}"
                )

    def test_client_flag_is_agy(self, transform):
        """agy hooks must use --client agy."""
        for event, hook_entries in transform["hooks"].items():
            for cmd in self._iter_commands(hook_entries):
                assert "--client agy" in cmd, (
                    f"Expected --client agy in {event} hook command: {cmd}"
                )

    def test_pre_tool_use_timeout_raised_to_floor(self, transform):
        """PreToolUse timeout must be raised to the agy cold-start floor (>=15000ms).

        Defence-in-depth for the cold-start spurious-deny bug (aops-7697a478): a
        short 5000ms PreToolUse timeout can be blown by a first-call cold venv
        build, which agy surfaces as 'Tool call denied by jsonhook__...'.
        """
        timeout = transform["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"]
        assert timeout >= 15000, (
            f"PreToolUse timeout {timeout}ms is below the 15000ms agy floor; "
            "cold-start can blow it and produce spurious denials"
        )

    def test_timeout_floor_never_lowers_existing(self, build_mod, tmp_path):
        """The floor only raises a timeout; a higher source value is preserved."""
        src_data = {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "echo x", "timeout": 30000}]}
                ],
            }
        }
        src = tmp_path / "hooks_in.json"
        dst = tmp_path / "hooks_out.json"
        src.write_text(json.dumps(src_data))
        build_mod._generate_antigravity_hooks_json(src, dst)
        result = json.loads(dst.read_text())
        assert result["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] == 30000

    def test_disabled_entries_not_included(self, build_mod, tmp_path):
        """Entries under 'hooks-disabled' keys must never appear in output."""
        # Construct a minimal hooks.json with a -disabled entry
        src_data = {
            "hooks": {
                "PreToolUse": [{"hooks": [{"type": "command", "command": "echo active"}]}],
                "Stop-disabled": [{"hooks": [{"type": "command", "command": "echo disabled"}]}],
            }
        }
        src = tmp_path / "hooks_in.json"
        dst = tmp_path / "hooks_out.json"
        src.write_text(json.dumps(src_data))

        build_mod._generate_antigravity_hooks_json(src, dst)
        result = json.loads(dst.read_text())
        assert "Stop-disabled" not in result["hooks"]
        assert "PostInvocation" not in result["hooks"]  # disabled entry should not produce output
