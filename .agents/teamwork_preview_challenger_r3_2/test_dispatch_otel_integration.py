#!/usr/bin/env python3
"""Integration test for dispatch.py OTEL instrumentation."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

def test_dispatch_otel_integration():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        env = dict(os.environ)
        env["COPE_EVALUATOR_OTEL_TRACE_PATH"] = tmp_path
        env["TRACEPARENT"] = "00-1234567890abcdef1234567890abcdef-abcdef1234567890-01"

        payload = {
            "session_id": "test_dispatch_sess",
            "conversationId": "test_dispatch_sess",
            "tool_name": "SendMessage",
            "tool_input": {
                "recipient": "target_agent_alpha"
            }
        }

        proc = subprocess.run(
            ["/home/worker/.venv/bin/python", "/workspace/lib/hooks/dispatch.py", "claude", "PreToolUse"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
        )
        assert proc.returncode == 0, f"dispatch.py failed: stderr={proc.stderr}"

        # Now parse OTLP spans from tmp_path
        with open(tmp_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        assert len(lines) > 0, "No spans written by dispatch.py!"
        
        data = json.loads(lines[0])
        spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 1
        span = spans[0]
        assert span["name"] == "agent.send_message"
        assert span.get("parentSpanId") == "abcdef1234567890"

        print("PASS: dispatch.py OTEL integration test passed successfully!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    test_dispatch_otel_integration()
