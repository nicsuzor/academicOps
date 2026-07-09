"""Tests for polecat/entrypoint.sh's PKB_MCP_URL -> settings.json seeding.

Pins the seeded plugin key to aops-pkb@academicOps, the plugin that actually
declares `userConfig.pkb_mcp_url` for the Claude platform. Regression coverage
for the entrypoint seeding the pre-migration aops-core@academicOps key after
pkb's userConfig moved to aops-pkb (mcp.json.template / plugin.json).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
ENTRYPOINT = REPO_ROOT / "polecat" / "entrypoint.sh"


def _extract_seed_script() -> str:
    """Pull the embedded python3 heredoc that seeds pkb_mcp_url into settings.json."""
    text = ENTRYPOINT.read_text()
    match = re.search(r"python3 - <<'PY'\n(.*?)\nPY", text, re.DOTALL)
    assert match, "entrypoint.sh no longer has the expected python3 heredoc for pkb_mcp_url seeding"
    return match.group(1)


def test_seeds_aops_pkb_plugin_key(tmp_path):
    settings = tmp_path / "settings.json"
    result = subprocess.run(
        [sys.executable, "-c", _extract_seed_script()],
        env={"PKB_MCP_URL": "http://example.test/mcp", "SETTINGS": str(settings)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    data = json.loads(settings.read_text())
    assert data["pluginConfigs"]["aops-pkb@academicOps"]["options"]["pkb_mcp_url"] == (
        "http://example.test/mcp"
    )
    assert "aops-core@academicOps" not in data.get("pluginConfigs", {})


def test_preserves_existing_settings(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"otherKey": "keep-me"}))

    result = subprocess.run(
        [sys.executable, "-c", _extract_seed_script()],
        env={"PKB_MCP_URL": "http://example.test/mcp", "SETTINGS": str(settings)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    data = json.loads(settings.read_text())
    assert data["otherKey"] == "keep-me"
    assert data["pluginConfigs"]["aops-pkb@academicOps"]["options"]["pkb_mcp_url"] == (
        "http://example.test/mcp"
    )
