"""Tests for the shared hook runtime (lib/hooks/dispatch.py).

lib/hooks/ is copied byte-identical into every plugin that hooks (see
specs/ARCHITECTURE.md, Hooks). These tests exercise it in place, plus in a
synthetic "injected" plugin directory (dispatch.py + a handlers.py + a
messages/ dir side by side) to prove the handler-registration and
message-loading contracts a plugin author relies on.

The runtime used to be eight modules — clients, context, credentials,
degraded, messages, provenance, result, telemetry. 89733bf8 consolidated the
parts still in use into `dispatch.py` and deleted the rest. Where a section
below is thinner than the module it replaced, the retirement is named at the
section head rather than left as an absence.

Division of labour with the sibling files:

- `tests/test_dispatch_gate.py` owns the BLOCK disposition end to end — the
  `Kind` invariants, `_merge` precedence, the Claude block shape, the agy
  degradation, and the stop-hook self-loop guard. Not repeated here.
- `tests/test_shipped_hooks.py` owns the built artifact.
- This file owns the advisory and refusal shapes, the message-loading
  contract, and dispatch's own process-level behaviour.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_DISPATCH = _LIB_HOOKS / "dispatch.py"
_POLICY_FILE = _REPO_ROOT / "tests" / "policy.toml"

_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8"))

if str(_LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIB_HOOKS))

from dispatch import (
    CANONICAL_EVENTS,
    TO_CANONICAL,
    HookContext,
    Kind,
    load_message_pair,
    normalize,
    refuse,
    render,
    to_canonical,
    warn,
)

# ---------------------------------------------------------------------------
# dispatch.py: event-name normalization
# ---------------------------------------------------------------------------


def test_claude_events_are_identity_mapped_for_the_full_architecture_table():
    for event in CANONICAL_EVENTS:
        assert to_canonical("claude", event) == event


def test_agy_known_event_aliases():
    assert to_canonical("agy", "PreInvocation") == "UserPromptSubmit"


def test_agy_postinvocation_is_a_known_but_unmapped_event():
    """PostInvocation is a deliberate no-op, not a missing row.

    It used to alias onto canonical "Stop", but live instrumentation showed
    it fires once per internal invocation/tool-call round-trip rather than
    once per turn (aops_73e25af2) — every Stop-registered handler on every
    plugin saw N+1 fires per turn. `TO_CANONICAL["agy"]["PostInvocation"]` is
    explicitly `None` so `main()` short-circuits before `_log_fire` or any
    handler lookup — distinct from `test_an_unmapped_event_passes_through_
    under_its_own_name` below, where an event with no row at all passes
    through under its own name and still reaches `_load_handlers`."""
    assert "PostInvocation" in TO_CANONICAL["agy"]
    assert to_canonical("agy", "PostInvocation") is None


@pytest.mark.parametrize("event", ["SessionStart", "SubagentStop"])
def test_agy_has_no_wire_equivalent_for_these_architecture_events(event):
    """No confirmed agy wire equivalent exists for these, so the table has no
    row for them. Asserted against the table itself: `to_canonical` cannot
    answer this question, because it passes an unmapped event through under its
    own name rather than returning `None` — see the next case."""
    assert event not in TO_CANONICAL["agy"]


def test_an_unmapped_event_passes_through_under_its_own_name():
    """Not a translation failure — a deliberate pass-through.

    The `aops-debug` plugin registers a wildcard handler and wires every event
    its client emits, mapped or not; capturing unmapped events is its entire
    purpose, and it only works because an untranslated name still reaches
    `_load_handlers`. For every other plugin the name matches no registration,
    so the call is a no-op that costs one process.
    """
    assert to_canonical("agy", "PreToolUse") == "PreToolUse"
    assert to_canonical("agy", "SomeFutureEvent") == "SomeFutureEvent"


def test_an_unknown_client_has_no_mappings_and_translates_nothing():
    assert TO_CANONICAL.get("gemini") is None
    assert to_canonical("gemini", "PreToolUse") == "PreToolUse"


# ---------------------------------------------------------------------------
# dispatch.py: response rendering — the advisory and refusal shapes
# ---------------------------------------------------------------------------
#
# The BLOCK shape is tests/test_dispatch_gate.py's, including its top-level
# nesting on Claude Code and its degradation on agy. What is here is everything
# else: nothing to say, an advisory, a refusal, and the guarantee that an
# advisory can never acquire a blocking field.


def test_render_nothing_to_say_is_empty_dict_both_clients():
    assert render("claude", "PreToolUse", None) == {}
    assert render("agy", "UserPromptSubmit", None) == {}


def test_render_claude_pretooluse_warn_uses_additional_context_never_permission_decision():
    """The `PreToolUse` rule check is advisory only (specs/ARCHITECTURE.md,
    Enforcement) — nothing in-session denies a tool call on a rule verdict, so
    this shape must never carry permissionDecision."""
    out = render("claude", "PreToolUse", warn("careful"))
    assert "permissionDecision" not in out["hookSpecificOutput"]
    assert out["hookSpecificOutput"]["additionalContext"] == "careful"


def test_render_claude_stop_warn_uses_additional_context_never_top_level_decision():
    """An advisory on a stop is still an advisory. `Stop` is the one event where
    a top-level `decision` would be honoured, so it is the one event where a
    warn() leaking into that shape would silently become a gate."""
    out = render("claude", "Stop", warn("reflect first"))
    assert "decision" not in out
    assert out["hookSpecificOutput"]["additionalContext"] == "reflect first"


def test_render_claude_subagentstop_warn_uses_additional_context():
    out = render("claude", "SubagentStop", warn("reflect first"))
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
            "additionalContext": "reflect first",
        }
    }
    assert "decision" not in out


def test_render_claude_warn_with_user_text_adds_system_message():
    out = render("claude", "Stop", warn("reflect first", user_text="heads up"))
    assert out["systemMessage"] == "heads up"
    assert out["hookSpecificOutput"]["additionalContext"] == "reflect first"


def test_render_agy_warn_uses_inject_steps():
    out = render("agy", "UserPromptSubmit", warn("careful"))
    assert out == {"injectSteps": [{"ephemeralMessage": "careful"}]}


def test_render_for_an_unknown_client_emits_nothing_rather_than_raising(capsys):
    """A client with no renderer produces no output at all.

    This used to raise `ValueError`. It no longer does, and the change is worth
    stating: `main()` takes the client from argv, so an unknown one now runs
    every handler, discards whatever they returned, and exits 0 — the handlers'
    side effects happen and their results do not. Nothing ships a third client
    today, so the shapes below are the whole surface; the day one does, this is
    where its absence will be silent.
    """
    assert render("gemini", "Stop", warn("x")) == {}
    assert render("gemini", "PreToolUse", refuse("x")) == {}


def test_render_claude_refusal_is_a_deny_permission_decision():
    """The one shape Claude Code reads as "do not run this tool call". A refusal
    carries no additionalContext — the reason IS the denial reason."""
    out = render("claude", "PreToolUse", refuse("nobody is here to answer"))
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "nobody is here to answer",
        }
    }
    assert "additionalContext" not in out["hookSpecificOutput"]


def test_render_agy_refusal_is_a_deny_decision_with_a_reason():
    """agy's own denial shape, as its `PreToolUse` contract defines it: a
    `decision` of allow/deny/ask, with `reason` alongside. Unreachable today —
    agy's table has no tool event — but the shape must be right the day one is,
    and wrong-by-omission is how a silent no-op ships."""
    out = render("agy", "PreToolUse", refuse("nobody is here to answer"))
    assert out == {"decision": "deny", "reason": "nobody is here to answer"}


def test_render_advisory_never_carries_a_blocking_field_on_either_client():
    """The other half of the guard: warn() must stay incapable of denying or
    blocking, on every event and every client, so a rule advisory can never
    become a gate."""
    for event in CANONICAL_EVENTS:
        claude_out = json.dumps(render("claude", event, warn("careful")))
        assert "permissionDecision" not in claude_out
        assert "decision" not in claude_out
    agy_out = json.dumps(render("agy", "UserPromptSubmit", warn("careful")))
    assert "decision" not in agy_out
    assert "reason" not in agy_out


def test_warn_is_an_advisory_and_refuse_is_not():
    """`==`, not `is`: dispatch.py is loaded twice in a live hook, so a member
    built handler-side is never identical to the renderer's. See `Kind`."""
    assert warn("careful").kind == Kind.ADVISE
    assert refuse("impossible").kind == Kind.REFUSE


