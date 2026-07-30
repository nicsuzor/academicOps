"""Behavioural tests for rbg's dual-layer rule channel.

Every case here runs the *real* shipped `dispatch.py` as a subprocess with a
synthetic hook payload on stdin, against a plugin directory staged the way
`build/build.py` stages one — `lib/hooks/` copied in first, the plugin's own
`hooks/` laid on top. Nothing is mocked and no handler is called directly:
what is asserted is the JSON that would actually reach the client, and the
exit code that would actually accompany it.

That matters more than usual here. A hook can be registered in a manifest, be
present in `HANDLERS`, and still emit nothing a client honours — so the thing
worth pinning is the wire output, not the wiring.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
RBG_HOOKS = REPO_ROOT / "plugins" / "rbg" / "hooks"
RBG_MANIFEST = REPO_ROOT / "plugins" / "rbg" / "manifest" / "hooks.template.json"

RULE_CHECK_TEXT = (RBG_HOOKS / "messages" / "rule-check.md").read_text(encoding="utf-8").strip()

STOP_EVENTS = ("Stop", "SubagentStop")


@pytest.fixture
def staged(tmp_path) -> Path:
    """A plugin `hooks/` directory assembled exactly as the build assembles one.

    Build stage 1 injects `lib/hooks/` into the plugin tree, so at runtime
    `dispatch.py` and `handlers.py` sit in the same directory and import each
    other as flat modules. Reproducing that here is what makes these tests
    exercise the shipped arrangement rather than a repository-only one.

    Per-test, not shared: several cases below swap `handlers.py` or a message
    file to prove a property, and a fixture they can reach across tests would
    make those swaps somebody else's flake.
    """
    hooks = tmp_path / "hooks"
    shutil.copytree(LIB_HOOKS, hooks, ignore=shutil.ignore_patterns("__pycache__"))
    for item in RBG_HOOKS.iterdir():
        if item.name == "__pycache__":
            continue
        if item.is_dir():
            shutil.copytree(item, hooks / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, hooks / item.name)
    return hooks


def fire(staged: Path, client: str, event: str, payload: dict | None = None):
    """Run one hook the way the client runs it: argv, JSON on stdin, JSON out."""
    proc = subprocess.run(
        [sys.executable, str(staged / "dispatch.py"), client, event],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        timeout=60,
        # No evaluator configured anywhere in this file: `evaluate` must be a
        # clean no-op, and nothing here may reach the network.
        env={"PATH": "/usr/bin:/bin", "HOME": str(staged)},
    )
    return proc


def parsed(proc) -> dict | None:
    assert proc.returncode == 0, f"exit {proc.returncode}; stderr: {proc.stderr}"
    out = proc.stdout.strip()
    return json.loads(out) if out else None


# ---------------------------------------------------------------------------
# Layer 2: the stop gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event", STOP_EVENTS)
def test_a_plain_stop_is_blocked_with_the_shipped_reason(staged, event):
    """The disposition the client honours is top-level `decision: block` — not
    a field under `hookSpecificOutput`, which is where every advisory goes and
    where a block would be silently ignored."""
    out = parsed(fire(staged, "claude", event, {"session_id": "s1"}))
    assert out == {"decision": "block", "reason": RULE_CHECK_TEXT}


@pytest.mark.parametrize("event", STOP_EVENTS)
def test_stop_hook_active_absent_and_false_both_block(staged, event):
    """Absent and explicitly false are the same state; a guard that only read
    the key's presence would let the gate fire on neither or on both."""
    for payload in ({"session_id": "s1"}, {"session_id": "s1", "stop_hook_active": False}):
        out = parsed(fire(staged, "claude", event, payload))
        assert out is not None and out["decision"] == "block"


