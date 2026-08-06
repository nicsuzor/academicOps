#!/usr/bin/env python3
"""Empirical test suite for R2 implementation (Persistence Verification & Defaults).
Executed by Challenger 1.
"""

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, UTC
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, "/workspace/lib")

from polecat import cli
from polecat.env_contract import CONTAINER_SET_ENV, FORWARDED_ENV, docker_env_args


def test_verify_transcript_created():
    print("--- 1. Testing _verify_transcript_created() ---")
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)

        # Sub-case 1.1: Missing transcript directory / empty directory
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is False, f"Expected found False, got {res}"
        assert res["path"] is None
        assert res["bytes"] is None
        assert res["count"] == 0
        assert res["event_count"] == 0
        print("  [PASS] 1.1: Missing transcripts / empty directory")
        results.append(("1.1 Missing transcripts", "PASS"))

        # Sub-case 1.2: 0-byte claude transcript file
        claude_uuid = str(uuid.uuid4())
        zero_byte_file = session_dir / f"{claude_uuid}.jsonl"
        zero_byte_file.touch()
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is False, f"Expected found False for 0-byte file, got {res}"
        assert res["path"] is None
        assert res["bytes"] is None
        assert res["count"] == 1
        assert res["event_count"] == 0
        print("  [PASS] 1.2: 0-byte .jsonl file (claude)")
        results.append(("1.2 0-byte claude file", "PASS"))
        zero_byte_file.unlink()

        # Sub-case 1.3: Empty lines / whitespace lines transcript file
        empty_lines_file = session_dir / f"{claude_uuid}.jsonl"
        empty_lines_file.write_text("\n   \n\t\n  \n")
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is False, f"Expected found False for whitespace file, got {res}"
        assert res["path"] is None
        assert res["bytes"] is None
        assert res["count"] == 1
        assert res["event_count"] == 0
        print("  [PASS] 1.3: Empty line files")
        results.append(("1.3 Empty line files", "PASS"))
        empty_lines_file.unlink()

        # Sub-case 1.4: Valid multi-line claude transcript
        valid_file = session_dir / f"{claude_uuid}.jsonl"
        valid_content = '{"type":"user","message":"hello"}\n{"type":"assistant","message":"hi"}\n'
        valid_file.write_text(valid_content)
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is True, f"Expected found True, got {res}"
        assert res["path"] == str(valid_file)
        assert res["bytes"] == len(valid_content.encode("utf-8"))
        assert res["count"] == 1
        assert res["event_count"] == 2
        print("  [PASS] 1.4: Valid multi-line claude transcript")
        results.append(("1.4 Valid multi-line transcript", "PASS"))
        valid_file.unlink()

        # Sub-case 1.5: Non-matching jsonl filenames (e.g. polecat-session-hooks.jsonl)
        non_matching = session_dir / "polecat-session-hooks.jsonl"
        non_matching.write_text('{"event":"hook"}\n')
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is False, f"Expected found False for hook log, got {res}"
        assert res["count"] == 0
        print("  [PASS] 1.5: Ignore non-matching .jsonl files")
        results.append(("1.5 Ignore hook jsonl", "PASS"))
        non_matching.unlink()

        # Sub-case 1.6: agy transcript structure (agy-brain/<uuid>/.system_generated/logs/transcript1.jsonl)
        agy_dir = session_dir / "agy-brain" / str(uuid.uuid4()) / ".system_generated" / "logs"
        agy_dir.mkdir(parents=True, exist_ok=True)
        agy_file = agy_dir / "transcript_123.jsonl"
        agy_content = '{"event": "start"}\n{"event": "stop"}\n'
        agy_file.write_text(agy_content)
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is True, f"Expected found True for agy transcript, got {res}"
        assert res["path"] == str(agy_file)
        assert res["bytes"] == len(agy_content.encode("utf-8"))
        assert res["count"] == 1
        assert res["event_count"] == 2
        print("  [PASS] 1.6: Valid agy transcript")
        results.append(("1.6 Valid agy transcript", "PASS"))

        # Sub-case 1.7: Multiple transcripts (determine largest & total event count)
        claude_file_1 = session_dir / f"{uuid.uuid4()}.jsonl"
        claude_file_1.write_text('{"a":1}\n') # smaller file
        res = cli._verify_transcript_created(session_dir)
        assert res["count"] == 2
        assert res["path"] == str(agy_file) # agy_file is larger
        assert res["event_count"] == 3 # 2 from agy, 1 from claude
        print("  [PASS] 1.7: Multiple transcripts select largest and sum total event count")
        results.append(("1.7 Multiple transcripts", "PASS"))

    return results


