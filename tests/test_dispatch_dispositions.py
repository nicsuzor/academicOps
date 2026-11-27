"""Behavioural tests for how the shared dispatcher treats a blocking disposition.

Every case runs the real `lib/hooks/dispatch.py` as a subprocess with a
synthetic hook payload on stdin, beside a stand-in `handlers.py`. Nothing is
mocked: what is asserted is the JSON that would reach the client and the exit
code that would accompany it. The dispatcher is copied into every plugin's
`hooks/` at build time, so these rules bind every plugin's handlers.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parent.parent
DISPATCH = REPO_ROOT / "lib" / "hooks" / "dispatch.py"


@pytest.fixture
def staged(tmp_path) -> Path:
    """A plugin `hooks/` directory holding only the shared dispatcher."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    shutil.copy2(DISPATCH, hooks / "dispatch.py")
    return hooks


def fire(staged: Path, client: str, event: str, payload: dict | None = None):
    """Run one hook the way the client runs it: argv, JSON on stdin, JSON out."""
    return subprocess.run(
        [sys.executable, str(staged / "dispatch.py"), client, event],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(staged)},
    )


def parsed(proc) -> dict | None:
    assert proc.returncode == 0, f"exit {proc.returncode}; stderr: {proc.stderr}"
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def test_the_continuation_guard_is_in_the_runtime_not_the_handler(staged):
    """A block gives the session another turn, which stops again and re-fires
    the hook with `stop_hook_active` set. Firing again there is the loop that
    never lets a session end, so a handler with no guard of its own must still
    stay silent on the marked stop."""
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
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "", "a handler with no guard of its own still fired"


@pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
def test_a_block_outranks_an_advisory_when_handlers_are_merged(staged, event):
    """`_merge` takes the strongest disposition, so an advisory registered
    alongside a gate cannot displace it — first-registered order must not
    decide which one the client sees.

    This holds within one plugin's process only. Two plugins on the same event
    are two processes and never reach `_merge` at all.
    """
    (staged / "handlers.py").write_text(
        "from dispatch import block, warn\n\n"
        "def advise(ctx):\n"
        "    return warn('just a note')\n\n"
        "def gate(ctx):\n"
        "    return block('the real instruction')\n\n"
        "HANDLERS = {'Stop': [advise, gate], 'SubagentStop': [gate, advise]}\n",
        encoding="utf-8",
    )
    out = parsed(fire(staged, "claude", event, {"session_id": "s1"}))
    assert out == {"decision": "block", "reason": "the real instruction"}, (
        f"{event}: registration order decided the disposition"
    )


def test_a_block_on_a_non_blockable_event_degrades_and_says_so(staged):
    """Claude Code has no `decision` field on `PreToolUse`, so emitting one
    there would be a no-op a handler could mistake for enforcement. It becomes
    an advisory instead, and the misuse is reported."""
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
    assert "is illegal on event" in proc.stderr
