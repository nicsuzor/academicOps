"""Tests for lib/host_secrets — env-only forwarded-secret resolution.

The polecat launcher resolves forwarded secret VALUES from the PROCESS
ENVIRONMENT ONLY. AOPS reads no files (no sops, no ~/.env.local); populating
the environment is the operator's responsibility. Required secrets fail loud
when absent. Source-name aliasing is a pure name map within the process env.
Hard assertions only.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aops-core"))

from lib.host_secrets import (  # noqa: E402
    MissingForwardSecretError,
    resolve_forward_values,
)


class TestResolveFromProcessEnv:
    """Values resolve from the process env (source_env) only."""

    def test_resolves_from_source_env(self):
        resolved = resolve_forward_values(
            ["GEMINI_API_KEY"],
            source_env={"GEMINI_API_KEY": "gem-from-env"},
        )
        assert resolved == {"GEMINI_API_KEY": "gem-from-env"}

    def test_defaults_to_os_environ(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gem-from-os-environ")
        resolved = resolve_forward_values(["GEMINI_API_KEY"])
        assert resolved["GEMINI_API_KEY"] == "gem-from-os-environ"

    def test_only_whitelisted_names_resolved(self):
        resolved = resolve_forward_values(
            ["WANTED"],
            source_env={"WANTED": "yes", "UNWANTED": "no"},
        )
        assert resolved == {"WANTED": "yes"}

    def test_no_file_reading_attribute(self):
        # The module must not expose any file-reading seam anymore.
        import lib.host_secrets as hs

        for gone in (
            "load_host_secrets",
            "_load_sops_secrets",
            "_DEFAULT_SOPS_SECRETS",
            "_DEFAULT_ENV_LOCAL",
        ):
            assert not hasattr(hs, gone), f"{gone} should be removed"


class TestOptionalAbsentSkipped:
    """Names NOT declared required and absent/empty are simply omitted."""

    def test_empty_value_skipped_when_not_required(self):
        resolved = resolve_forward_values(
            ["EMPTY_TOK", "ABSENT_TOK"],
            source_env={"EMPTY_TOK": ""},
        )
        assert "EMPTY_TOK" not in resolved
        assert "ABSENT_TOK" not in resolved

    def test_absent_optional_returns_empty_dict_no_raise(self):
        # No required set → no raise even when nothing resolves.
        assert resolve_forward_values(["ABSENT"], source_env={}) == {}


class TestRequiredFailsLoud:
    """A REQUIRED forwarded secret that resolves empty/absent must raise,
    naming the missing var(s). No silent empty/fallback."""

    def test_missing_required_raises_naming_var(self):
        with pytest.raises(MissingForwardSecretError) as excinfo:
            resolve_forward_values(
                ["GEMINI_API_KEY"],
                source_env={},
                required=["GEMINI_API_KEY"],
            )
        assert "GEMINI_API_KEY" in str(excinfo.value)
        assert excinfo.value.missing == ["GEMINI_API_KEY"]

    def test_empty_required_raises(self):
        with pytest.raises(MissingForwardSecretError) as excinfo:
            resolve_forward_values(
                ["GEMINI_API_KEY"],
                source_env={"GEMINI_API_KEY": ""},
                required=["GEMINI_API_KEY"],
            )
        assert "GEMINI_API_KEY" in str(excinfo.value)

    def test_multiple_missing_required_all_named(self):
        with pytest.raises(MissingForwardSecretError) as excinfo:
            resolve_forward_values(
                ["GEMINI_API_KEY", "AGY_API_KEY"],
                source_env={},
                required=["GEMINI_API_KEY", "AGY_API_KEY"],
            )
        msg = str(excinfo.value)
        assert "GEMINI_API_KEY" in msg
        assert "AGY_API_KEY" in msg
        assert set(excinfo.value.missing) == {"GEMINI_API_KEY", "AGY_API_KEY"}

    def test_present_required_does_not_raise(self):
        resolved = resolve_forward_values(
            ["GEMINI_API_KEY"],
            source_env={"GEMINI_API_KEY": "present"},
            required=["GEMINI_API_KEY"],
        )
        assert resolved == {"GEMINI_API_KEY": "present"}

    def test_required_satisfied_via_alias_source(self):
        # A required name satisfied through its alias source must NOT raise.
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"AOPS_CC_OAUTH_TOKEN": "tok-aops"},
            required=["CLAUDE_CODE_OAUTH_TOKEN"],
        )
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-aops"}

    def test_optional_missing_alongside_required_present(self):
        # Optional absent name is skipped; required present name resolves.
        resolved = resolve_forward_values(
            ["GEMINI_API_KEY", "AGY_API_KEY"],
            source_env={"GEMINI_API_KEY": "gem"},
            required=["GEMINI_API_KEY"],
        )
        assert resolved == {"GEMINI_API_KEY": "gem"}


class TestForwardSourceAliases:
    """Source-name indirection: the Claude OAuth token is sourced from
    AOPS_CC_OAUTH_TOKEN in the process env but injected under the official
    container name CLAUDE_CODE_OAUTH_TOKEN (aops-b368109a — leak closed at the
    agent). This is a pure NAME map within the process env — no file fallback."""

    def test_claude_token_sourced_from_aops_alias(self):
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"AOPS_CC_OAUTH_TOKEN": "tok-aops"},
        )
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-aops"}

    def test_official_name_is_transitional_fallback(self):
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={"CLAUDE_CODE_OAUTH_TOKEN": "tok-official"},
        )
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-official"}

    def test_alias_source_wins_over_official_name(self):
        resolved = resolve_forward_values(
            ["CLAUDE_CODE_OAUTH_TOKEN"],
            source_env={
                "AOPS_CC_OAUTH_TOKEN": "tok-aops",
                "CLAUDE_CODE_OAUTH_TOKEN": "tok-official",
            },
        )
        assert resolved == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-aops"}

    def test_unaliased_name_unaffected(self):
        resolved = resolve_forward_values(
            ["GEMINI_API_KEY"],
            source_env={"GEMINI_API_KEY": "gk"},
        )
        assert resolved == {"GEMINI_API_KEY": "gk"}


class TestForwardSourceAliasesGHToken:
    """GH_TOKEN and GITHUB_TOKEN are sourced from AOPS_BOT_GH_TOKEN in the
    process env but injected under their standard names (gh CLI / git)."""

    def test_gh_token_sourced_from_aops_bot(self):
        resolved = resolve_forward_values(
            ["GH_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_bot"},
        )
        assert resolved == {"GH_TOKEN": "ghp_bot"}

    def test_github_token_sourced_from_aops_bot(self):
        resolved = resolve_forward_values(
            ["GITHUB_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_bot"},
        )
        assert resolved == {"GITHUB_TOKEN": "ghp_bot"}

    def test_aops_bot_alias_wins_over_direct_name(self):
        resolved = resolve_forward_values(
            ["GH_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_aops", "GH_TOKEN": "ghp_direct"},
        )
        assert resolved == {"GH_TOKEN": "ghp_aops"}

    def test_gh_token_fallback_to_direct_name(self):
        resolved = resolve_forward_values(
            ["GH_TOKEN"],
            source_env={"GH_TOKEN": "ghp_direct"},
        )
        assert resolved == {"GH_TOKEN": "ghp_direct"}

    def test_both_gh_names_resolve_from_single_alias(self):
        resolved = resolve_forward_values(
            ["GH_TOKEN", "GITHUB_TOKEN"],
            source_env={"AOPS_BOT_GH_TOKEN": "ghp_one"},
        )
        assert resolved == {"GH_TOKEN": "ghp_one", "GITHUB_TOKEN": "ghp_one"}
