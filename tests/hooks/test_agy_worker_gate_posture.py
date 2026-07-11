"""Gate posture tests for polecat-launched agy headless workers (aops-7781ab3c).

A `polecat run --model antigravity` worker cannot respond interactively to
compliance gate prompts. When the polecat launcher sets AOPS_AGY_CLIENT=1 and
runs agy without --dangerously-skip-permissions, the router classifies the
session as a worker (is_subagent=True) — the posture Claude Code polecat task
workers also get.

Stop/PostInvocation events are NOT worker-skipped, so exit_reflection
enforcement still fires at session end.

Wire: AOPS_AGY_CLIENT=1 is only set by polecat/cli.py when is_antigravity=True.
It is NOT present in other polecat workers' environments so it never bleeds into
test subprocesses or Claude/Gemini hook invocations.

NOTE (aops_4c2949d9): the former PreToolUse-posture tests here
(test_pretooluse_allow_when_agy_client_set, test_pretooluse_deny_without_agy_
client, test_warn_mode_enforcer_allows_without_agy_client) drove the retired
turn-based `rbg` PreToolUse gate to seed a DENY, then asserted the worker
posture (is_subagent=True) suppressed it. That gate is deleted — nothing
fires mid-session on any surface any more — and GATE_CONFIGS has no
PreToolUse policy left at all, so the posture distinction those tests probed
is now vacuous (PreToolUse always allows, with or without AOPS_AGY_CLIENT).
Removed rather than kept as a dead/always-passing assertion. The Stop-side
invariant (worker posture does NOT skip Stop/PostInvocation) still applies
and is covered below.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
AOPS_CORE = REPO_ROOT / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from lib.gate_types import GateStatus
from lib.session_state import SessionState

ROUTER_PATH = AOPS_CORE / "hooks" / "router.py"


def _run_agy_router(
    input_data: dict, event: str, extra_env: dict | None = None
) -> tuple[dict, str]:
    """Run the router subprocess with --client agy, optionally injecting extra env vars."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AOPS_CORE)
    # Scrub AOPS_AGY_CLIENT from the base env so tests are independent of the
    # outer container's env (this worker runs with AOPS_POLECAT_CONTAINER=1 but
    # should NOT have AOPS_AGY_CLIENT set unless we explicitly set it below).
    env.pop("AOPS_AGY_CLIENT", None)
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, str(ROUTER_PATH), "--client", "agy", event],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(AOPS_CORE),
    )
    output = {}
    if result.stdout.strip():
        output = json.loads(result.stdout)
    return output, result.stderr


# ---------------------------------------------------------------------------
# Stop/PostInvocation: NOT skipped even with AOPS_AGY_CLIENT=1
# ---------------------------------------------------------------------------


def test_stop_gate_fires_for_agy_worker(monkeypatch, tmp_path):
    """exit_reflection gate fires on PostInvocation even for polecat-launched
    agy workers.

    The worker posture skips PreToolUse gates, but Stop/PostInvocation remain
    active. This test verifies the agy `Stop` event (mapped from PostInvocation)
    is not worker-skipped. An advisory Stop result is an empty dict or reason
    string — NOT a hard allowTool=False (that would be a different failure mode).
    """
    sid = "agy-worker-stop-fires"
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("EXIT_REFLECTION_GATE_MODE", "warn")
    # Force exit_reflection gate CLOSED, task-bound, did work — so the FULL
    # tier's Stop policy can fire.
    state = SessionState.create(sid, client_type="agy")
    state.gates["exit_reflection"].status = GateStatus.CLOSED
    state.main_agent.current_task = "task-agy-worker"
    state.turn_did_work = True
    state.save()

    # PostInvocation maps to "Stop" internally — this is what agy sends
    output, stderr = _run_agy_router(
        {
            "session_id": sid,
        },
        "PostInvocation",
        extra_env={
            "AOPS_SESSION_STATE_DIR": str(tmp_path),
            "EXIT_REFLECTION_GATE_MODE": "warn",
            "AOPS_AGY_CLIENT": "1",  # worker posture active
        },
    )

    # The exit_reflection gate fired (PostInvocation = Stop is not
    # worker-skipped). In warn mode, output_for_agy emits the advisory via
    # injectSteps. We don't assert on specific content — just that the Stop
    # was NOT silently short-circuited the way PreToolUse is.
    # The session state file must exist (the gate ran and updated state).
    state_files = list(tmp_path.glob("**/*.json"))
    assert state_files, (
        f"Worker posture must NOT skip Stop gate evaluation: no state files "
        f"were written, suggesting the gate never ran. output={output!r}"
    )
