"""Tests for the shared hook runtime (lib/hooks/).

lib/hooks/ is copied byte-identical into every plugin that hooks (see
specs/ARCHITECTURE.md, Hooks). These tests exercise it in place, plus in a
synthetic "injected" plugin directory (dispatch.py + a handlers.py + a
messages/ dir side by side) to prove the handler-registration and
message-loading contracts a plugin author relies on.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_DISPATCH = _LIB_HOOKS / "dispatch.py"

if str(_LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIB_HOOKS))

import clients  # noqa: E402
import credentials  # noqa: E402
import degraded  # noqa: E402
import messages  # noqa: E402
import telemetry  # noqa: E402
from result import Result, merge, refuse, warn  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_degradation_state(monkeypatch, tmp_path):
    """degraded.py holds two pieces of state a test must not inherit: the
    faults recorded so far (module scope, because one hook invocation is one
    process) and the once-per-session markers it writes under the OS temp
    directory, which outlive the run that made them."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    degraded.reset()
    yield
    degraded.reset()


# ---------------------------------------------------------------------------
# clients.py: event-name normalization
# ---------------------------------------------------------------------------


def test_claude_events_are_identity_mapped_for_the_full_architecture_table():
    for event in clients.CANONICAL_EVENTS:
        assert clients.to_canonical("claude", event) == event


def test_agy_known_event_aliases():
    assert clients.to_canonical("agy", "PreInvocation") == "UserPromptSubmit"
    assert clients.to_canonical("agy", "PostInvocation") == "Stop"


@pytest.mark.parametrize("event", ["SessionStart", "PreToolUse", "SubagentStop"])
def test_agy_unmapped_architecture_events_return_none(event):
    """No confirmed agy wire equivalent exists yet for these — a clean no-op,
    not a guess."""
    assert clients.to_canonical("agy", event) is None


def test_unknown_client_has_no_mappings():
    assert clients.to_canonical("gemini", "PreToolUse") is None


# ---------------------------------------------------------------------------
# clients.py: response rendering
# ---------------------------------------------------------------------------


def test_render_nothing_to_say_is_empty_dict_both_clients():
    assert clients.render("claude", "PreToolUse", None) == {}
    assert clients.render("agy", "UserPromptSubmit", None) == {}


def test_render_claude_pretooluse_warn_uses_additional_context_never_permission_decision():
    """cope's PreToolUse rule enforcement is advisory only (specs/ARCHITECTURE.md,
    Enforcement) — nothing in-session blocks on a hook verdict, so this shape
    must never carry permissionDecision."""
    out = clients.render("claude", "PreToolUse", warn("careful"))
    assert "permissionDecision" not in out["hookSpecificOutput"]
    assert out["hookSpecificOutput"]["additionalContext"] == "careful"


def test_render_claude_stop_uses_additional_context_never_top_level_decision():
    out = clients.render("claude", "Stop", warn("reflect first"))
    assert "decision" not in out
    assert out["hookSpecificOutput"]["additionalContext"] == "reflect first"


def test_render_claude_subagentstop_warn_uses_additional_context():
    out = clients.render("claude", "SubagentStop", warn("reflect first"))
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
            "additionalContext": "reflect first",
        }
    }
    assert "decision" not in out


def test_render_claude_warn_with_user_text_adds_system_message():
    out = clients.render("claude", "Stop", warn("reflect first", user_text="heads up"))
    assert out["systemMessage"] == "heads up"
    assert out["hookSpecificOutput"]["additionalContext"] == "reflect first"


def test_render_agy_warn_uses_inject_steps():
    out = clients.render("agy", "UserPromptSubmit", warn("careful"))
    assert out == {"injectSteps": [{"ephemeralMessage": "careful"}]}


def test_render_unknown_client_raises():
    with pytest.raises(ValueError):
        clients.render("gemini", "Stop", warn("x"))


# ---------------------------------------------------------------------------
# clients.py: the refusal shape, per client
# ---------------------------------------------------------------------------


