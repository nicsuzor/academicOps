"""ida's Stop gate, proven through the artifact ida actually ships.

The gate is only real if the built plugin wires a `Stop` hook, the shipped
runtime loads the shipped message file, and the response comes back in the
shape the client parses. Each of those has failed independently before — a
message file with no handler, a handler with no hook entry, a hook wired to an
event the client never fires — and every one of them is invisible to a test
that imports the handler and calls it.

So these build the real plugin and run the real command, once per client. That
is what separates this file from tests/test_stop_gates.py, which assembles a
synthetic hooks/ dir and skips the build: here the manifest, `hooks.json`, and
the command string a client actually executes are all under test.

No assertion below quotes message wording. Every expected string is read from
the built tree, so editing a message file changes what is expected rather than
breaking a test that had the old words baked in.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_POLICY_FILE = Path(__file__).resolve().parent / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}


def _require_ida_hooks_enabled():
    if not _policy.get("ida", {}).get("strip_the_reply_enabled", True):
        pytest.skip("ida hooks are disabled by policy")


from build.build import build_all

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MARKETPLACE = _REPO_ROOT / "build" / "marketplace.toml"

_CLIENTS = ["claude", "agy"]


@pytest.fixture(scope="module")
def ida_dist(tmp_path_factory) -> Path:
    """The ida plugin, really built, both clients."""
    root = tmp_path_factory.mktemp("ida-dist")
    build_all(
        _REPO_ROOT,
        root,
        marketplace_path=_MARKETPLACE,
        plugins=["ida"],
        # PEP 440, because the built plugin carries this into its own
        # pyproject.toml and `uv run` — which is how every hook command starts
        # — refuses to parse a version it cannot resolve. A non-conforming
        # value fails every hook in this file with a TOML error, at the point
        # furthest from its cause.
        version="0.0.0.dev0",
    )
    return root


def _claude_hooks_dir(ida_dist: Path) -> Path:
    return ida_dist / "ida-claude" / "hooks"


def _shipped_message(ida_dist: Path, name: str) -> str:
    """The message file as built, not as written here."""
    return (_claude_hooks_dir(ida_dist) / "messages" / name).read_text(encoding="utf-8").strip()


def _stop_command(ida_dist: Path, client: str) -> tuple[Path, str]:
    """(plugin root, command string) for the hook wired to this client's
    stop-equivalent event, read out of the built config rather than restated."""
    if client == "claude":
        build_dir = ida_dist / "ida-claude"
        config = json.loads((build_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entries = config["hooks"]["PostToolBatch"]
        return build_dir, entries[0]["hooks"][0]["command"]

    build_dir = ida_dist / "ida-agy"
    config = json.loads((build_dir / "hooks.json").read_text(encoding="utf-8"))
    # agy keys by hook NAME; PostInvocation is the event lib/hooks maps to Stop.
    (spec,) = config.values()
    return build_dir, spec["PostInvocation"][0]["command"]


def _run(build_dir: Path, command: str, payload: dict) -> subprocess.CompletedProcess:
    """Run the hook the way its client runs it: through a shell, with Claude
    Code's plugin-root variable expanded, and — for agy, which defines no such
    variable — from the plugin root it supplies as the working directory."""
    return subprocess.run(  # noqa: S602
        command.replace("${CLAUDE_PLUGIN_ROOT}", str(build_dir)),
        shell=True,
        cwd=build_dir,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=180,
    )


def _injected(client: str, stdout: str) -> str:
    """The agent-facing text, out of each client's own response shape.

    Both shapes come from the same warn-only disposition — ida's Stop gate
    never blocks (commit 81e32c09) — but `_render_claude` and `_render_agy`
    (lib/hooks/dispatch.py) still carry it in different places. Claude Code
    nests it under `hookSpecificOutput.additionalContext`; agy, which has no
    blocking shape on any event, puts it at `injectSteps[0].ephemeralMessage`.
    """
    out = json.loads(stdout)
    if client == "claude":
        return out["hookSpecificOutput"]["additionalContext"]
    return out["injectSteps"][0]["ephemeralMessage"]


@pytest.mark.parametrize("client", _CLIENTS)
def test_stop_delivers_the_shipped_message_through_the_real_build(ida_dist, client):
    """The gate fires on a fresh stop, and the agent-facing text that arrives is
    byte-for-byte the message file that shipped — not a Python literal, and not
    a truncation.

    This does not assert the gate's disposition — it is warn-only, not a block
    (commit 81e32c09) — only that whichever shape carries the text carries the
    right text.
    """
    _require_ida_hooks_enabled()
    build_dir, command = _stop_command(ida_dist, client)
    proc = _run(build_dir, command, {"session_id": "stop-gate-test"})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    expected = _shipped_message(ida_dist, "quiet.md")
    assert expected, "quiet.md shipped empty, so this case would assert nothing"
    assert _injected(client, proc.stdout) == expected


@pytest.mark.parametrize("client", ["agy"])
def test_agy_never_receives_a_blocking_shape(ida_dist, client):
    """agy's PostInvocation response contract has no disposition field, and the
    invocation has already ended by the time the event fires. The same result
    therefore has to reach it as advice or not at all — never as a shape agy
    would drop on the floor while this side recorded a block that happened."""
    _require_ida_hooks_enabled()
    build_dir, command = _stop_command(ida_dist, client)
    proc = _run(build_dir, command, {"session_id": "stop-gate-test"})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    out = json.loads(proc.stdout)
    assert "decision" not in out
    assert list(out) == ["injectSteps"]


def test_claude_stop_tells_the_person_watching(ida_dist):
    """The gate firing is a fact about the answer they are about to read."""
    _require_ida_hooks_enabled()
    build_dir, command = _stop_command(ida_dist, "claude")
    proc = _run(build_dir, command, {"session_id": "stop-gate-test"})
    assert json.loads(proc.stdout)["systemMessage"] == _shipped_message(ida_dist, "quiet.user.md")


@pytest.mark.parametrize("client", _CLIENTS)
def test_stop_is_silent_on_its_own_continuation(ida_dist, client):
    """Injecting on a stop gives the session another turn, which stops again.
    Without the `stop_hook_active` guard this handler re-fires against its own
    continuation and the session cannot end. The guard is dispatch.py's, so this
    proves it survives the build rather than proving the handler checks it."""
    build_dir, command = _stop_command(ida_dist, client)
    proc = _run(build_dir, command, {"session_id": "stop-gate-test", "stop_hook_active": True})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""


def test_subagentstop_is_not_wired_so_the_gate_stays_scoped_to_the_face(ida_dist):
    """What scopes this hook to ida is the event, because the payload carries no
    per-agent discriminator. `Stop` fires on the session's own turn boundary;
    a subagent ends on `SubagentStop`. Wiring that too would put the face's
    obligations in front of every worker the session dispatches.
    """
    build_dir = ida_dist / "ida-claude"
    config = json.loads((build_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert "SubagentStop" not in config["hooks"]

    handlers = (build_dir / "hooks" / "handlers.py").read_text(encoding="utf-8")
    assert '"SubagentStop"' not in handlers


def test_every_message_the_handlers_load_ships_beside_them(ida_dist):
    """Every message file a handler names is actually in the build, and none of
    them shipped empty.

    Derived from the built source rather than listed here: a hardcoded list goes
    stale the moment a handler is added, and goes stale silently — the new
    handler's message would simply never be checked.
    """
    handlers = (_claude_hooks_dir(ida_dist) / "handlers.py").read_text(encoding="utf-8")
    names = re.findall(r'load_message_pair\(\s*ctx\.hooks_dir,\s*"([^"]+)"\s*\)', handlers)
    assert names, "no handler loads a message pair; this test would assert nothing"

    messages = _claude_hooks_dir(ida_dist) / "messages"
    for name in names:
        agent = messages / f"{name}.md"
        assert agent.is_file(), f"{name}.md is loaded by a handler but did not ship"
        assert agent.read_text(encoding="utf-8").strip(), f"{name}.md shipped empty"


def test_no_handler_returns_a_string_literal(ida_dist):
    """The failure `load_message_pair` exists to prevent: text inlined in the
    handler drifts from the file reviewers read, and silently keeps firing the
    old wording after the file is corrected. Checked at the source, because a
    payload that happens not to reach an inlined branch would not notice.

    Every registered handler is covered, not just the ones a payload here
    reaches — a handler whose every `return` goes through `load_message_pair`
    has no other way to produce text.
    """
    handlers = (_claude_hooks_dir(ida_dist) / "handlers.py").read_text(encoding="utf-8")
    returns = [
        line.strip()
        for line in handlers.splitlines()
        if line.strip().startswith("return ") and "load_message_pair" not in line
    ]
    offenders = [line for line in returns if '"' in line or "'" in line]
    assert offenders == [], f"handler text built from a Python literal: {offenders}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
