"""End-to-end tests for ida's quiet gate
(plugins/aops-core/hooks/handlers.py:be_quiet) and orchestrate's hearsay
reminder and honesty advisory
(plugins/orchestrate/hooks/handlers.py:rule_against_hearsay, honest_output).

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
import tomllib
from pathlib import Path

import pytest

_POLICY_FILE = Path(__file__).resolve().parent / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}


def _require_orchestrate_hearsay_enabled():
    if not _policy.get("orchestrate", {}).get("rule_against_hearsay_enabled", True):
        pytest.skip("orchestrate hearsay hook is disabled by policy")


_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_IDA_HOOKS = _REPO_ROOT / "plugins" / "aops-core" / "hooks"
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
        "PostToolBatch",
        {"hook_event_name": "PostToolBatch", "stop_hook_active": True},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_ida_registers_no_posttooluse_handler(ida_hooks):
    """The hearsay reminder moved to orchestrate with the dispatch machinery it
    binds. ida registers ``PostToolBatch`` alone, so a ``PostToolUse`` here
    finds no handler and emits nothing — which is why the built manifest
    wires no such event (tests/test_plugin_manifests.py)."""
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


def test_orchestrate_hearsay_fires_once_on_a_batch_carrying_an_agent_report(orchestrate_hooks):
    """``PostToolBatch`` fires exactly once per batch, with every resolved call
    in ``tool_calls`` — so a batch that dispatched a subagent alongside other
    tools still gets the reminder, and gets it once rather than per call."""
    _require_orchestrate_hearsay_enabled()
    hearsay_md = (
        (_ORCHESTRATE_HOOKS / "messages" / "hearsay.md").read_text(encoding="utf-8").strip()
    )
    result = _run(
        orchestrate_hooks,
        "claude",
        "PostToolBatch",
        {
            "hook_event_name": "PostToolBatch",
            "tool_calls": [
                {"tool_name": "Read", "tool_use_id": "a"},
                {"tool_name": "Agent", "tool_use_id": "b"},
            ],
        },
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == hearsay_md


def test_orchestrate_hearsay_is_silent_on_a_batch_with_no_agent_call(orchestrate_hooks):
    """The event is wired without a matcher, so the handler itself is the filter
    (specs/ARCHITECTURE.md, Hooks). A report only lands from the Agent tool;
    injecting on Read or Bash would put the reminder in front of an agent with
    no report to weigh."""
    result = _run(
        orchestrate_hooks,
        "claude",
        "PostToolBatch",
        {
            "hook_event_name": "PostToolBatch",
            "tool_calls": [{"tool_name": "Read", "tool_use_id": "a"}],
        },
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# orchestrate: honest_output
# ---------------------------------------------------------------------------


def _honesty_md() -> str:
    return (_ORCHESTRATE_HOOKS / "messages" / "honesty.md").read_text(encoding="utf-8").strip()


def test_orchestrate_honesty_fires_on_claude_subagent_start(orchestrate_hooks):
    """SubagentStart is where honest_output is registered, providing an advisory
    evidence reminder at the start of a subagent's turn."""
    result = _run(
        orchestrate_hooks, "claude", "SubagentStart", {"hook_event_name": "SubagentStart"}
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    assert out["hookSpecificOutput"]["additionalContext"] == _honesty_md()


def test_orchestrate_honesty_skips_ida_on_subagent_start(orchestrate_hooks):
    """ida speaks to the person and is exempt from the subagent honesty reminder."""
    result = _run(
        orchestrate_hooks,
        "claude",
        "SubagentStart",
        {"hook_event_name": "SubagentStart", "agent_type": "pkb:ida"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_orchestrate_honesty_fires_for_a_named_agent_that_is_not_ida(orchestrate_hooks):
    result = _run(
        orchestrate_hooks,
        "claude",
        "SubagentStart",
        {"hook_event_name": "SubagentStart", "agent_type": "orchestrate:james"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    assert out["hookSpecificOutput"]["additionalContext"] == _honesty_md()


def test_orchestrate_stop_returns_nothing_on_claude_stop(orchestrate_hooks):
    """Stop only runs tracer stop (which returns None)."""
    result = _run(orchestrate_hooks, "claude", "Stop", {"hook_event_name": "Stop"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_orchestrate_honesty_is_silent_on_agys_post_invocation(orchestrate_hooks):
    """agy fires ``PostInvocation`` after every tool call and dispatch maps it
    onto canonical ``Stop``; agy sends no ``stop_hook_active``, so the
    once-per-chain guard cannot suppress the repeat. Injecting here puts the
    whole block in front of the agent on every tool call — the failure that
    truncated context by step 4 and took rbg's stop gate offline."""
    result = _run(orchestrate_hooks, "agy", "PostInvocation", {"conversationId": "c1"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_orchestrate_honesty_is_silent_on_the_continuation_stop(orchestrate_hooks):
    """The advisory gives the session another turn, which stops again. Once per
    chain is dispatch.py's structural guard, not this handler's."""
    result = _run(
        orchestrate_hooks,
        "claude",
        "Stop",
        {"hook_event_name": "Stop", "stop_hook_active": True},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_orchestrate_honesty_is_silent_when_subagentstop_not_in_handlers(orchestrate_hooks):
    """SubagentStop is not registered in HANDLERS, so a subagent handback receives
    nothing until re-registered."""
    result = _run(
        orchestrate_hooks,
        "claude",
        "SubagentStop",
        {"hook_event_name": "SubagentStop", "agent_type": "Explore"},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_orchestrate_stop_hook_is_wired_synchronously(orchestrate_hooks):
    """An ``async`` ``Stop`` hook's output is discarded by Claude Code (2.1.227:
    the advisory reaches the model neither on that turn nor the next), so the
    honesty advisory only lands from a synchronous entry."""
    manifest = json.loads(
        (_REPO_ROOT / "plugins" / "orchestrate" / "manifest" / "hooks.template.json").read_text(
            encoding="utf-8"
        )
    )
    for event in ("Stop", "SubagentStop"):
        for entry in manifest["clients"]["claude"]["hooks"][event]:
            for hook in entry["hooks"]:
                assert not hook.get("async"), f"{event} is declared async"


def test_orchestrate_hearsay_survives_a_payload_with_no_tool_calls(orchestrate_hooks):
    """``tool_calls`` is absent on every event but ``PostToolBatch``, and a
    client may omit it on an empty batch. ``normalize`` defaults it to an empty
    tuple so the handler reads it unguarded — the alternative is the
    ``AttributeError`` this handler raised on every batch before the field
    existed (lib/hooks/dispatch.py:HookContext)."""
    result = _run(
        orchestrate_hooks,
        "claude",
        "PostToolBatch",
        {"hook_event_name": "PostToolBatch"},
    )
    assert result.returncode == 0
    assert result.stderr.strip() == ""
    assert result.stdout.strip() == ""
