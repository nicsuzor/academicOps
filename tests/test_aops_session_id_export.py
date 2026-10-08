"""SessionStart writes the session's id to CLAUDE_ENV_FILE as AOPS_SESSION_ID,
so the premise-check verdict script run from that session's Bash records its
verdict without --session (nicsuzor/academicOps#2798), and the tracer's
session.id grouping reads the same value.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA = REPO_ROOT / "plugins" / "ida"
IDA_HOOKS = IDA / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct
import dispatch
import handlers
import premise_check_gate as pcg

SESSION = "0b7c2f4e-1d2a-4c55-9e7d-3f1a2b3c4d5e"


def _ctx(session_id: str = SESSION) -> dispatch.HookContext:
    return dispatch.HookContext(
        client="claude",
        event="SessionStart",
        session_id=session_id,
        raw={"session_id": session_id, "source": "startup"},
    )


def test_session_start_writes_aops_session_id(tmp_path, monkeypatch):
    env_file = tmp_path / "env.sh"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    handlers.session_start(_ctx())
    assert handlers._read_env_file(env_file)["AOPS_SESSION_ID"] == SESSION


def test_session_start_keeps_existing_env_file_entries(tmp_path, monkeypatch):
    env_file = tmp_path / "env.sh"
    env_file.write_text("export OTHER=1\n")
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.invalid")
    handlers.session_start(_ctx())
    values = handlers._read_env_file(env_file)
    assert values["OTHER"] == "1"
    assert values["PKB_MCP_URL"] == "https://pkb.invalid"
    assert values["AOPS_SESSION_ID"] == SESSION


def test_each_session_writes_its_own_id(tmp_path, monkeypatch):
    """A nested session inheriting a parent's AOPS_SESSION_ID still writes its
    own: the premise-check gate keys its state by this session's id."""
    env_file = tmp_path / "env.sh"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    monkeypatch.setenv("AOPS_SESSION_ID", "parent-session")
    handlers.session_start(_ctx())
    assert handlers._read_env_file(env_file)["AOPS_SESSION_ID"] == SESSION


def test_no_env_file_no_write(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    assert handlers._export_session_id(_ctx()) is False


def test_tracer_reads_the_exported_id(tmp_path, monkeypatch):
    env_file = tmp_path / "env.sh"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    handlers.session_start(_ctx())
    monkeypatch.setenv("AOPS_SESSION_ID", handlers._read_env_file(env_file)["AOPS_SESSION_ID"])
    assert cct.resolve_session_id({}, "session_id", prefer_env=True) == SESSION


def _clean_env(tmp_path: Path) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("OTEL_", "GENAI_ENGINE_", "AOPS_", "CLAUDE_"))
    }
    env["HOME"] = str(tmp_path)
    env["AOPS_PREMISE_GATE_DIR"] = str(tmp_path / "gate")
    return env


def test_verdict_script_records_without_session_flag(tmp_path):
    """End to end, as Claude Code runs it: SessionStart through dispatch.py,
    then the documented verdict command in a Bash that sources CLAUDE_ENV_FILE,
    from a cwd that is not the skill directory, with no --session."""
    env = _clean_env(tmp_path)
    env_file = tmp_path / "claude-env" / "sessionstart-hook-0.sh"
    env["CLAUDE_ENV_FILE"] = str(env_file)

    start = subprocess.run(
        [sys.executable, str(IDA_HOOKS / "dispatch.py"), "claude", "SessionStart"],
        input=json.dumps({"hook_event_name": "SessionStart", "session_id": SESSION}),
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=60,
    )
    assert start.returncode == 0, start.stderr

    pcg.arm(SESSION, claim_id="r1")
    assert pcg.is_armed(SESSION) is True

    verdict = IDA / "skills" / "premise-check" / "scripts" / "verdict.py"
    bash_env = {k: v for k, v in env.items() if k != "CLAUDE_ENV_FILE"}
    run = subprocess.run(
        [
            "bash",
            "-c",
            f'. "{env_file}" && "{sys.executable}" "{verdict}" '
            '--report r1 --verdict PASS --reason "holds"',
        ],
        capture_output=True,
        text=True,
        env=bash_env,
        cwd=tmp_path,
        timeout=60,
    )
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    assert out["disarmed"] is True
    assert pcg.is_armed(SESSION) is False
    assert pcg.get_state(SESSION)["last_verdict"]["verdict"] == "PASS"


@pytest.fixture(autouse=True)
def _gate_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))
