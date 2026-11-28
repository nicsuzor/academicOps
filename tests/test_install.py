"""Tests for build/install.py -- the curated autoMode settings.json merge.

Exercises: multi-section scoped merge (`allow`, `soft_deny`, etc.) with user
entries and untouched sections preserved, survival of Claude Code's built-in
rules via per-section `$defaults` splice sentinels, idempotent re-install,
retraction of stale rules (including legacy soft_deny-only axiom state),
reversible uninstall, and hard-error validation paths.
"""

import json
from pathlib import Path

import pytest

from build.install import (
    DEFAULTS_SENTINEL,
    InstallError,
    install_automode,
    uninstall_automode,
)


def _write_automode_json(dist_root: Path, plugin: str, payload: object) -> None:
    plugin_dir = dist_root / f"{plugin}-claude"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "auto-mode.json").write_text(json.dumps(payload), encoding="utf-8")


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    return tmp_path / "dist", tmp_path / "settings.json", tmp_path / "state.json"


ALLOW_A = "Internal-Org PR Lifecycle: allow internal PR retargeting."
SOFT_A = "Guard & Check Bypass: deny --no-verify."
SOFT_B = "No Shell Polling Loops: deny while/sleep polling."


def test_install_merges_allow_and_soft_deny_into_empty_settings(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["allow"] == [DEFAULTS_SENTINEL, ALLOW_A]
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, SOFT_A]


def test_install_gathers_and_deduplicates_across_multiple_plugins(tmp_path):
    """Curated rules come from whichever plugin(s) ship auto-mode.json,
    deduplicated in declaration order."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "alpha", {"soft_deny": [SOFT_A, SOFT_B]})
    _write_automode_json(dist_root, "beta", {"allow": [ALLOW_A], "soft_deny": [SOFT_B]})

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["allow"] == [DEFAULTS_SENTINEL, ALLOW_A]
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, SOFT_A, SOFT_B]


def test_install_preserves_user_entries_and_untouched_automode_sections(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})
    settings_path.write_text(
        json.dumps(
            {
                "autoMode": {
                    "soft_deny": ["users-own-rule: hand-written by the user"],
                    "hard_deny": ["rm -rf /"],
                    "environment": [DEFAULTS_SENTINEL, "**Organization**: Example"],
                },
                "someOtherTopLevelKey": {"untouched": True},
            }
        )
    )

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert "users-own-rule: hand-written by the user" in settings["autoMode"]["soft_deny"]
    assert SOFT_A in settings["autoMode"]["soft_deny"]
    assert ALLOW_A in settings["autoMode"]["allow"]
    assert settings["autoMode"]["hard_deny"] == ["rm -rf /"]
    assert settings["autoMode"]["environment"] == [DEFAULTS_SENTINEL, "**Organization**: Example"]
    assert settings["someOtherTopLevelKey"] == {"untouched": True}


def test_install_is_idempotent(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A, SOFT_B]})

    install_automode(dist_root, settings_path, state_path)
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["allow"] == [DEFAULTS_SENTINEL, ALLOW_A]
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, SOFT_A, SOFT_B]


def test_install_retracts_stale_entries_and_legacy_axiom_slogans(tmp_path):
    """Re-installing retracts previously owned entries -- including legacy
    1-line axiom slogans recorded by older installer versions."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    legacy_slogan = "excellence: Excellence is the standard; compliance is the floor."
    settings_path.write_text(
        json.dumps(
            {
                "autoMode": {
                    "soft_deny": [DEFAULTS_SENTINEL, "user-rule", legacy_slogan],
                }
            }
        )
    )
    state_path.write_text(json.dumps({"soft_deny": [legacy_slogan]}))
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, "user-rule", SOFT_A]
    assert settings["autoMode"]["allow"] == [DEFAULTS_SENTINEL, ALLOW_A]


def test_install_splices_defaults_sentinel_per_written_section_and_reports_it(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})

    message = install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["allow"][0] == DEFAULTS_SENTINEL
    assert settings["autoMode"]["soft_deny"][0] == DEFAULTS_SENTINEL
    assert DEFAULTS_SENTINEL in message


def test_install_does_not_duplicate_sentinel_or_record_it_as_owned(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})

    install_automode(dist_root, settings_path, state_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A, SOFT_B]})
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["allow"].count(DEFAULTS_SENTINEL) == 1
    assert settings["autoMode"]["soft_deny"].count(DEFAULTS_SENTINEL) == 1
    state = json.loads(state_path.read_text())
    assert DEFAULTS_SENTINEL not in state["allow"]
    assert DEFAULTS_SENTINEL not in state["soft_deny"]