def test_write_run_record():
    print("\n--- 2. Testing write_run_record() ---")
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)
        workspace_dir = Path(tmpdir) / "workspace"
        workspace_dir.mkdir()

        # Sub-case 2.1: Agent command ("claude") with valid transcript -> status: "success"
        claude_uuid = str(uuid.uuid4())
        valid_file = session_dir / f"{claude_uuid}.jsonl"
        valid_file.write_text('{"event": "user"}\n')

        record_path = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-session-1",
            container_id="cid123",
            container_name="polecat-test",
            agent="claude",
            task_id="task-1",
            seeded_prompt="/pull task-1",
            image_ref="aops-crew:latest",
            image_digest="sha256:12345",
            workspace_dir=workspace_dir,
            commit_start="sha1",
            commit_end="sha2",
            exit_code=0,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model="claude-3-5-sonnet-20241022",
            degraded=[],
        )
        data = json.loads(record_path.read_text())
        assert data["status"] == "success", f"Expected status success, got {data['status']}"
        assert data["transcript"]["found"] is True
        assert data["transcript"]["event_count"] == 1
        assert not any(d.get("what") == "transcript_missing" for d in data["degraded"])
        print("  [PASS] 2.1: Agent command with valid transcript -> status: success")
        results.append(("2.1 Agent cmd + valid transcript", "PASS"))

        # Sub-case 2.2: Agent command ("claude") with missing transcript -> status: "degraded"
        valid_file.unlink()
        record_path = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-session-2",
            container_id="cid123",
            container_name="polecat-test",
            agent="claude",
            task_id="task-1",
            seeded_prompt="/pull task-1",
            image_ref="aops-crew:latest",
            image_digest="sha256:12345",
            workspace_dir=workspace_dir,
            commit_start="sha1",
            commit_end="sha2",
            exit_code=0,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model="claude-3-5-sonnet-20241022",
            degraded=[],
        )
        data = json.loads(record_path.read_text())
        assert data["status"] == "degraded", f"Expected status degraded, got {data['status']}"
        assert data["transcript"]["found"] is False
        assert any(d.get("what") == "transcript_missing" for d in data["degraded"])
        print("  [PASS] 2.2: Agent command + missing transcript -> status: degraded & transcript_missing recorded")
        results.append(("2.2 Agent cmd + missing transcript", "PASS"))

        # Sub-case 2.3: Agent command ("agy") with 0-byte transcript -> status: "degraded"
        zero_file = session_dir / f"{claude_uuid}.jsonl"
        zero_file.touch()
        record_path = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-session-3",
            container_id="cid123",
            container_name="polecat-test",
            agent="agy",
            task_id=None,
            seeded_prompt=None,
            image_ref="aops-crew:latest",
            image_digest="sha256:12345",
            workspace_dir=workspace_dir,
            commit_start="sha1",
            commit_end="sha2",
            exit_code=0,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model=None,
            degraded=[],
        )
        data = json.loads(record_path.read_text())
        assert data["status"] == "degraded", f"Expected status degraded, got {data['status']}"
        assert data["transcript"]["found"] is False
        assert any(d.get("what") == "transcript_missing" for d in data["degraded"])
        assert any(d.get("what") == "worker_model" for d in data["degraded"])
        print("  [PASS] 2.3: Agent command ('agy') + 0-byte transcript -> status: degraded & metadata nulls recorded")
        results.append(("2.3 Agent cmd ('agy') + 0-byte transcript", "PASS"))
        zero_file.unlink()

        # Sub-case 2.4: Non-agent command ("shell") with missing transcript -> status: "success"
        record_path = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-session-4",
            container_id="cid123",
            container_name="polecat-test",
            agent="shell",
            task_id=None,
            seeded_prompt=None,
            image_ref="aops-crew:latest",
            image_digest="sha256:12345",
            workspace_dir=workspace_dir,
            commit_start="sha1",
            commit_end="sha2",
            exit_code=0,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model=None,
            degraded=[],
        )
        data = json.loads(record_path.read_text())
        assert data["status"] == "success", f"Expected status success for non-agent, got {data['status']}"
        assert not any(d.get("what") == "transcript_missing" for d in data["degraded"])
        print("  [PASS] 2.4: Non-agent command ('shell') with missing transcript -> status: success")
        results.append(("2.4 Non-agent cmd + missing transcript", "PASS"))

        # Sub-case 2.5: Non-agent command ("sleep") with missing transcript -> status: "success"
        record_path = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-session-5",
            container_id="cid123",
            container_name="polecat-test",
            agent="sleep",
            task_id=None,
            seeded_prompt=None,
            image_ref="aops-crew:latest",
            image_digest="sha256:12345",
            workspace_dir=workspace_dir,
            commit_start="sha1",
            commit_end="sha2",
            exit_code=0,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model=None,
            degraded=[],
        )
        data = json.loads(record_path.read_text())
        assert data["status"] == "success", f"Expected status success for sleep, got {data['status']}"
        assert not any(d.get("what") == "transcript_missing" for d in data["degraded"])
        print("  [PASS] 2.5: Non-agent command ('sleep') with missing transcript -> status: success")
        results.append(("2.5 Non-agent cmd ('sleep')", "PASS"))

    return results


