"""Behavioural tests for the headless background-job stop gate (academicOps#2750).

Each end-to-end case runs the real ``dispatch.py`` as a subprocess against a
staged copy of the ida hooks, with a synthetic transcript in the shape Claude
Code writes: a Bash ``tool_use``, its ``tool_result`` carrying
``toolUseResult.backgroundTaskId``, and optionally a ``<task-notification>``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import bg_wait_gate  # type: ignore[import-not-found]  # noqa: E402


@pytest.fixture
def staged(tmp_path: Path) -> Path:
    hooks = tmp_path / "hooks"
    shutil.copytree(IDA_HOOKS, hooks, ignore=shutil.ignore_patterns("__pycache__"))
    return hooks


@pytest.fixture(autouse=True)
def gate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AOPS_BG_WAIT_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.delenv("AOPS_BG_WAIT_GATE", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-cli")


def _launch(task_id: str, output_file: Path, command: str = "cargo test", n: int = 1) -> list[dict]:
    use_id = f"toolu_{n}"
    return [
        {
            "type": "assistant",
            "isSidechain": False,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": use_id,
                        "name": "Bash",
                        "input": {"command": command, "run_in_background": True},
                    }
                ],
            },
        },
        {
            "type": "user",
            "isSidechain": False,
            "message": {
                "role": "user",
                "content": [
                    {
                        "tool_use_id": use_id,
                        "type": "tool_result",
                        "content": (
                            f"Command running in background with ID: {task_id}. "
                            f"Output is being written to: {output_file}. "
                            "You will be notified when it completes."
                        ),
                    }
                ],
            },
            "toolUseResult": {"stdout": "", "stderr": "", "backgroundTaskId": task_id},
        },
    ]


def _notification(task_id: str, status: str = "completed") -> dict:
    return {
        "type": "queue-operation",
        "operation": "enqueue",
        "content": (
            f"<task-notification>\n<task-id>{task_id}</task-id>\n"
            f"<status>{status}</status>\n</task-notification>"
        ),
    }


def _transcript(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    return path


def _running(tmp_path: Path, name: str) -> Path:
    out = tmp_path / f"{name}.output"
    out.write_text("Compiling mem v0.1.0\n", encoding="utf-8")
    return out


def _exited(tmp_path: Path, name: str) -> Path:
    out = tmp_path / f"{name}.output"
    out.write_text("test result: ok\n\n[exited with code 0]\n", encoding="utf-8")
    return out


def fire(staged: Path, payload: dict, env_extra: dict | None = None):
    import os

    env = dict(os.environ)
    env.update(env_extra or {})
    proc = subprocess.run(
        [sys.executable, str(staged / "dispatch.py"), "claude", "Stop"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=30,
        cwd=str(staged),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------


def test_running_job_is_pending(tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", _running(tmp_path, "bjob1")))
    pending = bg_wait_gate.pending_background_jobs(str(t))
    assert [j["id"] for j in pending] == ["bjob1"]
    assert pending[0]["command"] == "cargo test"


def test_notified_job_is_not_pending(tmp_path: Path):
    entries = _launch("bjob1", _running(tmp_path, "bjob1")) + [_notification("bjob1", "failed")]
    assert bg_wait_gate.pending_background_jobs(str(_transcript(tmp_path, entries))) == []


def test_exit_trailer_means_not_pending(tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", _exited(tmp_path, "bjob1")))
    assert bg_wait_gate.pending_background_jobs(str(t)) == []


def test_missing_output_file_is_not_pending(tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", tmp_path / "gone.output"))
    assert bg_wait_gate.pending_background_jobs(str(t)) == []


def test_only_unfinished_jobs_are_pending(tmp_path: Path):
    """Both specimens on #2750: the first job reported back, the second did not."""
    entries = (
        _launch("bfirst", _exited(tmp_path, "bfirst"), "rustup install", n=1)
        + [_notification("bfirst")]
        + _launch("bsecond", _running(tmp_path, "bsecond"), "cargo test; cargo clippy", n=2)
    )
    pending = bg_wait_gate.pending_background_jobs(str(_transcript(tmp_path, entries)))
    assert [j["id"] for j in pending] == ["bsecond"]


def test_non_bash_background_results_are_ignored(tmp_path: Path):
    entries = _launch("bmon", _running(tmp_path, "bmon"))
    entries[0]["message"]["content"][0]["name"] = "Monitor"
    assert bg_wait_gate.pending_background_jobs(str(_transcript(tmp_path, entries))) == []


# ---------------------------------------------------------------------------
# End to end through dispatch.py
# ---------------------------------------------------------------------------


def test_headless_stop_with_running_job_blocks(staged: Path, tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", _running(tmp_path, "bjob1")))
    out = fire(staged, {"session_id": "s1", "transcript_path": str(t)})
    assert out["decision"] == "block"
    assert "bjob1" in out["reason"]
    assert "release" in out["reason"]


def test_continuation_stop_with_running_job_still_blocks(staged: Path, tmp_path: Path):
    """A second text-only stop while the job runs is the same failure."""
    t = _transcript(tmp_path, _launch("bjob1", _running(tmp_path, "bjob1")))
    payload = {"session_id": "s1", "transcript_path": str(t), "stop_hook_active": True}
    assert fire(staged, payload)["decision"] == "block"


def test_headless_stop_after_job_exits_is_allowed(staged: Path, tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", _exited(tmp_path, "bjob1")))
    out = fire(staged, {"session_id": "s1", "transcript_path": str(t)})
    assert out.get("decision") != "block"


def test_continuation_stop_with_no_jobs_is_silent(staged: Path, tmp_path: Path):
    t = _transcript(tmp_path, [])
    payload = {"session_id": "s1", "transcript_path": str(t), "stop_hook_active": True}
    assert fire(staged, payload) == {}


def test_interactive_session_is_not_gated(staged: Path, tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", _running(tmp_path, "bjob1")))
    out = fire(
        staged,
        {"session_id": "s1", "transcript_path": str(t)},
        {"CLAUDE_CODE_ENTRYPOINT": "cli"},
    )
    assert out.get("decision") != "block"


def test_gate_gives_up_after_max_blocks(staged: Path, tmp_path: Path):
    t = _transcript(tmp_path, _launch("bjob1", _running(tmp_path, "bjob1")))
    payload = {"session_id": "s-cap", "transcript_path": str(t), "stop_hook_active": True}
    for _ in range(bg_wait_gate._MAX_BLOCKS):
        assert fire(staged, payload)["decision"] == "block"
    assert fire(staged, payload).get("decision") != "block"