def test_render_claude_refusal_is_a_deny_permission_decision():
    """The one blocking shape Claude Code understands. A refusal carries no
    additionalContext — the reason IS the denial reason."""
    out = clients.render("claude", "PreToolUse", refuse("nobody is here to answer"))
    assert out == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "nobody is here to answer",
        }
    }
    assert "additionalContext" not in out["hookSpecificOutput"]


def test_render_agy_refusal_is_a_deny_decision_with_a_reason():
    """agy's own blocking shape, as its `PreToolUse` contract defines it: a
    `decision` of allow/deny/ask, with `reason` alongside. Unreachable today —
    no agy tool event is mapped (see to_canonical below) — but the shape must
    be right the day one is, and wrong-by-omission is how a silent no-op ships."""
    out = clients.render("agy", "PreToolUse", refuse("nobody is here to answer"))
    assert out == {"decision": "deny", "reason": "nobody is here to answer"}
    assert clients.to_canonical("agy", "PreToolUse") is None


def test_render_advisory_never_carries_a_blocking_field_on_either_client():
    """The other half of the guard: warn() must stay incapable of blocking, on
    every event and every client, so cope's advisories can never become a gate."""
    for event in clients.CANONICAL_EVENTS:
        claude_out = json.dumps(clients.render("claude", event, warn("careful")))
        assert "permissionDecision" not in claude_out
        assert "decision" not in claude_out
    agy_out = json.dumps(clients.render("agy", "UserPromptSubmit", warn("careful")))
    assert "decision" not in agy_out
    assert "reason" not in agy_out


# ---------------------------------------------------------------------------
# result.py: merge semantics (a refusal beats an advisory; else first wins)
# ---------------------------------------------------------------------------


def test_merge_first_advisory_wins_regardless_of_registration_order():
    assert merge([None, warn("careful"), None]) == warn("careful")
    assert merge([warn("first"), warn("second")]) == warn("first")
    assert merge([None, None]) is None
    assert merge([]) is None


def test_merge_refusal_beats_an_advisory_registered_before_it():
    """A session that structurally cannot carry out the call must not have that
    fact hidden behind an earlier handler's suggestion."""
    assert merge([warn("careful"), refuse("impossible")]) == refuse("impossible")
    assert merge([refuse("impossible"), warn("careful")]) == refuse("impossible")


def test_merge_first_refusal_wins_among_refusals():
    assert merge([refuse("first"), refuse("second")]) == refuse("first")


def test_warn_is_never_a_refusal():
    assert warn("careful").is_refusal is False
    assert refuse("impossible").is_refusal is True


# ---------------------------------------------------------------------------
# messages.py: markdown-only wording contract
# ---------------------------------------------------------------------------


def test_messages_load_returns_stripped_text(tmp_path):
    (tmp_path / "messages").mkdir()
    (tmp_path / "messages" / "handover.md").write_text("\n  hand it over cleanly  \n")
    assert messages.load(tmp_path, "handover") == "hand it over cleanly"


def test_messages_load_missing_file_is_a_hard_error(tmp_path):
    with pytest.raises(messages.MessageNotFoundError):
        messages.load(tmp_path, "nonexistent")


def test_messages_load_empty_file_is_a_hard_error(tmp_path):
    (tmp_path / "messages").mkdir()
    (tmp_path / "messages" / "blank.md").write_text("   \n")
    with pytest.raises(messages.MessageNotFoundError):
        messages.load(tmp_path, "blank")


# --- the second reader: <name>.user.md ---------------------------------------
#
# A message has two audiences with opposite needs — the agent, where length
# buys precision, and the person watching, where it buys nothing. The short
# version lives in a sibling file so that adding one cannot disturb the text
# already going to the agent, and so this module needs no frontmatter parser
# inside a hook subprocess that has only the standard library.


def _message(tmp_path, name: str, agent: str, user: str | None = None) -> None:
    (tmp_path / "messages").mkdir(exist_ok=True)
    (tmp_path / "messages" / f"{name}.md").write_text(agent)
    if user is not None:
        (tmp_path / "messages" / f"{name}.user.md").write_text(user)


