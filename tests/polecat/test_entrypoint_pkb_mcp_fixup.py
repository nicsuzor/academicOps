"""Tests for entrypoint.sh's container-runtime call to
docker_gemini_fixups.py's fixup-mcp-config-paths, added because the agy
client's pkb `services` server ships with the literal placeholder
YOUR_PKB_URL baked into the image at `docker build` time -- before
$PKB_MCP_URL is known -- and nothing else in the container's lifecycle ever
resolves it (aops_agy_services_mcp_fix, aops_bifrost_proof_agy).

Verifies:
1. When docker_gemini_fixups.py exists at $HOME, entrypoint.sh invokes it
   with `fixup-mcp-config-paths`, with $PKB_MCP_URL visible in its
   environment, before exec'ing the agent.
2. Without the script present (a non-crew AGENT_CMD image, or any test that
   does not stage one), entrypoint.sh is unaffected -- no error, agent still
   runs.
"""

import os
import stat
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENTRYPOINT_SH = _REPO_ROOT / "lib" / "polecat" / "entrypoint.sh"


def _base_env(tmp_path, extra=None):
    env = {
        "GIT_AUTHOR_NAME": "Test Agent",
        "GIT_AUTHOR_EMAIL": "agent@test.com",
        "AOPS_BOT_GH_TOKEN": "token-123",
        "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
        "HOME": str(tmp_path),
        "PATH": os.environ.get("PATH", "/bin:/usr/bin"),
    }
    if extra:
        env.update(extra)
    return env


def _write_mock_agent(tmp_path, name):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    agent_bin = bin_dir / name
    agent_bin.write_text('#!/bin/sh\necho "$0" "$@"\n')
    agent_bin.chmod(agent_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def test_entrypoint_calls_the_fixup_script_with_pkb_mcp_url_in_env(tmp_path):
    """entrypoint.sh runs docker_gemini_fixups.py fixup-mcp-config-paths with
    $PKB_MCP_URL already in its own environment, so the script can resolve
    the agy client's YOUR_PKB_URL placeholder."""
    bin_dir = _write_mock_agent(tmp_path, "agy")
    marker = tmp_path / "fixup-invocation.txt"
    (tmp_path / "docker_gemini_fixups.py").write_text(
        "import os, sys, pathlib\n"
        f"pathlib.Path({str(marker)!r}).write_text(\n"
        "    ' '.join(sys.argv[1:]) + '|' + os.environ.get('PKB_MCP_URL', '<unset>')\n"
        ")\n"
    )

    env = _base_env(
        tmp_path,
        {
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '/bin:/usr/bin')}",
            "PKB_MCP_URL": "https://pkb.example.ts.net/mcp",
        },
    )
    proc = subprocess.run(
        ["bash", str(_ENTRYPOINT_SH), "agy", "--print", "hi"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "entrypoint.sh never invoked docker_gemini_fixups.py"
    assert marker.read_text() == "fixup-mcp-config-paths|https://pkb.example.ts.net/mcp"
    # The agent still runs after the fixup call.
    assert "--print hi" in proc.stdout


def test_entrypoint_is_a_no_op_without_the_fixup_script(tmp_path):
    """A container image with no docker_gemini_fixups.py at $HOME (e.g. a
    non-crew AGENT_CMD, or any bare test fixture) is unaffected -- no error,
    the agent still runs.

    Uses a passthrough AGENT_CMD name that is neither `bash` nor `sh`: naming
    the mock binary `bash` would shadow the outer interpreter subprocess.run
    itself needs to execute entrypoint.sh, since a list-form subprocess.run
    call with an explicit `env=` resolves argv[0] against that env's own
    PATH, not the real one.
    """
    bin_dir = _write_mock_agent(tmp_path, "passthrough-agent")
    env = _base_env(tmp_path, {"PATH": f"{bin_dir}:{os.environ.get('PATH', '/bin:/usr/bin')}"})

    proc = subprocess.run(
        ["bash", str(_ENTRYPOINT_SH), "passthrough-agent", "-c", "echo hello"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "-c echo hello" in proc.stdout
