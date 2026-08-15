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
import tomllib
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
_POLICY_FILE = _REPO_ROOT / "tests" / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}


def _require_evaluate_enabled():
    if not _policy.get("rbg", {}).get("evaluate", {}).get("enabled", True):
        pytest.skip("rbg evaluate hook is disabled by policy")


_CLIENTS = ("claude", "agy")

# PEP 440, because the built plugin carries this into its own pyproject.toml
# and `uv run` — which is how every hook command starts — refuses to parse a
# version it cannot resolve. `0.0.0-test` is not PEP 440: uv exits 2 with a
# TOML parse error before dispatch.py is reached, which fails every hook
# execution case in this file at the point furthest from its cause.
_VERSION = "0.0.0.dev0"

# The debug plugin registers a wildcard handler (`HANDLERS = {"*": [...]}`) and
# wires every event its client can emit, mapped or not — capturing unmapped
# events is the whole point of it. Both the wiring-coverage assertions below
# are about plugins whose handlers register named canonical events, so they
# exempt any plugin that registers `*`. Detected from the shipped handlers.py
# rather than by plugin name, so a second debug-style plugin is covered and a
# rename does not silently reopen the hole.
_WILDCARD_EVENT = "*"

if str(_LIB_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIB_HOOKS))

from dispatch import TO_CANONICAL  # noqa: E402


def _wire_events(client: str) -> dict[str, str]:
    """This client's whole wire vocabulary: wire event name -> canonical name.

    Read straight off the shipped table rather than through
    `dispatch.to_canonical`, which falls back to returning an unmapped wire
    event under its own name and so cannot answer "is this event in the table
    at all". An unknown client has no vocabulary — an empty mapping, not an
    error.
    """
    return dict(TO_CANONICAL.get(client, {}))


