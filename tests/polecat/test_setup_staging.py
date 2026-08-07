"""Regression tests for polecat/cli.py setup_staging().

Two defects are covered here.

Gemini settings: setup_staging() used to copy the host's ~/.gemini/settings.json
(and ~/.gemini/antigravity-cli/settings.json) verbatim into every container,
leaking live mcpServers API keys, internal-only URLs, and host hook command
paths to every polecat worker. It must now regenerate a minimal, secret-free
settings.json instead.

Plugin config: the PKB MCP URL used to be staged under `aops@academicOps`,
but `pkb_mcp_url` is declared by the aops-pkb plugin. Claude Code drops an
option staged under a plugin that does not declare it, so every containerised
session came up with an unset PKB URL and no reachable knowledge base.
"""

import json
from pathlib import Path

import pytest

from lib.polecat.cli import setup_staging

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MCP_URL = "https://pkb.example/mcp"

LEAKED_API_KEY = "sk-live-totally-secret-context7-key"
LEAKED_INTERNAL_URL = "https://internal-tailscale-only.example/mcp"
LEAKED_HOOK_PATH = "/home/nic/.gemini/hooks/rtk-hook-gemini.sh"
LEAKED_HOST_PROJECT_PATH = "/home/nic/src/some-other-private-project"


@pytest.fixture
def fake_gemini_home(tmp_path):
    """A fake $GEMINI_CONFIG_DIR containing exactly the shape that leaked live."""
    home = tmp_path / "fake_home"
    gemini = home / ".gemini"
    gemini.mkdir(parents=True)

    (gemini / "settings.json").write_text(
        json.dumps(
            {
                "security": {"auth": {"selectedType": "oauth-personal"}},
                "hooks": {
                    "BeforeTool": [{"hooks": [{"command": LEAKED_HOOK_PATH}]}],
                },
                "mcpServers": {
                    "context7": {
                        "httpUrl": "https://context7.example/mcp",
                        "headers": {"CONTEXT7_API_KEY": LEAKED_API_KEY},
                    },
                    "home": {"httpUrl": LEAKED_INTERNAL_URL},
                },
            }
        )
    )
    (gemini / "google_accounts.json").write_text('{"account": "user@example.com"}')
    (gemini / "oauth_creds.json").write_text('{"access_token": "fake-oauth-token"}')
    (gemini / "installation_id").write_text("fake-installation-id")

    agy = gemini / "antigravity-cli"
    agy.mkdir()
    (agy / "settings.json").write_text(
        json.dumps(
            {
                "mcpServers": {"context7": {"type": "http", "url": LEAKED_INTERNAL_URL}},
                "trustedWorkspaces": [LEAKED_HOST_PROJECT_PATH, "/workspace"],
                "model": "some-personal-model-choice",
            }
        )
    )
    (agy / "antigravity-oauth-token").write_text("fake-agy-oauth-token")
    (agy / "installation_id").write_text("fake-agy-installation-id")

    return gemini


def test_gemini_settings_regenerated_without_secrets(fake_gemini_home, tmp_path):
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    setup_staging(str(staging_dir), None, str(fake_gemini_home))

    staged_raw = (staging_dir / ".gemini" / "settings.json").read_text()
    assert LEAKED_API_KEY not in staged_raw
    assert LEAKED_INTERNAL_URL not in staged_raw
    assert LEAKED_HOOK_PATH not in staged_raw

    staged = json.loads(staged_raw)
    assert "mcpServers" not in staged
    assert "hooks" not in staged
    assert staged["security"]["auth"]["selectedType"] == "oauth-personal"


def test_antigravity_settings_not_created_in_staging(fake_gemini_home, tmp_path):
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    setup_staging(str(staging_dir), None, str(fake_gemini_home))

    assert not (staging_dir / ".gemini" / "antigravity-cli" / "settings.json").exists()


def _plugin_declaring(option):
    """The plugin whose manifest declares `option` under claude userConfig."""
    declaring = [
        json.loads(manifest.read_text())
        for manifest in sorted(_REPO_ROOT.glob("plugins/*/manifest/plugin.template.json"))
    ]
    names = [
        m["clients"]["__base__"]["name"]
        for m in declaring
        if option in (m["clients"].get("claude", {}).get("userConfig") or {})
    ]
    assert len(names) == 1, f"expected exactly one plugin to declare {option}, got {names}"
    return names[0]


def test_pkb_url_staged_under_the_plugin_that_declares_it(tmp_path):
    """The staged key must name the plugin whose userConfig declares
    `pkb_mcp_url`. Under any other key Claude Code ignores the option and the
    container has no PKB URL at all."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    setup_staging(str(staging_dir), MCP_URL, None)

    settings = json.loads((staging_dir / ".claude" / "settings.json").read_text())
    expected_key = f"{_plugin_declaring('pkb_mcp_url')}@academicOps"

    assert list(settings["pluginConfigs"]) == [expected_key]
    assert settings["pluginConfigs"][expected_key]["options"]["pkb_mcp_url"] == MCP_URL


def test_no_settings_file_staged_without_an_mcp_url(tmp_path, monkeypatch):
    """Absent a URL there is nothing to configure — staging an empty
    pluginConfigs block would assert a config the operator never gave."""
    monkeypatch.delenv("POLECAT_WORKER_MODEL", raising=False)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    setup_staging(str(staging_dir), None, None)

    assert not (staging_dir / ".claude" / "settings.json").exists()


def test_credential_files_still_replicated(fake_gemini_home, tmp_path):
    """The fix only touches settings.json content — credential files must
    still be staged so agy/gemini auth keeps working in the container."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    setup_staging(str(staging_dir), None, str(fake_gemini_home))

    gemini_dst = staging_dir / ".gemini"
    assert (gemini_dst / "oauth_creds.json").read_text() == '{"access_token": "fake-oauth-token"}'
    assert (gemini_dst / "google_accounts.json").exists()
    assert (gemini_dst / "installation_id").read_text() == "fake-installation-id"
    assert (
        gemini_dst / "antigravity-cli" / "antigravity-oauth-token"
    ).read_text() == "fake-agy-oauth-token"
    assert (
        gemini_dst / "antigravity-cli" / "installation_id"
    ).read_text() == "fake-agy-installation-id"
