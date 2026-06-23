"""Tests for lib/env_provision — per-surface env-var provisioning contract.

Covers surface detection, the GHA-skip path, the host required-var check, and
the SUCCESS/FAILURE block rendering + secret redaction. Hard assertions only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aops-core"))

from lib.env_provision import (  # noqa: E402
    Surface,
    detect_surface,
    validate_surface,
)

# A complete host-required env (canonical minimum set).
_HOST_OK = {
    "AOPS_BOT_GH_TOKEN": "ghp_secretvalue1234",
    "ACA_DATA": "/home/nic/brain",
    "AOPS": "/home/nic/src/academicOps",
    "AOPS_SESSIONS": "/home/nic/.polecat/sessions",
    "PKB_MCP_URL": "http://services:8026/mcp",
}


class TestDetectSurface:
    def test_gha_detected_from_github_actions_true(self):
        assert detect_surface({"GITHUB_ACTIONS": "true"}) is Surface.GHA

    def test_host_is_default(self):
        assert detect_surface({}) is Surface.HOST

    def test_github_actions_not_true_is_host(self):
        # A literal other than "true" must NOT be treated as GHA.
        assert detect_surface({"GITHUB_ACTIONS": "false"}) is Surface.HOST


class TestGhaSurface:
    def test_gha_skips_required_check(self):
        # GHA with NONE of the host-required vars must still be ok+skipped.
        report = validate_surface({"GITHUB_ACTIONS": "true"})
        assert report.surface is Surface.GHA
        assert report.ok is True
        assert report.skipped is True
        assert report.missing == []
        assert any("provisioning skipped" in line for line in report.lines)


class TestHostSuccess:
    def test_all_present_is_ok_with_success_block(self):
        report = validate_surface(dict(_HOST_OK))
        assert report.surface is Surface.HOST
        assert report.ok is True
        assert report.missing == []
        joined = "\n".join(report.lines)
        assert "ENV OK" in joined

    def test_secrets_redacted_non_secrets_verbatim(self):
        report = validate_surface(dict(_HOST_OK))
        joined = "\n".join(report.lines)
        # Secret value must NOT appear in cleartext; redaction shows last 4.
        assert "ghp_secretvalue1234" not in joined
        assert "1234" in joined  # last-4 of the redacted secret
        # Non-secret path locator shown verbatim.
        assert "/home/nic/src/academicOps" in joined


class TestHostFailure:
    def test_missing_required_var_flags_failure_but_reports_missing(self):
        env = dict(_HOST_OK)
        del env["AOPS_BOT_GH_TOKEN"]
        report = validate_surface(env)
        assert report.ok is False
        assert "AOPS_BOT_GH_TOKEN" in report.missing
        joined = "\n".join(report.lines)
        assert "ENV INCOMPLETE" in joined
        # Env-only model (#1919): the fix is to export the missing var in the
        # environment — no ~/.env.local file is read or referenced.
        assert "~/.env.local" not in joined
        assert "export AOPS_BOT_GH_TOKEN=" in joined

    def test_oauth_tokens_not_required_on_host(self):
        # CLAUDE_CODE_OAUTH_TOKEN / GEMINI_API_KEY are hold-for-delegation,
        # NOT host-required — their absence must NOT cause a failure.
        env = dict(_HOST_OK)  # contains no OAuth tokens
        report = validate_surface(env)
        assert report.ok is True
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in report.missing
        assert "GEMINI_API_KEY" not in report.missing

    def test_multiple_missing_all_listed(self):
        env = dict(_HOST_OK)
        del env["ACA_DATA"]
        del env["PKB_MCP_URL"]
        report = validate_surface(env)
        assert report.ok is False
        assert set(report.missing) == {"ACA_DATA", "PKB_MCP_URL"}
