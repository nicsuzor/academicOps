"""Tests against the SHIPPED artifact, not the source it was built from.

`tests/test_hooks.py` proves the hook runtime works when Python imports it.
`tests/test_build.py` proves the builder puts files where the client looks.
Neither one ever executed a shipped hook the way its client executes it, so
every Python hook could ship non-executable — invoked by bare path, mode
`0644` — and the whole suite stayed green while nothing fired.

These tests close that gap by treating the built tree as the unit under test:
they read the `command` string out of the built `hooks.json` and run it exactly
as its client would — through a shell, with Claude Code's plugin-root variable
expanded for Claude Code, and with the working directory set to the plugin root
for agy, which is what agy gives a hook instead of a plugin-root variable.

The fixture builds the real `plugins/` into a temporary dist, so the assertions
hold for whatever `make build` would produce right now, with no dependency on
a `dist/` a developer may or may not have refreshed.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from build.build import build_all
from build.marketplace import load_marketplace_toml
from build.tree import EXCLUDE_NAMES, has_shebang

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LIB_HOOKS = _REPO_ROOT / "lib" / "hooks"
_MARKETPLACE = _REPO_ROOT / "build" / "marketplace.toml"
_CLIENTS = ("claude", "agy")
_VERSION = "0.0.0-test"

if str(_LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIB_HOOKS))

import clients  # noqa: E402

# Where each client reads its hook config from (build/clients/*.py).
_HOOKS_JSON_PATH = {"claude": Path("hooks/hooks.json"), "agy": Path("hooks.json")}

# Claude Code expands this in a hook command; agy has no counterpart and
# defines no variable of its own, so an agy command carries a path relative to
# the plugin root and agy supplies that root as the working directory.
_CLAUDE_PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"

# One representative payload per canonical event, shaped like the real thing.
# PreToolUse carries the reproduction case: a `--no-verify` commit, which is
# exactly the shape cope's halt-on-failure policy exists to catch.
_PAYLOADS: dict[str, dict] = {
    "SessionStart": {"hook_event_name": "SessionStart", "session_id": "test-session"},
    "UserPromptSubmit": {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "test-session",
        "prompt": "what did we decide about the build?",
    },
    "PreToolUse": {
        "hook_event_name": "PreToolUse",
        "session_id": "test-session",
        "tool_name": "Bash",
        "tool_input": {"command": "git commit --no-verify -m x"},
    },
    "Stop": {"hook_event_name": "Stop", "session_id": "test-session"},
    "SubagentStop": {"hook_event_name": "SubagentStop", "session_id": "test-session"},
    "SessionEnd": {
        "hook_event_name": "SessionEnd",
        "session_id": "test-session",
        "transcript_path": "/nonexistent/test-session.jsonl",
    },
}


@pytest.fixture(scope="module")
def dist_root(tmp_path_factory) -> Path:
    """The real plugins, really built — every plugin, both clients."""
    root = tmp_path_factory.mktemp("shipped-dist")
    build_all(_REPO_ROOT, root, marketplace_path=_MARKETPLACE, version=_VERSION)
    return root


@pytest.fixture(scope="module")
def pristine_dist(tmp_path_factory) -> Path:
    """A build nothing has executed out of.

    The cleanliness assertions are about what the BUILD emits. They get their
    own tree because running a Python hook writes `__pycache__` next to the
    module it imported — so the execution tests above legitimately dirty the
    tree they run in, and asserting on that tree would measure CPython's
    bytecode cache rather than the builder.
    """
    root = tmp_path_factory.mktemp("pristine-dist")
    build_all(_REPO_ROOT, root, marketplace_path=_MARKETPLACE, version=_VERSION)
    return root


def _marketplace_names() -> list[str]:
    return [entry["name"] for entry in load_marketplace_toml(_MARKETPLACE)["plugins"]]


def _build_dirs(dist_root: Path) -> list[tuple[str, str, Path]]:
    """(marketplace name, client, build dir) for everything that got built."""
    out = []
    for name in _marketplace_names():
        for client in _CLIENTS:
            build_dir = dist_root / f"{name}-{client}"
            if build_dir.is_dir():
                out.append((name, client, build_dir))
    return out


def _hooks_config(client: str, build_dir: Path) -> dict:
    path = build_dir / _HOOKS_JSON_PATH[client]
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _hook_handlers(client: str, build_dir: Path) -> list[tuple[str, dict]]:
    """(wire event, handler object) for every hook the built config registers.

    The two clients disagree about the file's shape at every level, so this is
    where that is absorbed. Claude Code keys by event under a `hooks` wrapper,
    each event holding matcher groups. agy keys by hook NAME; the events sit
    inside that name's spec, and only its two tool events group their handlers
    under a matcher — the rest list handlers directly.
    """
    handlers: list[tuple[str, dict]] = []

    def collect(wire_event: str, entries: list) -> None:
        for entry in entries:
            if isinstance(entry, dict) and "hooks" in entry:
                handlers.extend((wire_event, hook) for hook in entry["hooks"])
            else:
                handlers.append((wire_event, entry))

    config = _hooks_config(client, build_dir)
    if client == "claude":
        for wire_event, entries in config.get("hooks", {}).items():
            collect(wire_event, entries)
        return handlers
    for spec in config.values():
        for wire_event, entries in spec.items():
            if wire_event == "enabled":
                continue
            collect(wire_event, entries)
    return handlers


def _hook_commands(client: str, build_dir: Path) -> list[tuple[str, str]]:
    """(wire event, command string) for every hook the built config registers."""
    return [
        (wire_event, handler["command"])
        for wire_event, handler in _hook_handlers(client, build_dir)
        if "command" in handler
    ]


# Every variable that makes aops's PreToolUse hook treat a session as headless.
# Tests that care must set or clear these explicitly: CI runners export `CI`,
# so inheriting the ambient environment would silently flip the outcome.
_HEADLESS_ENV = ("NONINTERACTIVE", "CI", "AOPS_POLECAT_CONTAINER", "CLAUDE_CODE_NON_INTERACTIVE")


def _run_shipped_hook(
    client: str,
    build_dir: Path,
    command: str,
    payload: dict,
    env_overrides: dict[str, str | None] | None = None,
) -> subprocess.CompletedProcess:
    """Run a hook command the way its client runs it.

    Both clients hand the command to a shell, so quoting is honoured in each.
    What differs is how the command finds the plugin it belongs to: Claude Code
    expands a plugin-root variable, and agy — which defines no such variable —
    runs the command with the working directory set to the directory holding
    `hooks.json`, which for a plugin is its root. Running it from anywhere else
    here would pass a command that cannot resolve its own script in the field.

    ``env_overrides`` sets or, with a ``None`` value, unsets one variable for
    this run — the hooks under test read the environment, so a test that
    asserts on their behaviour has to control it rather than inherit it.
    """
    resolved = command.replace(_CLAUDE_PLUGIN_ROOT_VAR, str(build_dir))
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_REMOTE", None)  # keep the ts hooks on their no-op path
    for key, value in (env_overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(  # noqa: S602
        resolved,
        shell=True,
        cwd=None if client == "claude" else build_dir,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _command_for(client: str, build_dir: Path, wire_event: str) -> str:
    matches = [cmd for wire, cmd in _hook_commands(client, build_dir) if wire == wire_event]
    assert len(matches) == 1, f"{build_dir.name}: {len(matches)} {wire_event} hooks, expected 1"
    return matches[0]


# --- 0. schema: agy can parse what we ship it ---------------------------------
#
# Every agy hook the framework shipped was dead, and had always been dead, for
# a reason no test could see: `hooks.json` carried Claude Code's shape, and agy
# rejected the whole file — `invalid hook "hooks": command hook must specify
# 'command'` — before a single handler loaded. Executing the command proves the
# command works; it says nothing about whether the client ever gets that far.
#
# The schema asserted here is agy's own. The CLI binary embeds its "Lifecycle
# Hooks (`hooks.json`)" reference: top-level keys are hook NAMES, each mapping
# to a spec whose keys are events; `PreToolUse`/`PostToolUse` group handlers
# under a `matcher`, and `PreInvocation`/`PostInvocation`/`Stop` list handlers
# directly. A handler needs a `command`; `type` defaults to "command".

_AGY_GROUPED_EVENTS = {"PreToolUse", "PostToolUse"}
_AGY_FLAT_EVENTS = {"PreInvocation", "PostInvocation", "Stop"}


def test_shipped_agy_hooks_json_matches_agys_schema(dist_root):
    """Every agy `hooks.json` we ship, checked against the shape agy parses."""
    checked = 0
    for name, client, build_dir in _build_dirs(dist_root):
        if client != "agy":
            continue
        config = _hooks_config(client, build_dir)
        if not config:
            continue

        assert "hooks" not in config, (
            f"{name}-agy: hooks.json has a top-level 'hooks' key. agy reads "
            f"top-level keys as hook NAMES, so this ships a hook named 'hooks' "
            f"and the whole file fails to load."
        )
        for hook_name, spec in config.items():
            assert isinstance(spec, dict), f"{name}-agy: hook {hook_name!r} is not an object"
            events = {key for key in spec if key != "enabled"}
            assert events, f"{name}-agy: hook {hook_name!r} registers no event"
            unknown = events - _AGY_GROUPED_EVENTS - _AGY_FLAT_EVENTS
            assert not unknown, (
                f"{name}-agy: {hook_name!r} wires events agy does not fire: {unknown}"
            )

            for event in events:
                for entry in spec[event]:
                    if event in _AGY_GROUPED_EVENTS:
                        assert "matcher" in entry, f"{name}-agy: {event} group has no matcher"
                        handlers = entry["hooks"]
                    else:
                        assert "hooks" not in entry, (
                            f"{name}-agy: {event} takes handlers directly, but this entry "
                            f"wraps them in a 'hooks' group — agy reads the group itself as "
                            f"the handler and rejects it for having no 'command'"
                        )
                        handlers = [entry]
                    for handler in handlers:
                        assert handler.get("command"), (
                            f"{name}-agy: {event} handler has no 'command': {handler}"
                        )
            checked += 1
    assert checked > 0, "no agy hooks.json was checked"


def test_shipped_agy_hook_commands_resolve_from_the_plugin_root(dist_root):
    """agy defines no plugin-root variable — `${AGY_PLUGIN_ROOT}` expands to
    nothing and the path never resolves. What it does give a hook is the
    working directory: the directory holding `hooks.json`, which for a plugin
    is its root. So every script an agy hook names must exist at that path,
    relative to the build dir."""
    checked = 0
    for name, client, build_dir in _build_dirs(dist_root):
        if client != "agy":
            continue
        for _, command in _hook_commands(client, build_dir):
            assert "AGY_PLUGIN_ROOT" not in command, (
                f"{name}-agy: `{command}` names a variable agy never sets"
            )
            scripts = [word for word in shlex.split(command) if word.endswith((".py", ".sh"))]
            assert scripts, f"{name}-agy: `{command}` names no script"
            for script in scripts:
                assert (build_dir / script).is_file(), (
                    f"{name}-agy: `{command}` resolves to {build_dir / script}, which "
                    f"does not exist"
                )
                checked += 1
    assert checked > 0, "no agy hook commands were checked"


def test_no_shipped_config_asks_agy_to_expand_a_variable(dist_root):
    """agy substitutes nothing in the files it reads.

    `${AGY_PLUGIN_ROOT}` was the loud case — it is not a variable agy has, so
    it expanded to nothing and every hook died. The quiet case is a `${VAR}`
    that reaches a launched process verbatim: a script testing whether its
    variable is set sees the literal text, finds it non-empty, and proceeds
    into a failure that names something else entirely. Neither may ship, so
    this sweeps every JSON config in every agy build rather than the two files
    that happened to be wrong.
    """
    offenders = []
    for name, client, build_dir in _build_dirs(dist_root):
        if client != "agy":
            continue
        for config in sorted(build_dir.glob("*.json")):
            for match in set(re.findall(r"\$\{[^}]*\}", config.read_text(encoding="utf-8"))):
                offenders.append(f"{name}-agy/{config.name}: {match}")
    assert offenders == [], f"agy expands none of these: {offenders}"


def test_every_shipped_agy_mcp_server_is_stdio_or_remote_not_both(dist_root):
    """agy's own rule, quoted from the CLI binary: a server "must have either
    command or serverUrl", and "cannot have both". A config it rejects is a set
    of tools that silently never appear."""
    for name, client, build_dir in _build_dirs(dist_root):
        if client != "agy":
            continue
        config = build_dir / "mcp_config.json"
        if not config.is_file():
            continue
        servers = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
        assert servers, f"{name}-agy ships an empty mcp_config.json; ship no file instead"
        for server_name, server in servers.items():
            assert ("command" in server) != ("serverUrl" in server), (
                f"{name}-agy: MCP server {server_name!r} sets both or neither of "
                f"'command' and 'serverUrl'"
            )


# A hook timeout is expressed in SECONDS by both clients — Claude Code's hook
# `timeout`, and agy's, which its reference documents as "Execution timeout in
# seconds. Defaults to 30". Ten minutes is longer than any hook this framework
# ships has business taking, and is far below the smallest plausible
# milliseconds value (1000 = 16 minutes), so it separates the two units
# cleanly without pinning any particular hook's budget.
_MAX_HOOK_TIMEOUT_SECONDS = 600


def test_no_shipped_hook_timeout_is_a_milliseconds_value(dist_root):
    """The regression: `"timeout": 30000` meaning 30 seconds.

    Read as seconds — which is what both clients do — that is eight hours and
    twenty minutes, and its sibling `300000` is three and a half days. A
    timeout that long is not a timeout: the guarantee it exists to give, that a
    wedged hook cannot hold the session open indefinitely, is gone, and nothing
    observable changes until the day something hangs.
    """
    for name, client, build_dir in _build_dirs(dist_root):
        for wire_event, handler in _hook_handlers(client, build_dir):
            timeout = handler.get("timeout")
            if timeout is None:
                continue
            assert timeout <= _MAX_HOOK_TIMEOUT_SECONDS, (
                f"{name}-{client} {wire_event}: timeout={timeout}. Hook timeouts are "
                f"SECONDS, so this is {timeout / 3600:.1f} hours — almost certainly a "
                f"milliseconds value. Cap is {_MAX_HOOK_TIMEOUT_SECONDS}s."
            )


# --- 1. execution: every shipped hook command actually runs -------------------


def test_every_shipped_hook_command_runs(dist_root):
    """The test whose absence let a whole fleet of dead hooks ship.

    For every plugin, for both clients: take the command out of the built
    config, point it at the real build dir, run it with a representative
    payload, and require a clean exit and a response the client can parse.
    """
    ran = 0
    for name, client, build_dir in _build_dirs(dist_root):
        for wire_event, command in _hook_commands(client, build_dir):
            canonical = clients.to_canonical(client, wire_event)
            payload = _PAYLOADS.get(canonical or wire_event, {"hook_event_name": wire_event})
            proc = _run_shipped_hook(client, build_dir, command, payload)
            assert proc.returncode == 0, (
                f"{name}-{client} {wire_event}: `{command}` exited {proc.returncode}\n"
                f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}"
            )
            if proc.stdout.strip():
                json.loads(proc.stdout)  # a client parses this; so must we
            ran += 1
    assert ran > 0, "no shipped hook commands were found to run"


def test_no_dispatch_hook_is_wired_to_an_unmappable_event(dist_root):
    """A `dispatch.py` hook wired to a wire event `lib/hooks/clients.py` cannot
    map is provably dead: dispatch returns 0 before loading a single handler.

    Scoped to `dispatch.py` hooks on purpose. A plugin whose hook is a plain
    script — ts's `tailscale-up.sh` — never consults that table, so the table
    says nothing about which events it may legitimately register.
    """
    for name, client, build_dir in _build_dirs(dist_root):
        for wire_event, command in _hook_commands(client, build_dir):
            if "dispatch.py" not in command:
                continue
            assert clients.to_canonical(client, wire_event) is not None, (
                f"{name}-{client}: hooks.json runs dispatch.py for wire event "
                f"{wire_event!r}, which lib/hooks/clients.py maps to nothing — "
                f"the hook would fire and immediately no-op"
            )


class _StubReflexesEvaluator(BaseHTTPRequestHandler):
    """A loopback CoPE label endpoint, speaking the Reflexes evaluator contract:
    one policy in (`criteria_text`), one `label` out. cope ships with no
    endpoint, so exercising the built artifact's evaluation path at all means
    standing one up."""

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))
        label = 1 if "workaround" in payload.get("criteria_text", "").lower() else 0
        body = json.dumps({"label": label, "confidence": 0.9}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the default stderr access log
        pass


@pytest.fixture()
def stub_evaluator_env(tmp_path):
    """Environment overrides pointing cope's hook at the loopback evaluator.

    `ACA_DATA` is cleared and the OS temp directory redirected because the hook
    reports its own degradation on the same response (lib/hooks/degraded.py),
    once per session, behind a marker file: an ambient `ACA_DATA` naming no
    rules directory is a real fault, and a marker left in the real temp
    directory would decide whether the next run saw it.
    """
    marker_root = tmp_path / "os-tmp"
    marker_root.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubReflexesEvaluator)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield {
        "COPE_EVALUATOR_URL": f"http://127.0.0.1:{server.server_address[1]}/v1/label",
        "COPE_EVALUATOR_PROTOCOL": "cope",
        "COPE_EVALUATOR_MODEL": "stub-model",
        "COPE_EVALUATOR_API_KEY": None,
        "COPE_EVALUATOR_TIMEOUT": "20",
        "ACA_DATA": None,
        "TMPDIR": str(marker_root),
    }
    server.shutdown()
    server.server_close()


def test_cope_shipped_hook_flags_the_axiom_it_ships_for(dist_root, stub_evaluator_env):
    """End-to-end through the artifact: the built cope hook, run as Claude Code
    runs it, on a `--no-verify` commit, against an evaluator that flags the
    matching policy. It names halt-on-failure and echoes the call. Exit 0 alone
    would also be satisfied by a hook that does nothing."""
    build_dir = dist_root / "aops-cope-claude"
    commands = _hook_commands("claude", build_dir)
    assert commands, "aops-cope-claude ships no hook command"

    _, command = commands[0]
    proc = _run_shipped_hook(
        "claude", build_dir, command, _PAYLOADS["PreToolUse"], env_overrides=stub_evaluator_env
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    advisory = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "halt-on-failure" in advisory
    assert "--no-verify" in advisory


def test_cope_shipped_hook_tells_the_person_watching_which_rule_was_flagged(
    dist_root, stub_evaluator_env
):
    """The artifact, not the source: the built hook must put `systemMessage` on
    stdout, because that is the only field of this response Claude Code shows
    the person whose rules these are. Without it the check runs, corrects the
    agent, and never surfaces — leaving them nothing to decide on."""
    build_dir = dist_root / "aops-cope-claude"
    _, command = _hook_commands("claude", build_dir)[0]
    proc = _run_shipped_hook(
        "claude", build_dir, command, _PAYLOADS["PreToolUse"], env_overrides=stub_evaluator_env
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    out = json.loads(proc.stdout)
    assert "systemMessage" in out, "the shipped hook flagged a rule and told only the agent"
    assert "halt-on-failure" in out["systemMessage"]
    assert "\n" not in out["systemMessage"]
    assert (build_dir / "hooks" / "messages" / "verdict.user.md").is_file()


def test_cope_shipped_hook_tells_the_person_watching_when_it_is_degraded(
    dist_root, stub_evaluator_env, tmp_path
):
    """The framework's own failure, on the wire, out of the built artifact.

    A rule file that cannot be read is a rule that is not being enforced. That
    has always been reported — on stderr, which the client captures into the
    transcript and shows nobody. `systemMessage` is the only field of this
    response a person ever sees, so a fault that never reaches it is a fault
    the person whose rules these are cannot know about or fix.
    """
    project = tmp_path / "project"
    (project / ".agents" / "rules").mkdir(parents=True)
    (project / ".agents" / "rules" / "unreadable.md").mkdir()  # a rule file that is not a file

    build_dir = dist_root / "aops-cope-claude"
    _, command = _hook_commands("claude", build_dir)[0]
    proc = _run_shipped_hook(
        "claude",
        build_dir,
        command,
        {**_PAYLOADS["PreToolUse"], "session_id": "degraded-session", "cwd": str(project)},
        env_overrides=stub_evaluator_env,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    out = json.loads(proc.stdout)
    assert "unreadable.md" in out["systemMessage"], (
        "the shipped hook degraded and told only its own stderr"
    )
    assert "not being checked" in out["systemMessage"]
    # the log keeps the precise reason, and so does the agent
    assert "unreadable.md" in proc.stderr
    assert "IsADirectoryError" in out["hookSpecificOutput"]["additionalContext"]
    # and reporting it is not a gate: cope may never block a tool call
    assert "decision" not in out
    assert "permissionDecision" not in out["hookSpecificOutput"]
    assert (build_dir / "hooks" / "messages" / "degraded.user.md").is_file()


def test_cope_shipped_hook_is_a_silent_no_op_with_no_evaluator_configured(dist_root):
    """The shipped default. cope bakes in no endpoint, so an installation that
    has not configured one must cost the session nothing on every tool call:
    no advisory, no error, no stderr."""
    build_dir = dist_root / "aops-cope-claude"
    _, command = _hook_commands("claude", build_dir)[0]
    proc = _run_shipped_hook(
        "claude",
        build_dir,
        command,
        _PAYLOADS["PreToolUse"],
        env_overrides=dict.fromkeys(
            (
                "COPE_EVALUATOR_URL",
                "COPE_EVALUATOR_PROTOCOL",
                "COPE_EVALUATOR_MODEL",
                "COPE_EVALUATOR_API_KEY",
                "COPE_EVALUATOR_TIMEOUT",
            )
        ),
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


# --- 1b. the one blocking hook, and the boundary around it --------------------
#
# A headless session cannot answer an interactive prompt, so the prompt hangs
# until the session times out. aops's PreToolUse hook refuses it. That is a
# capability fact, not a rule verdict (specs/ARCHITECTURE.md, Hooks), and these
# tests pin all four edges: it fires, it fires only on those tools, it fires
# only when headless, and cope still cannot reach the mechanism.

# The tool name a Claude Code session actually sends when it asks a person a
# question. This test file's whole claim about the refusal rests on this one
# string being the client's, not ours.
#
# The previous version of this constant was the production frozenset copied
# out of handlers.py, wrong names and all, and parametrized over. It proved
# the hook refuses four names Claude Code has never sent, never once exercised
# the name it does send, and stayed green while the hook was inert in every
# shipped session. A test that restates the implementation's own constant can
# only agree with it. So this list is written from the client's vocabulary,
# and nothing here imports from or mirrors handlers.py — if the two disagree,
# that disagreement is the finding.
_CLIENT_INTERACTIVE_TOOL = "AskUserQuestion"

# Spellings other harnesses give the same capability. Kept because the hook
# ships to more than one, but held separately: none of them is evidence about
# Claude Code, and a green run over these alone means nothing.
_OTHER_HARNESS_INTERACTIVE_TOOLS = (
    "ask_question",
    "AskFollowupQuestion",
    "ask_followup_question",
    "Question",
)

_INTERACTIVE_TOOLS = (_CLIENT_INTERACTIVE_TOOL, *_OTHER_HARNESS_INTERACTIVE_TOOLS)


def _aops_pretooluse(dist_root: Path, tool: str, env_overrides: dict[str, str | None]):
    build_dir = dist_root / "aops-claude"
    return _run_shipped_hook(
        "claude",
        build_dir,
        _command_for("claude", build_dir, "PreToolUse"),
        {"hook_event_name": "PreToolUse", "session_id": "test-session", "tool_name": tool},
        env_overrides=env_overrides,
    )


@pytest.mark.parametrize("headless_var", _HEADLESS_ENV)
@pytest.mark.parametrize("tool", _INTERACTIVE_TOOLS)
def test_shipped_aops_hook_refuses_an_interactive_prompt_in_a_headless_session(
    dist_root, tool, headless_var
):
    """Every interactive-prompt tool, under every headless signal."""
    env = dict.fromkeys(_HEADLESS_ENV, None)
    env[headless_var] = "1"
    proc = _aops_pretooluse(dist_root, tool, env)
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    assert tool in out["permissionDecisionReason"]
    assert "headless" in out["permissionDecisionReason"]


@pytest.mark.parametrize("tool", ["Read", "Bash", "Edit", "Task"])
def test_shipped_aops_hook_allows_an_ordinary_tool_in_a_headless_session(dist_root, tool):
    """The refusal is about one capability, not a general gate: a headless
    session runs every other tool untouched, and the hook stays silent."""
    proc = _aops_pretooluse(dist_root, tool, {**dict.fromkeys(_HEADLESS_ENV, None), "CI": "1"})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""


@pytest.mark.parametrize("tool", _INTERACTIVE_TOOLS)
def test_shipped_aops_hook_allows_an_interactive_prompt_when_someone_is_there(dist_root, tool):
    """With no headless signal set, a human may be at the keyboard — asking is
    exactly what these tools are for, and the hook must not touch them."""
    proc = _aops_pretooluse(dist_root, tool, dict.fromkeys(_HEADLESS_ENV, None))
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""


def test_shipped_aops_hook_refuses_the_tool_claude_code_actually_sends(dist_root):
    """The parametrized cases above pass with the client's real tool name
    missing, because four other names carry them. This one cannot: it names
    `AskUserQuestion` and nothing else, so a regression that drops it fails
    here specifically, instead of thinning a green parametrized sweep."""
    proc = _aops_pretooluse(
        dist_root,
        _CLIENT_INTERACTIVE_TOOL,
        {**dict.fromkeys(_HEADLESS_ENV, None), "NONINTERACTIVE": "1"},
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert _CLIENT_INTERACTIVE_TOOL in out["hookSpecificOutput"]["permissionDecisionReason"]
    # A refusal the user cannot see is a session that mysteriously stalls.
    assert _CLIENT_INTERACTIVE_TOOL in out["systemMessage"]


# --- 1c. both stop events reach the agent that is stopping --------------------


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_shipped_aops_stop_hooks_address_the_agent_that_is_stopping(dist_root, event):
    """A hook's output goes to the session it fired in, so `SubagentStop`
    reaches the subagent that just stopped — never its parent, which is not in
    that session. Both events therefore carry the same message: present your
    own answer with evidence. The regression this guards is the old wording,
    which told the reader to interrogate a result someone else had handed them,
    and landed in front of the agent that produced it."""
    build_dir = dist_root / "aops-claude"
    proc = _run_shipped_hook(
        "claude",
        build_dir,
        _command_for("claude", build_dir, event),
        _PAYLOADS[event],
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    out = json.loads(proc.stdout)
    injected = out["hookSpecificOutput"]["additionalContext"]
    assert "Before you stop" in injected
    assert "A subagent just returned" not in injected
    assert out["systemMessage"]


def test_shipped_aops_ships_no_message_file_nothing_sends(dist_root):
    """`subagent-result.md` addressed a parent that never receives this hook's
    output. A message file with no sender is dead weight, and worse, it reads
    as a live behaviour to anyone auditing the plugin."""
    messages_dir = dist_root / "aops-claude" / "hooks" / "messages"
    assert not (messages_dir / "subagent-result.md").exists()
    handlers = (dist_root / "aops-claude" / "hooks" / "handlers.py").read_text(encoding="utf-8")
    assert "subagent-result" not in handlers


def test_shipped_cope_hook_can_never_emit_a_blocking_decision(dist_root, stub_evaluator_env):
    """cope is advisory, permanently. Run its shipped PreToolUse hook on the
    payload most likely to provoke a block — a call its evaluator flags — under
    a headless environment, and require the advisory shape and nothing else."""
    build_dir = dist_root / "aops-cope-claude"
    proc = _run_shipped_hook(
        "claude",
        build_dir,
        _command_for("claude", build_dir, "PreToolUse"),
        _PAYLOADS["PreToolUse"],
        env_overrides={
            **dict.fromkeys(_HEADLESS_ENV, None),
            "NONINTERACTIVE": "1",
            **stub_evaluator_env,
        },
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert "permissionDecision" not in proc.stdout
    assert "allowTool" not in proc.stdout
    assert json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def test_shipped_cope_never_reaches_the_refusal_primitive(dist_root):
    """Structural, not behavioural: cope's own shipped modules must not be able
    to reach the blocking outcome at all. The runtime is shared, so the only
    thing keeping cope advisory is that its handlers never get there — assert
    that directly, rather than trusting one payload not to have found the path.

    Three tokens, not one. `refuse` is not a substring of `is_refusal`
    ("refuse" vs "refusal"), so searching for `refuse` alone would sail past
    `Result(text, is_refusal=True)`, which lib/hooks/clients.py renders as
    `permissionDecision: deny` just as a refuse() call would; a positional
    `Result(text, None, True)` evades both. Banning construction closes it, and
    costs nothing — the return annotation `Result | None` has no `(`.
    """
    cope_hooks = dist_root / "aops-cope-claude" / "hooks"
    cope_own = {"handlers.py", "evaluator.py", "rules.py"}
    offenders = [
        f"{path.name}: {token}"
        for path in sorted(cope_hooks.glob("*.py"))
        if path.name in cope_own
        for token in ("refuse", "is_refusal", "Result(")
        if token in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


# --- 2. mode: a shipped `#!` file is runnable ---------------------------------


def test_every_shipped_shebang_file_is_executable(dist_root):
    """A `#!` line declares an entry point. `shutil.copy2` reproduces the
    source's mode, so without the build asserting this, a library file
    committed 0644 ships unrunnable — silently, until a client invokes it."""
    not_executable = [
        str(path.relative_to(dist_root))
        for path in sorted(dist_root.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and has_shebang(path)
        and not os.access(path, os.X_OK)
    ]
    assert not_executable == []


# --- 3. cleanliness: no development artifacts anywhere in dist ----------------


def _is_artifact(name: str) -> bool:
    return name in EXCLUDE_NAMES or name.endswith((".pyc", ".pyo"))


def test_no_build_artifacts_in_dist_tree(pristine_dist):
    leaked = [
        str(path.relative_to(pristine_dist))
        for path in sorted(pristine_dist.rglob("*"))
        if _is_artifact(path.name)
    ]
    assert leaked == []


def test_no_build_artifacts_in_tarballs(dist_root):
    for archive in sorted(dist_root.glob("*.tar.gz")):
        with tarfile.open(archive) as tar:
            names = tar.getnames()
        leaked = [n for n in names if any(_is_artifact(part) for part in Path(n).parts)]
        assert leaked == [], f"{archive.name}: {leaked}"


def test_no_build_artifacts_in_cowork_zips(dist_root):
    zips = sorted((dist_root / "cowork").glob("*.zip"))
    assert zips, "cowork channel shipped no upload zips"
    for archive in zips:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        leaked = [n for n in names if any(_is_artifact(part) for part in Path(n).parts)]
        assert leaked == [], f"{archive.name}: {leaked}"


# --- 4. coverage: registered handlers are wired, and only those ----------------

_READ_REGISTERED_EVENTS = (
    "import importlib.util, json, sys\n"
    "hooks_dir, client = sys.argv[1], sys.argv[2]\n"
    "sys.path.insert(0, hooks_dir)\n"
    "spec = importlib.util.spec_from_file_location('handlers', hooks_dir + '/handlers.py')\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(module)\n"
    "runs = lambda h: getattr(h, 'only_on_clients', None) is None "
    "or client in h.only_on_clients\n"
    "events = [e for e, hs in module.HANDLERS.items() if any(runs(h) for h in hs)]\n"
    "print(json.dumps(sorted(events)))\n"
)


def _registered_events(hooks_dir: Path, client: str) -> set[str]:
    """Canonical events this plugin's shipped handlers.py registers for, for
    this client.

    A handler may scope itself with ``only_on_clients`` (lib/hooks/dispatch.py
    honours it), so "registered" is per client: a handler scoped away from this
    client would never run here, and wiring the event for it would spawn a
    process to do nothing.

    Loaded the same way dispatch.py loads it — from the built tree, with that
    tree's hooks/ on sys.path — in a subprocess, so one plugin's modules can
    never leak into the next plugin's import.
    """
    proc = subprocess.run(
        [sys.executable, "-c", _READ_REGISTERED_EVENTS, str(hooks_dir), client],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"{hooks_dir}: {proc.stderr}"
    return set(json.loads(proc.stdout))


def test_registered_handler_events_are_exactly_the_wired_events(dist_root):
    """Every canonical event a plugin registers a handler for is wired in the
    built hooks.json for each client that can fire it — and nothing else is.

    Equality, not containment, so this fails in both directions: a handler with
    no hook entry (dead code that never runs) and a hook entry with no handler
    (a process spawned every event to do nothing).
    """
    checked = 0
    for name, client, build_dir in _build_dirs(dist_root):
        hooks_dir = build_dir / "hooks"
        if not (hooks_dir / "handlers.py").is_file():
            continue  # ts ships a shell hook, not the Python runtime

        registered = _registered_events(hooks_dir, client)
        assert registered, f"{name}-{client}: handlers.py registers nothing"

        expected = {
            wire
            for wire, canonical in clients.wire_events(client).items()
            if canonical in registered
        }
        wired = {wire for wire, _ in _hook_commands(client, build_dir)}
        assert wired == expected, (
            f"{name}-{client}: handlers register {sorted(registered)}; "
            f"this client fires {sorted(expected)}; hooks.json wires {sorted(wired)}"
        )
        checked += 1
    assert checked > 0, "no hook-bearing plugins were checked"


def test_hook_bearing_plugins_all_present(dist_root):
    """Guards the loop above against silently checking nothing: these four are
    the Hooks table in specs/ARCHITECTURE.md."""
    hook_plugins = {
        name
        for name, client, build_dir in _build_dirs(dist_root)
        if _hooks_config(client, build_dir)
    }
    assert hook_plugins == {"aops", "aops-cope", "aops-pkb", "aops-ts"}


def test_cope_wires_preinvocation_on_agy(dist_root):
    """agy has no PreToolUse equivalent, so cope has no tool call to send its
    evaluator there. It still ships a hook: PreInvocation carries the prompt,
    which is enough to state the live rule set for the turn."""
    assert clients.to_canonical("agy", "PreToolUse") is None
    wired = {wire for wire, _ in _hook_commands("agy", dist_root / "aops-cope-agy")}
    assert wired == {"PreInvocation"}


def test_aops_wires_claude_pretooluse_and_agy_does_not(dist_root):
    """The refusal is Claude-only by necessity, not by choice: agy has no wire
    event that maps to PreToolUse, so wiring one there would spawn a process
    that returns before loading a handler."""
    claude_wired = {wire for wire, _ in _hook_commands("claude", dist_root / "aops-claude")}
    assert "PreToolUse" in claude_wired

    assert clients.to_canonical("agy", "PreToolUse") is None
    agy_wired = {wire for wire, _ in _hook_commands("agy", dist_root / "aops-agy")}
    assert agy_wired == {"PostInvocation"}


# --- 5. ts: the session transcript leaves the box, and takes no defaults ------


def _ts_session_end(dist_root: Path, payload: dict, env_overrides: dict[str, str | None]):
    build_dir = dist_root / "aops-ts-claude"
    return _run_shipped_hook(
        "claude",
        build_dir,
        _command_for("claude", build_dir, "SessionEnd"),
        payload,
        env_overrides=env_overrides,
    )


def test_ts_ships_an_executable_session_end_hook(dist_root):
    script = dist_root / "aops-ts-claude" / "hooks" / "session-end-sync.sh"
    assert script.is_file()
    assert os.access(script, os.X_OK)
    assert "session-end-sync.sh" in _command_for(
        "claude", dist_root / "aops-ts-claude", "SessionEnd"
    )


def test_ts_ships_no_agy_hooks_at_all(dist_root):
    """ts's two hooks are both session-level, and agy has no session-level hook
    event: its `hooks.json` fires PreToolUse, PostToolUse, PreInvocation,
    PostInvocation and Stop, and nothing else. So ts has no hooks on agy, which
    is stated by shipping no `hooks.json` rather than an empty one — and
    certainly not by wiring a `SessionStart` that never fires."""
    assert not (dist_root / "aops-ts-agy" / "hooks.json").exists()
    assert clients.to_canonical("agy", "SessionStart") is None
    assert clients.to_canonical("agy", "SessionEnd") is None


def test_ts_session_end_bakes_no_host_or_search_path(dist_root):
    """No host, endpoint, or path may be baked into a shipped artifact
    (specs/ARCHITECTURE.md, Binding constraints). The regression this guards is
    a client-installation search path used as a fallback when the configured
    source directory is unset."""
    text = (dist_root / "aops-ts-claude" / "hooks" / "session-end-sync.sh").read_text(
        encoding="utf-8"
    )
    assert ".claude/plugins/cache" not in text
    assert "$HOME/" not in text
    assert "${HOME}" not in text


def test_ts_session_end_renderer_contract_is_live(dist_root, tmp_path):
    """The hook renders transcripts by running a module out of the checkout at
    `AOPS_SRC_DIR`. That is the whole reason it needs no baked search path — so
    prove the target exists and the exact invocation works, rather than
    shipping a hook whose one useful path is aspirational.

    The alternative to rendering is shipping the raw, UNREDACTED JSONL, which
    is opt-in precisely because a silently-dead renderer must not become the
    default route for unredacted session data.
    """
    script = (dist_root / "aops-ts-claude" / "hooks" / "session-end-sync.sh").read_text(
        encoding="utf-8"
    )
    assert "lib/py/transcripts/runner.py" in script
    assert "-m transcripts.runner" in script

    fixture = _REPO_ROOT / "tests" / "transcripts" / "fixtures" / "claude_session.jsonl"
    env = dict(os.environ, AOPS_SESSIONS=str(tmp_path), PYTHONPATH=str(_REPO_ROOT / "lib" / "py"))
    proc = subprocess.run(
        [sys.executable, "-m", "transcripts.runner", str(fixture), "--no-sync"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    rendered = sorted(p.name for p in (tmp_path / "transcripts").rglob("*") if p.is_file())
    assert rendered, f"renderer produced nothing; stderr: {proc.stderr!r}"


def test_ts_session_end_no_op_when_not_a_remote_session(dist_root):
    """The hook must cost nothing and say nothing in a local session."""
    proc = _ts_session_end(dist_root, _PAYLOADS["SessionEnd"], {"CLAUDE_CODE_REMOTE": None})
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_ts_session_end_no_destination_is_a_clean_no_op_not_an_error(dist_root):
    """A missing destination is the unconfigured case, not a failure: exit 0,
    nothing on stdout (SessionEnd stdout reaches the model), and a diagnostic
    on stderr saying which variable is unset."""
    proc = _ts_session_end(
        dist_root,
        _PAYLOADS["SessionEnd"],
        {"CLAUDE_CODE_REMOTE": "true", "AOPS_TS_SYNC_DEST": None},
    )
    assert proc.returncode == 0
    assert proc.stdout == ""
    assert "AOPS_TS_SYNC_DEST" in proc.stderr


def test_cope_does_not_wire_claude_userpromptsubmit(dist_root):
    """The turn-level advisory is scoped to agy. Claude fires both events and
    is already covered by cope's PreToolUse check, and the pkb plugin owns
    Claude's UserPromptSubmit — so cope must not register a second one."""
    wired = {wire for wire, _ in _hook_commands("claude", dist_root / "aops-cope-claude")}
    assert wired == {"PreToolUse"}
