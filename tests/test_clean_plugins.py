"""Tests for scripts/clean_plugins.py — cleaning Cowork GUI packages and CLI caches."""

import json

from scripts.clean_plugins import clean_gui, is_aops_plugin


def test_is_aops_plugin():
    assert is_aops_plugin({"name": "aops"})
    assert is_aops_plugin({"name": "aops-tools"})
    assert is_aops_plugin({"name": "aops-cowork"})
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