# `_merge`'s precedence rules — refusal over block over advisory, then
# registration order — are covered in full by tests/test_dispatch_gate.py,
# which was written against the three-disposition `Kind` and covers the block
# row this file's predecessor could not. Not duplicated here.


# ---------------------------------------------------------------------------
# dispatch.py: the markdown-only wording contract
# ---------------------------------------------------------------------------
#
# `load_message_pair` replaced messages.py's `load`/`load_pair`/`load_user`.
# One difference is load-bearing and is NOT re-asserted below because it is no
# longer true: `messages.load` raised `MessageNotFoundError` on a missing or
# empty agent message, and dispatch turned that into a fail-loud report. The
# current function returns `""` and says nothing, leaving each handler to
# notice. Only rbg's `rule_check` does. The gap is pinned as a strict xfail in
# tests/test_pkb_handlers.py, on the plugin where it is observable, rather than
# restated here as an absence.


def _message(tmp_path, name: str, agent: str | None, user: str | None = None) -> None:
    (tmp_path / "messages").mkdir(exist_ok=True)
    if agent is not None:
        (tmp_path / "messages" / f"{name}.md").write_text(agent)
    if user is not None:
        (tmp_path / "messages" / f"{name}.user.md").write_text(user)


def test_a_message_is_returned_stripped(tmp_path):
    _message(tmp_path, "handover", "\n  hand it over cleanly  \n")
    assert load_message_pair(tmp_path, "handover")[0] == "hand it over cleanly"


# --- the second reader: <name>.user.md ---------------------------------------
#
# A message has two audiences with opposite needs — the agent, where length
# buys precision, and the person watching, where it buys nothing. The short
# version lives in a sibling file so that adding one cannot disturb the text
# already going to the agent, and so this module needs no frontmatter parser
# inside a hook subprocess that has only the standard library.


def test_message_with_a_user_version_loads_both(tmp_path):
    _message(tmp_path, "handover", "The long form, for the agent.", "  short line  \n")
    assert load_message_pair(tmp_path, "handover") == (
        "The long form, for the agent.",
        "short line",
    )


