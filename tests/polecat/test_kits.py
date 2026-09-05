"""Unit tests for Docker Sandboxes (sbx) kits for Claude and Agy."""

import tomllib
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_POLICY_FILE = _REPO_ROOT / "tests" / "policy.toml"
_policy = tomllib.loads(_POLICY_FILE.read_text(encoding="utf-8")) if _POLICY_FILE.exists() else {}


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

    # Network permissions defined by policy
    allow = data["permissions"]["network"]["allow"]
    claude_policy = _policy.get("kits", {}).get("claude", {})
    required_allow = claude_policy.get(
        "required_network_allow", ["api.anthropic.com:443", "github.com:443", "pypi.org:443"]
    )
    for endpoint in required_allow:
        assert endpoint in allow, f"Expected endpoint {endpoint} in claude network allowlist"

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

    # Network permissions defined by policy
    allow = data["permissions"]["network"]["allow"]
    agy_policy = _policy.get("kits", {}).get("agy", {})
    required_allow = agy_policy.get(
        "required_network_allow",
        [
            "antigravity.google:443",
            "accounts.google.com:443",
            "oauth2.googleapis.com:443",
            "generativelanguage.googleapis.com:443",
        ],
    )
    for endpoint in required_allow:
        assert endpoint in allow, f"Expected endpoint {endpoint} in agy network allowlist"

    # Host-side proxy OAuth credentials
    creds = data["credentials"]
    assert any(c.get("service") == "antigravity" for c in creds)

    # Setup tools installation or prebuilt container configuration
    if "setup" in data and "install" in data["setup"]:
        install_cmds = [item["command"] for item in data["setup"]["install"]]
        assert any("agy" in cmd for cmd in install_cmds)
    else:
        assert data.get("sandbox", {}).get("image") == "aops-crew:latest"


def test_aops_kit_spec_validity():
    """The aops kit spec.yaml exists, parses, and follows schemaVersion: '2'."""
    kit_file = _REPO_ROOT / "lib" / "kits" / "aops" / "spec.yaml"
    assert kit_file.is_file(), f"aops kit not found at {kit_file}"

    data = yaml.safe_load(kit_file.read_text())
    assert data["schemaVersion"] == "2"
    assert data["name"] == "aops"
