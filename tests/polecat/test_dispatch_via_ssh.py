#!/usr/bin/env python3
"""Unit tests for scripts/polecat-dispatch-via-ssh.sh.

Tests SSH command construction via --dry-run mode (no network required).
Covers: task-ID parsing, session-name derivation, env-var forwarding, host
resolution, and optional-arg pass-through.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
SCRIPT = REPO_ROOT / "scripts" / "polecat-dispatch-via-ssh.sh"


def run_dry(
    *extra_args: str,
    task_id: str | None = None,
    stdin: str | None = None,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the dispatch script in --dry-run mode and return the CompletedProcess."""
    base_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/root"),
        "POLECAT_HOME": "/host/polecat",
        "AOPS_SESSIONS": "/host/sessions",
    }
    if env_overrides:
        base_env.update(env_overrides)

    cmd = [str(SCRIPT), "--dry-run"]
    if task_id:
        cmd += ["-t", task_id]
    cmd += list(extra_args)

    return subprocess.run(
        cmd,
        input=stdin,
        text=True,
        capture_output=True,
        env=base_env,
    )


def parse_dry_output(output: str) -> dict[str, str]:
    """Parse the key: value lines emitted by --dry-run mode."""
    result: dict[str, str] = {}
    for line in output.splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            result[key.strip()] = val.strip()
    return result


class TestSessionName:
    def test_derived_from_task_id(self):
        r = run_dry(task_id="aops-abc123")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert out["session_name"] == "polecat-aops-abc123"

    def test_session_name_on_last_stdout_line(self):
        r = run_dry(task_id="aops-xyz")
        assert r.returncode == 0
        last_line = r.stdout.strip().splitlines()[-1]
        assert last_line == "polecat-aops-xyz"


class TestTaskIdFromStdin:
    def test_reads_id_from_json(self):
        stdin_json = json.dumps({"id": "aops-stdin-test", "title": "Test task"})
        r = run_dry(stdin=stdin_json)
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert out["session_name"] == "polecat-aops-stdin-test"

    def test_error_on_missing_id_field(self):
        r = run_dry(stdin=json.dumps({"title": "no id here"}))
        assert r.returncode != 0
        assert "id" in r.stderr.lower()

    def test_error_on_invalid_json(self):
        r = run_dry(stdin="not json at all")
        assert r.returncode != 0

    def test_flag_takes_precedence_over_stdin(self):
        stdin_json = json.dumps({"id": "aops-from-stdin"})
        r = run_dry("-t", "aops-from-flag", stdin=stdin_json)
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert out["session_name"] == "polecat-aops-from-flag"


class TestHostResolution:
    def test_default_host_is_host_docker_internal(self):
        r = run_dry(task_id="aops-1")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "host.docker.internal" in out["ssh_target"]

    def test_polecat_host_overrides_default(self):
        r = run_dry(task_id="aops-1", env_overrides={"POLECAT_HOST": "192.168.1.100"})
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "192.168.1.100" in out["ssh_target"]

    def test_ssh_user_is_included_in_target(self):
        r = run_dry(task_id="aops-1", env_overrides={"POLECAT_SSH_USER": "nic"})
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert out["ssh_target"].startswith("nic@")

    def test_custom_port_appears_in_options(self):
        r = run_dry(task_id="aops-1", env_overrides={"POLECAT_SSH_PORT": "2222"})
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "-p" in out["ssh_options"]
        assert "2222" in out["ssh_options"]

    def test_custom_key_appears_in_options(self):
        r = run_dry(task_id="aops-1", env_overrides={"POLECAT_SSH_KEY": "/tmp/test_key"})
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "-i" in out["ssh_options"]
        assert "/tmp/test_key" in out["ssh_options"]


class TestEnvForwarding:
    def test_required_vars_in_window_cmd(self):
        r = run_dry(
            task_id="aops-env-test",
            env_overrides={
                "POLECAT_HOME": "/custom/polecat",
                "AOPS_SESSIONS": "/custom/sessions",
            },
        )
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "POLECAT_HOME=/custom/polecat" in out["window_cmd"]
        assert "AOPS_SESSIONS=/custom/sessions" in out["window_cmd"]

    def test_pkb_url_forwarded_when_set(self):
        r = run_dry(
            task_id="aops-pkb",
            env_overrides={"PKB_MCP_URL": "http://localhost:3000"},
        )
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "PKB_MCP_URL=http://localhost:3000" in out["window_cmd"]

    def test_pkb_url_absent_when_not_set(self):
        r = run_dry(task_id="aops-no-pkb")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "PKB_MCP_URL" not in out["window_cmd"]

    def test_optional_vars_forwarded_when_set(self):
        extras = {
            "PKB_MCP_TOKEN": "tok123",
            "AOPS_BOT_GH_TOKEN": "ghp_abc",
            "CLAUDE_CODE_OAUTH_TOKEN": "oauth_xyz",
            "AOPS": "/home/user/aops",
            "AOPS_SRC_DIR": "/home/user/src",
            "AOPS_POLECAT_CONFIG": "/home/user/.aops/polecat.yaml",
        }
        r = run_dry(task_id="aops-opts", env_overrides=extras)
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        for var, val in extras.items():
            assert f"{var}={val}" in out["window_cmd"], f"{var} not found in window_cmd"

    def test_optional_vars_absent_when_empty(self):
        r = run_dry(
            task_id="aops-empty",
            env_overrides={"PKB_MCP_TOKEN": ""},
        )
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "PKB_MCP_TOKEN" not in out["window_cmd"]


class TestWindowCommand:
    def test_polecat_run_with_task_id(self):
        r = run_dry(task_id="aops-cmd-test")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "polecat run -t aops-cmd-test" in out["window_cmd"]

    def test_extra_args_passed_through(self):
        r = run_dry("-t", "aops-extra", "--", "--model", "opus")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert "--model" in out["window_cmd"]
        assert "opus" in out["window_cmd"]

    def test_env_prefix_before_polecat_run(self):
        r = run_dry(task_id="aops-order")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        cmd = out["window_cmd"]
        env_pos = cmd.find("POLECAT_HOME=")
        run_pos = cmd.find("polecat run")
        assert env_pos < run_pos, "env vars must appear before 'polecat run'"

    def test_window_cmd_starts_with_env(self):
        r = run_dry(task_id="aops-env-start")
        assert r.returncode == 0
        out = parse_dry_output(r.stdout)
        assert out["window_cmd"].startswith("env ")


class TestValidation:
    def test_missing_polecat_home_fails(self):
        r = run_dry(
            task_id="aops-1",
            env_overrides={"POLECAT_HOME": ""},
        )
        assert r.returncode != 0
        assert "POLECAT_HOME" in r.stderr

    def test_missing_aops_sessions_fails(self):
        base_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/root"),
            "POLECAT_HOME": "/host/polecat",
        }
        r = subprocess.run(
            [str(SCRIPT), "--dry-run", "-t", "aops-1"],
            text=True,
            capture_output=True,
            env=base_env,
        )
        assert r.returncode != 0
        assert "AOPS_SESSIONS" in r.stderr

    def test_no_task_id_and_no_stdin_fails(self):
        r = run_dry()
        assert r.returncode != 0

    def test_script_is_executable(self):
        assert SCRIPT.exists(), f"Script not found: {SCRIPT}"
        assert os.access(SCRIPT, os.X_OK), f"Script is not executable: {SCRIPT}"