@pytest.mark.parametrize("event", STOP_EVENTS)
def test_the_continuation_stop_is_silent(staged, event):
    """The block gives the session another turn, which stops again and re-fires
    this hook with `stop_hook_active` set. Firing again there is the loop that
    never lets a session end, so the second stop must produce nothing at all."""
    proc = fire(staged, "claude", event, {"session_id": "s1", "stop_hook_active": True})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_the_guard_is_in_the_runtime_not_the_handler(staged):
    """A handler that forgot the check would still be guarded. Proven by
    removing rbg's handlers entirely: a marked stop stays silent even with a
    handler registry that could not possibly have checked anything."""
    (staged / "handlers.py").rename(staged / "handlers.py.bak")
    try:
        (staged / "handlers.py").write_text(
            "from dispatch import block\n\n"
            "def always(ctx):\n"
            "    return block('unconditional')\n\n"
            "HANDLERS = {'Stop': [always]}\n",
            encoding="utf-8",
        )
        loud = parsed(fire(staged, "claude", "Stop", {"stop_hook_active": False}))
        assert loud == {"decision": "block", "reason": "unconditional"}

        proc = fire(staged, "claude", "Stop", {"stop_hook_active": True})
        assert proc.stdout.strip() == "", "a handler with no guard of its own still fired"
    finally:
        (staged / "handlers.py").unlink()
        (staged / "handlers.py.bak").rename(staged / "handlers.py")


def test_the_reason_is_the_shipped_message_file_not_a_python_literal(staged):
    """Agent-visible strings live in `hooks/messages/*.md` so they can be
    edited without touching code. Checked by editing one and requiring the
    change to come out the other end."""
    message = staged / "messages" / "rule-check.md"
    original = message.read_text(encoding="utf-8")
    try:
        message.write_text("CHECK THE RULES, PLEASE", encoding="utf-8")
        out = parsed(fire(staged, "claude", "Stop", {}))
        assert out == {"decision": "block", "reason": "CHECK THE RULES, PLEASE"}
    finally:
        message.write_text(original, encoding="utf-8")


# ---------------------------------------------------------------------------
# Client asymmetry: blocking is Claude-only, structurally
# ---------------------------------------------------------------------------


def test_agy_gets_an_advisory_and_never_a_block(staged):
    """agy's `PostInvocation` maps to canonical `Stop`, so `rule_check` does run
    there — but agy has no blockable event and its response contract carries no
    disposition field. The text has to arrive as advice or not at all."""
    out = parsed(fire(staged, "agy", "PostInvocation", {"conversationId": "c1"}))
    assert out == {"injectSteps": [{"ephemeralMessage": RULE_CHECK_TEXT}]}
    assert "decision" not in out


def test_a_block_on_a_non_blockable_event_degrades_and_says_so(staged):
    """Claude Code has no `decision` field on `PreToolUse`, so emitting one
    there would be a no-op a handler could mistake for enforcement. It becomes
    an advisory instead, and the misuse is reported."""
    (staged / "handlers.py").rename(staged / "handlers.py.bak")
    try:
        (staged / "handlers.py").write_text(
            "from dispatch import block\n\n"
            "def misplaced(ctx):\n"
            "    return block('wrong event')\n\n"
            "HANDLERS = {'PreToolUse': [misplaced]}\n",
            encoding="utf-8",
        )
        proc = fire(staged, "claude", "PreToolUse", {"tool_name": "Bash"})
        out = parsed(proc)
        assert out is not None
        assert "decision" not in out
        assert out["hookSpecificOutput"]["additionalContext"] == "wrong event"
        assert "does not honour one" in proc.stderr
    finally:
        (staged / "handlers.py").unlink()
        (staged / "handlers.py.bak").rename(staged / "handlers.py")


# ---------------------------------------------------------------------------
# Layer 1 stays advisory — the constraint that outranks the feature
# ---------------------------------------------------------------------------