def test_message_without_a_user_version_is_not_an_error(tmp_path):
    """The ordinary case. A hook with nothing worth putting in a status line
    says nothing there, and still injects its agent-facing text."""
    _message(tmp_path, "handover", "The long form, for the agent.")
    agent, user = load_message_pair(tmp_path, "handover")
    assert agent == "The long form, for the agent."
    assert user is None


def test_empty_user_version_renders_as_absent(tmp_path):
    """A blank line in the user's terminal is worse than silence.

    Asserted on the rendered output, not on the return value. An empty sibling
    comes back as `""` where a missing one comes back as `None`, and the two are
    NOT interchangeable to a handler that tests `is None` — but neither reaches
    the person, because `_render_claude` gates `systemMessage` on truthiness.
    The guarantee that matters is the one on the wire, so that is the one
    pinned; a handler relying on the distinction would be relying on something
    this contract does not promise.
    """
    _message(tmp_path, "handover", "The long form.", "   \n")
    agent, user = load_message_pair(tmp_path, "handover")
    assert not user
    assert "systemMessage" not in render("claude", "Stop", warn(agent, user))


def test_a_user_line_alone_yields_no_agent_text(tmp_path):
    """The user's line is an addition, never a substitute: it cannot stand in
    for the message the agent was supposed to receive. It is returned, because
    dropping it would lose the only text there is, but the agent's half stays
    empty rather than being filled from it."""
    _message(tmp_path, "orphan", None, "short line")
    agent, user = load_message_pair(tmp_path, "orphan")
    assert agent == ""
    assert user == "short line"


def test_claude_carries_the_user_line_on_an_advisory_and_a_refusal():
    """Claude Code has a channel for each reader, and both must be used. The
    refusal case matters most: the agent is told no, and this line is the only
    sign the user gets that a hook intervened."""
    advisory = render("claude", "Stop", warn("long form", "short line"))
    assert advisory["hookSpecificOutput"]["additionalContext"] == "long form"
    assert advisory["systemMessage"] == "short line"

    refusal = render("claude", "PreToolUse", refuse("long form", "short line"))
    assert refusal["hookSpecificOutput"]["permissionDecisionReason"] == "long form"
    assert refusal["systemMessage"] == "short line"


def test_claude_omits_the_user_line_when_there_is_none():
    assert "systemMessage" not in render("claude", "Stop", warn("long form"))


def test_agy_drops_the_user_line_rather_than_misdirecting_it():
    """agy has no user-facing channel — its response steps (`ephemeralMessage`,
    `userMessage`, `toolCall`) all speak to the agent, and `userMessage` would
    put the framework's words in the person's mouth. So the line is dropped,
    and this pins that it is dropped deliberately rather than leaking onto an
    agent-facing surface."""
    out = render("agy", "UserPromptSubmit", warn("long form", "short line"))
    assert out == {"injectSteps": [{"ephemeralMessage": "long form"}]}
    assert "short line" not in json.dumps(out)


# --- the second reader, across the plugins that actually ship ----------------
#
# A handler that takes only the agent's half of the pair —
# `load_message_pair(...)[0]` — cannot deliver the user's line no matter what
# is in the sibling file. That failure is silent in every direction: the file
# is present, the tests that read it pass, the build ships it, and the line
# never reaches a terminal. So it is checked against the source of every plugin
# that hooks, not left to each plugin's own suite to notice.

_PLUGINS_ROOT = _REPO_ROOT / "plugins"

# `load_message_pair(...)[0]` — the agent-only load, and the way a shipped
# `.user.md` becomes silently unreachable.
_AGENT_ONLY_LOAD = re.compile(
    r"""load_message_pair\(\s*ctx\.hooks_dir\s*,\s*["']([\w.-]+)["']\s*\)\s*\[\s*0\s*\]"""
)


def _hooking_plugins() -> list[Path]:
    return sorted(p for p in _PLUGINS_ROOT.glob("*/hooks") if (p / "handlers.py").is_file())


def test_every_plugin_that_hooks_is_discovered():
    """The guards below are loops over plugins; an empty loop passes silently."""
    assert _hooking_plugins(), f"no plugin under {_PLUGINS_ROOT} ships a hooks/handlers.py"


def test_no_shipped_user_line_lacks_the_agent_message_it_belongs_to():
    """A `.user.md` with no `.md` beside it ships a hook that injects an empty
    agent message while the person gets a line about it — the two readers
    disagree about whether anything happened."""
    orphans = [
        f"{hooks.parent.name}: {user_file.name}"
        for hooks in _hooking_plugins()
        for user_file in sorted((hooks / "messages").glob("*.user.md"))
        if not (hooks / "messages" / f"{user_file.name.removesuffix('.user.md')}.md").is_file()
    ]
    assert orphans == [], f"user-facing lines with no agent message beside them: {orphans}"


# --- the other direction: every message owes the person a line ---------------
#
# The guard above catches a user line with nothing behind it. This one catches
# the opposite and more common omission: a message written for the agent and
# never given a second reader. Nothing about that failure is visible — the hook
# fires, the agent acts on text the person never saw, and the session looks to
# them as though nothing happened. So a new message cannot ship user-blind by
# inattention; it can only ship that way by being listed below, with a reason,
# deliberately.


# Every directory whose `messages/` reaches a session: the plugins that hook,
# plus the shared runtime's own. The runtime ships no wording of its own today,
# but build/shared.py still copies `lib/hooks` wholesale into every hooking
# plugin, so a message added there would reach every session and is covered by
# the same rule.
def _message_dirs() -> list[Path]:
    return [*_hooking_plugins(), _LIB_HOOKS]


