"""Tests for the zombie-agent reaper (aops-1adfd28d).

`scripts/ci/reap-agent-processes.sh` is the cleanup mechanism for the enforcer's
rate-limit cancellation path: when the first agent attempt is "cancelled" the
underlying process can survive on the runner, race the retry, and double-post
reviews. The reaper kills any surviving agent process GROUP before the retry
launches.

These tests simulate a cancelled attempt with a real detached process whose
command line carries a unique marker, then assert:
  - the reaper kills the simulated zombie's whole process group (no process
    survives) — the proof-standard "simulated-cancellation" test;
  - the reaper does NOT kill a non-matching bystander process;
  - the reaper never kills itself / its caller (it runs to exit 0 even though
    its own argv contains the pattern).

Liveness is read through the Popen handle (whose .poll() reaps the child), not
os.kill(pid, 0): a SIGKILL'd-but-unwaited child lingers as a <defunct> zombie
that os.kill(pid, 0) still reports as alive.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "reap-agent-processes.sh"

# Per-test unique markers so concurrent / sequential tests never match each
# other's processes.
MARKER_KILL = "aops-reap-zombie-1adfd28d-kill"
MARKER_BYSTANDER = "aops-reap-1adfd28d-bystander"


def _spawn_zombie(tag: str) -> subprocess.Popen:
    """Spawn a detached process (its own session/process group, like the
    survived agent) whose command line contains `tag`."""
    # `exec -a <tag>` sets argv[0] so `pgrep -f <tag>` matches.
    proc = subprocess.Popen(
        ["bash", "-c", f"exec -a {tag} sleep 120"],
        start_new_session=True,  # os.setsid → distinct process group
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.3)  # let exec settle so pgrep can see the renamed argv
    return proc


def _terminated(proc: subprocess.Popen, timeout: float = 5.0) -> bool:
    """True if the process has exited within `timeout` (reaps it via poll)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.1)
    return proc.poll() is not None


def _cleanup(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _reap(pattern: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), pattern],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "REAP_GRACE_SECS": "1"},
    )


def test_reaper_kills_simulated_zombie_process_group():
    """Proof-standard (a): after the reap, no process from the cancelled
    attempt survives."""
    zombie = _spawn_zombie(MARKER_KILL)
    try:
        assert zombie.poll() is None, "zombie should be alive before reap"

        result = _reap(MARKER_KILL)
        assert result.returncode == 0, result.stderr

        assert _terminated(zombie), (
            f"zombie {zombie.pid} survived reap.\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "reaped_pgids=" in result.stdout
    finally:
        _cleanup(zombie)


def test_reaper_spares_non_matching_process():
    """The reaper must only target the pattern, not unrelated processes."""
    bystander = _spawn_zombie(MARKER_BYSTANDER)
    try:
        # Reap a pattern that matches NOTHING currently alive.
        result = _reap("aops-reap-1adfd28d-nomatch")
        assert result.returncode == 0, result.stderr
        time.sleep(1.5)
        assert bystander.poll() is None, "reaper killed a non-matching bystander"
        assert "no surviving processes match" in result.stdout
    finally:
        _cleanup(bystander)


def test_reaper_does_not_kill_itself():
    """The reaper's own argv contains the pattern; it must exclude its own
    process group and exit cleanly rather than self-terminate."""
    result = _reap("aops-reap-1adfd28d-selftest-nomatch")
    assert result.returncode == 0, result.stderr
    assert "no surviving processes match" in result.stdout
