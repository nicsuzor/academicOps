#!/usr/bin/env python3
"""Red tests: hook router must not silently fail inside polecat containers.

The sandbox hook router (router.sh → router.py) silently fails inside polecat
containers because it tries to write host paths (Path.home() → /home/nic).
Session state doesn't persist, hook telemetry isn't logged, and the handover gate
silently defaults to warn-only — all while exiting 0.

These tests spin up an aops-crew Docker container, invoke the hook router with
a synthetic SessionStart event, and verify:

  1. session_env_setup did not emit CRITICAL on stderr
  2. stderr contains no Permission denied or No such file or directory for host paths
  3. Hook session-state + event-log writes either succeed or the hook exits non-zero

Run: pytest tests/polecat/test_sandbox_hook_integrity.py -m 'slow and integration' -v
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from cli import _build_docker_cmd, _run_docker_container  # noqa: E402

from tests.conftest import _docker_available  # noqa: E402

# Synthetic SessionStart event fed to the router via stdin.
_SYNTHETIC_SESSION_START = json.dumps(
    {
        "hook_event_name": "SessionStart",
        "session_id": "test-sandbox-hook-integrity",
    }
)

# Script that invokes the hook router inside the container and captures stderr
# separately so we can inspect it. Prefers /workspace/aops-core (local source,
# mounted from the repo root) so changes are reflected immediately without
# rebuilding the image. Falls back to the installed plugin if not present.
_HOOK_INVOKE_SCRIPT = r"""
set -e

# Prefer the top-level workspace plugin so changes are reflected without
# image rebuilds. Stale Claude worktrees under .claude/worktrees/ may carry
# pre-SSoT plugin code and would mask the current source's behavior, so
# probe the canonical path first and only fall back to a search if absent.
if [ -f /workspace/aops-core/hooks/router.py ]; then
    PLUGIN_DIR=/workspace/aops-core/hooks/router.py
else
    PLUGIN_DIR=$(find /workspace -path '*/aops-core/hooks/router.py' \
        -not -path '*/.claude/worktrees/*' -maxdepth 6 -print -quit 2>/dev/null || true)
fi
if [ -z "$PLUGIN_DIR" ]; then
    PLUGIN_DIR=$(find /home -path '*/aops-core/hooks/router.py' -print -quit 2>/dev/null || true)
fi
if [ -z "$PLUGIN_DIR" ]; then
    PLUGIN_DIR=$(find /root -path '*/aops-core/hooks/router.py' -print -quit 2>/dev/null || true)
fi
if [ -z "$PLUGIN_DIR" ]; then
    PLUGIN_DIR=$(find / -path '*/aops-core/hooks/router.py' -maxdepth 8 -print -quit 2>/dev/null || true)
fi

if [ -z "$PLUGIN_DIR" ]; then
    echo "ROUTER_FOUND=false"
    echo "STDERR_OUTPUT="
    echo "EXIT_CODE=127"
    exit 0
fi

ROUTER_PY="$PLUGIN_DIR"
HOOK_DIR=$(dirname "$PLUGIN_DIR")
AOPS_CORE_DIR=$(dirname "$HOOK_DIR")

# Simulate the real polecat scenario: HOME points to the host user's home dir
# which doesn't exist inside the container. This is exactly what causes the
# silent failures in production polecat dispatches — the container inherits the
# host UID but /home/<host-user> doesn't exist or isn't writable.
export HOME="/home/simulated-host-user"

# Ensure uv can still run (its cache needs a writable location)
export UV_CACHE_DIR="/tmp/uv-cache-test"

# Run the router with synthetic SessionStart, capturing stderr
STDERR_FILE=$(mktemp)
set +e
echo '%%%SYNTHETIC_INPUT%%%' | \
    uv --directory "$AOPS_CORE_DIR" run python "$ROUTER_PY" --client claude SessionStart \
    > /dev/null 2>"$STDERR_FILE"
ROUTER_EXIT=$?
set -e

