"""Unit tests for Docker Sandboxes (sbx) kits for Claude and Agy."""

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_claude_kit_spec_validity():
    """Claude kit spec.yaml exists, parses, and follows schemaVersion: '2'."""
    kit_file = _REPO_ROOT / "lib" / "kits" / "claude" / "spec.yaml"
    assert kit_file.is_file(), f"Claude kit not found at {kit_file}"

    data = yaml.safe_load(kit_file.read_text())
    assert data["schemaVersion"] == "2"
    assert data["kind"] == "sandbox"
    assert data["name"] == "claude"
    assert data["extends"] == "claude"

    # Command configuration
    assert "--dangerously-skip-permissions" in data["sandbox"]["command"]["default"]

    # Network permissions
    allow = data["permissions"]["network"]["allow"]
    assert "api.anthropic.com:443" in allow
    assert "github.com:443" in allow
    assert "pypi.org:443" in allow

    # Setup tools installation
    install_cmds = [item["command"] for item in data["setup"]["install"]]
    assert any("uv" in cmd for cmd in install_cmds)


def test_agy_kit_spec_validity():
    """Agy kit spec.yaml exists, parses, and follows schemaVersion: '2'."""
    kit_file = _REPO_ROOT / "lib" / "kits" / "agy" / "spec.yaml"
    assert kit_file.is_file(), f"Agy kit not found at {kit_file}"

    data = yaml.safe_load(kit_file.read_text())
    assert data["schemaVersion"] == "2"
    assert data["kind"] == "sandbox"
    assert data["name"] == "agy"
    assert data["sandbox"]["entrypoint"] == ["agy"]

    # Execution flags
    cmd_flags = data["sandbox"]["command"]["default"]
    assert "--dangerously-skip-permissions" in cmd_flags
    assert "--mode=accept-edits" in cmd_flags

    # Network permissions
    allow = data["permissions"]["network"]["allow"]
    assert "antigravity.google:443" in allow
    assert "accounts.google.com:443" in allow
    assert "oauth2.googleapis.com:443" in allow
    assert "generativelanguage.googleapis.com:443" in allow

    # Host-side proxy OAuth credentials
    creds = data["credentials"]
    assert any(c.get("service") == "antigravity" for c in creds)

    # Setup tools installation
    install_cmds = [item["command"] for item in data["setup"]["install"]]
    assert any("agy" in cmd for cmd in install_cmds)


def test_aops_kit_spec_validity():
    """The aops kit spec.yaml exists, parses, and follows schemaVersion: '2'."""
    kit_file = _REPO_ROOT / "lib" / "kits" / "aops" / "spec.yaml"
    assert kit_file.is_file(), f"aops kit not found at {kit_file}"

    data = yaml.safe_load(kit_file.read_text())
    assert data["schemaVersion"] == "2"
    assert data["name"] == "aops"
