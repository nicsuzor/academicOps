"""Tests for automode rule management (lib/automode.py)."""

import json
from pathlib import Path

import pytest
from lib.automode import (
    _get_aops_rules,
    _merge_rules,
    install,
    is_installed,
)


class TestGetAopsRules:
    """Test rule loading from plugin.json and fallback."""

    def test_loads_from_plugin_json(self):
        rules = _get_aops_rules()
        assert rules is not None
        assert "environment" in rules
        assert "allow" in rules
        assert "soft_deny" in rules

    def test_plugin_json_has_expected_rule_counts(self):
        rules = _get_aops_rules()
        assert len(rules["environment"]) == 4
        assert len(rules["allow"]) == 1
        assert len(rules["soft_deny"]) == 15

    def test_rules_contain_axiom_references(self):
        """Each soft_deny rule should reference an A1-A10 axiom."""
        import re

        axiom_ref = re.compile(r"\(A(?:[1-9]|10)\)")
        rules = _get_aops_rules()
        for rule in rules["soft_deny"]:
            assert axiom_ref.search(rule), f"Rule missing axiom reference: {rule[:60]}..."


class TestMergeRules:
    """Test merge strategy: environment replaced, allow/soft_deny appended."""

    def test_environment_replaced(self):
        cc = {"environment": ["cc env"], "allow": [], "soft_deny": []}
        aops = {"environment": ["aops env"], "allow": [], "soft_deny": []}
        merged = _merge_rules(cc, aops)
        assert merged["environment"] == ["aops env"]

    def test_allow_appended(self):
        cc = {"environment": [], "allow": ["cc allow 1", "cc allow 2"], "soft_deny": []}
        aops = {"environment": [], "allow": ["aops allow 1"], "soft_deny": []}
        merged = _merge_rules(cc, aops)
        assert merged["allow"] == ["cc allow 1", "cc allow 2", "aops allow 1"]

    def test_soft_deny_appended(self):
        cc = {"environment": [], "allow": [], "soft_deny": ["cc deny"]}
        aops = {"environment": [], "allow": [], "soft_deny": ["aops deny"]}
        merged = _merge_rules(cc, aops)
        assert merged["soft_deny"] == ["cc deny", "aops deny"]

    def test_deduplication(self):
        cc = {"environment": [], "allow": ["shared rule"], "soft_deny": []}
        aops = {"environment": [], "allow": ["shared rule", "new rule"], "soft_deny": []}
        merged = _merge_rules(cc, aops)
        assert merged["allow"] == ["shared rule", "new rule"]

    def test_cc_order_preserved(self):
        cc = {"environment": [], "allow": ["b", "a", "c"], "soft_deny": []}
        aops = {"environment": [], "allow": ["d"], "soft_deny": []}
        merged = _merge_rules(cc, aops)
        assert merged["allow"] == ["b", "a", "c", "d"]


class TestIsInstalled:
    """Test fingerprint detection."""

    def test_detects_installed(self, tmp_path, monkeypatch):
        import lib.automode as mod

        settings = {"autoMode": {"soft_deny": ["Evidentiary Immutability (A10): ..."]}}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        monkeypatch.setattr(mod, "_read_user_settings", lambda: (settings, settings_path))
        assert is_installed() is True

    def test_detects_not_installed(self, tmp_path, monkeypatch):
        import lib.automode as mod

        settings = {"autoMode": {"soft_deny": ["some other rule"]}}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        monkeypatch.setattr(mod, "_read_user_settings", lambda: (settings, settings_path))
        assert is_installed() is False

    def test_detects_no_automode(self, tmp_path, monkeypatch):
        import lib.automode as mod

        settings = {}
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps(settings))

        monkeypatch.setattr(mod, "_read_user_settings", lambda: (settings, settings_path))
        assert is_installed() is False