def test_agent_teams_env_var():
    print("\n--- 3. Testing CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS propagation ---")
    results = []

    # Check CONTAINER_SET_ENV
    assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" in CONTAINER_SET_ENV, "Key missing from CONTAINER_SET_ENV"
    assert CONTAINER_SET_ENV["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] == "1", "Value must be '1'"
    print("  [PASS] 3.1: CONTAINER_SET_ENV contains CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
    results.append(("3.1 CONTAINER_SET_ENV check", "PASS"))

    # Check FORWARDED_ENV
    assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" not in FORWARDED_ENV, "Key should NOT be in FORWARDED_ENV to avoid duplication"
    print("  [PASS] 3.2: FORWARDED_ENV does not duplicate CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS")
    results.append(("3.2 FORWARDED_ENV deduplication", "PASS"))

    # Check docker_env_args
    args = docker_env_args()
    assert "-e" in args
    assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" in args
    print("  [PASS] 3.3: docker_env_args includes -e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
    results.append(("3.3 docker_env_args propagation", "PASS"))

    # Check get_env_forwards
    config = {
        "git_identity": {"name": "Test Bot", "email": "bot@example.com"}
    }
    env_forwards = cli.get_env_forwards(config)
    assert env_forwards.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1", f"Got {env_forwards.get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS')}"
    print("  [PASS] 3.4: get_env_forwards includes CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
    results.append(("3.4 get_env_forwards propagation", "PASS"))

    return results


if __name__ == "__main__":
    r1 = test_verify_transcript_created()
    r2 = test_write_run_record()
    r3 = test_agent_teams_env_var()

    total_pass = len(r1) + len(r2) + len(r3)
    print(f"\nTotal custom empirical tests passed: {total_pass}")
