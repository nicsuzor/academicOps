"""Tests for lib/host_secrets — host secret-store loader for polecat launch.

Covers the env-var standardisation Q2 contract: the polecat launcher resolves
forwarded secret VALUES from ~/.env.local *independent* of the launching
session's env. Hard assertions only.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aops-core"))

from lib.host_secrets import (  # noqa: E402
    _load_sops_secrets,
    load_host_secrets,
    resolve_forward_values,
)


class TestLoadSopsSecrets:
    """Tests for _load_sops_secrets — in-memory sops/age decrypt seam."""

    def test_returns_empty_when_file_missing(self, tmp_path):
        missing = tmp_path / "aops-secrets.env"
        assert _load_sops_secrets(missing) == {}

    def test_returns_empty_when_sops_not_installed(self, tmp_path):
        f = tmp_path / "aops-secrets.env"
        f.write_text("AOPS_BOT_GH_TOKEN=ENC[...]\n")
        with patch("lib.host_secrets.subprocess.run", side_effect=FileNotFoundError):
            assert _load_sops_secrets(f) == {}

    def test_returns_empty_when_sops_fails(self, tmp_path):
        f = tmp_path / "aops-secrets.env"
        f.write_text("AOPS_BOT_GH_TOKEN=ENC[...]\n")
        with patch("lib.host_secrets.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "sops", stderr="bad key")
            assert _load_sops_secrets(f) == {}

    def test_parses_sops_decrypted_output(self, tmp_path):
        f = tmp_path / "aops-secrets.env"
        f.write_text("placeholder")
        decrypted_output = (
            "AOPS_BOT_GH_TOKEN=ghp_decrypted\n"
            "AOPS_CC_OAUTH_TOKEN=sk-oauth-decrypted\n"
            "GEMINI_API_KEY=gem_decrypted\n"
        )
        with patch("lib.host_secrets.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=decrypted_output, returncode=0)
            result = _load_sops_secrets(f)
        assert result["AOPS_BOT_GH_TOKEN"] == "ghp_decrypted"
        assert result["AOPS_CC_OAUTH_TOKEN"] == "sk-oauth-decrypted"
        assert result["GEMINI_API_KEY"] == "gem_decrypted"

    def test_calls_sops_with_correct_args(self, tmp_path):
        f = tmp_path / "aops-secrets.env"
        f.write_text("placeholder")
        with patch("lib.host_secrets.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="KEY=val\n", returncode=0)
            _load_sops_secrets(f)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "sops"
        assert cmd[1] == "-d"
        assert cmd[2] == str(f)

    def test_override_via_aops_sops_secrets_file(self, tmp_path, monkeypatch):
        f = tmp_path / "custom-secrets.env"
        f.write_text("placeholder")
        monkeypatch.setenv("AOPS_SOPS_SECRETS_FILE", str(f))
        with patch("lib.host_secrets.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="OVERRIDE=yes\n", returncode=0)
            result = _load_sops_secrets()
        assert result["OVERRIDE"] == "yes"


class TestLoadHostSecretsMerge:
    """Tests for the two-tier merge: sops SSoT wins over ~/.env.local."""

    def test_sops_wins_on_conflict(self, tmp_path):
        env_local = tmp_path / ".env.local"
        env_local.write_text("AOPS_BOT_GH_TOKEN=old-value\n")
        sops_file = tmp_path / "aops-secrets.env"
        sops_file.write_text("placeholder")
        with patch("lib.host_secrets.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="AOPS_BOT_GH_TOKEN=new-from-sops\n", returncode=0
            )
            result = load_host_secrets(env_file=env_local, sops_file=sops_file)
        assert result["AOPS_BOT_GH_TOKEN"] == "new-from-sops"

    def test_env_local_fills_gaps_when_key_absent_from_sops(self, tmp_path):
        env_local = tmp_path / ".env.local"
        env_local.write_text("GEMINI_API_KEY=gem-from-env-local\n")
        sops_file = tmp_path / "aops-secrets.env"
        sops_file.write_text("placeholder")
        with patch("lib.host_secrets.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="AOPS_BOT_GH_TOKEN=ghp-from-sops\n", returncode=0
            )
            result = load_host_secrets(env_file=env_local, sops_file=sops_file)
        assert result["AOPS_BOT_GH_TOKEN"] == "ghp-from-sops"
        assert result["GEMINI_API_KEY"] == "gem-from-env-local"

    def test_env_local_fallback_when_sops_unavailable(self, tmp_path):
        env_local = tmp_path / ".env.local"
        env_local.write_text("AOPS_BOT_GH_TOKEN=from-env-local\n")
        missing_sops = tmp_path / "absent.env"
        result = load_host_secrets(env_file=env_local, sops_file=missing_sops)
        assert result["AOPS_BOT_GH_TOKEN"] == "from-env-local"

    def test_both_sources_absent_returns_empty(self, tmp_path):
        result = load_host_secrets(
            env_file=tmp_path / "absent.env",
            sops_file=tmp_path / "absent-sops.env",
        )
        assert result == {}


class TestLoadHostSecrets:
    def test_parses_export_and_bare_assignments(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text(
            "export AOPS_BOT_GH_TOKEN=ghp_abc123\n"
            "GEMINI_API_KEY=gem_xyz\n"
            "# a comment\n"
            "\n"
            'export CLAUDE_CODE_OAUTH_TOKEN="sk-oauth-quoted"\n'
        )
        result = load_host_secrets(f)
        assert result["AOPS_BOT_GH_TOKEN"] == "ghp_abc123"
        assert result["GEMINI_API_KEY"] == "gem_xyz"
        assert result["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-oauth-quoted"

    def test_single_quotes_stripped(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("export TOK='value-with-#-hash'\n")
        result = load_host_secrets(f)
        # Inside quotes, # is literal (not a comment).
        assert result["TOK"] == "value-with-#-hash"

    def test_inline_comment_stripped_for_unquoted(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("export TOK=plainvalue  # trailing note\n")
        result = load_host_secrets(f)
        assert result["TOK"] == "plainvalue"

    def test_missing_file_returns_empty_dict_no_raise(self, tmp_path):
        # GHA runners have no ~/.env.local — must no-op gracefully.
        missing = tmp_path / "does-not-exist.env"
        assert load_host_secrets(missing) == {}

    def test_last_assignment_wins(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("TOK=first\nTOK=second\n")
        assert load_host_secrets(f)["TOK"] == "second"

    def test_env_file_override_via_aops_host_env_file(self, tmp_path, monkeypatch):
        f = tmp_path / "custom.env"
        f.write_text("OVERRIDE_VAR=present\n")
        monkeypatch.setenv("AOPS_HOST_ENV_FILE", str(f))
        result = load_host_secrets()  # no explicit path → uses env override
        assert result["OVERRIDE_VAR"] == "present"


class TestResolveForwardValues:
    def test_env_local_is_authoritative_over_process_env(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("CLAUDE_CODE_OAUTH_TOKEN=from-env-local\n")
        # Even if the process env carries a (stale) value, ~/.env.local wins.
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"CLAUDE_CODE_OAUTH_TOKEN": "from-process"},
            env_file=f,
        )
        assert resolved["CLAUDE_CODE_OAUTH_TOKEN"] == "from-env-local"

    def test_process_env_fallback_when_absent_from_env_local(self, tmp_path):
        # GHA surface: no ~/.env.local entry, secret arrives via process env.
        f = tmp_path / ".env.local"
        f.write_text("# empty\n")
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"CLAUDE_CODE_OAUTH_TOKEN": "from-actions-secret"},
            env_file=f,
        )
        assert resolved["CLAUDE_CODE_OAUTH_TOKEN"] == "from-actions-secret"

    def test_independent_of_session_env_when_not_in_source(self, tmp_path):
        # The whole point of Q2: the value comes from ~/.env.local even when the
        # launching session's env does NOT carry it at all.
        f = tmp_path / ".env.local"
        f.write_text("GEMINI_API_KEY=gem-from-disk\n")
        resolved = resolve_forward_values(
            ["GEMINI_API_KEY"],
            source_env={},  # session env carries nothing
            env_file=f,
        )
        assert resolved["GEMINI_API_KEY"] == "gem-from-disk"

    def test_empty_values_skipped(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("EMPTY_TOK=\n")
        resolved = resolve_forward_values(
            ["EMPTY_TOK", "ABSENT_TOK"],
            source_env={"EMPTY_TOK": ""},
            env_file=f,
        )
        assert "EMPTY_TOK" not in resolved
        assert "ABSENT_TOK" not in resolved

    def test_only_whitelisted_names_resolved(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("WANTED=yes\nUNWANTED=no\n")
        resolved = resolve_forward_values(["WANTED"], source_env={}, env_file=f)
        assert resolved == {"WANTED": "yes"}


class TestForwardSourceAliases:
    """Source-name indirection: the Claude OAuth token is sourced from
    AOPS_CC_OAUTH_TOKEN on the host but injected under the official container
    name CLAUDE_CODE_OAUTH_TOKEN (aops-b368109a — leak closed at the agent)."""

    def test_claude_token_sourced_from_aops_alias(self, tmp_path):
        """Official name absent from the source env → value comes from the alias."""
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"AOPS_CC_OAUTH_TOKEN": "tok-aops"},
            env_file=tmp_path / "absent",
        )
        # Keyed by the CONTAINER name, valued from the alias source.
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-aops"}

    def test_official_name_is_transitional_fallback(self, tmp_path):
        """Before the host var is renamed, the official name still resolves."""
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"CLAUDE_CODE_OAUTH_TOKEN": "tok-official"},
            env_file=tmp_path / "absent",
        )
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-official"}

    def test_alias_source_wins_over_official_name(self, tmp_path):
        """When both are present, the alias source takes precedence."""
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={
                "AOPS_CC_OAUTH_TOKEN": "tok-aops",
                "CLAUDE_CODE_OAUTH_TOKEN": "tok-official",
            },
            env_file=tmp_path / "absent",
        )
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-aops"}

    def test_alias_source_from_env_local(self, tmp_path):
        """The alias source is resolved from ~/.env.local too, not just process env."""
        f = tmp_path / ".env.local"
        f.write_text("AOPS_CC_OAUTH_TOKEN=tok-from-file\n")
        resolved = resolve_forward_values(["CLAUDE_CODE_OAUTH_TOKEN"], source_env={}, env_file=f)
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-from-file"}

    def test_unaliased_name_unaffected(self, tmp_path):
        """A name with no alias resolves from its own name as before."""
        resolved = resolve_forward_values(
            ["GEMINI_API_KEY"],
            source_env={"GEMINI_API_KEY": "gk"},
            env_file=tmp_path / "absent",
        )
        assert resolved == {"GEMINI_API_KEY": "gk"}


class TestForwardSourceAliasesGHToken:
    """GH_TOKEN and GITHUB_TOKEN are sourced from AOPS_BOT_GH_TOKEN on the host
    but injected under their standard names (gh CLI / git) in the container."""

    def test_gh_token_sourced_from_aops_bot(self, tmp_path):
        resolved = resolve_forward_values(
            ["GH_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_bot"},
            env_file=tmp_path / "absent",
        )
        assert resolved == {"GH_TOKEN": "ghp_bot"}

    def test_github_token_sourced_from_aops_bot(self, tmp_path):
        resolved = resolve_forward_values(
            ["GITHUB_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_bot"},
            env_file=tmp_path / "absent",
        )
        assert resolved == {"GITHUB_TOKEN": "ghp_bot"}

    def test_aops_bot_alias_wins_over_direct_name(self, tmp_path):
        resolved = resolve_forward_values(
            ["GH_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_aops", "GH_TOKEN": "ghp_direct"},
            env_file=tmp_path / "absent",
        )
        assert resolved == {"GH_TOKEN": "ghp_aops"}

    def test_gh_token_fallback_to_direct_name(self, tmp_path):
        """If only GH_TOKEN is present (no AOPS_BOT_GH_TOKEN), it still resolves."""
        resolved = resolve_forward_values(
            ["GH_TOKEN"],
            source_env={"GH_TOKEN": "ghp_direct"},
            env_file=tmp_path / "absent",
        )
        assert resolved == {"GH_TOKEN": "ghp_direct"}

    def test_alias_source_from_env_local(self, tmp_path):
        f = tmp_path / ".env.local"
        f.write_text("AOPS_BOT_GH_TOKEN=ghp_from_file\n")
        resolved = resolve_forward_values(["GH_TOKEN", "GITHUB_TOKEN"], source_env={}, env_file=f)
        assert resolved == {"GH_TOKEN": "ghp_from_file", "GITHUB_TOKEN": "ghp_from_file"}
