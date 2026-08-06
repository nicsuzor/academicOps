#!/usr/bin/env python3
"""Empirical Stress Test Harness for Milestone R2 (Persistence Verification & Defaults)."""

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, "/workspace")

from lib.polecat.cli import _verify_transcript_created, transcript_evidence, write_run_record, _transcript_paths
from lib.polecat.env_contract import CONTAINER_SET_ENV, FORWARDED_ENV, docker_env_args

results = []

def record_result(name, passed, details=""):
    results.append({"name": name, "passed": passed, "details": details})
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if details:
        print(f"       Details: {details}")

print("=== 1. Testing Transcript Evidence & Edge Cases ===")

with tempfile.TemporaryDirectory() as tmpdir:
    tmppath = Path(tmpdir)
    
    # Case 1.1: Empty session directory
    res = _verify_transcript_created(tmppath)
    record_result(
        "1.1 Empty session dir",
        res["found"] is False and res["transcript_path"] is None and res["event_count"] == 0 and res["count"] == 0,
        f"Result: {res}"
    )

    # Case 1.2: Non-matching .jsonl files (e.g., polecat-hooks.jsonl, subagents/foo.jsonl, random.jsonl)
    (tmppath / "polecat-hooks.jsonl").write_text('{"event": "hook"}\n')
    (tmppath / "subagents").mkdir()
    (tmppath / "subagents" / f"{uuid.uuid4()}.jsonl").write_text('{"event": "sub"}\n')
    (tmppath / "custom.jsonl").write_text('{"event": "custom"}\n')
    res = _verify_transcript_created(tmppath)
    record_result(
        "1.2 Non-matching .jsonl files ignored",
        res["found"] is False and res["count"] == 0 and res["event_count"] == 0,
        f"Result: {res}"
    )

    # Case 1.3: 0-byte validly-named transcript
    valid_uuid = str(uuid.uuid4())
    t1_path = tmppath / f"{valid_uuid}.jsonl"
    t1_path.write_bytes(b"")
    res = _verify_transcript_created(tmppath)
    record_result(
        "1.3 0-byte valid transcript filename",
        res["found"] is False and res["count"] == 1 and res["transcript_path"] is None and res["event_count"] == 0,
        f"Result: {res}"
    )

    # Case 1.4: Whitespace/newlines-only transcript file
    t1_path.write_text("\n   \n\t\n  \n")
    res = _verify_transcript_created(tmppath)
    record_result(
        "1.4 Whitespace-only transcript file",
        res["found"] is False and res["count"] == 1 and res["event_count"] == 0,
        f"Result: {res}"
    )

    # Case 1.5: Valid transcript with non-empty line events
    t1_path.write_text('{"type": "user", "content": "hi"}\n\n{"type": "assistant", "content": "hello"}\n')
    res = _verify_transcript_created(tmppath)
    record_result(
        "1.5 Valid transcript with line events",
        res["found"] is True and res["count"] == 1 and res["event_count"] == 2 and res["transcript_bytes"] > 0,
        f"Result: {res}"
    )

    # Case 1.6: Binary / Non-UTF8 corrupted line
    t1_path.write_bytes(b'{"event": "1"}\n\xff\xfeInvalid utf8\n{"event": "2"}\n')
    res = _verify_transcript_created(tmppath)
    record_result(
        "1.6 Non-UTF8 bytes handled with replacement",
        res["found"] is True and res["event_count"] == 3,
        f"Result: {res}"
    )

    # Case 1.7: AGY brain directory structure
    agy_tmp = tmppath / "agy_session"
    agy_tmp.mkdir()
    agy_brain_logs = agy_tmp / "agy-brain" / "some-uuid" / ".system_generated" / "logs"
    agy_brain_logs.mkdir(parents=True)
    agy_transcript = agy_brain_logs / "transcript_123.jsonl"
    agy_transcript.write_text('{"event": "agy_start"}\n{"event": "agy_done"}\n')
    res_agy = _verify_transcript_created(agy_tmp)
    record_result(
        "1.7 AGY brain transcript detection",
        res_agy["found"] is True and res_agy["event_count"] == 2 and "transcript_123.jsonl" in res_agy["transcript_path"],
        f"Result: {res_agy}"
    )

    # Case 1.8: Multiple transcripts (e.g. smaller transcript with events vs larger transcript with only spaces)
    multi_tmp = tmppath / "multi_session"
    multi_tmp.mkdir()
    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())
    p1 = multi_tmp / f"{u1}.jsonl"
    p2 = multi_tmp / f"{u2}.jsonl"
    # p1 is larger in size (100 spaces) but has 0 events
    p1.write_text(" " * 100)
    # p2 is smaller (30 bytes) but has 1 event
    p2.write_text('{"type": "message"}\n')
    res_multi = _verify_transcript_created(multi_tmp)
    record_result(
        "1.8 Multiple transcripts size vs event count resolution",
        res_multi["found"] is True and res_multi["count"] == 2,
        f"Result: {res_multi}"
    )

print("\n=== 2. Testing Degraded Status Resolution & Run Record Ledger ===")