def test_message_with_a_user_version_loads_both(tmp_path):
    _message(tmp_path, "handover", "The long form, for the agent.", "  short line  \n")
    assert messages.load_pair(tmp_path, "handover") == (
        "The long form, for the agent.",
        "short line",
    )


def test_message_without_a_user_version_is_not_an_error(tmp_path):
    """The ordinary case. A hook with nothing worth putting in a status line
    says nothing there, and still injects its agent-facing text."""
    _message(tmp_path, "handover", "The long form, for the agent.")
    agent, user = messages.load_pair(tmp_path, "handover")
    assert agent == "The long form, for the agent."
    assert user is None


def test_empty_user_version_reads_as_absent(tmp_path):
    """A blank line in the user's terminal is worse than silence, so an empty
    sibling is `None` rather than `""` — unlike the agent's message, where
    empty is a hard error because something was meant to be injected."""
    _message(tmp_path, "handover", "The long form.", "   \n")
    assert messages.load_pair(tmp_path, "handover")[1] is None


def test_missing_agent_message_still_raises_even_with_a_user_version(tmp_path):
    """The user's line is an addition, never a substitute: it cannot stand in
    for the message the agent was supposed to receive."""
    (tmp_path / "messages").mkdir()
    (tmp_path / "messages" / "orphan.user.md").write_text("short line")
    with pytest.raises(messages.MessageNotFoundError):
        messages.load_pair(tmp_path, "orphan")


def test_claude_carries_the_user_line_on_an_advisory_and_a_refusal():
    """Claude Code has a channel for each reader, and both must be used. The
    refusal case matters most: the agent is told no, and this line is the only
    sign the user gets that a hook intervened."""
    advisory = clients.render("claude", "Stop", warn("long form", "short line"))
    assert advisory["hookSpecificOutput"]["additionalContext"] == "long form"
    assert advisory["systemMessage"] == "short line"

    refusal = clients.render("claude", "PreToolUse", refuse("long form", "short line"))
    assert refusal["hookSpecificOutput"]["permissionDecisionReason"] == "long form"
    assert refusal["systemMessage"] == "short line"


def test_claude_omits_the_user_line_when_there_is_none():
    assert "systemMessage" not in clients.render("claude", "Stop", warn("long form"))


def test_agy_drops_the_user_line_rather_than_misdirecting_it():
    """agy has no user-facing channel — its response steps (`ephemeralMessage`,
    `userMessage`, `toolCall`) all speak to the agent, and `userMessage` would
    put the framework's words in the person's mouth. So the line is dropped,
    and this pins that it is dropped deliberately rather than leaking onto an
    agent-facing surface."""
    out = clients.render("agy", "UserPromptSubmit", warn("long form", "short line"))
    assert out == {"injectSteps": [{"ephemeralMessage": "long form"}]}
    assert "short line" not in json.dumps(out)


# --- the second reader, across the plugins that actually ship ----------------
#
# `HookContext.message` returns one string. A handler that loads a message
# that way cannot deliver the user's line no matter what is in the sibling
# file — the pair has to come through `messages.load_pair`. That failure is
# silent in every direction: the file is present, the tests that read it pass,
# the build ships it, and the line never reaches a terminal. So it is checked
# against the source of every plugin that hooks, not left to each plugin's own
# suite to notice.

_PLUGINS_ROOT = _REPO_ROOT / "plugins"

# `ctx.message("name")` — the single-text load, and the only way a shipped
# `.user.md` can be silently unreachable.
_SINGLE_TEXT_LOAD = re.compile(r"""ctx\.message\(\s*["']([\w.-]+)["']""")


def _hooking_plugins() -> list[Path]:
    return sorted(p for p in _PLUGINS_ROOT.glob("*/hooks") if (p / "handlers.py").is_file())


def test_every_plugin_that_hooks_is_discovered():
    """The guard below is a loop over plugins; an empty loop passes silently."""
    assert _hooking_plugins(), f"no plugin under {_PLUGINS_ROOT} ships a hooks/handlers.py"


