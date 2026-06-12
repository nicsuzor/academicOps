"""Write-time secret redaction for session artifacts (aops-9f290e36).

Covers the redaction primitives plus their wiring into the two git-tracked
output chokepoints: transcript markdown (format_session_as_markdown) and
insights JSON (write_insights_file). The headline acceptance criterion — feed a
transcript carrying an env dump, assert no token-shaped string survives into the
written artifact — is exercised by the two wiring tests at the bottom.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AOPS_CORE = str(_REPO_ROOT / "aops-core")
if _AOPS_CORE not in sys.path:
    sys.path.insert(0, _AOPS_CORE)

from lib.insights_generator import write_insights_file
from lib.secret_redaction import REDACTED, redact_obj, redact_secrets
from lib.transcript_parser import Entry, ParsedSession, SessionProcessor

# A realistic `export`/`env` dump like the one that leaked on 2026-06-01.
ENV_DUMP = (
    "$ env\n"
    "GH_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
    "ANTHROPIC_API_KEY=sk-ant-api03-abc123def456ghi789jkl012mno345\n"
    "TAILSCALE_AUTHKEY=tskey-auth-k1A2b3C4d5E6f7\n"
    "ZOTERO_API_KEY=aB3xY9zQ1wE7rT5uI8oP2sD4\n"
    'AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI1K7MDENGbPxRfiCYEXAMPLEKEY"\n'
    "HOME=/Users/suzor\n"
    "EDITOR=vim\n"
    "PATH=/usr/bin:/bin\n"
)

# Token-shaped substrings that must never survive into a written artifact.
LEAKED_VALUES = [
    "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "sk-ant-api03-abc123def456ghi789jkl012mno345",
    "tskey-auth-k1A2b3C4d5E6f7",
    "aB3xY9zQ1wE7rT5uI8oP2sD4",
    "wJalrXUtnFEMI1K7MDENGbPxRfiCYEXAMPLEKEY",
]


class TestRedactSecrets:
    def test_env_dump_scrubbed_but_benign_preserved(self):
        out = redact_secrets(ENV_DUMP)
        for leaked in LEAKED_VALUES:
            assert leaked not in out, f"{leaked!r} survived redaction"
        # Key names are kept so the artifact still shows a secret was present.
        assert "GH_TOKEN=" in out
        assert "ANTHROPIC_API_KEY=" in out
        assert REDACTED in out
        # Benign environment lines are untouched.
        assert "HOME=/Users/suzor" in out
        assert "EDITOR=vim" in out
        assert "PATH=/usr/bin:/bin" in out

    def test_standalone_tokens_anywhere(self):
        text = "see token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 in the log"
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in redact_secrets(text)
        assert REDACTED in redact_secrets(text)

    def test_jwt_scrubbed(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4"
        assert jwt not in redact_secrets(f"auth: {jwt}")

    def test_json_form_value_scrubbed(self):
        text = '{"api_key": "aB3xY9zQ1wE7rT5uI8oP2sD4secret"}'
        out = redact_secrets(text)
        assert "aB3xY9zQ1wE7rT5uI8oP2sD4secret" not in out
        assert "api_key" in out  # key preserved

    def test_non_secret_prose_unchanged(self):
        text = "The transcript parser aggregates tokens by tool and by skill."
        assert redact_secrets(text) == text

    def test_non_string_passthrough(self):
        assert redact_secrets(None) is None  # type: ignore[arg-type]


class TestRedactObj:
    def test_recurses_values_not_keys(self):
        obj = {
            "summary": "ran env; GH_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            "count": 3,
            "nested": {"GH_TOKEN": "ghp_ZZZZZZZZZZZZZZZZZZZZZZ0123456789"},
            "items": ["sk-ant-api03-abc123def456ghi789jkl012mno345xyz", "ok"],
        }
        out = redact_obj(obj)
        blob = json.dumps(out)
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in blob
        assert "ghp_ZZZZZZZZZZZZZZZZZZZZZZ0123456789" not in blob
        assert "sk-ant-api03-abc123def456ghi789jkl012mno345xyz" not in blob
        assert out["count"] == 3  # non-strings pass through
        assert "ok" in out["items"]
        assert "summary" in out and "nested" in out  # keys preserved


class TestWiringIntoArtifacts:
    """End-to-end: a transcript/insights carrying secrets is scrubbed at write."""

    def test_insights_json_scrubbed_on_write(self, tmp_path: Path):
        insights = {
            "session_id": "deadbeef",
            "summary": "Investigated env; leaked " + ENV_DUMP,
            "accomplishments": [
                "set ANTHROPIC_API_KEY=sk-ant-api03-abc123def456ghi789jkl012mno345"
            ],
        }
        out_path = tmp_path / "summary.json"
        write_insights_file(out_path, insights, session_id=None)
        written = out_path.read_text(encoding="utf-8")
        for leaked in LEAKED_VALUES:
            assert leaked not in written, f"{leaked!r} leaked into insights JSON"
        # Still valid JSON with structure intact.
        parsed = json.loads(written)
        assert parsed["session_id"] == "deadbeef"
        assert REDACTED in parsed["summary"]

    def test_transcript_markdown_scrubbed_on_render(self):
        """Feed a transcript whose user turn contains an env dump; assert no
        token-shaped string survives into the rendered markdown."""
        session = ParsedSession(uuid="11111111-2222-3333-4444-555555555555")
        entries = [
            Entry(
                type="user",
                message={"content": f"here is my environment:\n{ENV_DUMP}"},
            ),
            Entry(
                type="assistant",
                message={"content": [{"type": "text", "text": "Noted."}]},
            ),
        ]
        md = SessionProcessor().format_session_as_markdown(
            session, entries, include_tool_results=True
        )
        for leaked in LEAKED_VALUES:
            assert leaked not in md, f"{leaked!r} leaked into transcript markdown"
        assert REDACTED in md
