"""Test write-time secret scrubbing for gate/narrative builder. (aops-efc4592f)"""

from __future__ import annotations

import json

from hooks.schemas import HookContext
from lib.gates.custom_actions import create_audit_file
from lib.secret_redaction import REDACTED

# A realistic env dump containing secrets
ENV_DUMP = (
    "$ env\n"
    "GH_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
    "AOPS_BOT_GH_TOKEN=ghp_ZZZZZZZZZZZZZZZZZZZZZZ0123456789\n"
    "CLOUDFLARE_API_TOKEN=sk-ant-api03-abc123def456ghi789jkl012mno345\n"
    "AOPS_CC_OAUTH_TOKEN=sk-ant-api03-oauth\n"
)


def test_create_audit_file_scrubs_secrets(tmp_path, monkeypatch):
    # Setup test file & mock path
    transcript_file = tmp_path / "session.jsonl"

    transcript_file.write_text(
        json.dumps(
            {
                "step_index": 0,
                "source": "USER_EXPLICIT",
                "type": "user",
                "message": {"content": f"Running dump env:\n{ENV_DUMP}"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    # Create HookContext
    ctx = HookContext(
        session_id="test-session-secrets",
        hook_event="Stop",
        raw_input={"transcript_path": str(transcript_file)},
    )
    ctx.transcript_path = str(transcript_file)
    ctx.client_type = "claude"

    # Mock status dir to write to our tmp_path
    monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(tmp_path))

    # Invoke custom action helper that builds the enforcer gate file
    gate_path = create_audit_file("test-session-secrets", "enforcer", ctx)

    assert gate_path.exists()

    content = gate_path.read_text(encoding="utf-8")

    # Assert secret tokens are scrubbed
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in content
    assert "ghp_ZZZZZZZZZZZZZZZZZZZZZZ0123456789" not in content
    assert "sk-ant-api03-abc123def456ghi789jkl012mno345" not in content

    # Assert REDACTED marker is present
    assert REDACTED in content
