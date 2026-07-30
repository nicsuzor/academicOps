"""The honesty floor, proven through the artifact ida actually ships.

The rule this pins is one a unit test on the source cannot reach: the floor is
only real if the built plugin wires a `Stop` hook, the shipped runtime loads
the shipped message file, and the response comes back in the shape the client
parses. Each of those has failed independently before — a message file with no
handler, a handler with no hook entry, a hook wired to an event the client
never fires — and every one of them is invisible to a test that imports the
handler and calls it.

So these build the real plugin and run the real command, once per client.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from build.build import build_all

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MARKETPLACE = _REPO_ROOT / "build" / "marketplace.toml"

# One phrase from each clause of messages/honesty.md that carries a distinct
# obligation. Asserting on the whole file would only restate it; asserting on
# these fails when a clause is dropped, which is exactly how this hook was lost
# the first time — the confidence clause did not survive a migration that kept
# the evidence clause.
# agy sets no plugin-root variable, and the builder only rewrites
# `${AGY_PLUGIN_ROOT}/<path>` — the form with a path after it. Every agy hook
# command in this repo also opens with `uv run --project "${AGY_PLUGIN_ROOT}"`,
# which has no path after it, so it survives into the shipped config, expands
# to nothing, and `uv` exits 2 before dispatch.py is reached. That is true of
# `pkb-agy` today and has nothing to do with this hook, so these cases are
# marked rather than silently dropped: when the builder is fixed they pass, and
# the marker is the record that ida's floor does not currently bind on agy.
_AGY_PLUGIN_ROOT_UNSET = pytest.mark.xfail(
    reason="shipped agy hook commands carry an unexpandable ${AGY_PLUGIN_ROOT}; "
    "uv exits 2 before the hook runs (affects every agy hook, not just this one)",
    strict=False,
)

_CLIENTS = [
    "claude",
    pytest.param("agy", marks=_AGY_PLUGIN_ROOT_UNSET),
]

_REQUIRED_CLAUSES = (
    "Never dress an inference as an observation",  # no confident-sounding guesses
    "carries its evidence inline",  # the hearsay rule's counterpart
    "Attach uncertainty to the claim",  # state the confidence level
    "Name what you did not do",  # gaps named, not smoothed
    "changed, unverified",  # completion claims need observed behaviour
)


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


def _stop_command(ida_dist: Path, client: str) -> tuple[Path, str]:
    """(plugin root, command string) for the hook wired to this client's
    stop-equivalent event, read out of the built config rather than restated."""
    if client == "claude":
        build_dir = ida_dist / "ida-claude"
        config = json.loads((build_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entries = config["hooks"]["Stop"]
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
    """The text that reaches the model, out of each client's own response shape."""
    out = json.loads(stdout)
    if client == "claude":
        return out["hookSpecificOutput"]["additionalContext"]
    return out["injectSteps"][0]["ephemeralMessage"]


@pytest.mark.parametrize("client", _CLIENTS)
def test_stop_injects_every_clause_of_the_honesty_floor(ida_dist, client):
    """The floor fires on a fresh stop, and arrives whole."""
    build_dir, command = _stop_command(ida_dist, client)
    proc = _run(build_dir, command, {"session_id": "honesty-test"})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"

    injected = _injected(client, proc.stdout)
    missing = [clause for clause in _REQUIRED_CLAUSES if clause not in injected]
    assert missing == [], f"the shipped floor dropped: {missing}"


@pytest.mark.parametrize("client", _CLIENTS)
def test_stop_is_advisory_and_never_blocks(ida_dist, client):
    """ida's floor corrects an answer; it may not hold the session open. A
    blocking shape here would trap the face in a stop-chain in front of a
    waiting person."""
    build_dir, command = _stop_command(ida_dist, client)
    proc = _run(build_dir, command, {"session_id": "honesty-test"})
    out = json.loads(proc.stdout)

    assert "decision" not in out
    assert "permissionDecision" not in out.get("hookSpecificOutput", {})


def test_claude_stop_tells_the_person_watching(ida_dist):
    """The floor firing is a fact about the answer they are about to read."""
    build_dir, command = _stop_command(ida_dist, "claude")
    proc = _run(build_dir, command, {"session_id": "honesty-test"})
    assert json.loads(proc.stdout)["systemMessage"]


@pytest.mark.parametrize("client", _CLIENTS)
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"stop_hook_active": True}, id="continuation"),
        pytest.param({"background_tasks": [{"id": "x"}]}, id="work-still-running"),
    ],
)
def test_stop_is_silent_when_it_must_be(ida_dist, client, payload):
    """Injecting on a stop gives the session another turn, which stops again.
    Without the `stop_hook_active` guard this handler re-fires against its own
    continuation and the session cannot end. `background_tasks` holds it quiet
    while work is still running, because no handback is being written yet."""
    build_dir, command = _stop_command(ida_dist, client)
    proc = _run(build_dir, command, {"session_id": "honesty-test", **payload})
    assert proc.returncode == 0, f"stderr: {proc.stderr!r}"
    assert proc.stdout.strip() == ""


def test_subagentstop_is_not_wired_so_the_floor_stays_scoped_to_the_face(ida_dist):
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


def test_the_floor_and_the_hearsay_rule_both_ship(ida_dist):
    """They are one rule seen from both ends — what ida may accept from a
    worker, and what ida may then assert to the user. Shipping either alone
    leaves the other half of the contract unenforced."""
    messages = ida_dist / "ida-claude" / "hooks" / "messages"
    for name in ("honesty", "hearsay"):
        assert (messages / f"{name}.md").is_file()
        assert (messages / f"{name}.user.md").is_file()


def test_no_shipped_message_text_is_built_from_a_python_literal(ida_dist):
    """Every agent-visible string comes from a message file. A handler that
    inlines its text drifts from the file reviewers read, and silently keeps
    firing the old wording after the file is corrected."""
    handlers = (ida_dist / "ida-claude" / "hooks" / "handlers.py").read_text(encoding="utf-8")
    for name in ("honesty", "hearsay"):
        assert f'load_message_pair(ctx.hooks_dir, "{name}")' in handlers


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