def test_no_shipped_user_line_is_stranded_on_the_single_text_path():
    stranded = []
    for hooks in _hooking_plugins():
        single_text = set(_SINGLE_TEXT_LOAD.findall((hooks / "handlers.py").read_text()))
        for user_file in sorted((hooks / "messages").glob("*.user.md")):
            name = user_file.name.removesuffix(".user.md")
            if name in single_text:
                stranded.append(f"{hooks.parent.name}: {user_file.name}")
    assert stranded == [], (
        "these user-facing lines ship but can never reach a terminal — their handler "
        "loads the message with ctx.message(), which returns the agent's text only. "
        f"Use messages.load_pair(ctx.hooks_dir, name) instead: {stranded}"
    )


def test_no_shipped_user_line_lacks_the_agent_message_it_belongs_to():
    """`load_pair` raises on a missing agent message, so this ships as a hook
    that hard-fails the moment it fires. Caught in the tree instead."""
    orphans = [
        f"{hooks.parent.name}: {user_file.name}"
        for hooks in _hooking_plugins()
        for user_file in sorted((hooks / "messages").glob("*.user.md"))
        if not (hooks / "messages" / f"{user_file.name.removesuffix('.user.md')}.md").is_file()
    ]
    assert orphans == [], f"user-facing lines with no agent message beside them: {orphans}"


# ---------------------------------------------------------------------------
# telemetry.py: reports only, never sets/defaults
# ---------------------------------------------------------------------------


def test_telemetry_report_not_configured(monkeypatch):
    for var in telemetry.CONTRACT:
        monkeypatch.delenv(var, raising=False)
    assert telemetry.report() == "telemetry: not configured"
    assert telemetry.configured_vars() == []


def test_telemetry_report_configured_and_enabled(monkeypatch):
    for var in telemetry.CONTRACT:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
    report = telemetry.report()
    assert "enabled" in report
    assert "2/" in report


def test_telemetry_report_never_mutates_environment(monkeypatch):
    for var in telemetry.CONTRACT:
        monkeypatch.delenv(var, raising=False)
    telemetry.report()
    telemetry.configured_vars()
    for var in telemetry.CONTRACT:
        assert var not in os.environ


# ---------------------------------------------------------------------------
# credentials.py: SessionStart env-file isolation for container sessions
# ---------------------------------------------------------------------------


def test_isolate_noop_without_env_file(monkeypatch):
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    assert credentials.isolate({}) is None


def test_isolate_writes_scoped_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "env.sh"
    env_file.write_text("")
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    monkeypatch.setenv("AOPS_BOT_GH_TOKEN", "mock-bot-token")
    monkeypatch.setenv("PKB_MCP_URL", "http://mock-mcp-url")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    persisted = credentials.isolate({"session_id": "test-session-12345"})

    assert persisted is not None
    assert persisted["AOPS_SESSION_ID"] == "test-session-12345"
    assert persisted["AOPS_BOT_GH_TOKEN"] == "mock-bot-token"
    assert persisted["GH_TOKEN"] == "mock-bot-token"
    assert persisted["GITHUB_TOKEN"] == "mock-bot-token"

    content = env_file.read_text()
    assert "export AOPS_BOT_GH_TOKEN=mock-bot-token\n" in content
    assert "export GH_TOKEN=mock-bot-token\n" in content
    assert "export GITHUB_TOKEN=mock-bot-token\n" in content
    assert "export PKB_MCP_URL=http://mock-mcp-url\n" in content
    assert "GEMINI_API_KEY" not in content


def test_isolate_without_bot_token_skips_git_shim(tmp_path, monkeypatch):
    env_file = tmp_path / "env.sh"
    env_file.write_text("")
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    monkeypatch.delenv("AOPS_BOT_GH_TOKEN", raising=False)

    persisted = credentials.isolate({})

    assert persisted is not None
    assert "GH_TOKEN" not in persisted
    assert "GIT_CONFIG_COUNT" not in persisted


# ---------------------------------------------------------------------------
# dispatch.py: end-to-end, both clients, every table event
# ---------------------------------------------------------------------------


