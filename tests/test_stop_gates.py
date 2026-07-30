"""End-to-end tests for the two Stop/SubagentStop gates this branch adds:
rbg's rule-check gate (plugins/rbg/hooks/handlers.py:check_rules_before_stopping)
and ida's quiet gate (plugins/ida/hooks/handlers.py:strip_the_reply).

Each case builds a synthetic hooks/ dir the way build stage 1 does — lib/hooks/
copied in, the real plugin's handlers.py and messages/ laid on top, exactly as
tests/test_pkb_handlers.py's ``_pkb_plugin`` fixture does for pkb — and runs
the real ``dispatch.py`` in a subprocess. No mocking of the handler or the
message files: this is the actual shipped wiring, minus the build step.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_RBG_HOOKS = _REPO_ROOT / "plugins" / "rbg" / "hooks"
_IDA_HOOKS = _REPO_ROOT / "plugins" / "ida" / "hooks"


def _plugin_hooks_dir(tmp_path: Path, plugin_hooks: Path) -> Path:
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    for py_file in _LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
    if (_LIB_HOOKS / "messages").is_dir():
        shutil.copytree(_LIB_HOOKS / "messages", hooks_dir / "messages", dirs_exist_ok=True)
    for py_file in plugin_hooks.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
    shutil.copytree(plugin_hooks / "messages", hooks_dir / "messages", dirs_exist_ok=True)
    return hooks_dir


def _run(hooks_dir: Path, client: str, event: str, raw: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(hooks_dir / "dispatch.py"), client, event],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# rbg: check_rules_before_stopping
# ---------------------------------------------------------------------------


@pytest.fixture()
def rbg_hooks(tmp_path):
    return _plugin_hooks_dir(tmp_path, _RBG_HOOKS)


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_rbg_stop_gate_blocks_with_the_shipped_message(rbg_hooks, event):
    stop_check_md = (_RBG_HOOKS / "messages" / "stop-check.md").read_text(encoding="utf-8").strip()
    result = _run(rbg_hooks, "claude", event, {"hook_event_name": event})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["decision"] == "block"
    assert out["reason"] == stop_check_md
    assert "systemMessage" in out


def test_rbg_stop_gate_self_loop_guard_suppresses_the_reentry(rbg_hooks):
    result = _run(
        rbg_hooks, "claude", "Stop", {"hook_event_name": "Stop", "stop_hook_active": True}
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_rbg_agy_stop_gets_an_advisory_never_a_block(rbg_hooks):
    result = _run(rbg_hooks, "agy", "PostInvocation", {})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "decision" not in out
    assert "injectSteps" in out


def test_rbg_pretooluse_and_userpromptsubmit_handlers_are_unaffected(rbg_hooks):
    """The stop gate is additive — evaluate() and inject_ruleset() still run
    their own events untouched, with no evaluator configured (clean no-op)."""
    result = _run(
        rbg_hooks,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# ida: strip_the_reply
# ---------------------------------------------------------------------------


@pytest.fixture()
def ida_hooks(tmp_path):
    return _plugin_hooks_dir(tmp_path, _IDA_HOOKS)


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_ida_stop_gate_blocks_with_the_shipped_message(ida_hooks, event):
    quiet_md = (_IDA_HOOKS / "messages" / "quiet.md").read_text(encoding="utf-8").strip()
    result = _run(ida_hooks, "claude", event, {"hook_event_name": event})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["decision"] == "block"
    assert out["reason"] == quiet_md
    assert "systemMessage" in out


def test_ida_stop_gate_self_loop_guard_suppresses_the_reentry(ida_hooks):
    result = _run(
        ida_hooks,
        "claude",
        "SubagentStop",
        {"hook_event_name": "SubagentStop", "stop_hook_active": True},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_ida_posttooluse_hearsay_handler_is_unaffected(ida_hooks):
    hearsay_md = (_IDA_HOOKS / "messages" / "hearsay.md").read_text(encoding="utf-8").strip()
    result = _run(
        ida_hooks,
        "claude",
        "PostToolUse",
        {"hook_event_name": "PostToolUse", "tool_name": "Agent"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == hearsay_md
