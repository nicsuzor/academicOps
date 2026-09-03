"""Behavioral tests for plugins/aops/scripts/run-mcp.sh.

The launcher's own header states its contract: the PKB MCP endpoint has "no
default, no config-file fallback, and no local server to fall back to". Every
case here pins the fail-loud half of that — an absent or unusable
precondition must produce an actionable non-zero exit, never a hang and never
a silent empty success on stdout, which the client would read as a server that
started and said nothing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_MCP = REPO_ROOT / "plugins" / "aops" / "scripts" / "run-mcp.sh"

# Resolved once, up front: a test that strips PATH down to an empty directory
# (to prove run-mcp.sh can't find `uvx`) must still be able to launch `bash`
# itself, which is a separate lookup from anything the script does internally.
BASH_BIN = shutil.which("bash") or "/bin/bash"


def _clean_launcher_env(**overrides: str) -> dict:
    """PATH/HOME only, plus whatever the caller supplies. A test that leaked
    the host's real PKB_MCP_URL (this very host has one exported, pointed at a
    live Tailscale host) would prove nothing about the no-default contract."""
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
