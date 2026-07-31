"""Behavioral tests for plugins/pkb/hooks/handlers.py.

pkb ships exactly one hook — `search_the_pkb`, registered for
`UserPromptSubmit` — and specs/ARCHITECTURE.md's Hooks table describes it as
firing on both clients to "Inject relevant PKB context, or instruct the agent
to search for it."

Each case runs in a subprocess with lib/hooks and the plugin's hooks/ on
sys.path, mirroring how test_aops_handlers.py exercises
plugins/aops/hooks/handlers.py and test_shipped_hooks.py loads shipped
handler modules. The dispatch-level cases build a synthetic hooks/ dir the
same way test_hooks.py's `injected_plugin` fixture does: lib/hooks/ copied in
byte-identical (build stage 1), the plugin's own handlers.py and messages/
laid on top.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_HOOKS = REPO_ROOT / "lib" / "hooks"
PKB_HOOKS = REPO_ROOT / "plugins" / "pkb" / "hooks"
RUN_MCP = REPO_ROOT / "plugins" / "pkb" / "scripts" / "run-mcp.sh"

# Resolved once, up front: a test that strips PATH down to an empty directory
# (to prove run-mcp.sh can't find `uvx`) must still be able to launch `bash`
# itself, which is a separate lookup from anything the script does internally.
BASH_BIN = shutil.which("bash") or "/bin/bash"

PKB_CONTEXT_TEXT = (PKB_HOOKS / "messages" / "pkb-context.md").read_text().strip()
# The second reader's copy: one line for the person watching the session,
# shipped beside the agent's text (lib/hooks/messages.py).
PKB_CONTEXT_USER_TEXT = (PKB_HOOKS / "messages" / "pkb-context.user.md").read_text().strip()

_RUN_HANDLER = """
import importlib.util, json, sys
lib_hooks, pkb_hooks, handler_name, raw_json = sys.argv[1:5]
sys.path.insert(0, pkb_hooks)
sys.path.insert(0, lib_hooks)
spec = importlib.util.spec_from_file_location("handlers", pkb_hooks + "/handlers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from context import normalize
raw = json.loads(raw_json)
event = raw.get("hook_event_name", "UserPromptSubmit")
ctx = normalize("claude", event, raw, __import__("pathlib").Path(pkb_hooks))
res = getattr(module, handler_name)(ctx)
print(json.dumps(
    None if res is None else {
        "inject_text": res.inject_text,
        "user_text": res.user_text,
        "kind": res.kind.value,
    }
))
"""

_READ_HANDLERS = """
import importlib.util, json, sys
lib_hooks, pkb_hooks = sys.argv[1:3]
sys.path.insert(0, pkb_hooks)
sys.path.insert(0, lib_hooks)
spec = importlib.util.spec_from_file_location("handlers", pkb_hooks + "/handlers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
wired = {event: sorted(h.__name__ for h in hs) for event, hs in module.HANDLERS.items()}
wired["names"] = sorted(n for n in dir(module) if not n.startswith("__"))
scopes = {}
for hs in module.HANDLERS.values():
    for h in hs:
        scope = getattr(h, "only_on_clients", None)
        scopes[h.__name__] = sorted(scope) if scope is not None else None
wired["only_on_clients"] = scopes
print(json.dumps(wired))
"""


def _handlers_module() -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _READ_HANDLERS, str(LIB_HOOKS), str(PKB_HOOKS)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _run(handler: str, raw: dict):
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _RUN_HANDLER,
            str(LIB_HOOKS),
            str(PKB_HOOKS),
            handler,
            json.dumps(raw),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# 1. Handler output contract
# ---------------------------------------------------------------------------


def test_search_the_pkb_is_wired_only_to_userpromptsubmit():
    registered = _handlers_module()
    assert registered["UserPromptSubmit"] == ["search_the_pkb"]
    assert set(registered["names"]) >= {"search_the_pkb", "HANDLERS"}


def test_search_the_pkb_has_no_client_scope_so_it_fires_on_both():
    """specs/ARCHITECTURE.md's Hooks table lists this hook as `both` clients.
    `dispatch.py`'s `_for_client` only narrows a handler that declares
    `only_on_clients` — the absence of that attribute is what makes `both`
    true, so this pins the absence rather than assuming it."""
    registered = _handlers_module()
    assert registered["only_on_clients"]["search_the_pkb"] is None


def test_search_the_pkb_returns_an_advisory_never_a_refusal():
    """The hook-runtime Result contract: the kind must stay advisory, because
    nothing in-session may block on this hook (specs/ARCHITECTURE.md,
    Enforcement) — a refusal is reserved for structural impossibility
    (lib/hooks/dispatch.py), and searching the PKB is never that."""
    res = _run("search_the_pkb", {"hook_event_name": "UserPromptSubmit", "prompt": "anything"})
    assert res is not None
    assert res["kind"] == "advise"
    assert res["inject_text"]


def test_search_the_pkb_carries_the_user_line_as_well_as_the_agent_text():
    """Both readers, every time. The handler loads the message as a pair
    (`messages.load_pair`), so the person watching gets the one-line version
    from `messages/pkb-context.user.md` alongside the agent's full text. This
    hook fires on every prompt: a silent one would make the framework's most
    frequent injection its least visible."""
    assert PKB_CONTEXT_USER_TEXT, "pkb-context.user.md ships empty, which reads as absent"
    res = _run("search_the_pkb", {"hook_event_name": "UserPromptSubmit"})
    assert res["user_text"] == PKB_CONTEXT_USER_TEXT
    # Not the agent's text over again: the two readers need different lengths,
    # which is the whole reason the pair exists.
    assert res["user_text"] != res["inject_text"]


# ---------------------------------------------------------------------------
# Dispatch-level fixture: the real runtime, both clients
# ---------------------------------------------------------------------------


def _pkb_plugin(tmp_path):
    """A synthetic pkb hooks/ dir: lib/hooks/ copied in as build stage 1 does
    (the runtime modules AND the messages the runtime itself loads), plus the
    real plugin's handlers.py and messages/ laid on top."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    for py_file in LIB_HOOKS.glob("*.py"):
        shutil.copy2(py_file, hooks_dir / py_file.name)
    if (LIB_HOOKS / "messages").is_dir():
        shutil.copytree(LIB_HOOKS / "messages", hooks_dir / "messages", dirs_exist_ok=True)
    shutil.copy2(PKB_HOOKS / "handlers.py", hooks_dir / "handlers.py")
    shutil.copytree(PKB_HOOKS / "messages", hooks_dir / "messages", dirs_exist_ok=True)
    return hooks_dir


def _dispatch(hooks_dir: Path, client: str, event: str, raw: dict, env: dict | None = None):
    return subprocess.run(
        [sys.executable, str(hooks_dir / "dispatch.py"), client, event],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
        env=env,
    )


def test_dispatch_claude_userpromptsubmit_uses_additional_context_never_a_permission_decision(
    tmp_path,
):
    hooks_dir = _pkb_plugin(tmp_path)
    result = _dispatch(
        hooks_dir,
        "claude",
        "UserPromptSubmit",
        {"hook_event_name": "UserPromptSubmit", "session_id": "s1"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "permissionDecision" not in out.get("hookSpecificOutput", {})
    assert "decision" not in out
    assert out["hookSpecificOutput"]["additionalContext"]


def test_dispatch_claude_puts_the_user_line_on_system_message(tmp_path):
    """The handler holding a user line proves nothing on its own — the line has
    to survive rendering. Claude Code is the client with a channel for each
    reader (lib/hooks/clients.py, `_render_claude`), and `systemMessage` is
    where the person's copy lands."""
    hooks_dir = _pkb_plugin(tmp_path)
    result = _dispatch(
        hooks_dir,
        "claude",
        "UserPromptSubmit",
        {"hook_event_name": "UserPromptSubmit", "session_id": "s-user-line"},
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["systemMessage"] == PKB_CONTEXT_USER_TEXT
    assert out["hookSpecificOutput"]["additionalContext"] == PKB_CONTEXT_TEXT


def test_dispatch_agy_preinvocation_alias_also_fires(tmp_path):
    """agy's `PreInvocation` is `UserPromptSubmit`'s canonical alias
    (lib/hooks/clients.py) — the architecture table marks this hook `both`, so
    the agy wire event must reach the same handler."""
    hooks_dir = _pkb_plugin(tmp_path)
    result = _dispatch(hooks_dir, "agy", "PreInvocation", {})
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out == {"injectSteps": [{"ephemeralMessage": PKB_CONTEXT_TEXT}]}


# ---------------------------------------------------------------------------
# 2. Message content: the agent-visible wording comes from hooks/messages/
# ---------------------------------------------------------------------------


def test_injected_text_is_exactly_the_shipped_message_file():
    res = _run("search_the_pkb", {"hook_event_name": "UserPromptSubmit"})
    assert res["inject_text"] == PKB_CONTEXT_TEXT


def test_editing_the_message_file_changes_the_output(tmp_path):
    """Proves the wording is loaded from markdown, not a Python literal — the
    contract lib/hooks/messages.py promises every hook message. If this test
    fails, `search_the_pkb` stopped calling `ctx.message(...)`."""
    hooks_dir = _pkb_plugin(tmp_path)
    (hooks_dir / "messages" / "pkb-context.md").write_text("Changed wording for this test.\n")
    result = _dispatch(
        hooks_dir, "claude", "UserPromptSubmit", {"hook_event_name": "UserPromptSubmit"}
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["additionalContext"] == "Changed wording for this test."


def test_handler_raises_when_its_message_file_is_missing_and_the_runtime_reports_it(tmp_path):
    """`search_the_pkb` does not catch `MessageNotFoundError` itself —
    `ctx.message` propagates it. Per specs/ARCHITECTURE.md's Hooks section, "a
    hook that cannot load its message file fails loudly": `dispatch.py`'s
    per-handler isolation (lib/hooks/dispatch.py `_run_handler`) is what turns
    that raise into a fail-loud report on the wire — never a silent empty
    injection, and never a crashed process."""
    hooks_dir = _pkb_plugin(tmp_path)
    (hooks_dir / "messages" / "pkb-context.md").unlink()
    # tempfile.gettempdir() only accepts a TMPDIR candidate that already
    # exists and is writable; an uncreated path is silently skipped in favour
    # of the real system temp dir, which would let this test's once-per-session
    # marker collide with another run's (lib/hooks/degraded.py, `_claim`) —
    # mirrors tests/test_hooks.py's `notice_env` fixture.
    marker_root = tmp_path / "os-tmp"
    marker_root.mkdir()
    env = {**os.environ, "TMPDIR": str(marker_root)}
    result = _dispatch(
        hooks_dir,
        "claude",
        "UserPromptSubmit",
        {"hook_event_name": "UserPromptSubmit", "session_id": "s-missing-message"},
        env=env,
    )
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "search_the_pkb" in out["systemMessage"]
    assert "did not run" in out["systemMessage"]
    assert "MessageNotFoundError" in out["hookSpecificOutput"]["additionalContext"]
    # stderr is the log, and the log is never rate-limited or dropped.
    assert "search_the_pkb" in result.stderr
    assert "MessageNotFoundError" in result.stderr


# ---------------------------------------------------------------------------
# 3. Both branches — FINDING: only one exists
# ---------------------------------------------------------------------------
#
# specs/ARCHITECTURE.md's Hooks table describes this hook's effect as "Inject
# relevant PKB context, or instruct the agent to search for it" — a live
# choice between two outcomes. The shipped handler's own docstring
# (plugins/pkb/hooks/handlers.py) says otherwise: it "always takes the
# 'instruct the agent to search' branch of the contract", on purpose, because
# reaching the PKB itself would put a slow or unreachable network call on the
# critical path of every prompt. So there is no code path here that ever
# injects PKB content, and no code path that distinguishes "PKB has nothing
# relevant" (legitimate absence) from "PKB is configured but unreachable"
# (degradation) — enforcement.md's harness delivery channel draws that line
# for cope's evaluator, but pkb's hook never attempts contact, so there is
# nothing for it to detect failing. The message text instead asks the AGENT
# to make that call itself ("If the PKB tools are unavailable in this
# session, say that too"), which is consistent with this repo's
# judgment-non-delegable rule but means the distinction is prose read by the
# agent, not a mechanism this hook implements or could fail to run. This is a
# genuine gap against the architecture doc's literal wording, not a bug in
# the handler; it is recorded here so the doc and the code stop disagreeing
# silently.


def test_search_the_pkb_output_is_identical_regardless_of_prompt_or_session():
    """Pins the actual, current behaviour: nothing in the payload — the
    prompt's content, the session id, an empty prompt — changes what this
    handler returns. There is exactly one branch."""
    baseline = _run("search_the_pkb", {"hook_event_name": "UserPromptSubmit", "session_id": "a"})
    variants = [
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "b",
            "prompt": "what did I decide about the release date?",
        },
        {"hook_event_name": "UserPromptSubmit", "session_id": "c", "prompt": ""},
        {"hook_event_name": "UserPromptSubmit"},
    ]
    for raw in variants:
        assert _run("search_the_pkb", raw) == baseline


def test_search_the_pkb_never_reaches_the_network():
    """The handler's own module docstring states it "never reach[es] the PKB
    itself" and "never waits on the network". There is no PKB server running
    in this test environment, so a handler that tried to would hang or raise
    instead of returning promptly — this asserts on the timing floor, not
    just the words in the docstring."""
    import time

    started = time.monotonic()
    res = _run("search_the_pkb", {"hook_event_name": "UserPromptSubmit"})
    elapsed = time.monotonic() - started
    assert res is not None
    assert elapsed < 5, "search_the_pkb took long enough to suggest a network round trip"


# ---------------------------------------------------------------------------
# 4. run-mcp.sh: fail-loud when its required configuration is absent
# ---------------------------------------------------------------------------


def _clean_launcher_env(**overrides: str) -> dict:
    """PATH/HOME only, plus whatever the caller supplies. run-mcp.sh's own
    header states its contract: "no default, no config-file fallback, and no
    local server to fall back to" — a test that leaks the host's real
    PKB_MCP_URL (this very host has one exported, pointed at a live
    Tailscale host) would prove nothing about that contract."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
    env.update(overrides)
    return env


def test_run_mcp_fails_loudly_without_pkb_mcp_url():
    result = subprocess.run(
        [BASH_BIN, str(RUN_MCP)],
        capture_output=True,
        text=True,
        timeout=30,
        env=_clean_launcher_env(),
    )
    assert result.returncode != 0
    assert result.stdout == "", "must never start a server on an unset URL"
    assert "PKB_MCP_URL" in result.stderr
    assert "not set" in result.stderr


def test_run_mcp_fails_loudly_with_an_empty_pkb_mcp_url():
    """`${PKB_MCP_URL:-}` under `-z` treats an empty string the same as unset
    — pinned explicitly, since "the client supplied an empty value" and "the
    client supplied nothing" are different failure modes for whoever is
    debugging this."""
    result = subprocess.run(
        [BASH_BIN, str(RUN_MCP)],
        capture_output=True,
        text=True,
        timeout=30,
        env=_clean_launcher_env(PKB_MCP_URL=""),
    )
    assert result.returncode != 0
    assert "PKB_MCP_URL" in result.stderr


def test_run_mcp_fails_loudly_when_uvx_is_unreachable(tmp_path):
    """PKB_MCP_URL present, but no `uvx` anywhere on PATH or in the script's
    fallback directories: still an actionable non-zero exit, not a
    hang and not a silent empty success.

    PATH is pared down to a directory holding only `mkdir` — enough for the
    script's own housekeeping — rather than a real system dir like `/usr/bin`,
    which could itself contain `uvx` on some machines and make this pass or
    fail by accident. USER and UV_CACHE_DIR are supplied directly so the
    script never needs to shell out to `id`, which this minimal PATH doesn't
    carry either."""
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    minimal_bin = tmp_path / "minimal-bin"
    minimal_bin.mkdir()
    (minimal_bin / "mkdir").symlink_to(shutil.which("mkdir"))
    result = subprocess.run(
        [BASH_BIN, str(RUN_MCP)],
        capture_output=True,
        text=True,
        timeout=30,
        env=_clean_launcher_env(
            PKB_MCP_URL="http://example.invalid/mcp",
            PATH=str(minimal_bin),
            AOPS_UVX_SEARCH_PATH=str(empty_bin),
            HOME=str(tmp_path),
            USER="testuser",
            UV_CACHE_DIR=str(tmp_path / "uv-cache"),
        ),
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "uvx" in result.stderr