@pytest.fixture()
def injected_plugin(tmp_path):
    """A synthetic plugin hooks/ dir: lib/hooks/ copied in (as the build does —
    the runtime modules AND the messages the runtime itself loads), plus this
    fixture's caller adds handlers.py / its own messages on top.
    """
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    for py_file in _LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
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


def test_dispatch_with_no_handlers_module_is_a_clean_noop(injected_plugin):
    """A plugin that ships no handlers.py at all: every table event is a no-op."""
    for event in clients.CANONICAL_EVENTS:
        result = _run_dispatch(injected_plugin, "claude", event, {"hook_event_name": event})
        assert result.returncode == 0
        assert result.stdout.strip() == ""


def test_dispatch_with_no_handler_for_this_event_is_a_clean_noop(injected_plugin):
    (injected_plugin / "handlers.py").write_text("HANDLERS = {}\n")
    result = _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def _write_handlers(hooks_dir: Path, body: str) -> None:
    (hooks_dir / "handlers.py").write_text(body)


def test_dispatch_runs_registered_handler_and_emits_claude_shape(injected_plugin):
    _write_handlers(
        injected_plugin,
        "from result import warn\n"
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
    """cope's PreToolUse rule enforcement is advisory only (specs/ARCHITECTURE.md,
    Enforcement) — even a handler explicitly trying to "block" via warn() only
    ever produces additionalContext, never permissionDecision/decision:block."""
    _write_handlers(
        injected_plugin,
        "from result import warn\n\ndef _flag(ctx):\n    return warn('this looks risky')\n\nHANDLERS = {'PreToolUse': [_flag]}\n",
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

    # agy has no wire mapping for PreToolUse yet (see clients.py) — clean no-op.
    agy_result = _run_dispatch(injected_plugin, "agy", "PreToolUse", {"tool_name": "Bash"})
    assert agy_result.returncode == 0
    assert agy_result.stdout.strip() == ""


def test_dispatch_pretooluse_handler_can_refuse_end_to_end(injected_plugin):
    """The one blocking path, proven through the real runtime: a handler that
    returns refuse() reaches Claude Code as a deny decision. Reserved for
    structural impossibility (lib/hooks/result.py); the test above proves the
    advisory path stays incapable of it."""
    _write_handlers(
        injected_plugin,
        "from result import refuse\n\ndef _block(ctx):\n    return refuse('nobody can answer that here')\n\nHANDLERS = {'PreToolUse': [_block]}\n",
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
    """Registration order must not decide whether the block happens."""
    _write_handlers(
        injected_plugin,
        "from result import refuse, warn\n"
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
        "from result import warn\n\ndef _hydrate(ctx):\n    assert ctx.event == 'UserPromptSubmit'\n    return warn('hydrate first')\n\nHANDLERS = {'UserPromptSubmit': [_hydrate]}\n",
    )
    result = _run_dispatch(injected_plugin, "agy", "PreInvocation", {})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out == {"injectSteps": [{"ephemeralMessage": "hydrate first"}]}


def test_dispatch_agy_stop_via_postinvocation_alias(injected_plugin):
    _write_handlers(
        injected_plugin,
        "from result import warn\n\ndef _handover(ctx):\n    assert ctx.event == 'Stop'\n    return warn('hand it over')\n\nHANDLERS = {'Stop': [_handover]}\n",
    )
    result = _run_dispatch(injected_plugin, "agy", "PostInvocation", {})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out == {"injectSteps": [{"ephemeralMessage": "hand it over"}]}


def test_dispatch_raising_handler_cannot_suppress_another_handlers_advisory(injected_plugin):
    _write_handlers(
        injected_plugin,
        "from result import warn\n"
        "\n"
        "def _raises(ctx):\n"
        "    raise RuntimeError('simulated handler failure')\n"
        "\n"
        "def _advises(ctx):\n"
        "    return warn('legitimate advisory that must still emit')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_raises, _advises]}\n",
    )
    result = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"},
    )
    assert result.returncode == 0
    assert "legitimate advisory that must still emit" in result.stdout
    assert "_raises" in result.stderr
    assert "simulated handler failure" in result.stderr


def test_dispatch_missing_message_file_is_isolated_not_fatal(injected_plugin):
    """A handler that names a message file which doesn't exist fails loudly
    (stderr) but does not crash the dispatch or block other handlers."""
    _write_handlers(
        injected_plugin,
        "from result import warn\n"
        "\n"
        "def _missing_message(ctx):\n"
        "    return warn(ctx.message('does-not-exist'))\n"
        "\n"
        "def _still_runs(ctx):\n"
        "    return warn('this one is fine')\n"
        "\n"
        "HANDLERS = {'Stop': [_missing_message, _still_runs]}\n",
    )
    result = _run_dispatch(injected_plugin, "claude", "Stop", {"hook_event_name": "Stop"})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "this one is fine"
    assert "does-not-exist" in result.stderr or "MessageNotFoundError" in result.stderr


def test_dispatch_ctx_message_loads_real_file(injected_plugin):
    (injected_plugin / "messages").mkdir(exist_ok=True)
    (injected_plugin / "messages" / "honesty.md").write_text("Be honest and useful.")
    _write_handlers(
        injected_plugin,
        "from result import warn\n\ndef _honesty(ctx):\n    return warn(ctx.message('honesty'))\n\nHANDLERS = {'SubagentStop': [_honesty]}\n",
    )
    result = _run_dispatch(
        injected_plugin, "claude", "SubagentStop", {"hook_event_name": "SubagentStop"}
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "Be honest and useful."


def test_dispatch_unknown_agy_event_is_a_clean_noop(injected_plugin):
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


# ---------------------------------------------------------------------------
# degraded.py: the framework's own failures, given a reader
# ---------------------------------------------------------------------------
#
# Every one of these failures used to go to stderr and stop there. Nothing
# renders a hook's stderr to the person running the session — the client shows
# them `systemMessage` and nothing else — so a check that stopped working
# stopped working invisibly. These tests are about the wire, because the wire
# is the only place a human can read.


def test_report_writes_the_log_line_it_always_wrote(capsys):
    """stderr is not being replaced. It is the log, it is right for the log,
    and it is the only record that survives the once-per-session gate."""
    degraded.report("a-kind", "cope: something broke", "OSError(2)")
    assert capsys.readouterr().err == "cope: something broke: OSError(2)\n"


def test_report_with_no_detail_logs_the_message_alone(capsys):
    degraded.report("a-kind", "cope: something broke")
    assert capsys.readouterr().err == "cope: something broke\n"


def test_the_two_readers_get_different_things(tmp_path):
    """The person watching needs to know a mechanism they rely on has stopped.
    The agent needs enough to say what and to work around it. One is a
    sentence; the other is the sentence plus the reason."""
    shutil.copytree(_LIB_HOOKS / "messages", tmp_path / "messages")
    degraded.report("a-kind", "cope: the rule evaluator did not answer", "OSError('refused')")

    result = degraded.attach(None, tmp_path, "session-a")

    assert result is not None
    assert result.is_refusal is False
    assert "OSError('refused')" in result.inject_text
    assert result.user_text is not None
    assert "the rule evaluator did not answer" in result.user_text
    assert "OSError('refused')" not in result.user_text
    assert "\n" not in result.user_text


def test_attach_says_nothing_when_nothing_degraded(tmp_path):
    assert degraded.attach(None, tmp_path, "session-a") is None
    assert degraded.attach(warn("careful"), tmp_path, "session-a") == warn("careful")


def test_attach_never_turns_an_advisory_into_a_refusal(tmp_path):
    shutil.copytree(_LIB_HOOKS / "messages", tmp_path / "messages")
    degraded.report("a-kind", "cope: something broke")
    result = degraded.attach(warn("careful", "heads up"), tmp_path, "session-a")
    assert result is not None
    assert result.is_refusal is False
    assert "careful" in result.inject_text
    assert result.user_text is not None
    assert result.user_text.startswith("heads up")


def test_attach_leaves_a_refusals_reason_exactly_as_it_was(tmp_path):
    """The denial reason is the whole contract of a refusal — the agent is
    being told no, and told why. A framework fault is not part of that reason,
    so it goes on the user's line instead."""
    shutil.copytree(_LIB_HOOKS / "messages", tmp_path / "messages")
    degraded.report("a-kind", "cope: something broke")
    result = degraded.attach(refuse("nobody is here to answer", "blocked"), tmp_path, "session-a")
    assert result == Result(
        "nobody is here to answer",
        "blocked cope: something broke — nothing was blocked. Reported once per session.",
        is_refusal=True,
    )


def test_attach_survives_a_missing_message_file(tmp_path):
    """A notice that broke the hook it was reporting on would be the worst
    outcome available here."""
    degraded.report("a-kind", "cope: something broke")
    assert degraded.attach(warn("careful"), tmp_path, "session-a") == warn("careful")


def test_the_degradation_message_pair_ships_with_the_runtime():
    """lib/hooks/ is injected into every plugin that hooks, messages included —
    the runtime loads this pair from the plugin's own hooks/messages/."""
    agent, user = messages.load_pair(_LIB_HOOKS, "degraded")
    assert "{faults}" in agent
    assert user is not None
    assert "{faults}" in user
    assert "\n" not in user, "the user's line is one line in their terminal"


# --- the same, through the real runtime, on the wire -------------------------

# A handler that raises the way a real one does: a bug, a missing message file,
# an evaluator client that threw. dispatch.py isolates it and exits 0.
_RAISING_HANDLERS = (
    "def _evaluate(ctx):\n"
    "    raise RuntimeError('simulated evaluator failure')\n"
    "\n"
    "HANDLERS = {'PreToolUse': [_evaluate]}\n"
)

_TOOL_CALL = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "session-a"}


@pytest.fixture()
def notice_env(tmp_path):
    """The once-per-session gate is a marker file under the OS temp directory,
    so a test asserting on a notice has to own that directory rather than
    inherit markers from another run."""
    marker_root = tmp_path / "os-tmp"
    marker_root.mkdir()
    return {**os.environ, "TMPDIR": str(marker_root)}


def test_a_failed_handler_reaches_the_person_watching(injected_plugin, notice_env):
    _write_handlers(injected_plugin, _RAISING_HANDLERS)
    result = _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)

    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "_evaluate" in out["systemMessage"]
    assert "did not run" in out["systemMessage"]
    assert "simulated evaluator failure" in out["hookSpecificOutput"]["additionalContext"]
    # stderr keeps everything it had, in full
    assert "_evaluate" in result.stderr
    assert "simulated evaluator failure" in result.stderr


def test_a_degradation_notice_is_never_a_gate(injected_plugin, notice_env):
    """Fail-open is the whole point of isolating a handler in the first place.
    Reporting the isolation must not undo it."""
    _write_handlers(injected_plugin, _RAISING_HANDLERS)
    result = _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)

    out = json.loads(result.stdout)
    assert result.returncode == 0
    assert "decision" not in out
    assert "permissionDecision" not in out["hookSpecificOutput"]


