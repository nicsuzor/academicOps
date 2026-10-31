"""The ida hooks do nothing in a Claude Cowork session.

Cowork, in the Claude desktop app, refuses any MCP call whose input a plugin
hook changed, and the SessionStart hook fails there on the environment it
lacks. So both hook entry points -- ``dispatch.py`` and
``mcp_caller_session.py`` -- exit silently, emitting nothing and changing no
input, when the environment carries the signal Claude Code's own process sets
for a Cowork session, and behave exactly as before without it.

The signal is read from the Claude Code 2.1.314 binary: the host-set variable
``CLAUDE_CODE_IS_COWORK``, and the ``CLAUDE_CODE_ENTRYPOINT`` values the
client itself labels "Cowork" (``local-agent``, ``remote_cowork``, plus the
``remote_cowork_trigger`` scheduled-run entrypoint and the ``local_agent``
spelling it normalises to ``local-agent``). A hook inherits the parent
environment (hooks reference, "Inherited environment").
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
DISPATCH = IDA_HOOKS / "dispatch.py"
CALLER_SESSION = IDA_HOOKS / "mcp_caller_session.py"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))


COWORK_ENVS = [
    pytest.param({"CLAUDE_CODE_IS_COWORK": "1"}, id="is-cowork-1"),
    pytest.param({"CLAUDE_CODE_IS_COWORK": "true"}, id="is-cowork-true"),
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "local-agent"}, id="entrypoint-local-agent"),
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "local_agent"}, id="entrypoint-local_agent"),
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "remote_cowork"}, id="entrypoint-remote_cowork"),
    pytest.param(
        {"CLAUDE_CODE_ENTRYPOINT": "remote_cowork_trigger"},
        id="entrypoint-remote_cowork_trigger",
    ),
]

NOT_COWORK_ENVS = [
    pytest.param({}, id="no-marker"),
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "cli"}, id="entrypoint-cli"),
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "claude-vscode"}, id="entrypoint-vscode"),
    # The desktop app's Code tab is not Cowork.
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "claude-desktop"}, id="entrypoint-desktop"),
    pytest.param({"CLAUDE_CODE_ENTRYPOINT": "remote_desktop"}, id="entrypoint-remote_desktop"),
    # A cloud session is remote but keeps its hooks.
    pytest.param(
        {"CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote"},
        id="cloud-session",
    ),
    pytest.param({"CLAUDE_CODE_IS_COWORK": ""}, id="is-cowork-empty"),
    pytest.param({"CLAUDE_CODE_IS_COWORK": "0"}, id="is-cowork-0"),
    pytest.param({"CLAUDE_CODE_IS_COWORK": "false"}, id="is-cowork-false"),
]

# One payload per event the Cowork failure was observed on, plus Stop.
_PAYLOADS = {
    "SessionStart": {"hook_event_name": "SessionStart", "session_id": "test-session"},
    "UserPromptSubmit": {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "test-session",
        "prompt": "what did we decide about the build?",
    },
    "PreToolUse": {
        "hook_event_name": "PreToolUse",
        "session_id": "test-session",
        "tool_name": "mcp__pkb__search",
        "tool_input": {"query": "observability"},
    },
    "Stop": {"hook_event_name": "Stop", "session_id": "test-session"},
}

_CALLER_SESSION_PAYLOAD = {
    "hook_event_name": "PreToolUse",
    "tool_name": "mcp__pkb__search",
    "session_id": "sess-cowork",
    "prompt_id": "prompt-cowork",
    "tool_use_id": "toolu-cowork",
    "tool_input": {"query": "observability"},
}


def _hook_env(tmp_path: Path, extra: dict[str, str]) -> dict[str, str]:
    """A hook environment with every Claude Code marker removed, then ``extra``.

    ``PKB_MCP_URL`` points at a host that does not resolve, so a SessionStart
    that runs emits its metadata line and a UserPromptSubmit that runs fails
    loudly in its output rather than reaching anything. ``CLAUDE_ENV_FILE`` is
    dropped so SessionStart cannot write into the developer's own session file.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("CLAUDE_CODE_") and k not in ("CLAUDE_ENV_FILE", "AOPS_HOOK_LOG_PATH")
    }
    env["PKB_MCP_URL"] = "http://pkb.invalid/mcp"
    env["AOPS_HOOK_LOG_PATH"] = str(tmp_path / "fires.jsonl")
    env.update(extra)
    return env


def _run(script: Path, args: list[str], payload: dict, env: dict[str, str]):
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# The one decision, as a function
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("extra", COWORK_ENVS)
def test_is_cowork_recognises_the_client_signal(extra):
    from dispatch import is_cowork

    assert is_cowork(extra) is True


@pytest.mark.parametrize("extra", NOT_COWORK_ENVS)
def test_is_cowork_is_false_on_every_other_surface(extra):
    from dispatch import is_cowork

    assert is_cowork(extra) is False


# ---------------------------------------------------------------------------
# dispatch.py: every event is silent in Cowork
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("extra", COWORK_ENVS)
@pytest.mark.parametrize("event", sorted(_PAYLOADS))
def test_dispatch_emits_nothing_in_cowork(tmp_path, event, extra):
    env = _hook_env(tmp_path, extra)
    proc = _run(DISPATCH, ["claude", event], _PAYLOADS[event], env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "", f"{event} emitted in Cowork: {proc.stdout!r}"
    assert not (tmp_path / "fires.jsonl").exists(), "the dispatcher logged a fire in Cowork"


@pytest.mark.parametrize("extra", NOT_COWORK_ENVS)
def test_dispatch_session_start_still_speaks_elsewhere(tmp_path, extra):
    """The control: without the signal SessionStart emits its metadata as before."""
    env = _hook_env(tmp_path, extra)
    proc = _run(DISPATCH, ["claude", "SessionStart"], _PAYLOADS["SessionStart"], env)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    context = out["hookSpecificOutput"]["additionalContext"]
    assert "session: test-session" in context
    assert "pkb: http://pkb.invalid/mcp" in context
    assert (tmp_path / "fires.jsonl").exists()


# ---------------------------------------------------------------------------
# mcp_caller_session.py: no input is changed in Cowork
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("extra", COWORK_ENVS)
def test_caller_session_changes_no_input_in_cowork(tmp_path, extra):
    env = _hook_env(tmp_path, extra)
    proc = _run(CALLER_SESSION, [], _CALLER_SESSION_PAYLOAD, env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "", f"caller-session hook rewrote input in Cowork: {proc.stdout!r}"


@pytest.mark.parametrize("extra", NOT_COWORK_ENVS)
def test_caller_session_still_injects_elsewhere(tmp_path, extra):
    """The control: without the signal the PKB call carries ``_session`` as before."""
    env = _hook_env(tmp_path, extra)
    proc = _run(CALLER_SESSION, [], _CALLER_SESSION_PAYLOAD, env)
    assert proc.returncode == 0, proc.stderr
    updated = json.loads(proc.stdout)["hookSpecificOutput"]["updatedInput"]
    assert updated["query"] == "observability"
    assert updated["_session"] == {"session_id": "sess-cowork", "prompt_id": "prompt-cowork"}