with tempfile.TemporaryDirectory() as tmpdir:
    tmppath = Path(tmpdir)
    now = datetime.now(timezone.utc)

    # Case 2.1: Agent = claude, exit 0, missing transcript -> degraded
    run_json_path = write_run_record(
        session_id="sess-1",
        container_id="c1",
        container_name="cn1",
        agent="claude",
        task_id="task-1",
        seeded_prompt="do task",
        image_ref="img:latest",
        image_digest="sha256:123",
        workspace_dir=tmppath,
        session_dir=tmppath,
        commit_start="sha1",
        commit_end="sha2",
        exit_code=0,
        delivery_guard={"ok": True},
        started_at=now,
        ended_at=now,
        worker_model="claude-3-5-sonnet",
        degraded=[],
    )
    import json
    data = json.loads(run_json_path.read_text())
    record_result(
        "2.1 Agent=claude, exit 0, missing transcript -> degraded status",
        data["status"] == "degraded" and any(d["what"] == "transcript_missing" for d in data["degraded"]),
        f"Status: {data['status']}, Degraded: {data['degraded']}"
    )

    # Case 2.2: Agent = AGY (uppercase), exit 0, missing transcript -> degraded (case insensitivity)
    run_json_path = write_run_record(
        session_id="sess-2",
        container_id="c2",
        container_name="cn2",
        agent="AGY",
        task_id="task-2",
        seeded_prompt="do task",
        image_ref="img:latest",
        image_digest="sha256:123",
        workspace_dir=tmppath,
        session_dir=tmppath,
        commit_start="sha1",
        commit_end="sha2",
        exit_code=0,
        delivery_guard={"ok": True},
        started_at=now,
        ended_at=now,
        worker_model="agy-model",
        degraded=[],
    )
    data = json.loads(run_json_path.read_text())
    record_result(
        "2.2 Agent=AGY (uppercase), exit 0, missing transcript -> degraded status",
        data["status"] == "degraded" and any(d["what"] == "transcript_missing" for d in data["degraded"]),
        f"Status: {data['status']}"
    )

    # Case 2.3: Agent = shell, exit 0, missing transcript -> success (non-agent no degradation)
    run_json_path = write_run_record(
        session_id="sess-3",
        container_id="c3",
        container_name="cn3",
        agent="shell",
        task_id="task-3",
        seeded_prompt="echo hi",
        image_ref="img:latest",
        image_digest="sha256:123",
        workspace_dir=tmppath,
        session_dir=tmppath,
        commit_start="sha1",
        commit_end="sha2",
        exit_code=0,
        delivery_guard={"ok": True},
        started_at=now,
        ended_at=now,
        worker_model=None,
        degraded=[],
    )
    data = json.loads(run_json_path.read_text())
    record_result(
        "2.3 Agent=shell, missing transcript -> success status",
        data["status"] == "success" and not any(d["what"] == "transcript_missing" for d in data["degraded"]),
        f"Status: {data['status']}"
    )

    # Case 2.4: Agent = claude, exit 1 (error), missing transcript -> failed status, transcript_missing in degraded[]
    run_json_path = write_run_record(
        session_id="sess-4",
        container_id="c4",
        container_name="cn4",
        agent="claude",
        task_id="task-4",
        seeded_prompt="do task",
        image_ref="img:latest",
        image_digest="sha256:123",
        workspace_dir=tmppath,
        session_dir=tmppath,
        commit_start="sha1",
        commit_end="sha2",
        exit_code=1,
        delivery_guard={"ok": True},
        started_at=now,
        ended_at=now,
        worker_model="claude-3-5-sonnet",
        degraded=[],
    )
    data = json.loads(run_json_path.read_text())
    record_result(
        "2.4 Agent=claude, exit 1, missing transcript -> status=failed, transcript_missing in degraded[]",
        data["status"] == "failed" and any(d["what"] == "transcript_missing" for d in data["degraded"]),
        f"Status: {data['status']}, Degraded: {data['degraded']}"
    )

    # Case 2.5: Agent = claude, valid transcript present -> status=success
    t_valid = tmppath / f"{uuid.uuid4()}.jsonl"
    t_valid.write_text('{"event": "start"}\n{"event": "finish"}\n')
    run_json_path = write_run_record(
        session_id="sess-5",
        container_id="c5",
        container_name="cn5",
        agent="claude",
        task_id="task-5",
        seeded_prompt="do task",
        image_ref="img:latest",
        image_digest="sha256:123",
        workspace_dir=tmppath,
        session_dir=tmppath,
        commit_start="sha1",
        commit_end="sha2",
        exit_code=0,
        delivery_guard={"ok": True},
        started_at=now,
        ended_at=now,
        worker_model="claude-3-5-sonnet",
        degraded=[],
    )
    data = json.loads(run_json_path.read_text())
    record_result(
        "2.5 Agent=claude, valid transcript present -> status=success",
        data["status"] == "success" and not any(d["what"] == "transcript_missing" for d in data["degraded"]) and data["transcript"]["found"] is True and data["transcript"]["event_count"] == 2,
        f"Status: {data['status']}, Transcript metadata: {data['transcript']}"
    )

print("\n=== 3. Testing Environment Defaults ===")

record_result(
    "3.1 CONTAINER_SET_ENV has CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1",
    CONTAINER_SET_ENV.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1",
    f"CONTAINER_SET_ENV: {CONTAINER_SET_ENV}"
)

record_result(
    "3.2 FORWARDED_ENV does NOT duplicate CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" not in FORWARDED_ENV,
    f"Found in FORWARDED_ENV: {'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' in FORWARDED_ENV}"
)

args = docker_env_args()
record_result(
    "3.3 docker_env_args emits -e CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1",
    "-e" in args and "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1" in args,
    f"docker_env_args output snippet: {[a for a in args if 'AGENT_TEAMS' in a]}"
)

print("\n=== Summary ===")
total = len(results)
passed = sum(1 for r in results if r["passed"])
failed = total - passed
print(f"Total: {total}, Passed: {passed}, Failed: {failed}")

if failed > 0:
    sys.exit(1)