def test_the_same_fault_is_announced_once_per_session(injected_plugin, notice_env):
    """These fire on PreToolUse. A line per tool call is a line the user learns
    to skip past, which is worse than no line at all."""
    _write_handlers(injected_plugin, _RAISING_HANDLERS)
    first = _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)
    second = _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)

    assert "systemMessage" in json.loads(first.stdout)
    assert second.stdout.strip() == ""
    assert "simulated evaluator failure" in second.stderr, "the log is never rate-limited"


def test_the_next_session_is_told_too(injected_plugin, notice_env):
    """The gate is per session, not per machine: a new session has a new person
    watching it, and the mechanism is still broken."""
    _write_handlers(injected_plugin, _RAISING_HANDLERS)
    _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)
    later = _run_dispatch(
        injected_plugin,
        "claude",
        "PreToolUse",
        {**_TOOL_CALL, "session_id": "session-b"},
        env=notice_env,
    )
    assert "_evaluate" in json.loads(later.stdout)["systemMessage"]


def test_a_payload_with_no_session_id_stays_on_stderr(injected_plugin, notice_env):
    """Nothing can bound a notice that cannot be keyed to a session, and an
    unbounded line on every tool call is worse than the log by itself."""
    _write_handlers(injected_plugin, _RAISING_HANDLERS)
    raw = {key: value for key, value in _TOOL_CALL.items() if key != "session_id"}
    result = _run_dispatch(injected_plugin, "claude", "PreToolUse", raw, env=notice_env)

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert "simulated evaluator failure" in result.stderr


