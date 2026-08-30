"""ida's quiet gate, proven through the artifact ida actually ships.

ida is an agent hosted inside the aops plugin (plugins/aops/agents/ida.md); its
hook — `be_quiet`, wired to `PostToolBatch` — ships from
plugins/aops/hooks/handlers.py alongside aops's own artifacts, so every path
below builds and reads the `aops` plugin.

The gate is only real if the built plugin wires a `PostToolBatch` hook, the shipped
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


@pytest.fixture(scope="module")
def ida_dist(tmp_path_factory) -> Path:
    """ida's host plugin (aops), really built, claude only — aops ships no
    agy hooks.json for this gate (test_plugin_manifests.py::
    test_ida_ships_the_quiet_gate_on_claude_only)."""
    root = tmp_path_factory.mktemp("ida-dist")
    build_all(
        _REPO_ROOT,
        root,
        marketplace_path=_MARKETPLACE,
        plugins=["aops"],
        # PEP 440, because the built plugin carries this into its own
        # pyproject.toml and `uv run` — which is how every hook command starts
        # — refuses to parse a version it cannot resolve. A non-conforming
        # value fails every hook in this file with a TOML error, at the point
        # furthest from its cause.
        version="0.0.0.dev0",
    )
    return root


def _claude_hooks_dir(ida_dist: Path) -> Path:
    return ida_dist / "aops-claude" / "hooks"


def _shipped_message(ida_dist: Path, name: str) -> str:
    """The message file as built, not as written here."""
    return (_claude_hooks_dir(ida_dist) / "messages" / name).read_text(encoding="utf-8").strip()


def _stop_command(ida_dist: Path) -> tuple[Path, str]:
    """(plugin root, command string) for the hook wired to claude's
    stop-equivalent event, read out of the built config rather than restated.

    claude only: aops ships no agy hooks.json for this gate (test_plugin_manifests.py::
    test_ida_ships_the_quiet_gate_on_claude_only)."""
    build_dir = ida_dist / "aops-claude"
    config = json.loads((build_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    entries = config["hooks"]["PostToolBatch"]
    return build_dir, entries[0]["hooks"][0]["command"]


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


def _injected(stdout: str) -> str:
    """The agent-facing text, out of claude's response shape.

    This is a warn-only disposition — ida's Stop gate never blocks (commit
    81e32c09) — so `_render_claude` (lib/hooks/dispatch.py) nests it under
    `hookSpecificOutput.additionalContext`.
    """
    out = json.loads(stdout)
    return out["hookSpecificOutput"]["additionalContext"]


def test_stop_delivers_the_shipped_message_through_the_real_build(ida_dist):
    """The gate fires on a fresh stop, and the agent-facing text that arrives is
    byte-for-byte the message file that shipped — not a Python literal, and not
    a truncation.

    This does not assert the gate's disposition — it is warn-only, not a block
    (commit 81e32c09) — only that whichever shape carries the text carries the
    right text.
    """
    _require_ida_hooks_enabled()
    build_dir, command = _stop_command(ida_dist)
    proc = _run(build_dir, command, {"session_id": "stop-gate-test"})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    expected = _shipped_message(ida_dist, "quiet.md")
    assert expected, "quiet.md shipped empty, so this case would assert nothing"
    assert _injected(proc.stdout) == expected


def test_the_gate_never_tells_the_person_it_fired(ida_dist):
    """The gate is silent to the person, and its silence is structural.

    It used to ship a `quiet.user.md` reading "ida: trimming the reply to what you
    actually need to see." — which made the suppression mechanism itself a mention
    of the delegated work it was suppressing. Between an instruction and its
    completion Nic is owed *nothing*, and a line announcing that something is
    being trimmed is not nothing.

    Asserted two ways on purpose. The absent file is what causes the silence
    (`load_message_pair` returns `None` for a missing user file, and dispatch.py
    only sets `systemMessage` when `user_text` is truthy), and the absent response
    key is the silence itself. Checking only the file would pass if some other
    handler started emitting one; checking only the response would pass on a
    payload that happened not to reach the gate.
    """
    _require_ida_hooks_enabled()
    messages = _claude_hooks_dir(ida_dist) / "messages"
    assert not (messages / "quiet.user.md").exists(), (
        "quiet.user.md is back — the gate has started announcing itself again"
    )

    build_dir, command = _stop_command(ida_dist)
    proc = _run(build_dir, command, {"session_id": "stop-gate-test"})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert "systemMessage" not in json.loads(proc.stdout)


def test_no_message_file_in_the_build_reaches_the_person(ida_dist):
    """None of the message files ida's own handler loads ship a `.user.md`
    counterpart, derived from the handler's `load_message_pair` calls rather
    than listed here.

    Scoped to the names ida's handler actually loads, not every `*.user.md` in
    the build: ida's hooks now ship from plugins/aops/hooks, alongside aops's
    own unrelated messages/pkb-context.user.md (a dead file from the
    permanently-disabled `search_the_pkb` hook, tests/policy.toml
    `aops.search_the_pkb_enabled`), so a directory-wide sweep would fail on a
    file this gate never touches.
    """
    handlers = (_claude_hooks_dir(ida_dist) / "handlers.py").read_text(encoding="utf-8")
    names = re.findall(r'load_message_pair\(\s*ctx\.hooks_dir,\s*"([^"]+)"\s*\)', handlers)
    assert names, "no handler loads a message pair; this test would assert nothing"

    messages = _claude_hooks_dir(ida_dist) / "messages"
    user_facing = sorted(
        f"{name}.user.md" for name in names if (messages / f"{name}.user.md").is_file()
    )
    assert user_facing == [], f"ida ships user-visible hook text: {user_facing}"


def test_stop_is_silent_on_its_own_continuation(ida_dist):
    """Injecting on a stop gives the session another turn, which stops again.
    Without the `stop_hook_active` guard this handler re-fires against its own
    continuation and the session cannot end. The guard is dispatch.py's, so this
    proves it survives the build rather than proving the handler checks it.

    claude only: pkb ships no agy hooks.json at all for this gate. Its only
    prior agy wiring was PostInvocation, which dispatch.py no longer maps to
    anything (aops_73e25af2 — it fired once per internal invocation/tool-call
    round-trip, not once per turn), so there is no agy stop-equivalent event
    left to test silence for."""
    build_dir, command = _stop_command(ida_dist)
    proc = _run(build_dir, command, {"session_id": "stop-gate-test", "stop_hook_active": True})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""


def test_subagentstop_is_not_wired_so_the_gate_stays_scoped_to_the_face(ida_dist):
    """What scopes this hook to ida is the event, because the payload carries no
    per-agent discriminator. `PostToolBatch` fires on the session's own turn boundary;
    a subagent ends on `SubagentStop`. Wiring that too would put the face's
    obligations in front of every worker the session dispatches.
    """
    build_dir = ida_dist / "aops-claude"
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
