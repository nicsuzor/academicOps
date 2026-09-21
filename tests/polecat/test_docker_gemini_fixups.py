"""Tests for lib/polecat/defaults/docker_gemini_fixups.py's
fixup_mcp_config_paths, specifically the YOUR_PKB_URL substitution added for
aops_agy_services_mcp_fix.

Baseline: the agy client's pkb `services` server ships the literal
placeholder text `YOUR_PKB_URL` (plugins/pkb/manifest/mcp.template.json),
baked in at `docker build` time before $PKB_MCP_URL is known. This module's
fixup_mcp_config_paths is invoked once at image-build time (to resolve
${extensionPath}/${CLAUDE_PLUGIN_ROOT}) and a second time by entrypoint.sh at
container start, once $PKB_MCP_URL is set in the container's own
environment -- that second call is what has to resolve YOUR_PKB_URL.
"""

import importlib.util
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXUPS_PATH = _REPO_ROOT / "lib" / "polecat" / "defaults" / "docker_gemini_fixups.py"


def _load_fixups_module(gemini_home: Path):
    spec = importlib.util.spec_from_file_location("docker_gemini_fixups", _FIXUPS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GEMINI_HOME = gemini_home
    return module


def _write_mcp_config(gemini_home: Path, plugin_name: str, url_placeholder: str) -> Path:
    plugin_dir = gemini_home / "config" / "plugins" / plugin_name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    mcp_file = plugin_dir / "mcp_config.json"
    # The shape plugins/pkb/manifest/mcp.template.json ships for agy: a remote
    # `serverUrl`, never a stdio launcher (which registers no tools under agy).
    mcp_file.write_text(json.dumps({"mcpServers": {"services": {"serverUrl": url_placeholder}}}))
    return mcp_file


def test_pkb_mcp_url_env_var_resolves_the_placeholder(tmp_path, monkeypatch):
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.ts.net/mcp")
    gemini_home = tmp_path / ".gemini"
    mcp_file = _write_mcp_config(gemini_home, "pkb", "YOUR_PKB_URL")

    module = _load_fixups_module(gemini_home)
    module.fixup_mcp_config_paths()

    data = json.loads(mcp_file.read_text())
    assert data["mcpServers"]["services"] == {"serverUrl": "https://pkb.example.ts.net/mcp"}


def test_pkb_mcp_url_env_var_resolves_braced_placeholder(tmp_path, monkeypatch):
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.ts.net/mcp")
    gemini_home = tmp_path / ".gemini"
    mcp_file = _write_mcp_config(gemini_home, "pkb", "${PKB_MCP_URL}")

    module = _load_fixups_module(gemini_home)
    module.fixup_mcp_config_paths()

    data = json.loads(mcp_file.read_text())
    assert data["mcpServers"]["services"] == {"serverUrl": "https://pkb.example.ts.net/mcp"}


def test_trailing_slash_is_stripped(tmp_path, monkeypatch):
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.ts.net/mcp/")
    gemini_home = tmp_path / ".gemini"
    mcp_file = _write_mcp_config(gemini_home, "pkb", "YOUR_PKB_URL")

    module = _load_fixups_module(gemini_home)
    module.fixup_mcp_config_paths()

    data = json.loads(mcp_file.read_text())
    assert data["mcpServers"]["services"] == {"serverUrl": "https://pkb.example.ts.net/mcp"}


def test_unset_pkb_mcp_url_leaves_the_placeholder_in_place(tmp_path, monkeypatch):
    """No $PKB_MCP_URL (a --no-pkb dispatch) is a no-op, not a failure --
    matching build.install.patch_agy_mcp's own behaviour."""
    monkeypatch.delenv("PKB_MCP_URL", raising=False)
    gemini_home = tmp_path / ".gemini"
    mcp_file = _write_mcp_config(gemini_home, "pkb", "YOUR_PKB_URL")
    before = mcp_file.read_text()

    module = _load_fixups_module(gemini_home)
    module.fixup_mcp_config_paths()

    assert mcp_file.read_text() == before
    assert "YOUR_PKB_URL" in mcp_file.read_text()


def test_extension_path_substitution_still_works_alongside_pkb_url(tmp_path, monkeypatch):
    """The pre-existing ${extensionPath}/${CLAUDE_PLUGIN_ROOT} rewrite is
    unaffected by the new PKB_MCP_URL substitution added alongside it."""
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.ts.net/mcp")
    gemini_home = tmp_path / ".gemini"
    plugin_dir = gemini_home / "config" / "plugins" / "other"
    plugin_dir.mkdir(parents=True)
    mcp_file = plugin_dir / "mcp_config.json"
    mcp_file.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "svc": {"command": "bash", "args": ["${extensionPath}/scripts/run.sh"]}
                }
            }
        )
    )

    module = _load_fixups_module(gemini_home)
    module.fixup_mcp_config_paths()

    data = json.loads(mcp_file.read_text())
    assert data["mcpServers"]["svc"]["args"] == [f"{plugin_dir}/scripts/run.sh"]


def test_no_pkb_url_substitution_when_placeholder_absent(tmp_path, monkeypatch):
    """A server that never had YOUR_PKB_URL (e.g. claude's own
    ${user_config.pkb_mcp_url} form) is left untouched by this substitution."""
    monkeypatch.setenv("PKB_MCP_URL", "https://pkb.example.ts.net/mcp")
    gemini_home = tmp_path / ".gemini"
    mcp_file = _write_mcp_config(gemini_home, "pkb", "${user_config.pkb_mcp_url}")
    before = mcp_file.read_text()

    module = _load_fixups_module(gemini_home)
    module.fixup_mcp_config_paths()

    assert mcp_file.read_text() == before