def _canonical_or_none(client: str, wire_event: str) -> str | None:
    """The canonical name for a wire event, or None if this client cannot fire
    it. Same reason as `_wire_events` for going to the table directly."""
    return TO_CANONICAL.get(client, {}).get(wire_event)


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
    # A resolved batch that dispatched a subagent alongside an ordinary call —
    # the shape orchestrate's receiver-side handback reminder exists to catch.
    "PostToolBatch": {
        "hook_event_name": "PostToolBatch",
        "session_id": "test-session",
        "tool_calls": [
            {"tool_name": "Read", "tool_use_id": "a", "tool_input": {}, "tool_response": {}},
            {"tool_name": "Agent", "tool_use_id": "b", "tool_input": {}, "tool_response": {}},
        ],
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
    """The real plugins, really built — every plugin, both clients.

    This is the tree the execution tests run hooks out of, and rbg's hook has
    nothing to do unless at least one rule is live. Which axioms are switched on
    is a deliberately movable fact — they are all parked today and are being
    re-armed one at a time — so the marker is flipped on here rather than left
    to whatever the roster happens to be. Otherwise every assertion about what
    the shipped hook *does* would quietly become an assertion that it does
    nothing, and still pass.

    The axiom bodies are the real ones; only the marker is touched. Assertions
    about what the build EMITS use `pristine_dist`, which is left exactly as
    built.
    """
    root = tmp_path_factory.mktemp("shipped-dist")
    build_all(_REPO_ROOT, root, marketplace_path=_MARKETPLACE, version=_VERSION)
    for md in (root / "rbg-claude" / "axioms").glob("*.md"):
        text = md.read_text(encoding="utf-8")
        md.write_text(
            text.replace("\ntrigger: off\n", "\ntrigger: always_on\n", 1), encoding="utf-8"
        )
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
    # This suite runs under `uv run`, so VIRTUAL_ENV names the academicOps
    # venv. Every hook command starts `uv run --project <plugin>`, and uv warns
    # on stderr when an active VIRTUAL_ENV is not the project's own. No client
    # runs a hook with this repo's venv active, so inheriting it would put
    # stderr output into these runs that the field never produces — and the
    # silence assertions would be measuring the test runner, not the hook.
    env.pop("VIRTUAL_ENV", None)
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

    `${extensionPath}` and `${CLAUDE_PLUGIN_ROOT}` are the one exception,
    mirroring the allowlist in `build/clients/agy._checked_mcp`: the
    aops-crew image's `docker_gemini_fixups.py fixup-mcp-config-paths` rewrites
    either token to the plugin's real install directory after `agy plugin
    install` has copied it there, so a config agy reads inside that container
    never sees the literal placeholder. Outside that image the config still
    ships broken — a bare-host `agy plugin install` gets an unresolved
    reference, same as before — which is why the allowlist stays this narrow
    rather than growing to cover any other variable.
    """
    allowed = {"${extensionPath}", "${CLAUDE_PLUGIN_ROOT}"}
    offenders = []
    for name, client, build_dir in _build_dirs(dist_root):
        if client != "agy":
            continue
        for config in sorted(build_dir.glob("*.json")):
            matches = set(re.findall(r"\$\{[^}]*\}", config.read_text(encoding="utf-8")))
            for match in matches - allowed:
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
    agy_commands = 0
    for name, client, build_dir in _build_dirs(dist_root):
        for wire_event, command in _hook_commands(client, build_dir):
            if client == "agy":
                agy_commands += 1
            canonical = _canonical_or_none(client, wire_event)
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
    assert agy_commands > 0, "no agy hook commands were found at all"


def _registers_wildcard(hooks_dir: Path) -> bool:
    """Does this plugin's shipped handlers.py register the `*` event?

    Read as text rather than imported: this is called from cases that only need
    the yes/no, and a subprocess import per plugin per case costs more than the
    question is worth. `_registered_events` does the real load where the actual
    event set matters.
    """
    handlers = hooks_dir / "handlers.py"
    if not handlers.is_file():
        return False
    return f'"{_WILDCARD_EVENT}"' in handlers.read_text(encoding="utf-8")


def test_no_dispatch_hook_is_wired_to_an_unmappable_event(dist_root):
    """A `dispatch.py` hook wired to a wire event `TO_CANONICAL` does not map
    for this client is a hook whose event name is never translated.

    `dispatch.to_canonical` passes an unmapped wire event straight through
    under its own name, so such a hook does not no-op cleanly: it goes on to
    load handlers under an event name no plugin registers, spawning a process
    per event to find nothing. Either way the hook does no work, and the
    wiring is the bug.

    Scoped to `dispatch.py` hooks on purpose. A plugin whose hook is a plain
    script — ts's `tailscale-up.sh` — never consults that table, so the table
    says nothing about which events it may legitimately register.
    """
    for name, client, build_dir in _build_dirs(dist_root):
        if _registers_wildcard(build_dir / "hooks"):
            continue
        for wire_event, command in _hook_commands(client, build_dir):
            if "dispatch.py" not in command:
                continue
            assert _canonical_or_none(client, wire_event) is not None, (
                f"{name}-{client}: hooks.json runs dispatch.py for wire event "
                f"{wire_event!r}, which lib/hooks/dispatch.py's TO_CANONICAL "
                f"does not map for this client — the hook fires and finds "
                f"no handler"
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
        "COPE_EVALUATOR_TRACE_PATH": None,  # unset here; tests that want it set it themselves
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
    _require_evaluate_enabled()
    build_dir = dist_root / "rbg-claude"
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
    _require_evaluate_enabled()
    build_dir = dist_root / "rbg-claude"
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


def test_rbg_shipped_hook_reports_a_degradation_out_of_the_built_artifact(
    dist_root, stub_evaluator_env, tmp_path
):
    """The framework's own failure, reported, out of the built artifact.

    A rule file that cannot be read is a rule that is not being enforced, and
    the report has to name the file — the only person who can fix it needs to
    know which one. It goes to stderr and nowhere else: the response channel
    for degradation notices went with lib/hooks/degraded.py (89733bf8), and the
    current contract is stated in plugins/rbg/hooks/evaluator.py's module
    docstring. The check that the notice still carries its detail is what
    survived that change, so that is what is asserted.

    The rest of the rule set keeps working regardless — one unreadable file
    displaces nothing else, which is the fail-open guarantee. And reporting is
    never a gate: this hook may not block a tool call.
    """
    _require_evaluate_enabled()
    project = tmp_path / "project"
    (project / ".agents" / "rules").mkdir(parents=True)
    (project / ".agents" / "rules" / "unreadable.md").mkdir()  # a rule file that is not a file

    build_dir = dist_root / "rbg-claude"
    _, command = _hook_commands("claude", build_dir)[0]
    proc = _run_shipped_hook(
        "claude",
        build_dir,
        command,
        {**_PAYLOADS["PreToolUse"], "session_id": "degraded-session", "cwd": str(project)},
        env_overrides=stub_evaluator_env,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    assert "unreadable.md" in proc.stderr, "the shipped hook degraded and said so nowhere"
    assert "not being checked" in proc.stderr
    assert "IsADirectoryError" in proc.stderr

    out = json.loads(proc.stdout)
    assert "halt-on-failure" in out["hookSpecificOutput"]["additionalContext"]
    assert "decision" not in out
    assert "permissionDecision" not in out["hookSpecificOutput"]


def test_rbg_shipped_hook_is_a_silent_no_op_with_no_evaluator_configured(dist_root):
    """The shipped default. The plugin bakes in no endpoint, so an installation
    that has not configured one must cost the session nothing on every tool
    call: no advisory, no error, no stderr.

    Run twice, asserting on the second. The first `uv run` against a freshly
    built tree creates the plugin's `.venv/` and narrates that on stderr, which
    would fail the silence assertion for a reason that has nothing to do with
    the hook. Warming it first keeps the assertion exact — stderr must be
    EMPTY, not merely free of anything that looks like a complaint.
    """
    _require_evaluate_enabled()
    build_dir = dist_root / "rbg-claude"
    _, command = _hook_commands("claude", build_dir)[0]
    unconfigured = dict.fromkeys(
        (
            "COPE_EVALUATOR_URL",
            "COPE_EVALUATOR_PROTOCOL",
            "COPE_EVALUATOR_MODEL",
            "COPE_EVALUATOR_API_KEY",
            "COPE_EVALUATOR_TIMEOUT",
            "COPE_EVALUATOR_TRACE_PATH",
        )
    )
    _run_shipped_hook(
        "claude", build_dir, command, _PAYLOADS["PreToolUse"], env_overrides=unconfigured
    )
    proc = _run_shipped_hook(
        "claude", build_dir, command, _PAYLOADS["PreToolUse"], env_overrides=unconfigured
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


def test_rbg_shipped_hook_traces_every_rule_evaluated_not_only_the_matches(
    dist_root, stub_evaluator_env, tmp_path
):
    """End-to-end proof that tracing is wired into the shipped artifact: set
    ``COPE_EVALUATOR_TRACE_PATH``, run the real hook against the real 23-rule
    axiom set, and check that every live rule shows up in the trace — not just
    ``halt-on-failure``, which is the one the stub evaluator flags. A tuning
    set built from the flags alone could never show what an unflagged rule was
    asked and answered, which is the whole reason every evaluation is traced."""
    _require_evaluate_enabled()
    build_dir = dist_root / "rbg-claude"
    _, command = _hook_commands("claude", build_dir)[0]
    trace_path = tmp_path / "trace" / "rbg-eval-trace.jsonl"
    env = dict(stub_evaluator_env)
    env["COPE_EVALUATOR_TRACE_PATH"] = str(trace_path)

    proc = _run_shipped_hook(
        "claude", build_dir, command, _PAYLOADS["PreToolUse"], env_overrides=env
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 1, "only one rule was traced; the whole live rule set should be"
    records = [json.loads(line) for line in lines]

    matched = [r for r in records if r["rule_slug"] == "halt-on-failure"]
    assert matched and matched[0]["label"] == 1
    assert matched[0]["error"] is None

    clean = [r for r in records if r["label"] == 0]
    assert clean, "no clean (label=0) rule made it into the trace — only flags were recorded"

    for record in records:
        assert record["rule_text"], f"{record['rule_slug']} traced with no policy text"
        assert record["model"] == "stub-model"
        assert record["protocol"] == "cope"
        assert record["concurrency"] == 8
        assert record["sweep_temperature"] == "cold"  # first sweep this session has run
        assert "api_key" not in record and "COPE_EVALUATOR_API_KEY" not in json.dumps(record)
    assert len({r["sweep_id"] for r in records}) == 1, "one tool call is one sweep"


# --- 1b. no shipped hook denies a tool call -----------------------------------
#
# The framework's one refusing hook — aops's `PreToolUse` check, which denied an
# interactive prompt in a headless session — retired with the aops plugin
# (plugins.disabled/aops/, and its `[[plugins]]` entry commented out in
# build/marketplace.toml). Its cases went with it; the refusal PRIMITIVE is
# still exercised, at the runtime level, by tests/test_dispatch_gate.py.
#
# What remains here is the boundary that outlived the hook: nothing that ships
# today may reach the deny shape. That is asserted below both behaviourally
# (the advisory shape and nothing else, on the payload most likely to provoke a
# block) and structurally (the source cannot construct a refusal at all).


def test_shipped_rbg_hook_can_never_emit_a_blocking_decision(dist_root, stub_evaluator_env):
    """rbg's rule check is advisory, permanently. Run its shipped PreToolUse
    hook on the payload most likely to provoke a block — a call its evaluator
    flags — under a headless environment, and require the advisory shape and
    nothing else.

    Scoped to `PreToolUse`. rbg's `Stop`/`SubagentStop` gate does carry a
    disposition, and legitimately: what it withholds is the stop, not the tool
    call. Its coverage is tests/test_rbg_stop_gate.py."""
    _require_evaluate_enabled()
    build_dir = dist_root / "rbg-claude"
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


def test_shipped_rbg_never_reaches_the_refusal_primitive(dist_root):
    """Structural, not behavioural: rbg's own shipped modules must not be able
    to reach the REFUSAL outcome at all. The runtime is shared, so the only
    thing keeping the rule check off the deny shape is that its handlers never
    get there — assert that directly, rather than trusting one payload not to
    have found the path.

    A refusal denies a tool call. rbg's `block` on a stop is a different
    disposition and is deliberately not banned here — see the module note above
    section 1b.

    Three tokens, not one. `refuse` (lowercase) does not match `Kind.REFUSE`,
    so searching for the helper alone would sail past
    `Result(text, None, Kind.REFUSE)`, which lib/hooks/dispatch.py renders as
    `permissionDecision: deny` just as a refuse() call would; a positional
    construction evades both. Banning construction closes it, and costs nothing
    — the return annotation `Result | None` has no `(`.
    """
    rbg_hooks = dist_root / "rbg-claude" / "hooks"
    rbg_own = {"handlers.py", "evaluator.py", "rules.py"}
    offenders = [
        f"{path.name}: {token}"
        for path in sorted(rbg_hooks.glob("*.py"))
        if path.name in rbg_own
        for token in ("refuse", "Kind.REFUSE", "Result(")
        if token in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


# --- 2. mode: a shipped `#!` file is runnable ---------------------------------


def test_every_shipped_shebang_file_is_executable(pristine_dist):
    """A `#!` line declares an entry point. `shutil.copy2` reproduces the
    source's mode, so without the build asserting this, a library file
    committed 0644 ships unrunnable — silently, until a client invokes it.

    Against the pristine tree, for the same reason the cleanliness cases below
    are: this asserts what the BUILD emits, and the execution cases above run
    `uv run` inside their own tree, which creates a `.venv/` there full of
    third-party scripts whose modes are uv's business and not the builder's.
    """
    not_executable = [
        str(path.relative_to(pristine_dist))
        for path in sorted(pristine_dist.rglob("*"))
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
        if _registers_wildcard(hooks_dir):
            continue  # the debug plugin wires every event on purpose

        registered = _registered_events(hooks_dir, client)
        if not registered:
            # If a plugin is entirely disabled by policy, we allow it to register nothing.
            is_disabled = False
            if name == "rbg" and not _policy.get("rbg", {}).get("evaluate", {}).get(
                "enabled", True
            ):
                is_disabled = True
            elif name == "ida" and not _policy.get("ida", {}).get("strip_the_reply_enabled", True):
                is_disabled = True
            elif name == "pkb" and not _policy.get("pkb", {}).get("search_the_pkb_enabled", True):
                is_disabled = True
            elif name == "orchestrate":
                p = _policy.get("orchestrate", {})
                if not p.get("rule_against_hearsay_enabled", True) and not p.get(
                    "honest_output_enabled", True
                ):
                    is_disabled = True
            assert is_disabled, f"{name}-{client}: handlers.py registers nothing"
            continue

        expected = {
            wire for wire, canonical in _wire_events(client).items() if canonical in registered
        }
        wired = {wire for wire, _ in _hook_commands(client, build_dir)}

        def _wires_for(canonical: str, c_name: str = client) -> set[str]:
            return {w for w, c in _wire_events(c_name).items() if c == canonical} | {canonical}

        allowed_missing = set()
        if name == "orchestrate":
            allowed_missing.update(_wires_for("SubagentStop"))
            p = _policy.get("orchestrate", {})
            if not p.get("rule_against_hearsay_enabled", True):
                allowed_missing.update(_wires_for("PostToolBatch"))
            if not p.get("honest_output_enabled", True):
                allowed_missing.update(_wires_for("SubagentStart"))
        elif name == "rbg" and not _policy.get("rbg", {}).get("evaluate", {}).get("enabled", True):
            allowed_missing.update(_wires_for("PreToolUse"))
        elif name == "ida" and not _policy.get("ida", {}).get("strip_the_reply_enabled", True):
            allowed_missing.update(_wires_for("PostToolBatch"))
            allowed_missing.update(_wires_for("Stop"))
        elif name == "pkb" and not _policy.get("pkb", {}).get("search_the_pkb_enabled", True):
            allowed_missing.update(_wires_for("UserPromptSubmit"))

        wired = wired - allowed_missing
        expected = expected - allowed_missing

        assert wired == expected, (
            f"{name}-{client}: handlers register {sorted(registered)}; "
            f"this client fires {sorted(expected)}; hooks.json wires {sorted(wired)}"
        )
        checked += 1
    assert checked > 0, "no hook-bearing plugins were checked"


def test_hook_bearing_plugins_all_present(dist_root):
    """Guards the loop above against silently checking nothing: these are the
    Hooks table in specs/ARCHITECTURE.md, plus the debug plugin.

    Equality, so a plugin that stops shipping hooks fails here rather than
    quietly dropping out of the coverage loop above.
    """
    hook_plugins = {
        name
        for name, client, build_dir in _build_dirs(dist_root)
        if _hooks_config(client, build_dir)
    }
    assert hook_plugins == {"aops-debug", "ida", "orchestrate", "pkb", "rbg", "ts"}


def test_rbg_wires_preinvocation_on_agy(dist_root):
    """agy has no PreToolUse equivalent, so rbg has no tool call to send its
    evaluator there. It still ships a hook: PreInvocation carries the prompt,
    which is enough to state the live rule set for the turn."""
    assert _canonical_or_none("agy", "PreToolUse") is None
    wired = {wire for wire, _ in _hook_commands("agy", dist_root / "rbg-agy")}
    assert wired == {"PreInvocation", "PostInvocation"}


def test_rbg_wires_claude_pretooluse_and_agy_does_not(dist_root):
    """The evaluator check is Claude-only by necessity, not by choice: agy has
    no wire event that maps to PreToolUse, so wiring one there would spawn a
    process that finds no tool call to judge."""
    claude_wired = {wire for wire, _ in _hook_commands("claude", dist_root / "rbg-claude")}
    assert "PreToolUse" in claude_wired

    assert _canonical_or_none("agy", "PreToolUse") is None
    agy_wired = {wire for wire, _ in _hook_commands("agy", dist_root / "rbg-agy")}
    assert "PreToolUse" not in agy_wired


# --- 5. ts: the session transcript leaves the box, and takes no defaults ------


def _ts_session_end(dist_root: Path, payload: dict, env_overrides: dict[str, str | None]):
    build_dir = dist_root / "ts-claude"
    return _run_shipped_hook(
        "claude",
        build_dir,
        _command_for("claude", build_dir, "SessionEnd"),
        payload,
        env_overrides=env_overrides,
    )


def test_ts_ships_an_executable_session_end_hook(dist_root):
    script = dist_root / "ts-claude" / "hooks" / "session-end-sync.sh"
    assert script.is_file()
    assert os.access(script, os.X_OK)
    assert "session-end-sync.sh" in _command_for("claude", dist_root / "ts-claude", "SessionEnd")


def test_ts_ships_no_agy_hooks_at_all(dist_root):
    """ts's two hooks are both session-level, and agy has no session-level hook
    event: its `hooks.json` fires PreToolUse, PostToolUse, PreInvocation,
    PostInvocation and Stop, and nothing else. So ts has no hooks on agy, which
    is stated by shipping no `hooks.json` rather than an empty one — and
    certainly not by wiring a `SessionStart` that never fires."""
    assert not (dist_root / "ts-agy" / "hooks.json").exists()
    assert _canonical_or_none("agy", "SessionStart") is None
    assert _canonical_or_none("agy", "SessionEnd") is None


def test_ts_session_end_bakes_no_host_or_search_path(dist_root):
    """No host, endpoint, or path may be baked into a shipped artifact
    (specs/ARCHITECTURE.md, Binding constraints). The regression this guards is
    a client-installation search path used as a fallback when the configured
    source directory is unset."""
    text = (dist_root / "ts-claude" / "hooks" / "session-end-sync.sh").read_text(encoding="utf-8")
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
    script = (dist_root / "ts-claude" / "hooks" / "session-end-sync.sh").read_text(encoding="utf-8")
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


def test_rbg_does_not_wire_claude_userpromptsubmit(dist_root):
    """The turn-level ruleset advisory is scoped to agy. Claude fires both
    events and is already covered by rbg's PreToolUse check, and the pkb plugin
    owns Claude's UserPromptSubmit — so rbg must not register a second one.

    Asserted as an absence rather than as the whole wired set: rbg legitimately
    wires the stop-side gate on Claude too (`Stop`/`SubagentStop`, covered by
    tests/test_rbg_stop_gate.py), and an equality here would fail on that for a
    reason this case is not about.
    """
    wired = {wire for wire, _ in _hook_commands("claude", dist_root / "rbg-claude")}
    assert "UserPromptSubmit" not in wired
    assert "PreToolUse" in wired


def test_no_handler_blocks_on_agy(dist_root):
    """No handler is permitted to return a blocking disposition on agy.

    Policy-as-code invariant from tests/policy.toml [hooks.blocking].allow_blocking_agy.
    """
    allow_blocking_agy = (
        _policy.get("hooks", {}).get("blocking", {}).get("allow_blocking_agy", False)
    )
    if allow_blocking_agy:
        pytest.skip("blocking on agy is explicitly allowed by policy")

    for name, client, build_dir in _build_dirs(dist_root):
        if client != "agy":
            continue
        hooks_dir = build_dir / "hooks"
        if not (hooks_dir / "handlers.py").is_file():
            continue
        for wire_event, cmd in _hook_commands("agy", build_dir):
            canonical = _canonical_or_none("agy", wire_event)
            payload = _PAYLOADS.get(canonical or wire_event, {"conversationId": "test-session"})
            proc = _run_shipped_hook("agy", build_dir, cmd, payload)
            assert proc.returncode == 0, (
                f"{name}-agy {wire_event}: hook failed with stderr {proc.stderr!r}"
            )
            if proc.stdout.strip():
                try:
                    data = json.loads(proc.stdout)
                    assert data.get("decision") != "deny", (
                        f"{name}-agy {wire_event} emitted blocking decision: {data}"
                    )
                except json.JSONDecodeError:
                    pass