def test_pretooluse_with_no_evaluator_is_a_clean_no_op(staged):
    """Unconfigured is a legitimate state, not a fault: no output, no network,
    exit 0. Layer 2 firing on the same plugin must not change that."""
    proc = fire(
        staged, "claude", "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_no_layer_one_surface_can_ever_carry_a_disposition(staged):
    """The binding constraint on Layer 1: advisory, overridable, permanently.
    Asserted at the source, because a payload that happens not to trigger a
    disposition would not notice one being added.

    Three spellings, because `refuse` is not a substring of `is_refusal` and a
    positional `Result(text, None, True)` evades both — and `block` is now a
    fourth route the older form of this guard could not see.
    """
    layer_one = ("evaluate", "inject_ruleset")
    source = (RBG_HOOKS / "handlers.py").read_text(encoding="utf-8")

    for name in layer_one:
        start = source.index(f"def {name}(")
        body = source[start : source.index("\ndef ", start + 1)]
        for token in ("refuse", "is_refusal", "is_block", "block(", "Result("):
            assert token not in body, f"{name} can reach a disposition via {token!r}"


def test_that_token_list_would_actually_catch_a_violation():
    """The guard above is a string search, so it is worth exactly what its
    tokens catch. Prove each construction is caught, and that the shapes Layer 1
    legitimately uses are not."""
    tokens = ("refuse", "is_refusal", "is_block", "block(", "Result(")
    for violation in (
        "return refuse('no')",
        "return Result('no', None, True)",
        "return Result('no', is_refusal=True)",
        "return block('no')",
        "return Result('no', is_block=True)",
    ):
        assert any(t in violation for t in tokens), f"a handler could ship {violation!r} unnoticed"

    for allowed in ("def evaluate(ctx: HookContext) -> Result | None:", "return warn(advisory)"):
        assert not any(t in allowed for t in tokens), f"the guard false-positives on {allowed!r}"


def test_every_rbg_handler_refuses_nothing_and_blocks_only_on_a_stop(staged):
    """Behavioural counterpart to the source guard: fire every registered
    handler on its own event and check the disposition that comes out."""
    events = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib.util,json,sys;"
                "sys.path.insert(0, sys.argv[1]);"
                "s=importlib.util.spec_from_file_location('h', sys.argv[1]+'/handlers.py');"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                "print(json.dumps(sorted(m.HANDLERS)))",
                str(staged),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        ).stdout
    )
    assert events, "no handlers registered; this test checked nothing"

    for event in events:
        client = "agy" if event == "UserPromptSubmit" else "claude"
        out = parsed(fire(staged, client, event, {"tool_name": "Bash"}))
        if out is None:
            continue
        assert "permissionDecision" not in json.dumps(out), f"{event} produced a refusal"
        if out.get("decision") == "block":
            assert event in STOP_EVENTS, f"{event} produced a block"


# ---------------------------------------------------------------------------
# Registration has two halves, and a hook needs both
# ---------------------------------------------------------------------------


def test_the_manifest_and_the_registry_declare_the_same_claude_events(staged):
    """A manifest event with no handler is a process spawned to do nothing; a
    handler with no manifest event never runs at all. Both read as 'wired' from
    one side, so the check has to be made from both."""
    manifest = json.loads(RBG_MANIFEST.read_text(encoding="utf-8"))
    declared = set(manifest["clients"]["claude"]["hooks"])

    registered = set(
        json.loads(
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import importlib.util,json,sys;"
                    "sys.path.insert(0, sys.argv[1]);"
                    "s=importlib.util.spec_from_file_location('h', sys.argv[1]+'/handlers.py');"
                    "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                    "print(json.dumps(sorted(m.HANDLERS)))",
                    str(staged),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            ).stdout
        )
    )

    # UserPromptSubmit is registered but deliberately unwired on claude: the
    # handler is scoped `only_on("agy")`, claude is already covered at
    # PreToolUse, and pkb owns claude's UserPromptSubmit injection.
    assert declared == registered - {"UserPromptSubmit"}
    assert declared >= set(STOP_EVENTS)


def test_the_manifest_name_matches_the_marketplace_name():
    """`build/marketplace.toml` is the single source of truth for a plugin's
    name, and `_render_manifests` lets a template's own `name` win over it — so
    a stale template name ships in `plugin.json` while the directory, the
    marketplace entry, and every `plugin:agent` invocation string use the real
    one."""
    manifest_dir = REPO_ROOT / "plugins" / "rbg" / "manifest"
    for template in sorted(manifest_dir.glob("*.template.json")):
        data = json.loads(template.read_text(encoding="utf-8"))
        assert data.get("name") == "rbg", f"{template.name} declares {data.get('name')!r}"
        base = data.get("clients", {}).get("__base__", {})
        if "name" in base:
            assert base["name"] == "rbg", f"{template.name} __base__ declares {base['name']!r}"
