"""Tests for build/install.py — the autoMode settings.json merge.

Exercises: scoped merge (user's own entries untouched), survival of Claude
Code's built-in soft-block rules via the `$defaults` splice sentinel,
idempotent re-install (no duplication, stale entries retracted on axiom
rename/removal), reversible uninstall (removes exactly what was added,
idempotent), and the hard-error paths (malformed settings.json / state file /
axioms.jsonl).
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


def _write_axioms_jsonl(dist_root: Path, plugin: str, axioms: list[dict]) -> None:
    plugin_dir = dist_root / f"{plugin}-claude"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = plugin_dir / "axioms.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for axiom in axioms:
            f.write(json.dumps(axiom) + "\n")


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    return tmp_path / "dist", tmp_path / "settings.json", tmp_path / "state.json"


AXIOM_A = {
    "slug": "halt-on-failure",
    "description": "Fail fast.",
    "body": "...",
    "source_file": "a.md",
}
AXIOM_B = {
    "slug": "cite-sources",
    "description": "Cite everything.",
    "body": "...",
    "source_file": "b.md",
}


def test_install_merges_into_empty_settings(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [
        DEFAULTS_SENTINEL,
        "halt-on-failure: Fail fast.",
    ]


def test_install_gathers_from_multiple_plugins(tmp_path):
    """Axioms come from lib/axioms/ via whichever plugin(s) ship them —
    never hardcoded to one plugin's dist dir."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    _write_axioms_jsonl(dist_root, "aops-cope", [AXIOM_B])

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert set(settings["autoMode"]["soft_deny"]) == {
        DEFAULTS_SENTINEL,
        "halt-on-failure: Fail fast.",
        "cite-sources: Cite everything.",
    }


def test_install_preserves_user_owned_entries_and_other_automode_keys(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    settings_path.write_text(
        json.dumps(
            {
                "autoMode": {
                    "soft_deny": ["users-own-rule: hand-written by the user"],
                    "hard_deny": ["rm -rf /"],
                },
                "someOtherTopLevelKey": {"untouched": True},
            }
        )
    )

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert "users-own-rule: hand-written by the user" in settings["autoMode"]["soft_deny"]
    assert "halt-on-failure: Fail fast." in settings["autoMode"]["soft_deny"]
    assert settings["autoMode"]["hard_deny"] == ["rm -rf /"]  # untouched, not "replaced wholesale"
    assert settings["someOtherTopLevelKey"] == {"untouched": True}  # untouched


def test_install_is_idempotent(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A, AXIOM_B])

    install_automode(dist_root, settings_path, state_path)
    install_automode(dist_root, settings_path, state_path)  # re-run, same input

    settings = json.loads(settings_path.read_text())
    soft_deny = settings["autoMode"]["soft_deny"]
    assert sorted(soft_deny) == sorted(set(soft_deny))  # no duplicates
    assert len(soft_deny) == 3  # two axioms plus the defaults sentinel


def test_install_retracts_stale_entries_on_axiom_removal(tmp_path):
    """A renamed or removed axiom must never linger from a prior install."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A, AXIOM_B])
    install_automode(dist_root, settings_path, state_path)

    # Rebuild with only AXIOM_A — AXIOM_B's axiom was removed/renamed upstream.
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [
        DEFAULTS_SENTINEL,
        "halt-on-failure: Fail fast.",
    ]


def test_install_splices_claude_code_defaults_back_in(tmp_path):
    """Writing soft_deny at all discards Claude Code's built-in soft-block
    rules unless the array carries the `$defaults` splice sentinel. It leads,
    so the built-ins land in their shipped order with aops entries after."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])

    message = install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"][0] == DEFAULTS_SENTINEL
    assert DEFAULTS_SENTINEL in message  # never restored silently


def test_install_does_not_duplicate_the_sentinel_across_runs(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])

    install_automode(dist_root, settings_path, state_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A, AXIOM_B])  # axiom set changes
    install_automode(dist_root, settings_path, state_path)
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"].count(DEFAULTS_SENTINEL) == 1


