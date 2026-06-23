"""Tests for lib/host_secrets — env-only forwarded-secret resolution.

The polecat launcher resolves forwarded secret VALUES from the PROCESS
ENVIRONMENT ONLY. AOPS reads no files (no sops, no ~/.env.local); populating
the environment is the operator's responsibility. Resolution is
forward-if-present: absent/empty names are simply omitted, never raised.
Source-name aliasing is a pure name map within the process env.
Hard assertions only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aops-core"))

from lib.host_secrets import resolve_forward_values  # noqa: E402


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


class TestAbsentSkipped:
    """Absent/empty names are simply omitted — forward-if-present, never raise."""

    def test_empty_value_skipped(self):
        resolved = resolve_forward_values(
            ["EMPTY_TOK", "ABSENT_TOK"],
            source_env={"EMPTY_TOK": ""},
        )
        assert "EMPTY_TOK" not in resolved
        assert "ABSENT_TOK" not in resolved

    def test_all_absent_returns_empty_dict_no_raise(self):
        # Nothing resolves → empty dict, no raise.
        assert resolve_forward_values(["ABSENT"], source_env={}) == {}


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
