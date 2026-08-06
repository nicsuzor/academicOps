#!/usr/bin/env python3
"""Stress test and edge case harness for R2 implementation.
Executed by Challenger 1.
"""

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, UTC
from pathlib import Path

sys.path.insert(0, "/workspace/lib")
from polecat import cli


def stress_test_verify_transcript():
    print("--- Stress Testing _verify_transcript_created() ---")
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir)

        # Edge case A: session_dir is a file instead of directory
        fake_file = session_dir / "not_a_dir"
        fake_file.touch()
        res = cli._verify_transcript_created(fake_file)
        assert res["found"] is False
        assert res["count"] == 0
        print("  [PASS] Edge A: session_dir is a file")
        results.append(("Edge A: session_dir is file", "PASS"))

        # Edge case B: Invalid UTF-8 bytes in .jsonl file
        claude_uuid = str(uuid.uuid4())
        bad_utf8_file = session_dir / f"{claude_uuid}.jsonl"
        bad_utf8_file.write_bytes(b"\x80\x81\xff\n{\"valid\":\"line\"}\n")
        res = cli._verify_transcript_created(session_dir)
        assert res["found"] is True
        assert res["event_count"] == 2 # 1 invalid line (replaced with replacement char, strip is non-empty) + 1 valid json line
        print("  [PASS] Edge B: Invalid UTF-8 bytes handled gracefully")
        results.append(("Edge B: Invalid UTF-8 bytes", "PASS"))
        bad_utf8_file.unlink()

        # Edge case C: Case sensitivity of agent command in write_run_record
        res_c = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-upper",
            container_id="cid",
            container_name="polecat-test",
            agent="CLAUDE",
            task_id=None,
            seeded_prompt=None,
            image_ref="aops-crew:latest",
            image_digest=None,
            workspace_dir=session_dir,
            commit_start=None,
            commit_end=None,
            exit_code=0,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model=None,
            degraded=[],
        )
        data_c = json.loads(res_c.read_text())
        assert data_c["status"] == "degraded", f"Upper case agent should degrade when transcript missing, got {data_c['status']}"
        print("  [PASS] Edge C: Uppercase agent command ('CLAUDE') correctly identified")
        results.append(("Edge C: Uppercase agent command", "PASS"))

        # Edge case D: Agent command exit_code=1 with missing transcript -> status: "failed" but degraded list updated
        res_d = cli.write_run_record(
            session_dir=session_dir,
            session_id="test-failed-exit",
            container_id="cid",
            container_name="polecat-test",
            agent="claude",
            task_id=None,
            seeded_prompt=None,
            image_ref="aops-crew:latest",
            image_digest=None,
            workspace_dir=session_dir,
            commit_start=None,
            commit_end=None,
            exit_code=1,
            delivery_guard={"ok": True, "error": None},
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            worker_model="model",
            degraded=[],
        )
        data_d = json.loads(res_d.read_text())
        assert data_d["status"] == "failed", f"Non-zero exit code should be status failed, got {data_d['status']}"
        assert any(d.get("what") == "transcript_missing" for d in data_d["degraded"])
        print("  [PASS] Edge D: Agent exit code != 0 returns status 'failed' with transcript_missing in degraded[]")
        results.append(("Edge D: Exit code 1 with missing transcript", "PASS"))

    return results

if __name__ == "__main__":
    res = stress_test_verify_transcript()
    print(f"\nAll {len(res)} stress test cases passed!")