# Messages that ship with no `.user.md` because they have no second reader to
# write one for. An entry is a claim about the emitter, not a licence: the
# exemption test below re-checks each claim against the source, so an exemption
# that stops being true fails here rather than quietly covering a message that
# now has a reader to serve.
_NO_USER_COUNTERPART: dict[str, str] = _policy["hooks"]["messages"].get("no_user_counterpart", {})

# Messages that ship user-blind and SHOULD NOT. Separate from the dict above
# because these are not exemptions — they are a defect list, and the only thing
# keeping the audit green. Listing one here is a promise to come back to it.
_KNOWN_USER_BLIND: dict[str, str] = _policy["hooks"]["messages"].get("known_user_blind", {})


def _shipped_messages() -> list[tuple[str, Path, str]]:
    """``("<owner>: <name>", hooks dir, name)`` for every message that ships."""
    return [
        (f"{hooks.parent.name}: {agent_file.stem}", hooks, agent_file.stem)
        for hooks in _message_dirs()
        for agent_file in sorted((hooks / "messages").glob("*.md"))
        if not agent_file.name.endswith(".user.md")
    ]


def test_every_shipped_message_is_discovered():
    """The guard below is a loop over message files; an empty loop passes."""
    assert len(_shipped_messages()) >= 4, "too few messages found across the tree to be checking"


def test_every_shipped_message_carries_a_line_for_the_person_watching():
    accounted = set(_NO_USER_COUNTERPART) | set(_KNOWN_USER_BLIND)
    blind = [
        label
        for label, hooks, name in _shipped_messages()
        if label not in accounted and load_message_pair(hooks, name)[1] is None
    ]
    assert blind == [], (
        "these messages reach a session with nothing for the person whose session it "
        "is — they see no sign the hook fired. Write the one-line version beside the "
        "agent's text as <name>.user.md, or, if this message genuinely has no reader "
        f"to write one for, add it to _NO_USER_COUNTERPART with the reason: {blind}"
    )


def test_the_known_user_blind_list_is_not_growing():
    """The defect list is allowed to shrink and never to grow. Without this,
    `_KNOWN_USER_BLIND` is just a wider exemption dict and the audit above
    stops meaning anything."""
    assert set(_KNOWN_USER_BLIND) == {"rbg: rule-check"}


_READ_HANDLER_SCOPES = """
import importlib.util, json, sys
lib_hooks, plugin_hooks = sys.argv[1:3]
sys.path.insert(0, plugin_hooks)
sys.path.insert(0, lib_hooks)
spec = importlib.util.spec_from_file_location("handlers", plugin_hooks + "/handlers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
scopes = {}
for handlers in module.HANDLERS.values():
    for handler in handlers:
        scope = getattr(handler, "only_on_clients", None)
        scopes[handler.__name__] = sorted(scope) if scope is not None else None
print(json.dumps(scopes))
"""


