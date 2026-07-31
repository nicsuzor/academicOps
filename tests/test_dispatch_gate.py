"""Tests for the ``block`` result kind and the Stop/SubagentStop self-loop
guard in ``lib/hooks/dispatch.py``, which the rbg stop gate is built on.

Originally written on the `gate-wiring-v07` branch, carried across here rather
than rewritten. The cases covering the ida quiet gate were dropped with that
gate; everything about the shared runtime is kept. Its counterpart file
``tests/test_rbg_stop_gate.py`` drives the same runtime end to end through the
shipped plugin — these are the unit layer beneath it, and they are what pin
``_merge``'s precedence, which no end-to-end case reaches.

``tests/test_hooks.py`` is the file that would normally carry these — its own
docstring says it "covers the dispatch runtime" — but as of this branch it
cannot be collected at all: it imports ``clients``, ``result``, ``messages``,
``degraded``, ``credentials``, ``provenance`` and ``telemetry`` from
``lib/hooks/``, none of which exist any more (``lib/hooks/`` now holds only
``dispatch.py`` and ``messages/``). That break predates this change and is out
of scope here, so these cases live in a file that actually runs instead of
being added to one that cannot collect.

Two layers, matching the pattern the rest of the suite uses for the shared
runtime: direct import of ``dispatch.py`` for the pure functions
(``_merge``, ``render``), and a real subprocess through ``dispatch.py`` itself
for the end-to-end self-loop-guard and wire-shape behaviour — dispatch.py has
no other module dependencies, so no synthetic plugin scaffolding is needed
beyond a handlers.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_DISPATCH = _LIB_HOOKS / "dispatch.py"

if str(_LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIB_HOOKS))

import dispatch  # noqa: E402

# ---------------------------------------------------------------------------
# dispatch.py: the block() constructor and Result shape
# ---------------------------------------------------------------------------


def test_block_is_distinct_from_refuse_and_warn():
    b = dispatch.block("keep going")
    assert b.is_block is True
    assert b.is_refusal is False
    assert dispatch.warn("careful").is_block is False
    assert dispatch.refuse("impossible").is_block is False


def test_block_carries_a_user_line_like_warn_and_refuse_do():
    b = dispatch.block("keep going", user_text="checking rules")
    assert b.inject_text == "keep going"
    assert b.user_text == "checking rules"


# ---------------------------------------------------------------------------
# dispatch.py: _merge precedence — refusal > block > warn
# ---------------------------------------------------------------------------


def test_merge_refusal_beats_block_and_warn_regardless_of_order():
    r, b, w = dispatch.refuse("impossible"), dispatch.block("keep going"), dispatch.warn("careful")
    assert dispatch._merge([w, b, r]) is r
    assert dispatch._merge([r, b, w]) is r
    assert dispatch._merge([b, r, w]) is r


def test_merge_block_beats_warn_regardless_of_order():
    b, w = dispatch.block("keep going"), dispatch.warn("careful")
    assert dispatch._merge([w, b]) is b
    assert dispatch._merge([b, w]) is b


def test_merge_first_block_wins_among_blocks():
    first, second = dispatch.block("first"), dispatch.block("second")
    assert dispatch._merge([first, second]) is first


def test_merge_first_warn_wins_among_warns_when_no_block_or_refusal():
    first, second = dispatch.warn("first"), dispatch.warn("second")
    assert dispatch._merge([first, second]) is first


def test_merge_of_nothing_is_none():
    assert dispatch._merge([None, None]) is None
    assert dispatch._merge([]) is None


# ---------------------------------------------------------------------------
# dispatch.py: render() — the exact claude Stop/SubagentStop block wire shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_render_claude_block_is_a_top_level_decision_not_hookspecificoutput(event):
    out = dispatch.render("claude", event, dispatch.block("keep going"))
    assert out == {"decision": "block", "reason": "keep going"}
    assert "hookSpecificOutput" not in out


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_render_claude_block_with_user_text_adds_system_message(event):
    out = dispatch.render("claude", event, dispatch.block("keep going", user_text="checking"))
    assert out == {
        "decision": "block",
        "reason": "keep going",
        "systemMessage": "checking",
    }


@pytest.mark.parametrize(
    "event",
    [e for e in dispatch.CANONICAL_EVENTS if e not in ("Stop", "SubagentStop")],
)
def test_render_claude_block_on_a_non_stop_event_never_emits_decision_block(event, capsys):
    """A block() on any event other than Stop/SubagentStop is a handler-wiring
    bug, not a legal shape Claude Code understands there. It must degrade to
    the ordinary advisory shape, loudly, rather than corrupt the response or
    silently vanish."""
    out = dispatch.render("claude", event, dispatch.block("keep going"))
    assert "decision" not in out
    assert out["hookSpecificOutput"]["additionalContext"] == "keep going"
    assert "permissionDecision" not in out["hookSpecificOutput"]
    # Asserted on substance rather than on one word of the message: the report
    # has to name the offending event and say the disposition did not survive,
    # which is what makes it actionable. A single magic word would break on any
    # rewording while proving less.
    err = capsys.readouterr().err
    assert event in err, f"the report does not name the event: {err!r}"
    assert "advisory" in err, f"the report does not say it degraded: {err!r}"


def test_render_claude_refusal_still_wins_its_own_shape_on_stop():
    """A refusal is a different kind of result from a block and keeps its own
    wire shape even on Stop, where a block would render at the top level."""
    out = dispatch.render("claude", "Stop", dispatch.refuse("nobody is here to answer"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "decision" not in out


# ---------------------------------------------------------------------------
# dispatch.py: render() — agy never receives a block
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event", list(dispatch.CANONICAL_EVENTS))
def test_render_agy_never_emits_a_block_shape_on_any_event(event):
    out = dispatch.render("agy", event, dispatch.block("keep going"))
    assert out == {"injectSteps": [{"ephemeralMessage": "keep going"}]}
    assert "decision" not in out


def test_render_agy_block_carries_no_user_text_channel():
    out = dispatch.render("agy", "Stop", dispatch.block("keep going", user_text="checking"))
    assert "checking" not in json.dumps(out)


# ---------------------------------------------------------------------------
# dispatch.py: main() — the self-loop guard, end to end through a subprocess
# ---------------------------------------------------------------------------


@pytest.fixture()
def gated_plugin(tmp_path):
    """A synthetic plugin hooks/ dir: dispatch.py copied in (the only file it
    needs — it has no other module dependencies), plus a handlers.py this
    fixture's caller writes on top."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "dispatch.py").write_text(_DISPATCH.read_text(encoding="utf-8"), encoding="utf-8")
    return hooks_dir