def test_a_notice_rides_beside_a_real_advisory_without_displacing_it(injected_plugin, notice_env):
    _write_handlers(
        injected_plugin,
        "from result import warn\n"
        "\n"
        "def _evaluate(ctx):\n"
        "    raise RuntimeError('simulated evaluator failure')\n"
        "\n"
        "def _advises(ctx):\n"
        "    return warn('the advisory that must still emit', 'flagged something')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_evaluate, _advises]}\n",
    )
    out = json.loads(
        _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env).stdout
    )

    injected = out["hookSpecificOutput"]["additionalContext"]
    assert injected.startswith("the advisory that must still emit")
    assert "simulated evaluator failure" in injected
    assert out["systemMessage"].startswith("flagged something")
    assert "_evaluate" in out["systemMessage"]
    assert "\n" not in out["systemMessage"]


def test_a_refusal_keeps_its_reason_and_still_reports_the_fault(injected_plugin, notice_env):
    _write_handlers(
        injected_plugin,
        "from result import refuse\n"
        "\n"
        "def _evaluate(ctx):\n"
        "    raise RuntimeError('simulated evaluator failure')\n"
        "\n"
        "def _block(ctx):\n"
        "    return refuse('nobody can answer that here', 'blocked a prompt')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_evaluate, _block]}\n",
    )
    out = json.loads(
        _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env).stdout
    )

    specific = out["hookSpecificOutput"]
    assert specific["permissionDecision"] == "deny"
    assert specific["permissionDecisionReason"] == "nobody can answer that here"
    assert out["systemMessage"].startswith("blocked a prompt")
    assert "_evaluate" in out["systemMessage"]


