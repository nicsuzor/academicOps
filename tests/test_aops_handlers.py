"""Behavioral tests for plugins/aops/hooks/handlers.py.

The handlers import the shared runtime (result, context, messages) as
top-level modules — the layout dispatch.py builds at runtime — so each case
runs in a subprocess with lib/hooks and the plugin's hooks/ on sys.path,
mirroring how test_shipped_hooks.py loads shipped handler modules.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
AOPS_HOOKS = REPO_ROOT / "plugins" / "aops" / "hooks"

_RUN_HANDLER = """
import importlib.util, json, sys
lib_hooks, aops_hooks, handler_name, raw_json = sys.argv[1:5]
sys.path.insert(0, aops_hooks)
sys.path.insert(0, lib_hooks)
spec = importlib.util.spec_from_file_location("handlers", aops_hooks + "/handlers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from context import normalize
raw = json.loads(raw_json)
event = raw.get("hook_event_name", "Stop")
ctx = normalize("claude", event, raw, __import__("pathlib").Path(aops_hooks))
res = getattr(module, handler_name)(ctx)
print(json.dumps(
    None if res is None else {
        "inject_text": res.inject_text,
        "user_text": res.user_text,
        "is_refusal": res.is_refusal,
    }
))
"""

_READ_HANDLERS = """
import importlib.util, json, sys
lib_hooks, aops_hooks = sys.argv[1:3]
sys.path.insert(0, aops_hooks)
sys.path.insert(0, lib_hooks)
spec = importlib.util.spec_from_file_location("handlers", aops_hooks + "/handlers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
wired = {event: sorted(h.__name__ for h in hs) for event, hs in module.HANDLERS.items()}
wired["names"] = sorted(n for n in dir(module) if not n.startswith("__"))
wired["headless_env"] = sorted(module._HEADLESS_ENV)
print(json.dumps(wired))
"""


def _handlers_module() -> dict:
    """The shipped HANDLERS mapping, by handler name, plus the module's names."""
    proc = subprocess.run(
        [sys.executable, "-c", _READ_HANDLERS, str(LIB_HOOKS), str(AOPS_HOOKS)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# Every variable aops reads as "no human is at the keyboard". A test that cares
# sets or clears all of them: CI runners export CI, so inheriting the ambient
# environment would silently decide the outcome.
#
# This restates a production constant, which is the shape that let the
# interactive-tool list ship wrong. Here it is unavoidable — clearing the
# environment means naming every variable — so the duplication is pinned by
# the equality test below instead of left to drift. Copying is safe when a
# divergence fails; it is only dangerous when a divergence passes.
_HEADLESS_ENV = ("NONINTERACTIVE", "CI", "AOPS_POLECAT_CONTAINER", "CLAUDE_CODE_NON_INTERACTIVE")


def _run(handler: str, raw: dict, env_overrides: dict[str, str | None] | None = None):
    env = dict(os.environ)
    for key, value in (env_overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _RUN_HANDLER,
            str(LIB_HOOKS),
            str(AOPS_HOOKS),
            handler,
            json.dumps(raw),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_stop_handler_warns_on_a_plain_stop(event):
    """One handler serves both stop events. `SubagentStop` output reaches the
    subagent that is stopping, not its parent, so there is no second reader to
    write a second message for."""
    res = _run("present_checkable_evidence", {"hook_event_name": event})
    assert res is not None and res["inject_text"]


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_stop_handler_stays_silent_once_a_stop_hook_already_fired(event):
    """stop_hook_active means a stop hook already continued this stop cycle;
    injecting again re-continues it — an unbounded loop with no user input."""
    res = _run("present_checkable_evidence", {"hook_event_name": event, "stop_hook_active": True})
    assert res is None


def test_headless_signals_here_are_the_signals_production_reads():
    """Pins the copy above to the real constant, in both directions.

    A variable production reads and this file does not clear is one an
    inherited CI environment can flip mid-test; a variable this file clears
    and production has stopped reading is a case that silently stopped
    testing anything. Neither is visible without asserting the equality.
    """
    assert _handlers_module()["headless_env"] == sorted(_HEADLESS_ENV)


def test_subagent_stop_handler_is_the_one_that_serves_stop():
    """Wiring, not wording: both stop events must resolve to the same handler.
    The retired `require_evidence_from_subagent` addressed a parent agent that
    never receives this hook's output."""
    registered = _handlers_module()
    assert registered["SubagentStop"] == registered["Stop"]
    assert "require_evidence_from_subagent" not in registered["names"]


def test_evidence_reminder_stays_silent_while_background_tasks_run():
    res = _run(
        "present_checkable_evidence",
        {"hook_event_name": "Stop", "background_tasks": [{"task_id": "b1"}]},
    )
    assert res is None


def _ask(tool: str, env_overrides: dict[str, str | None]):
    return _run(
        "refuse_interactive_prompt_when_headless",
        {"hook_event_name": "PreToolUse", "tool_name": tool},
        env_overrides=env_overrides,
    )


def test_askuserquestion_is_refused_in_a_headless_session():
    """AskUserQuestion is Claude Code's real name for the ask-a-human tool, so
    it is the name the framework's only refusing hook has to know. Without it
    the hook is inert in every shipped Claude Code session: it sees the tool
    call, matches nothing, and lets a headless run block on a prompt no one
    will answer."""
    res = _ask("AskUserQuestion", {**dict.fromkeys(_HEADLESS_ENV, None), "NONINTERACTIVE": "1"})
    assert res is not None
    assert res["is_refusal"]
    assert "AskUserQuestion" in res["inject_text"]


def test_askuserquestion_is_allowed_when_someone_is_there_to_answer():
    """The refusal turns on a capability fact — nobody to answer — not on a
    rule about the tool. With no headless signal set, asking is exactly what
    the tool is for and the hook must not touch it."""
    assert _ask("AskUserQuestion", dict.fromkeys(_HEADLESS_ENV, None)) is None


# ---------------------------------------------------------------------------
# SessionStart: three compact facts, and never a crashed session
# ---------------------------------------------------------------------------
#
# This handler runs before the session has produced anything, so a raise here
# costs the whole session. These run it against the SOURCE tree, where neither
# the rendered manifest nor the client registry exists — the worst case for a
# reporter, and the one a developer hits every day.


def _session_start(env_overrides: dict[str, str | None] | None = None):
    return _run(
        "session_start",
        {"hook_event_name": "SessionStart", "session_id": "test-session"},
        env_overrides={"CLAUDE_ENV_FILE": None, **(env_overrides or {})},
    )


def test_session_start_reports_all_three_facts():
    """Telemetry was always reported; the build and the installed roster are
    what the session had no way to see. All three land in one advisory."""
    res = _session_start()
    assert res is not None
    injected = res["inject_text"]
    assert "telemetry:" in injected
    assert "plugin:" in injected
    assert "plugins installed:" in injected


def test_session_start_leaves_no_placeholder_unsubstituted():
    """The failure mode of a `.format()`-driven message: a new placeholder in
    the markdown that no handler fills reaches the agent as literal braces."""
    res = _session_start()
    assert res is not None
    for placeholder in ("{telemetry}", "{plugin}", "{installed}"):
        assert placeholder not in res["inject_text"]


def test_session_start_does_not_raise_when_neither_fact_is_available():
    """Run against the source tree: no rendered manifest, no client registry.
    Both facts are unavailable and the handler still returns an advisory."""
    res = _session_start()
    assert res is not None
    assert res["is_refusal"] is False
    assert "not readable" in res["inject_text"]
    assert "no client registry" in res["inject_text"]


def test_session_start_still_supplies_no_endpoint():
    """The disclaimer is the point of the message and must survive any addition
    to it: this hook sets nothing and names no endpoint, and a trace URL is not
    among the facts it can report (lib/hooks/telemetry.py, EXPORT_VARS)."""
    res = _session_start()
    assert res is not None
    assert "no value is supplied by default" in res["inject_text"]
    assert res["user_text"] and "no endpoint was supplied" in res["user_text"]


def test_session_start_reports_facts_not_a_report():
    """This fires on every session, so the injection-tier discipline applies:
    one line per fact. The three fact lines head the message, ahead of the
    standing disclaimer paragraph."""
    res = _session_start()
    assert res is not None
    facts = res["inject_text"].split("\n\n")[0].splitlines()
    assert len(facts) == 3


# ---------------------------------------------------------------------------
# Two readers per message: the agent's full text, the user's one line
# ---------------------------------------------------------------------------


def test_refusal_carries_a_user_line_with_the_tool_name_substituted():
    """The user line takes the same `{tool}` substitution the agent's text
    does. A refusal the user cannot see is a session that stalls for reasons
    only the transcript explains."""
    res = _ask("AskUserQuestion", {**dict.fromkeys(_HEADLESS_ENV, None), "CI": "1"})
    assert res is not None
    assert res["user_text"]
    assert "AskUserQuestion" in res["user_text"]
    assert "{tool}" not in res["user_text"]


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_stop_advisory_carries_both_versions(event):
    """Both readers served from one message name: the long form injected into
    the agent's context, the short form for the person watching."""
    res = _run("present_checkable_evidence", {"hook_event_name": event})
    assert res is not None
    assert res["user_text"]
    # Short is the point — a paragraph in a status line is not a status line.
    assert len(res["user_text"]) < len(res["inject_text"])
    assert "\n" not in res["user_text"]