echo "ROUTER_FOUND=true"
echo "EXIT_CODE=$ROUTER_EXIT"
echo "---STDERR_START---"
cat "$STDERR_FILE"
echo "---STDERR_END---"
rm -f "$STDERR_FILE"
""".replace("%%%SYNTHETIC_INPUT%%%", _SYNTHETIC_SESSION_START.replace("'", "'\\''"))


def _parse_hook_output(stdout: str) -> dict:
    """Parse the structured output from the container script."""
    result = {"router_found": False, "exit_code": -1, "stderr": ""}
    for line in stdout.splitlines():
        if line.startswith("ROUTER_FOUND="):
            result["router_found"] = line.split("=", 1)[1].strip() == "true"
        elif line.startswith("EXIT_CODE="):
            try:
                result["exit_code"] = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass

    # Extract stderr block
    if "---STDERR_START---" in stdout and "---STDERR_END---" in stdout:
        start = stdout.index("---STDERR_START---") + len("---STDERR_START---")
        end = stdout.index("---STDERR_END---")
        result["stderr"] = stdout[start:end].strip()

    return result


@pytest.mark.slow
@pytest.mark.integration
class TestSandboxHookIntegrity:
    """Verify the hook router does not silently fail inside polecat containers.

    These are red tests: they are expected to FAIL on main until the hook
    router is fixed to handle sandbox paths correctly. The purpose is to
    prove the test suite catches the bug before we trust a fix.
    """

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    @pytest.fixture(scope="class")
    def hook_results(self) -> dict:
        """Run the hook router inside an aops-crew container and capture output.

        Uses REPO_ROOT as work_dir so:
        1. Colima's virtiofs can bind-mount it (repo is under ~/, inside Colima's
           shared path — unlike tmp_path_factory dirs in /var/folders).
        2. Local aops-core source is available at /workspace/aops-core so the
           hook script uses it instead of the installed image plugin — changes
           are reflected immediately without image rebuilds.
        """
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        env = {
            "POLECAT_SESSION_TYPE": "polecat",
        }

        tmp_files: list[Path] = []
        docker_cmd = _build_docker_cmd(
            cli_tool="claude",
            work_dir=REPO_ROOT,
            env=env,
            agent_cmd=["bash", "-c", _HOOK_INVOKE_SCRIPT],
            is_interactive=False,
            tmp_files=tmp_files,
        )

        try:
            result = _run_docker_container(
                docker_cmd,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"Container itself exited {result.returncode}:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            parsed = _parse_hook_output(result.stdout)
            if not parsed["router_found"]:
                pytest.skip("router.py not found inside container — plugin may not be installed")
            return parsed
        finally:
            for f in tmp_files:
                if f.is_dir():
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    f.unlink(missing_ok=True)

    def test_no_critical_errors_on_stderr(self, hook_results):
        """session_env_setup must not emit CRITICAL on stderr.

        Invariant 1: A CRITICAL log line means session state failed to persist,
        which silently breaks all downstream gate enforcement.
        """
        stderr = hook_results["stderr"]
        critical_lines = [line for line in stderr.splitlines() if "CRITICAL" in line]
        assert not critical_lines, (
            "Hook router emitted CRITICAL errors inside sandbox:\n" + "\n".join(critical_lines)
        )

    def test_no_host_path_permission_errors(self, hook_results):
        """stderr must not contain Permission denied or No such file for host paths.

        Invariant 3: The hook tries to write to host paths (e.g., /home/nic/.aops/...)
        which don't exist or are inaccessible inside the container. These errors
        prove the hook is operating on wrong paths.
        """
        stderr = hook_results["stderr"]
        host_path_errors = [
            line
            for line in stderr.splitlines()
            if (
                ("Permission denied" in line or "No such file or directory" in line)
                and ("/home/" in line or "/.aops/" in line or "/.claude/" in line)
            )
        ]
        assert not host_path_errors, (
            "Hook router tried to access host paths inside sandbox:\n" + "\n".join(host_path_errors)
        )

    def test_hook_exits_zero_only_if_clean(self, hook_results):
        """Hook must not exit 0 if it emitted CRITICAL or WARNING errors.

        Invariant 4: If the hook's session-state or event-log writes fail, it
        must either succeed cleanly (no errors) or exit non-zero. Silent failure
        (exit 0 + CRITICAL stderr) means the agent has no signal that enforcement
        is broken.
        """
        stderr = hook_results["stderr"]
        exit_code = hook_results["exit_code"]

        failure_indicators = [
            line
            for line in stderr.splitlines()
            if any(
                marker in line
                for marker in [
                    "CRITICAL:",
                    "Permission denied",
                    "No such file or directory",
                    "Failed to save session state",
                    "Failed to load session state",
                    "Failed to log hook event",
                ]
            )
        ]

        if exit_code == 0 and failure_indicators:
            pytest.fail(
                f"Hook exited 0 despite {len(failure_indicators)} failure(s) on stderr:\n"
                + "\n".join(failure_indicators)
                + "\n\nThe hook must either handle sandbox paths correctly (no errors) "
                + "or exit non-zero when it cannot function."
            )