def test_install_drops_section_when_all_aops_entries_withdrawn_and_no_user_entries(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})
    install_automode(dist_root, settings_path, state_path)

    _write_automode_json(dist_root, "crew", {"soft_deny": [SOFT_A]})
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert "allow" not in settings["autoMode"]
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, SOFT_A]


def test_install_leaves_relocated_sentinel_where_user_put_it(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [SOFT_A]})
    settings_path.write_text(
        json.dumps({"autoMode": {"soft_deny": ["users-own-rule: first", DEFAULTS_SENTINEL]}})
    )

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [
        "users-own-rule: first",
        DEFAULTS_SENTINEL,
        SOFT_A,
    ]


def test_install_restores_deleted_sentinel_and_reports_it(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [SOFT_A]})
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    settings["autoMode"]["soft_deny"] = [
        e for e in settings["autoMode"]["soft_deny"] if e != DEFAULTS_SENTINEL
    ]
    settings_path.write_text(json.dumps(settings))

    message = install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert DEFAULTS_SENTINEL in settings["autoMode"]["soft_deny"]
    assert DEFAULTS_SENTINEL in message


def test_install_writes_only_declared_automode_sections(tmp_path):
    """Undeclared sections (`hard_deny`, `environment`) are never created."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert list(settings["autoMode"]) == ["allow", "soft_deny"]


def test_install_no_automode_files_is_not_an_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    dist_root.mkdir()

    message = install_automode(dist_root, settings_path, state_path)

    assert "nothing to merge" in message
    assert not settings_path.exists()
    assert not state_path.exists()


def test_install_missing_dist_root_is_not_an_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)

    message = install_automode(dist_root, settings_path, state_path)

    assert "nothing to merge" in message


def test_uninstall_removes_owned_entries_across_sections_and_keeps_user_entries(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})
    settings_path.write_text(json.dumps({"autoMode": {"soft_deny": ["users-own-rule: kept"]}}))

    install_automode(dist_root, settings_path, state_path)
    uninstall_automode(settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert "allow" not in settings["autoMode"]
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, "users-own-rule: kept"]
    assert not state_path.exists()


def test_uninstall_drops_empty_automode_key_entirely(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})
    install_automode(dist_root, settings_path, state_path)

    uninstall_automode(settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert "autoMode" not in settings


def test_uninstall_preserves_untouched_sections(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"allow": [ALLOW_A], "soft_deny": [SOFT_A]})
    settings_path.write_text(json.dumps({"autoMode": {"hard_deny": ["rm -rf /"]}}))

    install_automode(dist_root, settings_path, state_path)
    uninstall_automode(settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"] == {"hard_deny": ["rm -rf /"]}


def test_uninstall_is_idempotent(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [SOFT_A]})
    install_automode(dist_root, settings_path, state_path)

    uninstall_automode(settings_path, state_path)
    message = uninstall_automode(settings_path, state_path)

    assert "nothing to remove" in message


def test_malformed_settings_json_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [SOFT_A]})
    settings_path.write_text("{not valid json")

    with pytest.raises(InstallError, match="settings.json"):
        install_automode(dist_root, settings_path, state_path)


def test_malformed_state_file_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [SOFT_A]})
    state_path.write_text("{not valid json")

    with pytest.raises(InstallError, match="install state"):
        install_automode(dist_root, settings_path, state_path)


def test_unknown_automode_section_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"softDeny": [SOFT_A]})

    with pytest.raises(InstallError, match="unknown autoMode section"):
        install_automode(dist_root, settings_path, state_path)


def test_sentinel_inside_plugin_automode_json_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [DEFAULTS_SENTINEL, SOFT_A]})

    with pytest.raises(InstallError, match=r"\$defaults"):
        install_automode(dist_root, settings_path, state_path)


def test_non_string_entry_in_automode_json_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_automode_json(dist_root, "crew", {"soft_deny": [123]})

    with pytest.raises(InstallError, match="non-empty string"):
        install_automode(dist_root, settings_path, state_path)


def test_uninstall_malformed_state_file_is_hard_error(tmp_path):
    _, settings_path, state_path = _paths(tmp_path)
    state_path.write_text("{not valid json")

    with pytest.raises(InstallError, match="install state"):
        uninstall_automode(settings_path, state_path)
