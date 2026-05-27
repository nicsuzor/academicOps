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

    def test_plugin_root_var_replaced_with_extension_path(self, transform):
        """All commands must use ${extensionPath} not ${CLAUDE_PLUGIN_ROOT}."""
        for event, hook_entries in transform["hooks"].items():
            for entry in hook_entries:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    assert "${CLAUDE_PLUGIN_ROOT}" not in cmd, (
                        f"${'{CLAUDE_PLUGIN_ROOT}'} not replaced in {event} hook: {cmd}"
                    )
                    assert "${extensionPath}" in cmd, (
                        f"${'{extensionPath}'} missing in {event} hook: {cmd}"
                    )

    def test_client_flag_is_claude(self, transform):
        """agy hooks must use --client claude (agy uses Claude's JSON payload format)."""
        for event, hook_entries in transform["hooks"].items():
            for entry in hook_entries:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    assert "--client claude" in cmd, (
                        f"Expected --client claude in {event} hook command: {cmd}"
                    )

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
