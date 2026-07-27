"""Regression tests for polecat/cli.py setup_staging()'s Gemini settings handling.

setup_staging() used to copy the host's ~/.gemini/settings.json (and
~/.gemini/antigravity-cli/settings.json) verbatim into every container,
leaking live mcpServers API keys, internal-only URLs, and host hook
command paths to every polecat worker. It must now
regenerate a minimal, secret-free settings.json instead.
"""

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PLUGINS_DIR = str(_REPO_ROOT / "plugins")
if _PLUGINS_DIR not in sys.path:
    sys.path.insert(0, _PLUGINS_DIR)

from aops.polecat.cli import setup_staging  # noqa: E402

LEAKED_API_KEY = "sk-live-totally-secret-context7-key"
LEAKED_INTERNAL_URL = "https://internal-tailscale-only.example/mcp"
LEAKED_HOOK_PATH = "/home/nic/.gemini/hooks/rtk-hook-gemini.sh"
LEAKED_HOST_PROJECT_PATH = "/home/nic/src/some-other-private-project"


@pytest.fixture
def fake_gemini_home(tmp_path):
    """A fake $POLECAT_AGENT_HOME containing exactly the shape that leaked live."""
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


def test_antigravity_settings_regenerated_without_secrets(fake_gemini_home, tmp_path):
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    setup_staging(str(staging_dir), None, str(fake_gemini_home))

    staged_raw = (staging_dir / ".gemini" / "antigravity-cli" / "settings.json").read_text()
    assert LEAKED_INTERNAL_URL not in staged_raw
    assert LEAKED_HOST_PROJECT_PATH not in staged_raw

    staged = json.loads(staged_raw)
    assert "mcpServers" not in staged
    assert staged["trustedWorkspaces"] == ["/workspace"]


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
