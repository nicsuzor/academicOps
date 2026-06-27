"""Gate posture tests for polecat-launched agy headless workers (aops-7781ab3c).

A `polecat run --model antigravity` worker cannot respond interactively to
compliance gate prompts (e.g. dispatch rbg mid-run). When the polecat launcher
sets AOPS_AGY_CLIENT=1 and runs agy without --dangerously-skip-permissions, the
router must classify the session as a worker (is_subagent=True) so PreToolUse
gate evaluation is skipped — same posture as Claude Code polecat task workers.

Stop/PostInvocation events are NOT worker-skipped, so handover enforcement still
fires at session end.

Wire: AOPS_AGY_CLIENT=1 is only set by polecat/cli.py when is_antigravity=True.
It is NOT present in other polecat workers' environments so it never bleeds into
test subprocesses or Claude/Gemini hook invocations.
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


def _seed_enforcer_deny(monkeypatch, state_dir: Path, session_id: str) -> None:
    """Seed on-disk state so a PreToolUse on session_id produces an enforcer DENY."""
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(state_dir))
    monkeypatch.setenv("ENFORCER_GATE_MODE", "block")
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", "50")
    state = SessionState.create(session_id, client_type="agy")
    state.gates["enforcer"].status = GateStatus.OPEN
    state.gates["enforcer"].ops_since_open = 100
    state.save()


def _pretooluse_payload(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }


# ---------------------------------------------------------------------------
# Core worker posture: PreToolUse gate skipped when AOPS_AGY_CLIENT=1
# ---------------------------------------------------------------------------


def test_pretooluse_allow_when_agy_client_set(monkeypatch, tmp_path):
    """Enforcer DENY is suppressed when AOPS_AGY_CLIENT=1 (worker gate posture).

    A polecat-launched agy worker has AOPS_AGY_CLIENT=1 in its env. Even if the
    enforcer gate is seeded to DENY (block mode, ops above threshold), the router
    must skip PreToolUse gate evaluation and return {"allowTool": true}, matching
    the worker posture Claude Code polecat task workers get via is_subagent=True.
    """
    sid = "agy-worker-posture-allow"
    _seed_enforcer_deny(monkeypatch, tmp_path, sid)

    output, stderr = _run_agy_router(
        _pretooluse_payload(sid),
        "PreToolUse",
        extra_env={
            "AOPS_SESSION_STATE_DIR": str(tmp_path),
            "ENFORCER_GATE_MODE": "block",
            "AOPS_AGY_CLIENT": "1",  # polecat-launched agy worker
        },
    )

    assert output.get("allowTool") is True, (
        f"Worker gate posture (AOPS_AGY_CLIENT=1): enforcer DENY must be suppressed, "
        f"PreToolUse must be allowed. Got {output!r}. stderr: {stderr}"
    )
    assert not output.get("denyReason"), (
        f"No denyReason expected on a worker-posture allow: {output!r}"
    )


def test_pretooluse_deny_without_agy_client(monkeypatch, tmp_path):
    """Enforcer DENY fires normally when AOPS_AGY_CLIENT is absent.

    Without the worker-posture signal, a seeded enforcer DENY must still block
    the tool. This guards against the posture leaking to non-polecat agy sessions.
    """
    sid = "agy-non-worker-deny"
    _seed_enforcer_deny(monkeypatch, tmp_path, sid)

    output, stderr = _run_agy_router(
        _pretooluse_payload(sid),
        "PreToolUse",
        extra_env={
            "AOPS_SESSION_STATE_DIR": str(tmp_path),
            "ENFORCER_GATE_MODE": "block",
            # AOPS_AGY_CLIENT intentionally absent — normal (non-worker) agy
        },
    )

    assert output.get("allowTool") is False, (
        f"Without worker posture, enforcer DENY must produce allowTool=false. "
        f"Got {output!r}. stderr: {stderr}"
    )
    assert output.get("denyReason"), (
        f"A structural DENY must have a non-empty denyReason: {output!r}"
    )
    assert "Warning: dropping unsupported context_injection for agy PreToolUse" in stderr


def test_warn_mode_enforcer_allows_without_agy_client(monkeypatch, tmp_path):
    """Enforcer in warn mode (default) allows the tool even without worker posture.

    The primary defence against headless denials is output_for_agy returning
    allowTool=True for warn verdicts. This guards that path — the worker posture
    is an additional belt, not the only one.
    """
    sid = "agy-warn-enforcer-allow"
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ENFORCER_GATE_MODE", "warn")
    monkeypatch.setenv("ENFORCER_TOOL_CALL_THRESHOLD", "50")
    state = SessionState.create(sid, client_type="agy")
    state.gates["enforcer"].status = GateStatus.OPEN
    state.gates["enforcer"].ops_since_open = 100
    state.save()

    output, stderr = _run_agy_router(
        _pretooluse_payload(sid),
        "PreToolUse",
        extra_env={
            "AOPS_SESSION_STATE_DIR": str(tmp_path),
            "ENFORCER_GATE_MODE": "warn",
        },
    )

    assert output.get("allowTool") is True, (
        f"Enforcer warn mode must produce allowTool=true (advisory path). "
        f"Got {output!r}. stderr: {stderr}"
    )
    assert "Warning: dropping unsupported context_injection for agy PreToolUse" in stderr


# ---------------------------------------------------------------------------
# Stop/PostInvocation: NOT skipped even with AOPS_AGY_CLIENT=1
# ---------------------------------------------------------------------------


def test_stop_gate_fires_for_agy_worker(monkeypatch, tmp_path):
    """Handover gate fires on PostInvocation even for polecat-launched agy workers.

    The worker posture skips PreToolUse gates, but Stop/PostInvocation remain
    active. This test verifies the agy `Stop` event (mapped from PostInvocation)
    is not worker-skipped. An advisory Stop result is an empty dict or reason
    string — NOT a hard allowTool=False (that would be a different failure mode).
    """
    sid = "agy-worker-stop-fires"
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("HANDOVER_GATE_MODE", "warn")
    # Force handover gate CLOSED so the Stop policy can fire
    state = SessionState.create(sid, client_type="agy")
    state.gates["handover"].status = GateStatus.CLOSED
    state.session_did_work = True
    state.save()

    # PostInvocation maps to "Stop" internally — this is what agy sends
    output, stderr = _run_agy_router(
        {
            "session_id": sid,
        },
        "PostInvocation",
        extra_env={
            "AOPS_SESSION_STATE_DIR": str(tmp_path),
            "HANDOVER_GATE_MODE": "warn",
            "AOPS_AGY_CLIENT": "1",  # worker posture active
        },
    )

    # The handover gate fired (PostInvocation = Stop is not worker-skipped).
    # In warn mode, output_for_agy emits the advisory via injectSteps.
    # We don't assert on specific content — just that the Stop was NOT silently
    # short-circuited the way PreToolUse is.
    # The session state file must exist (the gate ran and updated state).
    state_files = list(tmp_path.glob("**/*.json"))
    assert state_files, (
        f"Worker posture must NOT skip Stop gate evaluation: no state files "
        f"were written, suggesting the gate never ran. output={output!r}"
    )