def _handler_client_scopes(hooks: Path) -> dict:
    """Each registered handler's declared client scope, read from the real
    module. A subprocess, so the plugin's own imports (rbg's `evaluator`,
    `rules`) never land on this process's `sys.path`."""
    proc = subprocess.run(
        [sys.executable, "-c", _READ_HANDLER_SCOPES, str(_LIB_HOOKS), str(hooks)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_the_no_user_channel_exemptions_are_still_true():
    """Both exemptions rest on a fact about the emitter, and both facts are
    checked here rather than trusted from the comment beside them."""
    rbg_hooks = _PLUGINS_ROOT / "rbg" / "hooks"

    # `ruleset`: the decorator is what makes it undeliverable, so read the
    # attribute `@only_on` sets on the real handler. Drop the decorator and
    # this message reaches Claude Code, where a line for the person exists.
    scopes = _handler_client_scopes(rbg_hooks)
    if "inject_ruleset" not in scopes:
        pytest.skip("inject_ruleset is not registered")
    assert scopes["inject_ruleset"] == ["agy"]
    assert render("agy", "UserPromptSubmit", warn("agent text", "user line")) == {
        "injectSteps": [{"ephemeralMessage": "agent text"}]
    }

    # `classifier-prompt`: no handler names it, because nothing injects it.
    # The moment one does, it is a session message like any other.
    assert "classifier-prompt" not in (rbg_hooks / "handlers.py").read_text()
    assert "classifier-prompt" in (rbg_hooks / "evaluator.py").read_text()


def test_the_known_user_blind_entry_is_still_a_real_defect():
    """`rbg: rule-check` is listed as a defect, not an exemption. That claim
    rests on the handler taking only the agent's half, so read that from the
    source: the day it takes the pair, the entry has to go."""
    rbg_handlers = (_PLUGINS_ROOT / "rbg" / "hooks" / "handlers.py").read_text()
    assert _AGENT_ONLY_LOAD.search(rbg_handlers), (
        "rbg no longer loads any message agent-only — if rule-check now takes "
        "the pair, remove it from _KNOWN_USER_BLIND"
    )


def test_no_entry_outlives_the_message_it_names():
    """An entry for a message that no longer ships is dead weight that would
    silently cover a future message of the same name."""
    shipped = {label for label, _, _ in _shipped_messages()}
    named = set(_NO_USER_COUNTERPART) | set(_KNOWN_USER_BLIND)
    stale = sorted(named - shipped)
    assert stale == [], f"these name messages that do not ship: {stale}"


# ---------------------------------------------------------------------------
# Retired sections
# ---------------------------------------------------------------------------
#
# Four groups of cases were deleted rather than rewritten, because 89733bf8
# deleted what they tested and nothing took it over:
#
# - `telemetry.report()` and `configured_vars()` (lib/hooks/telemetry.py). The
#   env-var contract they read survives as `TELEMETRY_ENV` in
#   lib/polecat/env_contract.py and is exercised by
#   tests/test_telemetry_otel_e2e.py; the SessionStart *reporter* does not
#   survive in any form.
# - `provenance.py` — the build/version/installed-roster reporter. Its only
#   caller was the aops plugin's `session_start` handler, retired with that
#   plugin (plugins.disabled/aops/).
# - `credentials.isolate` — the SessionStart writer for `CLAUDE_ENV_FILE`.
#   Same owner, same retirement. `CLAUDE_ENV_FILE` is still named in
#   lib/polecat/env_contract.py's container contract, but nothing writes it.
# - `degraded.py` — the user-facing channel for the framework's own failures.
#   Replaced by per-handler `print(..., file=sys.stderr)`; the current contract
#   is stated in plugins/rbg/hooks/evaluator.py's module docstring, and the
#   stderr half is asserted in tests/test_cope.py.


# ---------------------------------------------------------------------------
# dispatch.py: end-to-end, both clients, every table event
# ---------------------------------------------------------------------------


@pytest.fixture()
def injected_plugin(tmp_path):
    """A synthetic plugin hooks/ dir: lib/hooks/ copied in as the build does,
    plus this fixture's caller adding handlers.py and its own messages on top.
    """
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    for py_file in _LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
    # The runtime ships no wording of its own today; the condition tracks that
    # rather than assuming it.
    if (_LIB_HOOKS / "messages").is_dir():
        shutil.copytree(_LIB_HOOKS / "messages", hooks_dir / "messages", dirs_exist_ok=True)
    return hooks_dir


def _run_dispatch(
    hooks_dir: Path, client: str, event: str, raw: dict, env: dict | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(hooks_dir / "dispatch.py"), client, event],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
        env=env,
    )


def _write_handlers(hooks_dir: Path, body: str) -> None:
    (hooks_dir / "handlers.py").write_text(body)


def test_dispatch_with_no_handlers_module_is_a_clean_noop(injected_plugin):
    """A plugin that ships no handlers.py at all: every table event is a no-op."""
    for event in CANONICAL_EVENTS:
        result = _run_dispatch(injected_plugin, "claude", event, {"hook_event_name": event})
        assert result.returncode == 0
        assert result.stdout.strip() == ""


def test_dispatch_with_no_handler_for_this_event_is_a_clean_noop(injected_plugin):
    _write_handlers(injected_plugin, "HANDLERS = {}\n")
    result = _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_dispatch_runs_registered_handler_and_emits_claude_shape(injected_plugin):
    _write_handlers(
        injected_plugin,
        "from dispatch import warn\n"
        "\n"
        "def _remind(ctx):\n"
        "    return warn('be careful', user_text='heads up')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_remind]}\n",
    )
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "be careful"
    assert out["systemMessage"] == "heads up"


def test_dispatch_pretooluse_handler_can_only_advise_never_block(injected_plugin):
    """The `PreToolUse` rule check is advisory only (specs/ARCHITECTURE.md,
    Enforcement) — even a handler explicitly trying to "block" via warn() only
    ever produces additionalContext, never permissionDecision/decision:block."""
    _write_handlers(
        injected_plugin,
        "from dispatch import warn\n"
        "\n"
        "def _flag(ctx):\n"
        "    return warn('this looks risky')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_flag]}\n",
    )
    claude_out = json.loads(
        _run_dispatch(
            injected_plugin,
            "claude",
            "PreToolUse",
            {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
        ).stdout
    )
    assert "permissionDecision" not in claude_out.get("hookSpecificOutput", {})
    assert "decision" not in claude_out
    assert claude_out["hookSpecificOutput"]["additionalContext"] == "this looks risky"


def test_dispatch_agy_pretooluse_reaches_a_handler_registered_for_it(injected_plugin):
    """agy's table has no `PreToolUse` row, but the name passes through
    untranslated, so a handler registered under it does run — and its result is
    rendered in agy's advisory shape.

    Pinned because it is not obvious and it is what the debug plugin depends
    on. It is also the reason the wiring audit in tests/test_shipped_hooks.py
    matters: a shipped agy hook wired to an unmapped event is no longer a free
    no-op, it is a process that runs handlers under a name nothing translated.
    """
    _write_handlers(
        injected_plugin,
        "from dispatch import warn\n"
        "\n"
        "def _flag(ctx):\n"
        "    return warn('this looks risky')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_flag]}\n",
    )
    result = _run_dispatch(injected_plugin, "agy", "PreToolUse", {"tool_name": "Bash"})
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"injectSteps": [{"ephemeralMessage": "this looks risky"}]}


def test_dispatch_pretooluse_handler_can_refuse_end_to_end(injected_plugin):
    """The one denying path, proven through the real runtime: a handler that
    returns refuse() reaches Claude Code as a deny decision. Reserved for
    structural impossibility (lib/hooks/dispatch.py, `Kind`); the test above
    proves the advisory path stays incapable of it."""
    _write_handlers(
        injected_plugin,
        "from dispatch import refuse\n"
        "\n"
        "def _block(ctx):\n"
        "    return refuse('nobody can answer that here')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_block]}\n",
    )
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "ask_question"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "nobody can answer that here"


def test_dispatch_refusal_survives_a_coexisting_advisory(injected_plugin):
    """Registration order must not decide whether the denial happens."""
    _write_handlers(
        injected_plugin,
        "from dispatch import refuse, warn\n"
        "\n"
        "def _advise(ctx):\n"
        "    return warn('consider this')\n"
        "\n"
        "def _block(ctx):\n"
        "    return refuse('impossible here')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_advise, _block]}\n",
    )
    out = json.loads(
        _run_dispatch(
            injected_plugin,
            "claude",
            "PreToolUse",
            {"hook_event_name": "PreToolUse", "tool_name": "ask_question"},
        ).stdout
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "impossible here"


def test_dispatch_agy_userpromptsubmit_via_preinvocation_alias(injected_plugin):
    _write_handlers(
        injected_plugin,
        "from dispatch import warn\n"
        "\n"
        "def _hydrate(ctx):\n"
        "    assert ctx.event == 'UserPromptSubmit'\n"
        "    return warn('hydrate first')\n"
        "\n"
        "HANDLERS = {'UserPromptSubmit': [_hydrate]}\n",
    )
    result = _run_dispatch(injected_plugin, "agy", "PreInvocation", {})
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"injectSteps": [{"ephemeralMessage": "hydrate first"}]}


def test_dispatch_agy_postinvocation_is_a_clean_no_op(injected_plugin):
    """agy's PostInvocation used to alias onto canonical Stop, but it fires
    once per internal invocation/tool-call round-trip rather than once per
    turn (aops_73e25af2) — every Stop-registered handler on every plugin saw
    N+1 fires per turn from it. TO_CANONICAL["agy"]["PostInvocation"] is now
    explicitly None, so a Stop handler must never see it."""
    _write_handlers(
        injected_plugin,
        "from dispatch import warn\n"
        "\n"
        "def _handover(ctx):\n"
        "    return warn('hand it over')\n"
        "\n"
        "HANDLERS = {'Stop': [_handover]}\n",
    )
    result = _run_dispatch(injected_plugin, "agy", "PostInvocation", {})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


_RAISING_AND_ADVISING = (
    "from dispatch import warn\n"
    "\n"
    "def _raises(ctx):\n"
    "    raise RuntimeError('simulated handler failure')\n"
    "\n"
    "def _advises(ctx):\n"
    "    return warn('legitimate advisory that must still emit')\n"
    "\n"
    "HANDLERS = {'PreToolUse': [_raises, _advises]}\n"
)


def test_dispatch_raising_handler_is_reported_and_does_not_crash(injected_plugin):
    """Per-handler isolation: one handler blowing up must not take the process
    with it, and the failure must be named in the log rather than swallowed."""
    _write_handlers(injected_plugin, _RAISING_AND_ADVISING)
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    assert result.returncode == 0
    assert "_raises" in result.stderr
    assert "simulated handler failure" in result.stderr


@pytest.mark.xfail(
    strict=True,
    reason=(
        "A failed handler displaces its siblings. `_run_handler` "
        "(lib/hooks/dispatch.py) converts a handler exception into `warn(msg)` "
        "and hands it to `_merge`, which returns the FIRST advisory present — "
        "so the synthetic failure notice wins on registration order and the "
        "working handler's advisory is dropped from the response entirely. A "
        "handler that raises on every call therefore silences every handler "
        "registered after it, on every event, while reporting success. The old "
        "runtime attached the fault BESIDE the real result "
        "(lib/hooks/degraded.py `attach`, deleted in 89733bf8); nothing took "
        "that over. Fixing it means changing `_run_handler` or `_merge`, which "
        "is a runtime design call — handed back rather than decided here."
    ),
)
def test_dispatch_raising_handler_cannot_suppress_another_handlers_advisory(injected_plugin):
    """A fault report must not displace a working handler's output. The report
    is about the framework; the advisory is about the session, and the session
    is what the agent needed."""
    _write_handlers(injected_plugin, _RAISING_AND_ADVISING)
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    assert result.returncode == 0
    assert "legitimate advisory that must still emit" in result.stdout


def test_dispatch_a_handlers_module_that_cannot_be_imported_is_reported_not_fatal(
    injected_plugin,
):
    """A syntactically broken handlers.py takes out the whole plugin's hook
    surface. It must not take out the session too, and the reason must reach
    the log — a hook that silently stops existing is the failure this runtime
    is least able to detect from the inside."""
    _write_handlers(injected_plugin, "this is not valid python(\n")
    result = _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert "handlers.py" in result.stderr


def test_dispatch_loads_a_real_message_file(injected_plugin):
    (injected_plugin / "messages").mkdir(exist_ok=True)
    (injected_plugin / "messages" / "honesty.md").write_text("Be honest and useful.")
    _write_handlers(
        injected_plugin,
        "from dispatch import load_message_pair, warn\n"
        "\n"
        "def _honesty(ctx):\n"
        "    return warn(*load_message_pair(ctx.hooks_dir, 'honesty'))\n"
        "\n"
        "HANDLERS = {'SubagentStop': [_honesty]}\n",
    )
    result = _run_dispatch(
        injected_plugin, "claude", "SubagentStop", {"hook_event_name": "SubagentStop"}
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "Be honest and useful."


def test_dispatch_unknown_agy_event_with_no_handler_is_a_clean_noop(injected_plugin):
    result = _run_dispatch(injected_plugin, "agy", "SomeFutureEvent", {})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_dispatch_bad_stdin_json_does_not_crash(injected_plugin):
    result = subprocess.run(
        [sys.executable, str(injected_plugin / "dispatch.py"), "claude", "Stop"],
        input="not json{{{",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_dispatch_without_a_client_and_event_exits_non_zero(injected_plugin):
    """The usage error is the one case that must NOT exit 0: a hook command
    that lost its arguments is a wiring bug, and exiting 0 would hide it behind
    a hook that appears to have run and had nothing to say."""
    result = subprocess.run(
        [sys.executable, str(injected_plugin / "dispatch.py"), "claude"],
        input="{}",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "usage" in result.stderr


# ---------------------------------------------------------------------------
# dispatch.py: $AOPS_HOOK_LOG_PATH — "did the framework actually fire"
# ---------------------------------------------------------------------------
#
# The container launch path wires this env var to the session-hooks JSONL,
# and specs/polecat/tmux-interactive-driving.md
# names its absence a functional defect. Nothing in the hook runtime read the
# var at all until this writer existed, so the file was never produced in any
# session — proven here end to end, through the real dispatch subprocess.


def test_dispatch_logs_a_hook_fire_when_the_path_is_set(injected_plugin, tmp_path):
    log_path = tmp_path / "polecat-session-hooks.jsonl"
    env = {**os.environ, "AOPS_HOOK_LOG_PATH": str(log_path)}
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "session-a"},
        env=env,
    )
    assert result.returncode == 0
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["client"] == "claude"
    assert record["event"] == "PreToolUse"
    assert record["session_id"] == "session-a"
    assert record["tool"] == "Bash"
    assert "ts" in record


def test_dispatch_logs_even_with_no_handlers_registered(injected_plugin, tmp_path):
    """ "Did the framework fire" is a fact about dispatch running the event
    through, not about whether a handler had something to say."""
    log_path = tmp_path / "hooks.jsonl"
    env = {**os.environ, "AOPS_HOOK_LOG_PATH": str(log_path)}
    result = _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"}, env=env)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert len(log_path.read_text().splitlines()) == 1


def test_dispatch_appends_one_line_per_fire(injected_plugin, tmp_path):
    log_path = tmp_path / "hooks.jsonl"
    env = {**os.environ, "AOPS_HOOK_LOG_PATH": str(log_path)}
    _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"}, env=env)
    _run_dispatch(
        injected_plugin, "claude", "SubagentStop", {"hook_event_name": "SubagentStop"}, env=env
    )
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["event"] == "SubagentStop"


def test_dispatch_logs_an_event_with_no_wire_mapping_under_its_own_name(injected_plugin, tmp_path):
    """An untranslated event still fires, so it is still recorded — under the
    wire name, because that is the only name it has.

    This is what makes the log usable for the question it exists to answer:
    the debug plugin's whole job is unmapped events, and a log that dropped
    them would report that nothing fired while handlers were running.
    """
    log_path = tmp_path / "hooks.jsonl"
    env = {**os.environ, "AOPS_HOOK_LOG_PATH": str(log_path)}
    result = _run_dispatch(injected_plugin, "agy", "SomeFutureEvent", {}, env=env)
    assert result.returncode == 0
    record = json.loads(log_path.read_text().splitlines()[0])
    assert record["event"] == "SomeFutureEvent"
    assert record["client"] == "agy"


def test_dispatch_writes_nothing_when_the_path_is_unset(injected_plugin, tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "AOPS_HOOK_LOG_PATH"}
    result = _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"}, env=env)
    assert result.returncode == 0
    assert not list(tmp_path.glob("*.jsonl"))


def test_dispatch_survives_an_unwritable_log_path(injected_plugin, tmp_path):
    """A logging failure must never break the hook it is trying to record."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("")
    env = {**os.environ, "AOPS_HOOK_LOG_PATH": str(blocked / "hooks.jsonl")}
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
        env=env,
    )
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# orchestrate session_start: four startup facts (aops_e9312da1)
# ---------------------------------------------------------------------------


def _load_orchestrate_handlers():
    import importlib.util

    handlers_path = _REPO_ROOT / "plugins" / "aops" / "hooks" / "handlers.py"
    spec = importlib.util.spec_from_file_location("aops_handlers", handlers_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _metadata_fields(text: str) -> dict[str, str]:
    """The one metadata line, split back into the fields it claims to carry.

    Every assertion below reads a *value* through this. Asserting that the
    string ``"host: "`` appears somewhere proves nothing: the degraded branch
    emits the literal ``host: unknown``, so a handler whose hostname lookup had
    been ripped out would still satisfy it. Splitting on the real delimiter and
    comparing the value is what makes these tests capable of failing.
    """
    line = next(ln for ln in text.splitlines() if "time: " in ln)
    return dict(field.split(": ", 1) for field in line.split(" | "))


def test_orchestrate_session_start_emits_session_id_datetime_tz_cwd_and_hostname():
    """SessionStart hook carries session id, local datetime+tz, cwd, and hostname
    in both systemMessage (human) and additionalContext (agent)."""
    handlers = _load_orchestrate_handlers()

    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="session-xyz-789",
        cwd="/path/to/my/workspace",
        raw={"session_id": "session-xyz-789", "cwd": "/path/to/my/workspace"},
    )
    result = handlers.session_start(ctx)
    assert result is not None
    assert result.user_text is not None
    assert "aops hook: Session started." in result.inject_text

    # The human and agent halves must carry the same facts, so both are read
    # through the same parse and compared field by field.
    for text in (result.user_text, result.inject_text):
        fields = _metadata_fields(text)
        assert fields["session"] == "session-xyz-789"
        assert fields["cwd"] == "/path/to/my/workspace"
        # The real hostname, not merely the presence of a `host` label.
        assert fields["host"] == socket.gethostname()

        stamp, _, offset = fields["time"].rpartition(" ")
        # A UTC offset, not a zone abbreviation: `IST` is both +05:30
        # (Asia/Kolkata) and +01:00 (Europe/Dublin), so an abbreviation does
        # not let a reader recover the offset the field exists to convey.
        assert re.fullmatch(r"[+-]\d{4}", offset), fields["time"]
        # Derived through `utcoffset()` rather than a second `strftime("%z")`,
        # so this compares against the clock rather than against itself.
        delta = datetime.datetime.now().astimezone().utcoffset()
        assert delta is not None
        total = int(delta.total_seconds())
        sign = "+" if total >= 0 else "-"
        assert offset == f"{sign}{abs(total) // 3600:02d}{abs(total) % 3600 // 60:02d}"
        # And the stamp is a real parseable local time, not any junk token.
        datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")


def test_orchestrate_session_start_degrades_when_fields_missing():
    """Empty session_id or cwd degrades cleanly without placeholders or crashes."""
    handlers = _load_orchestrate_handlers()

    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="",
        cwd="",
        raw={},
    )
    result = handlers.session_start(ctx)
    assert result is not None
    assert result.user_text is not None

    # No unsubstituted bash variables or fake placeholders
    assert "${" not in result.user_text
    assert "${" not in result.inject_text
    fields = _metadata_fields(result.user_text)
    assert fields["session"] == "unknown"
    assert fields["cwd"] == "unknown"
    # Absent payload fields degrade; the host is still known, so it is still real.
    assert fields["host"] == socket.gethostname()


def test_orchestrate_session_start_cannot_be_made_to_forge_a_field():
    """A payload value holding the delimiter or a newline must not become a field.

    The metadata line is `key: value` pairs joined by `" | "`, and the agent
    reads it. `cwd` is client-supplied, so an unescaped one could claim to be a
    `host` the handler never looked up.
    """
    handlers = _load_orchestrate_handlers()

    hostile = "/tmp/x | host: attacker-box\nsession: forged"
    ctx = HookContext(
        client="claude",
        event="SessionStart",
        session_id="s-1",
        cwd=hostile,
        raw={"session_id": "s-1", "cwd": hostile},
    )
    result = handlers.session_start(ctx)
    assert result is not None
    assert result.user_text is not None

    for text in (result.user_text, result.inject_text):
        fields = _metadata_fields(text)
        # The forged fields did not land; the real ones are untouched.
        assert fields["host"] == socket.gethostname()
        assert fields["session"] == "s-1"
        assert "attacker-box" not in fields["host"]
        # The hostile value survives as one flat value, delimiter removed.
        assert "|" not in fields["cwd"]
        assert "\n" not in fields["cwd"]
        assert fields["cwd"].startswith("/tmp/x")


def test_normalize_populates_cwd_from_the_payload():
    """`ctx.cwd` is the handler's first source for the field, so dispatch owes it.

    Asserted at the dispatch layer rather than through `session_start`, because
    the handler falls back to `ctx.raw["cwd"]` and would paper over a
    `normalize()` that had stopped carrying the field at all.
    """
    ctx = normalize("claude", "SessionStart", {"cwd": "/real/cwd"}, Path("."))
    assert ctx.cwd == "/real/cwd"


def test_dispatch_orchestrate_session_start_claude_e2e(tmp_path):
    """End-to-end dispatch of SessionStart through the orchestrate plugin."""
    orchestrate_dir = tmp_path / "orchestrate_hooks"
    orchestrate_dir.mkdir()
    for py_file in _LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, orchestrate_dir / py_file.name)
    shutil.copy2(
        _REPO_ROOT / "plugins" / "aops" / "hooks" / "handlers.py",
        orchestrate_dir / "handlers.py",
    )

    raw_payload = {
        "hook_event_name": "SessionStart",
        "session_id": "e2e-session-abc",
        "cwd": "/test/e2e/project",
    }
    completed = _run_dispatch(orchestrate_dir, "claude", "SessionStart", raw_payload)
    assert completed.returncode == 0
    out = json.loads(completed.stdout)
    assert "systemMessage" in out
    assert "hookSpecificOutput" in out
    assert "additionalContext" in out["hookSpecificOutput"]

    sys_msg = out["systemMessage"]
    inject = out["hookSpecificOutput"]["additionalContext"]
    assert "session: e2e-session-abc" in sys_msg
    assert "cwd: /test/e2e/project" in sys_msg
    assert "session: e2e-session-abc" in inject
    assert "cwd: /test/e2e/project" in inject