class TestInstall:
    """Test end-to-end install into settings.json."""

    def test_install_writes_settings(self, tmp_path, monkeypatch):
        import lib.automode as mod

        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text('{"existing": "value"}')

        monkeypatch.setattr(
            mod, "_read_user_settings", lambda: ({"existing": "value"}, settings_path)
        )
        monkeypatch.setattr(
            mod,
            "_get_aops_rules",
            lambda: {
                "environment": ["e"],
                "allow": ["a"],
                "soft_deny": ["Evidentiary Immutability (A10): test"],
            },
        )
        monkeypatch.setattr(
            mod,
            "_get_cc_defaults",
            lambda: {"environment": ["cc"], "allow": ["cc a"], "soft_deny": ["cc d"]},
        )

        ok, msg = install()
        assert ok
        assert str(settings_path) in msg

        written = json.loads(settings_path.read_text())
        assert written["existing"] == "value"
        assert written["autoMode"]["environment"] == ["e"]
        assert "cc a" in written["autoMode"]["allow"]
        assert "a" in written["autoMode"]["allow"]

    def test_install_dry_run(self, monkeypatch):
        import lib.automode as mod

        monkeypatch.setattr(
            mod,
            "_get_aops_rules",
            lambda: {"environment": ["e"], "allow": [], "soft_deny": []},
        )
        monkeypatch.setattr(
            mod,
            "_get_cc_defaults",
            lambda: {"environment": [], "allow": [], "soft_deny": []},
        )

        ok, msg = install(dry_run=True)
        assert ok
        parsed = json.loads(msg)
        assert parsed["environment"] == ["e"]

    def test_install_fails_without_claude_cli(self, monkeypatch):
        import lib.automode as mod

        monkeypatch.setattr(
            mod,
            "_get_aops_rules",
            lambda: {"environment": [], "allow": [], "soft_deny": []},
        )
        monkeypatch.setattr(mod, "_get_cc_defaults", lambda: None)

        ok, msg = install()
        assert not ok
        assert "CC auto-mode defaults" in msg


class TestUpdatePolecatDefaults:
    """Test updating polecat/defaults/claude-settings.json."""

    def test_update_polecat_defaults(self, tmp_path, monkeypatch):
        import lib.automode as mod

        # Mock AOPS_CORE_DIR to point to a tmp directory
        # AOPS_CORE_DIR in automode.py is aops-core/
        # so AOPS_CORE_DIR.parent / "polecat" / "defaults" / "claude-settings.json"
        # will be tmp_path / "polecat" / "defaults" / "claude-settings.json"

        aops_core_mock = tmp_path / "aops-core"
        aops_core_mock.mkdir()
        monkeypatch.setattr(mod, "AOPS_CORE_DIR", aops_core_mock)

        polecat_defaults_dir = tmp_path / "polecat" / "defaults"
        polecat_defaults_dir.mkdir(parents=True)
        polecat_settings_path = polecat_defaults_dir / "claude-settings.json"
        polecat_settings_path.write_text(json.dumps({"model": "test-model", "autoMode": {}}))

        monkeypatch.setattr(
            mod,
            "_get_aops_rules",
            lambda: {"environment": ["e"], "allow": ["a"], "soft_deny": ["d"]},
        )
        monkeypatch.setattr(
            mod,
            "_get_cc_defaults",
            lambda: {"environment": [], "allow": ["cc a"], "soft_deny": []},
        )

        from lib.automode import update_polecat_defaults

        ok, msg = update_polecat_defaults()
        assert ok
        assert "Updated polecat defaults" in msg

        written = json.loads(polecat_settings_path.read_text())
        assert written["model"] == "test-model"
        assert written["autoMode"]["environment"] == ["e"]
        assert "cc a" in written["autoMode"]["allow"]
        assert "a" in written["autoMode"]["allow"]


class TestPolekatDefaultsContainAopsRules:
    """Verify polecat/defaults/claude-settings.json contains all aops autoMode rules."""

    @pytest.fixture()
    def plugin_rules(self):
        plugin_path = Path(__file__).parent.parent / "aops-core" / ".claude-plugin" / "plugin.json"
        manifest = json.loads(plugin_path.read_text())
        return manifest["autoMode"]

    @pytest.fixture()
    def polecat_automode(self):
        polecat_path = (
            Path(__file__).parent.parent / "polecat" / "defaults" / "claude-settings.json"
        )
        settings = json.loads(polecat_path.read_text())
        return settings["autoMode"]

    def test_environment_matches(self, plugin_rules, polecat_automode):
        assert polecat_automode["environment"] == plugin_rules["environment"]

    def test_allow_rules_present(self, plugin_rules, polecat_automode):
        for rule in plugin_rules["allow"]:
            assert rule in polecat_automode["allow"], f"Missing allow rule: {rule[:60]}..."

    def test_soft_deny_rules_present(self, plugin_rules, polecat_automode):
        for rule in plugin_rules["soft_deny"]:
            assert rule in polecat_automode["soft_deny"], f"Missing soft_deny rule: {rule[:60]}..."
