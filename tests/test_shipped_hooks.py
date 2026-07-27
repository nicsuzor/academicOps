"""Tests against the SHIPPED artifact, not the source it was built from.

`tests/test_hooks.py` proves the hook runtime works when Python imports it.
`tests/test_build.py` proves the builder puts files where the client looks.
Neither one ever executed a shipped hook the way its client executes it, so
every Python hook could ship non-executable — invoked by bare path, mode
`0644` — and the whole suite stayed green while nothing fired.

These tests close that gap by treating the built tree as the unit under test:
they read the `command` string out of the built `hooks.json`, substitute the
real plugin root, and run it exactly as its client would — through a shell for
Claude Code, through argv for agy, which execs without shell expansion.

The fixture builds the real `plugins/` into a temporary dist, so the assertions
hold for whatever `make build` would produce right now, with no dependency on
a `dist/` a developer may or may not have refreshed.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tarfile
import zipfile
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

# The plugin-root variable each client expands in a hook command.
_PLUGIN_ROOT_VAR = {"claude": "${CLAUDE_PLUGIN_ROOT}", "agy": "${AGY_PLUGIN_ROOT}"}

# One representative payload per canonical event, shaped like the real thing.
# PreToolUse carries the reproduction case: a `--no-verify` commit, which is
# exactly what cope's halt-on-failure detector exists to catch.
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


def _hook_commands(client: str, build_dir: Path) -> list[tuple[str, str]]:
    """(wire event, command string) for every hook the built config registers."""
    commands = []
    for wire_event, entries in _hooks_config(client, build_dir).get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                if "command" in hook:
                    commands.append((wire_event, hook["command"]))
    return commands


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

    Claude Code hands the command to a shell, so quoting is honoured. agy execs
    an argv vector with no shell expansion, which is why the agy adapter strips
    quotes — splitting here without a shell is what proves that stripping was
    necessary and sufficient.

    ``env_overrides`` sets or, with a ``None`` value, unsets one variable for
    this run — the hooks under test read the environment, so a test that
    asserts on their behaviour has to control it rather than inherit it.
    """
    resolved = command.replace(_PLUGIN_ROOT_VAR[client], str(build_dir))
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_REMOTE", None)  # keep the ts hooks on their no-op path
    for key, value in (env_overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    kwargs = dict(input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=60)
    if client == "claude":
        return subprocess.run(resolved, shell=True, **kwargs)  # noqa: S602
    return subprocess.run(shlex.split(resolved), **kwargs)


def _command_for(client: str, build_dir: Path, wire_event: str) -> str:
    matches = [cmd for wire, cmd in _hook_commands(client, build_dir) if wire == wire_event]
    assert len(matches) == 1, f"{build_dir.name}: {len(matches)} {wire_event} hooks, expected 1"
    return matches[0]


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


def test_cope_shipped_hook_flags_the_axiom_it_ships_for(dist_root):
    """End-to-end through the artifact: the built cope hook, run as Claude Code
    runs it, on a `--no-verify` commit, names halt-on-failure and echoes the
    match. Exit 0 alone would also be satisfied by a hook that does nothing."""
    build_dir = dist_root / "aops-cope-claude"
    commands = _hook_commands("claude", build_dir)
    assert commands, "aops-cope-claude ships no hook command"

    _, command = commands[0]
    proc = _run_shipped_hook("claude", build_dir, command, _PAYLOADS["PreToolUse"])
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    advisory = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "--no-verify" in advisory


# --- 1b. the one blocking hook, and the boundary around it --------------------
#
# A headless session cannot answer an interactive prompt, so the prompt hangs
# until the session times out. aops's PreToolUse hook refuses it. That is a
# capability fact, not a rule verdict (specs/ARCHITECTURE.md, Hooks), and these
# tests pin all four edges: it fires, it fires only on those tools, it fires
# only when headless, and cope still cannot reach the mechanism.

_INTERACTIVE_TOOLS = ("ask_question", "AskFollowupQuestion", "ask_followup_question", "Question")


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


def test_shipped_cope_hook_can_never_emit_a_blocking_decision(dist_root):
    """cope is advisory, permanently. Run its shipped PreToolUse hook on the
    payload most likely to provoke a block — a rule it actively detects — under
    a headless environment, and require the advisory shape and nothing else."""
    build_dir = dist_root / "aops-cope-claude"
    proc = _run_shipped_hook(
        "claude",
        build_dir,
        _command_for("claude", build_dir, "PreToolUse"),
        _PAYLOADS["PreToolUse"],
        env_overrides={**dict.fromkeys(_HEADLESS_ENV, None), "NONINTERACTIVE": "1"},
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert "permissionDecision" not in proc.stdout
    assert "allowTool" not in proc.stdout
    assert json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def test_shipped_cope_never_reaches_the_refusal_primitive(dist_root):
    """Structural, not behavioural: cope's own shipped modules must not so much
    as name `refuse`. The runtime is shared, so the only thing keeping cope
    advisory is that its handlers never call it — assert that directly, rather
    than trusting one payload not to have found the path."""
    cope_hooks = dist_root / "aops-cope-claude" / "hooks"
    cope_own = {"handlers.py", "detectors.py", "rules.py"}
    offenders = [
        path.name
        for path in sorted(cope_hooks.glob("*.py"))
        if path.name in cope_own and "refuse" in path.read_text(encoding="utf-8")
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
    """agy has no PreToolUse equivalent, so cope's detectors can never run
    there. It still ships a hook: PreInvocation carries the prompt, which is
    enough to state the live rule set for the turn."""
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


def test_ts_session_end_is_not_wired_for_agy(dist_root):
    """agy has no confirmed SessionEnd wire event. Shipping one anyway would be
    a hook that never fires, indistinguishable from a working one."""
    wired = {wire for wire, _ in _hook_commands("agy", dist_root / "aops-ts-agy")}
    assert wired == {"SessionStart"}


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
