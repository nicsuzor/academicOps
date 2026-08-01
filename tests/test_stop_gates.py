"""End-to-end tests for ida's quiet gate
(plugins/ida/hooks/handlers.py:strip_the_reply) and orchestrate's hearsay
reminder (plugins/orchestrate/hooks/handlers.py:rule_against_hearsay).

rbg's own Stop/SubagentStop gate (``rule_check``) has its end-to-end coverage
in tests/test_rbg_stop_gate.py, added by the rbg-dual-channel-v07 branch this
repo now runs; the rbg cases that used to live here (against the superseded
gate-wiring-v07 ``check_rules_before_stopping``) were dropped as duplicates
when that branch was superseded.

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
_IDA_HOOKS = _REPO_ROOT / "plugins" / "ida" / "hooks"
_ORCHESTRATE_HOOKS = _REPO_ROOT / "plugins" / "orchestrate" / "hooks"


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
# ida: strip_the_reply
# ---------------------------------------------------------------------------


@pytest.fixture()
def ida_hooks(tmp_path):
    return _plugin_hooks_dir(tmp_path, _IDA_HOOKS)


def test_ida_quiet_gate_is_not_registered_on_subagentstop(ida_hooks):
    """SubagentStop fires on the *stopping subagent's* own context, never the
    face's — wiring the quiet gate there would direct a worker or james to
    strip a reply it never sends to the person. This is the defect the
    superseded gate-wiring-v07 branch shipped; the fix is that dispatch.py
    finds no handler for SubagentStop here and emits nothing at all."""
    result = _run(ida_hooks, "claude", "SubagentStop", {"hook_event_name": "SubagentStop"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_ida_stop_gate_self_loop_guard_suppresses_the_reentry(ida_hooks):
    result = _run(
        ida_hooks,
        "claude",
        "Stop",
        {"hook_event_name": "Stop", "stop_hook_active": True},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_ida_registers_no_posttooluse_handler(ida_hooks):
    """The hearsay reminder moved to orchestrate with the dispatch machinery it
    binds. ida registers ``Stop`` alone, so a ``PostToolUse`` here finds no
    handler and emits nothing — which is why the built manifest wires no such
    event (tests/test_plugin_manifests.py)."""
    result = _run(
        ida_hooks,
        "claude",
        "PostToolUse",
        {"hook_event_name": "PostToolUse", "tool_name": "Agent"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# orchestrate: rule_against_hearsay
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrate_hooks(tmp_path):
    return _plugin_hooks_dir(tmp_path, _ORCHESTRATE_HOOKS)


def test_orchestrate_posttooluse_hearsay_fires_on_an_agent_report(orchestrate_hooks):
    hearsay_md = (
        (_ORCHESTRATE_HOOKS / "messages" / "hearsay.md").read_text(encoding="utf-8").strip()
    )
    result = _run(
        orchestrate_hooks,
        "claude",
        "PostToolUse",
        {"hook_event_name": "PostToolUse", "tool_name": "Agent"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == hearsay_md


def test_orchestrate_posttooluse_hearsay_is_silent_on_every_other_tool(orchestrate_hooks):
    """The event is wired without a matcher, so the handler itself is the filter
    (specs/ARCHITECTURE.md, Hooks). A report only lands from the Agent tool;
    injecting on Read or Bash would put the reminder in front of an agent with
    no report to weigh."""
    result = _run(
        orchestrate_hooks,
        "claude",
        "PostToolUse",
        {"hook_event_name": "PostToolUse", "tool_name": "Read"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
