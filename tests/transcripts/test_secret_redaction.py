"""Write-time secret redaction for session artifacts.

Covers the redaction primitives plus their wiring into the git-tracked output
chokepoints. The headline acceptance criterion — feed content carrying an env
dump, assert no token-shaped string survives into the written artifact — is
exercised by the wiring tests at the bottom.

The wiring tests target the current pipeline: `transcripts.runner`'s four
session artifacts and `transcripts.domain.ledger`'s prompt ledger. An earlier
version of this file tested `write_insights_file` and
`SessionProcessor.format_session_as_markdown`; both modules were deleted when
the transcript pipeline was restructured into the `transcripts` package, and
redaction was lost in that move rather than carried across.
"""

from __future__ import annotations

import json
from pathlib import Path

from transcripts.domain.secret_redaction import REDACTED, redact_obj, redact_secrets

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

    def test_token_count_metrics_not_redacted(self):
        # Usage metrics use ``*_tokens`` keys which match the ``TOKEN``
        # component in ``_SENSITIVE_NAME``. Their values are bare integers /
        # floats — never credentials — and must survive into the rendered
        # transcript so cost analysis stays usable.
        stats = (
            "stats:\n"
            "  input_tokens: 12345\n"
            "  output_tokens: 678\n"
            "  cache_read_tokens: 90\n"
            "  cache_created_tokens: 0\n"
            "  tool_calls: 38\n"
            "  duration_minutes: 3.4\n"
        )
        out = redact_secrets(stats)
        assert REDACTED not in out
        for n in ("12345", "678", "90", "0", "38", "3.4"):
            assert f": {n}" in out, f"metric value {n!r} did not survive"

    def test_numeric_shell_assignment_not_redacted(self):
        # The same protection applies to shell-style ``FOO_TOKEN=12345``: a
        # bare integer is never a credential.
        assert redact_secrets("MAX_TOKENS=4096") == "MAX_TOKENS=4096"

    def test_non_numeric_token_assignment_still_redacted(self):
        # Guardrail: real credentials (non-numeric) still get scrubbed even
        # though we now spare numeric ``*TOKEN*`` values.
        out = redact_secrets("GH_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in out
        assert REDACTED in out
        out2 = redact_secrets('"api_key": "sk-ant-api03-abc123def456"')
        assert "sk-ant-api03-abc123def456" not in out2
        assert REDACTED in out2


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
    """End-to-end: content carrying secrets is scrubbed at every write chokepoint.

    These are the tests that would have caught the regression. Each asserts on
    bytes actually written to disk, not on the redaction helper in isolation —
    a helper that exists but is never called is exactly the failure mode being
    guarded against.
    """

    def test_runner_scrubs_every_session_artifact(self, tmp_path: Path, monkeypatch):
        """All four artifacts `process_single_session` writes must be scrubbed.

        Written against the write chokepoint rather than a renderer, so adding
        a fifth output format cannot silently ship unredacted.
        """
        from transcripts import runner

        written: dict[str, str] = {}

        def _fake_write_text(self: Path, data: str, **kwargs: object) -> int:
            written[self.name] = data
            return len(data)

        poisoned = f"here is my environment:\n{ENV_DUMP}"
        monkeypatch.setattr(
            runner,
            "render_session_to_all_formats",
            lambda *a, **k: (poisoned, poisoned, poisoned),
        )
        monkeypatch.setattr(runner, "render_to_full_markdown", lambda *a, **k: poisoned)
        monkeypatch.setattr(Path, "write_text", _fake_write_text)

        runner.process_single_session(
            _stub_session(), tmp_path, _NeverSkipCache(), force=True
        )

        assert written, "no artifacts were written; the wiring test proved nothing"
        assert len(written) == 4, f"expected 4 artifacts, saw {sorted(written)}"
        for name, content in written.items():
            for leaked in LEAKED_VALUES:
                assert leaked not in content, f"{leaked!r} leaked into {name}"
            assert REDACTED in content, f"{name} was written without any redaction"

    def test_prompt_ledger_scrubbed_on_write(self, tmp_path: Path):
        """The ledger embeds raw user prompt text — the 2026-06-01 leak vector."""
        from transcripts.domain.ledger import generate_prompt_ledger

        sidecar_dir = tmp_path / "transcripts" / "2026-07"
        sidecar_dir.mkdir(parents=True)
        # Schema must match what generate_prompt_ledger actually reads
        # (`user_prompts: [{text, timestamp}]`). Getting this wrong produces an
        # empty ledger that passes the leak assertions vacuously.
        (sidecar_dir / "20260701-10-aops-test.json").write_text(
            json.dumps(
                {
                    "session_id": "deadbeefcafe",
                    "project": "aops",
                    "has_user_context": True,
                    "started_at": "2026-07-01T10:00:00+00:00",
                    "insights": "looked at the environment",
                    "user_prompts": [
                        {
                            "text": f"GH_TOKEN={LEAKED_VALUES[0]} please debug",
                            "timestamp": "2026-07-01T10:00:00+00:00",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        # since_arg well before the fixture date, so the row is not filtered out
        generate_prompt_ledger(tmp_path, "2026-06-01")

        ledger = tmp_path / "state" / "prompt_ledger.md"
        assert ledger.exists(), "ledger was not generated; the test proved nothing"
        content = ledger.read_text(encoding="utf-8")
        # Guard against a vacuous pass: the row must actually be present.
        assert "deadbeef" in content, (
            "no prompt row reached the ledger, so the leak assertion below "
            f"proves nothing. Ledger content:\n{content}"
        )
        assert REDACTED in content, "ledger row was written without redaction"
        for leaked in LEAKED_VALUES:
            assert leaked not in content, f"{leaked!r} leaked into the prompt ledger"


class _NeverSkipCache:
    """Minimal SkipCache stand-in: never skips, records nothing."""

    def is_skipped(self, session_id: str) -> bool:
        return False

    def mark_empty(self, session_id: str) -> None:
        return None

    def mark_processed(self, session_id: str) -> None:
        return None


def _stub_session():
    """A NormalizedSession with one user event, enough to pass the empty check."""
    from transcripts.model import NormalizedEvent, NormalizedSession

    return NormalizedSession(
        session_id="11111111-2222-3333-4444-555555555555",
        source_file=Path("stub.jsonl"),
        events=[
            NormalizedEvent(
                event_id="e1",
                timestamp="2026-07-01T10:00:00+00:00",
                source="user",
                type="message",
                content="hello",
            )
        ],
    )
