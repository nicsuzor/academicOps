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
        assert len(rules["allow"]) == 3
        assert len(rules["soft_deny"]) == 11

    def test_rules_contain_axiom_references(self):
        """Each soft_deny rule should reference its axiom number."""
        rules = _get_aops_rules()
        for rule in rules["soft_deny"]:
            assert "P#" in rule, f"Rule missing axiom reference: {rule[:60]}..."

    def test_fallback_to_config_file(self, tmp_path, monkeypatch):
        """If plugin.json has no autoMode, falls back to config file."""
        import lib.automode as mod

        # Point to a plugin.json without autoMode
        fake_plugin_dir = tmp_path / ".claude-plugin"
        fake_plugin_dir.mkdir()
        (fake_plugin_dir / "plugin.json").write_text('{"name": "test"}')

        # Point to a valid config file
        fake_config_dir = tmp_path / "config"
        fake_config_dir.mkdir()
        (fake_config_dir / "automode-rules.json").write_text(
            json.dumps(
                {
                    "_comment": ["test"],
                    "environment": ["test env"],
                    "allow": ["test allow"],
                    "soft_deny": ["test deny"],
                }
            )
        )

        monkeypatch.setattr(mod, "AOPS_CORE_DIR", tmp_path)
        rules = _get_aops_rules()
        assert rules == {
            "environment": ["test env"],
            "allow": ["test allow"],
            "soft_deny": ["test deny"],
        }


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

        settings = {"autoMode": {"soft_deny": ["Research Data Immutable (P#42): ..."]}}
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
            lambda: {"environment": ["e"], "allow": ["a"], "soft_deny": ["P#42 test"]},
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


class TestPluginJsonAndConfigInSync:
    """Verify plugin.json autoMode and automode-rules.json stay in sync."""

    @pytest.fixture()
    def plugin_rules(self):
        plugin_path = Path(__file__).parent.parent / "aops-core" / ".claude-plugin" / "plugin.json"
        manifest = json.loads(plugin_path.read_text())
        return manifest["autoMode"]

    @pytest.fixture()
    def config_rules(self):
        config_path = Path(__file__).parent.parent / "aops-core" / "config" / "automode-rules.json"
        raw = json.loads(config_path.read_text())
        return {k: v for k, v in raw.items() if k in ("environment", "allow", "soft_deny")}

    def test_environment_matches(self, plugin_rules, config_rules):
        assert plugin_rules["environment"] == config_rules["environment"]

    def test_allow_matches(self, plugin_rules, config_rules):
        assert plugin_rules["allow"] == config_rules["allow"]

    def test_soft_deny_matches(self, plugin_rules, config_rules):
        assert plugin_rules["soft_deny"] == config_rules["soft_deny"]
