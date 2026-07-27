"""Write-time secret redaction for session artifacts.

Covers the redaction primitives plus their wiring into the git-tracked output
chokepoints. The headline acceptance criterion — feed content carrying an env
dump, assert no token-shaped string survives into the written artifact — is
exercised by the wiring tests at the bottom.

The second criterion is that the artifact still parses. Redaction used to run
as a regex over the *serialised* sidecar, where a match abutting an escaped
quote ate the backslash and re-emitted a bare `"`, ending the JSON string and
producing a file nothing could read. `TestStructuredCorpus` holds the floor
under the fix: every credential shape, in every position it turns up in, has to
come out both scrubbed and parseable — a value-walking redaction that quietly
stopped seeing names or keys would show up there.

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

import pytest
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

    def test_opaque_value_under_a_sensitive_key(self):
        """The case a value-only walk would drop.

        Serialised, ``{"ZOTERO_API_KEY": "aB3x..."}`` is text the assignment
        regex matches across the key/value boundary. A walk that only looks at
        values never sees the name, so the name is carried down instead.
        """
        obj = {"env": {"ZOTERO_API_KEY": "aB3xY9zQ1wE7rT5uI8oP2sD4"}}
        out = redact_obj(obj)
        assert out["env"]["ZOTERO_API_KEY"] == REDACTED
        assert "ZOTERO_API_KEY" in out["env"], "the name must stay visible"

    def test_sensitive_key_spares_numeric_and_non_string_values(self):
        """``tokens_used`` matches the sensitive-name pattern; it is a metric."""
        out = redact_obj({"tokens_used": 12345, "total_tokens_used": "678", "cost_usd": 0.5})
        assert out == {"tokens_used": 12345, "total_tokens_used": "678", "cost_usd": 0.5}

    def test_secret_used_as_a_key_is_redacted(self):
        """A credential can sit in a key. The text pass caught those; so must this."""
        out = redact_obj({"ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789": "some value"})
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in json.dumps(out)
        assert REDACTED in out


# --- The structured corpus -------------------------------------------------
# One literal per credential shape the module claims to catch, crossed with the
# positions a credential actually turns up in. The sidecar is redacted as data
# and serialised afterwards, so each case must come out both scrubbed and
# parseable — a regex over the serialised form fails one or the other.

TOKEN_SHAPES = {
    "gh-pat": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "gh-oauth": "gho_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "gh-user-server": "ghu_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "gh-server": "ghs_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "gh-refresh": "ghr_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "gh-fine-grained": "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz",
    "anthropic": "sk-ant-api03-abc123def456ghi789jkl012mno345",
    "openai": "sk-abcdefghijklmnopqrstuvwxyz0123456789ABCDEF",
    "tailscale": "tskey-auth-k1A2b3C4d5E6f7",
    "aws-access-key-id": "AKIAIOSFODNN7EXAMPLE",
    "slack": "xoxb-1234567890-ABCDEFGHIJKLMNOP",
    "google": "AIzaSyD-1234567890abcdefghijklmnopqrstuvw",
    "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4",
}

# Opaque values no shape can recognise; only a sensitive *name* gives them away.
NAMED_SHAPES = {
    "ZOTERO_API_KEY": "aB3xY9zQ1wE7rT5uI8oP2sD4",
    "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI1K7MDENGbPxRfiCYEXAMPLEKEY",
    "MY_PASSWORD": "hunter2correcthorsebattery",
    "SUDO_PASSWD": "opaquePasswdValue890123",
    "TAILSCALE_AUTHKEY": "opaqueAuthkeyValue567890",
    "CI_AUTH_TOKEN": "opaqueAuthTokenValue4567",
    "DB_CREDENTIAL": "opaqueCredentialValue123",
    "DEPLOY_PRIVATE_KEY": "MIIEpAIBAAKCAQEA0Zf9opaque",
    "AZURE_ACCESS_KEY": "opaqueAccessKeyValue7890",
    "OIDC_CLIENT_SECRET": "Kj3n2LmQpXvR8sT1uW4yZ7aB",
    "GITLAB_OAUTH": "opaqueOauthValue4567890a",
    "HTTP_BEARER": "OpaqueBearerValue9781234",
}

# position name -> builds a fragment holding one token-shaped secret
TOKEN_POSITIONS = {
    "inside-a-value": lambda s: {"insights": f"the runner printed {s} before failing"},
    "whole-value": lambda s: {"note": s},
    "adjacent-to-escapes": lambda s: {"text": f'API_TOKEN="{s}"'},
    "env-dump-line": lambda s: {"text": f"$ env\nHOME=/Users/suzor\nGH_TOKEN={s}\nEDITOR=vim\n"},
    "embedded-json": lambda s: {"text": f'tool args: {{"api_key": "{s}"}}'},
    "nested-deep": lambda s: {"subagents": [{"notes": [{"deep": {"d": [f"left {s} here"]}}]}]},
    "in-a-key": lambda s: {"keys": {s: "a value"}},
    "list-item": lambda s: {"items": ["ok", s]},
}

# position name -> builds a fragment holding one name-identified secret
NAMED_POSITIONS = {
    "shell-assignment": lambda name, s: {"text": f"$ export {name}={s}\n"},
    "shell-assignment-quoted": lambda name, s: {"text": f'{name}="{s}"\n'},
    "yaml-inside-a-value": lambda name, s: {"text": f"config:\n  {name}: {s}\n"},
    "json-inside-a-value": lambda name, s: {"text": f'{{"{name}": "{s}"}}'},
    "spanning-the-boundary": lambda name, s: {name: s},
    "spanning-a-nested-boundary": lambda name, s: {"cfg": {"env": {name: s}}},
}


class TestStructuredCorpus:
    """Every shape, in every position, redacted *and* still parseable."""

    @pytest.mark.parametrize("position", sorted(TOKEN_POSITIONS))
    def test_token_shapes(self, position: str):
        place = TOKEN_POSITIONS[position]
        obj = {"cases": [place(secret) for secret in TOKEN_SHAPES.values()]}
        blob = json.dumps(redact_obj(obj), indent=2)
        json.loads(blob)  # structure survives redaction
        for label, secret in TOKEN_SHAPES.items():
            assert secret not in blob, f"{label} survived in position {position}"

    @pytest.mark.parametrize("position", sorted(NAMED_POSITIONS))
    def test_named_shapes(self, position: str):
        place = NAMED_POSITIONS[position]
        obj = {"cases": [place(name, secret) for name, secret in NAMED_SHAPES.items()]}
        blob = json.dumps(redact_obj(obj), indent=2)
        json.loads(blob)
        for name, secret in NAMED_SHAPES.items():
            assert secret not in blob, f"{name} survived in position {position}"

    def test_benign_content_survives(self):
        """Over-redaction is not free: the transcript has to stay worth reading."""
        text = (
            "$ env\nHOME=/Users/suzor\nEDITOR=vim\nPATH=/usr/bin:/bin\nMAX_TOKENS=4096\n"
            "stats:\n  input_tokens: 12345\n  duration_minutes: 3.4\n"
        )
        out = redact_obj({"text": text})["text"]
        for benign in ("HOME=/Users/suzor", "EDITOR=vim", "PATH=/usr/bin:/bin", "MAX_TOKENS=4096"):
            assert benign in out, f"{benign!r} was destroyed by redaction"
        assert "input_tokens: 12345" in out


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
            # The sidecar reaches the chokepoint as data, not text.
            lambda *a, **k: (poisoned, poisoned, {"user_prompts": [{"text": poisoned}]}),
        )
        monkeypatch.setattr(runner, "render_to_full_markdown", lambda *a, **k: poisoned)
        monkeypatch.setattr(Path, "write_text", _fake_write_text)

        runner.process_single_session(_stub_session(), tmp_path, _NeverSkipCache(), force=True)

        assert written, "no artifacts were written; the wiring test proved nothing"
        assert len(written) == 4, f"expected 4 artifacts, saw {sorted(written)}"
        for name, content in written.items():
            for leaked in LEAKED_VALUES:
                assert leaked not in content, f"{leaked!r} leaked into {name}"
            assert REDACTED in content, f"{name} was written without any redaction"

    def test_sidecar_stays_parseable_through_redaction(self, tmp_path: Path):
        """The corrupting case, end to end and on real bytes.

        A prompt reading ``GH_TOKEN = os.environ.get("GH_TOKEN")`` used to have
        its escaped quote eaten by the redaction regex, which then re-emitted a
        bare ``"`` — terminating the JSON string and leaving a sidecar nothing
        could parse, and no signal that it had happened.
        """
        from transcripts import runner

        session = _stub_session(content='GH_TOKEN = os.environ.get("GH_TOKEN")')
        runner.process_single_session(session, tmp_path, _NeverSkipCache(), force=True)

        sidecars = list(tmp_path.glob("transcripts/**/*.json"))
        assert len(sidecars) == 1, f"expected one sidecar, found {sidecars}"
        raw = sidecars[0].read_text(encoding="utf-8")
        data = json.loads(raw)  # the assertion that used to fail
        assert data["user_prompts"][0]["text"].startswith("GH_TOKEN = ")
        assert REDACTED in raw, "the case must still be redacted, not merely parseable"

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


class TestLedgerReportsUnreadableSidecars:
    """A sidecar that will not parse is a session missing from the ledger.

    It used to be swallowed by a bare ``except: continue``, so an affected
    session vanished with no signal anywhere.
    """

    def _stage(self, tmp_path: Path) -> Path:
        sidecar_dir = tmp_path / "transcripts" / "2026-07"
        sidecar_dir.mkdir(parents=True)
        (sidecar_dir / "20260701-10-aops-good.json").write_text(
            json.dumps(
                {
                    "session_id": "deadbeefcafe",
                    "project": "aops",
                    "has_user_context": True,
                    "started_at": "2026-07-01T10:00:00+00:00",
                    "user_prompts": [
                        {"text": "a real prompt", "timestamp": "2026-07-01T10:00:00+00:00"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        # The shape the redaction bug produced: a bare quote ends the string early.
        (sidecar_dir / "20260701-11-aops-broken.json").write_text(
            '{"user_prompts": [{"text": "GH_TOKEN = [REDACTED]"GH_TOKEN\\")"}]}',
            encoding="utf-8",
        )
        return sidecar_dir

    def test_failure_is_logged_named_and_returned(self, tmp_path: Path, caplog):
        from transcripts.domain.ledger import generate_prompt_ledger

        self._stage(tmp_path)
        with caplog.at_level("ERROR"):
            status = generate_prompt_ledger(tmp_path, "2026-06-01")

        assert status == 1, "an incomplete ledger must not report success"
        assert any("20260701-11-aops-broken.json" in r.getMessage() for r in caplog.records), (
            "the unreadable sidecar was not logged"
        )

        content = (tmp_path / "state" / "prompt_ledger.md").read_text(encoding="utf-8")
        assert "20260701-11-aops-broken.json" in content, (
            "the ledger does not admit it is incomplete"
        )
        # The readable sessions still make it through: one bad file must not
        # cost every other session its row.
        assert "deadbeef" in content


class _NeverSkipCache:
    """Minimal SkipCache stand-in: never skips, records nothing."""

    def is_skipped(self, key: str, fingerprint: str) -> bool:
        return False

    def mark_empty(self, key: str, fingerprint: str) -> None:
        return None

    def forget(self, key: str) -> None:
        return None


def _stub_session(content: str = "hello"):
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
                content=content,
            )
        ],
    )