def test_install_never_records_the_sentinel_as_aops_owned(tmp_path):
    """The state file drives retraction. The sentinel must stay out of it."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])

    install_automode(dist_root, settings_path, state_path)

    assert DEFAULTS_SENTINEL not in json.loads(state_path.read_text())["soft_deny"]


def test_sentinel_survives_retraction_of_every_aops_entry(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A, AXIOM_B])
    install_automode(dist_root, settings_path, state_path)

    _write_axioms_jsonl(dist_root, "aops", [])  # every always-on axiom withdrawn
    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL]


def test_install_leaves_a_relocated_sentinel_where_the_user_put_it(tmp_path):
    """The defaults splice at the sentinel's position, so its index is the
    user's to choose. Placed once; never moved on a later run."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    settings_path.write_text(
        json.dumps({"autoMode": {"soft_deny": ["users-own-rule: first", DEFAULTS_SENTINEL]}})
    )

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [
        "users-own-rule: first",
        DEFAULTS_SENTINEL,
        "halt-on-failure: Fail fast.",
    ]


def test_install_restores_a_deleted_sentinel_and_reports_it(tmp_path):
    """Deleting the sentinel by hand strips the harness's own protections, and
    is indistinguishable from never having had one. The installer puts it back
    rather than shipping axioms in place of the built-ins — and says so."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
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


def test_install_writes_no_other_automode_section(tmp_path):
    """`allow`, `hard_deny` and `environment` keep their built-ins precisely
    because this installer never writes them — the sentinel is not needed
    there for anything this function does."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])

    install_automode(dist_root, settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert list(settings["autoMode"]) == ["soft_deny"]


def test_install_no_axioms_found_is_not_an_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    dist_root.mkdir()  # dist/ exists but no plugin ships always-on axioms

    message = install_automode(dist_root, settings_path, state_path)

    assert "nothing to merge" in message
    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL]


def test_install_missing_dist_root_is_not_an_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)  # dist_root never created

    message = install_automode(dist_root, settings_path, state_path)

    assert "nothing to merge" in message


def test_uninstall_removes_exactly_owned_entries(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    settings_path.write_text(json.dumps({"autoMode": {"soft_deny": ["users-own-rule: kept"]}}))

    install_automode(dist_root, settings_path, state_path)
    uninstall_automode(settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"]["soft_deny"] == [DEFAULTS_SENTINEL, "users-own-rule: kept"]
    assert not state_path.exists()


def test_uninstall_drops_empty_automode_key_entirely(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    install_automode(dist_root, settings_path, state_path)  # settings.json had no autoMode before

    uninstall_automode(settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert "autoMode" not in settings


def test_uninstall_drops_a_soft_deny_left_holding_only_the_sentinel(tmp_path):
    """`["$defaults"]` resolves to the built-in list, exactly as an absent
    array does — so dropping it loses no rule and leaves no residue. Other
    autoMode sections the installer never wrote stay put."""
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    settings_path.write_text(json.dumps({"autoMode": {"hard_deny": ["rm -rf /"]}}))

    install_automode(dist_root, settings_path, state_path)
    uninstall_automode(settings_path, state_path)

    settings = json.loads(settings_path.read_text())
    assert settings["autoMode"] == {"hard_deny": ["rm -rf /"]}


def test_uninstall_is_idempotent(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    install_automode(dist_root, settings_path, state_path)

    uninstall_automode(settings_path, state_path)
    message = uninstall_automode(settings_path, state_path)  # second run, state already gone

    assert "nothing to remove" in message


def test_malformed_settings_json_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    settings_path.write_text("{not valid json")

    with pytest.raises(InstallError, match="settings.json"):
        install_automode(dist_root, settings_path, state_path)


def test_malformed_state_file_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    _write_axioms_jsonl(dist_root, "aops", [AXIOM_A])
    state_path.write_text("{not valid json")

    with pytest.raises(InstallError, match="install state"):
        install_automode(dist_root, settings_path, state_path)


def test_malformed_axioms_jsonl_line_is_hard_error(tmp_path):
    dist_root, settings_path, state_path = _paths(tmp_path)
    plugin_dir = dist_root / "aops-claude"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "axioms.jsonl").write_text('{"slug": "x"}\n')  # missing required "description"

    with pytest.raises(InstallError, match="malformed axiom entry"):
        install_automode(dist_root, settings_path, state_path)


def test_uninstall_malformed_state_file_is_hard_error(tmp_path):
    _, settings_path, state_path = _paths(tmp_path)
    state_path.write_text("{not valid json")

    with pytest.raises(InstallError, match="install state"):
        uninstall_automode(settings_path, state_path)