def _write_handlers(hooks_dir: Path, body: str) -> None:
    (hooks_dir / "handlers.py").write_text(body, encoding="utf-8")


def _run_dispatch(
    hooks_dir: Path, client: str, event: str, raw: dict
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(hooks_dir / "dispatch.py"), client, event],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
    )


_BLOCKING_HANDLER = (
    "from dispatch import block\n"
    "\n"
    "def _gate(ctx):\n"
    "    return block('keep going', user_text='checking rules')\n"
    "\n"
    "HANDLERS = {'Stop': [_gate], 'SubagentStop': [_gate]}\n"
)


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_self_loop_guard_suppresses_output_when_stop_hook_active_is_true(gated_plugin, event):
    _write_handlers(gated_plugin, _BLOCKING_HANDLER)
    result = _run_dispatch(
        gated_plugin,
        "claude",
        event,
        {"hook_event_name": event, "stop_hook_active": True},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_self_loop_guard_does_not_suppress_a_fresh_stop(gated_plugin, event):
    _write_handlers(gated_plugin, _BLOCKING_HANDLER)
    result = _run_dispatch(gated_plugin, "claude", event, {"hook_event_name": event})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["decision"] == "block"


def test_self_loop_guard_does_not_apply_to_other_events(gated_plugin):
    """stop_hook_active is meaningless outside Stop/SubagentStop — a handler
    on another event must still run even if that flag happens to be set."""
    _write_handlers(
        gated_plugin,
        "from dispatch import warn\n"
        "\n"
        "def _advise(ctx):\n"
        "    return warn('careful')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_advise]}\n",
    )
    result = _run_dispatch(
        gated_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "stop_hook_active": True},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "careful"


def test_dispatch_block_end_to_end_on_claude_stop(gated_plugin):
    _write_handlers(gated_plugin, _BLOCKING_HANDLER)
    result = _run_dispatch(gated_plugin, "claude", "Stop", {"hook_event_name": "Stop"})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out == {
        "decision": "block",
        "reason": "keep going",
        "systemMessage": "checking rules",
    }


def test_dispatch_agy_stop_via_postinvocation_never_receives_a_block(gated_plugin):
    """The same handler that blocks Claude Code's Stop is also reachable on
    agy's Stop (mapped from PostInvocation, per clients.py's alias table) —
    agy must see the advisory shape, never a block."""
    _write_handlers(gated_plugin, _BLOCKING_HANDLER)
    result = _run_dispatch(gated_plugin, "agy", "PostInvocation", {})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out == {"injectSteps": [{"ephemeralMessage": "keep going"}]}
    assert "decision" not in out


def test_self_loop_guard_on_agy_stop_also_suppresses_output(gated_plugin):
    _write_handlers(gated_plugin, _BLOCKING_HANDLER)
    result = _run_dispatch(gated_plugin, "agy", "PostInvocation", {"stop_hook_active": True})
    assert result.returncode == 0
    assert result.stdout.strip() == ""