def test_a_handlers_module_that_cannot_be_imported_is_reported_not_fatal(
    injected_plugin, notice_env
):
    """Every check the plugin ships is gone, and the old behaviour was to exit
    non-zero with the reason on a channel nobody reads."""
    _write_handlers(injected_plugin, "import a_module_that_does_not_exist\n")
    result = _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)

    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "handlers could not be loaded" in out["systemMessage"]
    assert "ModuleNotFoundError" in out["hookSpecificOutput"]["additionalContext"]


def test_a_healthy_hook_says_nothing_about_degradation(injected_plugin, notice_env):
    """The condition this must never become: a line on a session where nothing
    is wrong."""
    _write_handlers(
        injected_plugin,
        "from result import warn\n"
        "\n"
        "def _advises(ctx):\n"
        "    return warn('careful', 'flagged something')\n"
        "\n"
        "HANDLERS = {'PreToolUse': [_advises]}\n",
    )
    result = _run_dispatch(injected_plugin, "claude", "PreToolUse", _TOOL_CALL, env=notice_env)

    assert result.stderr.strip() == ""
    assert json.loads(result.stdout)["systemMessage"] == "flagged something"


def test_a_failed_env_file_write_is_reported(tmp_path, monkeypatch):
    """credentials.isolate is SessionStart's, so its failure means git pushes
    fail later for a reason nothing connects back to this."""
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(tmp_path / "no-such-dir" / "env.sh"))
    monkeypatch.delenv("AOPS_BOT_GH_TOKEN", raising=False)

    persisted = credentials.isolate({"session_id": "session-a"})

    assert persisted is not None  # fail-open: the session still starts
    assert [fault.kind for fault in degraded._faults] == [degraded.CREDENTIALS]
    assert "environment file could not be written" in degraded._faults[0].message
