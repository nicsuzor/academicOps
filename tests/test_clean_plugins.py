"""Tests for scripts/clean_plugins.py — cleaning Cowork GUI packages and CLI caches."""

import json

from scripts.clean_plugins import (
    clean_gui,
    clean_settings,
    clean_trash,
    disable_synced_plugins,
    is_aops_plugin,
    uninstall_academicops_plugins,
)


def test_is_aops_plugin():
    assert is_aops_plugin({"name": "aops"})
    assert is_aops_plugin({"name": "aops-tools"})
    assert is_aops_plugin({"name": "aops-cowork"})
    assert is_aops_plugin({"name": "ida~g2"})
    assert is_aops_plugin({"name": "custom", "marketplaceName": "academicOps"})
    assert is_aops_plugin({"name": "custom", "marketplaceName": "academicOps-cowork"})
    assert is_aops_plugin({"name": "custom", "displayName": "aops custom tool"})
    assert not is_aops_plugin({"name": "other-plugin", "marketplaceName": "other"})


def test_clean_gui_prunes_cowork_manifest_and_directories(tmp_path, monkeypatch):
    base = tmp_path / "local-agent-mode-sessions"
    session_rpm = base / "acc1" / "surf1" / "rpm"
    session_rpm.mkdir(parents=True)

    plugin_dir = session_rpm / "plugin_123"
    plugin_dir.mkdir()
    (plugin_dir / "file.txt").write_text("hello")

    other_plugin_dir = session_rpm / "plugin_456"
    other_plugin_dir.mkdir()
    (other_plugin_dir / "file.txt").write_text("keep me")

    manifest = session_rpm / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "plugins": [
                    {"id": "plugin_123", "name": "aops"},
                    {"id": "plugin_456", "name": "unrelated"},
                ]
            }
        )
    )

    data_dir = base / "acc1" / "surf1" / ".claude" / "plugins" / "data" / "aops-inline"
    data_dir.mkdir(parents=True)

    monkeypatch.setattr("scripts.clean_plugins.get_cowork_bases", lambda: [base])

    clean_gui()

    assert not plugin_dir.exists()
    assert other_plugin_dir.exists()
    assert not data_dir.exists()

    updated = json.loads(manifest.read_text())
    assert updated["plugins"] == [{"id": "plugin_456", "name": "unrelated"}]


def test_uninstall_academicops_plugins(tmp_path):
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()

    installed = plugins_root / "installed_plugins.json"
    installed.write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    "tools@academicOps": [{"scope": "user"}],
                    "ida@aops": [{"scope": "user"}],
                },
            }
        )
    )

    manifests = plugins_root / ".install-manifests"
    manifests.mkdir()
    (manifests / "tools@academicOps.json").write_text("{}")
    (manifests / "ida@aops.json").write_text("{}")

    cache = plugins_root / "cache" / "academicOps" / "tools"
    cache.mkdir(parents=True)
    (cache / "dummy.txt").write_text("dummy")

    known_mp = plugins_root / "known_marketplaces.json"
    known_mp.write_text(
        json.dumps(
            {
                "academicOps": {"source": {"source": "git"}},
                "aops": {"source": {"source": "directory"}},
            }
        )
    )

    uninstall_academicops_plugins(plugins_root)

    updated_installed = json.loads(installed.read_text())
    assert "tools@academicOps" not in updated_installed["plugins"]
    assert "ida@aops" in updated_installed["plugins"]

    assert not (manifests / "tools@academicOps.json").exists()
    assert (manifests / "ida@aops.json").exists()

    assert not (plugins_root / "cache" / "academicOps").exists()

    updated_mp = json.loads(known_mp.read_text())
    assert "academicOps" not in updated_mp
    assert "aops" in updated_mp


def test_clean_trash(tmp_path):
    plugins_root = tmp_path / "plugins"
    trash = plugins_root / ".trash"
    trash.mkdir(parents=True)

    (trash / "file.txt").write_text("delete me")
    sub_dir = trash / "subdir"
    sub_dir.mkdir()
    (sub_dir / "nested.txt").write_text("nested")

    clean_trash(plugins_root)

    assert trash.exists()
    assert list(trash.iterdir()) == []


def test_clean_settings(tmp_path):
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"

    settings_file.write_text(
        json.dumps(
            {
                "enabledPlugins": {
                    "pkb@aops": True,
                    "orchestrate@aops": True,
                    "ts@aops": True,
                    "ida@academicOps": True,
                    "ida@aops": True,
                    "ida@synced": False,
                },
                "extraKnownMarketplaces": {
                    "academicOps": {"source": "git"},
                    "aops": {"source": "directory"},
                },
            }
        )
    )

    dist_plugins = {"ida", "rbg", "tools"}
    clean_settings(settings_dir, dist_plugins)

    updated = json.loads(settings_file.read_text())
    enabled = updated["enabledPlugins"]

    assert "pkb@aops" not in enabled
    assert "orchestrate@aops" not in enabled
    assert "ts@aops" not in enabled
    assert "ida@academicOps" not in enabled

    assert enabled["ida@aops"] is True
    assert enabled["ida@synced"] is False
    assert "academicOps" not in updated["extraKnownMarketplaces"]
    assert "aops" in updated["extraKnownMarketplaces"]


def test_disable_synced_plugins(tmp_path, monkeypatch):
    plugins_root = tmp_path / "plugins"
    synced_dir = plugins_root / "synced" / "org_user" / "ida~g2"
    synced_dir.mkdir(parents=True)

    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"
    settings_file.write_text(json.dumps({"enabledPlugins": {}}))

    monkeypatch.setattr("scripts.clean_plugins.get_aops_plugin_names", lambda: {"ida"})
    disable_synced_plugins(plugins_root, settings_dir)

    updated = json.loads(settings_file.read_text())
    assert updated["enabledPlugins"]["ida@synced"] is False
