"""Tests for lib/automode — autoMode classifier rule install plumbing.

Guards the source-of-truth and install-fingerprint contract that previously
drifted three ways (templates manifest vs. spec vs. fingerprint heading):

- ``templates/aops-core.plugin.json`` (``autoMode`` key) is the canonical SSoT.
  ``test_canonical_manifest_has_automode_rules`` fails loudly if the key drifts
  back out of source (the exact regression that left aops deploying zero rules).
- ``is_installed()`` fingerprints on the ``evidence-immutable`` axiom SLUG, not a
  prose heading. ``test_fingerprint_present_in_canonical_manifest`` is the
  load-bearing guard: it converts the old *silent runtime misfire* (heading
  reworded → fingerprint never matches → re-install every session) into a CI
  failure.
- ``_get_aops_rules`` resolves the manifest from a source checkout *or* an
  installed plugin (``.claude-plugin/plugin.json``) — the runtime layout the
  source-only path used to miss.
- The merge preserves CC defaults (appends, never clobbers) — the task's
  "without clobbering CC defaults" requirement.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from lib import automode  # noqa: E402
from lib.automode import (  # noqa: E402
    AOPS_RULES_FINGERPRINT,
    _get_aops_rules,
    _merge_rules,
    install,
    is_installed,
)

CANONICAL_MANIFEST = REPO_ROOT / "templates" / "aops-core.plugin.json"

# Minimal but representative CC defaults. autoMode in settings.json REPLACES the
# built-in defaults, so the merge must re-include them — this fixture stands in
# for `claude auto-mode defaults` so the logic tests are deterministic and need
# no `claude` CLI.
CC_DEFAULTS_FIXTURE = {
    "environment": [
        "**Trusted repo**: The git repository the agent started in",
        "**Source control**: The trusted repo and its remote(s) only",
    ],
    "allow": [
        "Read-Only Operations: GET requests and queries that don't modify state",
        "Local Operations: local file operations within project scope",
    ],
    "soft_deny": [
        "Git Destructive: Force pushing or rewriting remote history",
        "Production Deploy: Deploying to a production service",
    ],
    "hard_deny": ["Some hard deny CC keeps"],
}


# --- Canonical source of truth -------------------------------------------------


def test_canonical_manifest_has_automode_rules():
    """The SSoT manifest carries a non-empty autoMode.soft_deny.

    Regression guard: the autoMode key drifted out of source once already, which
    left ``_get_aops_rules()`` returning None and install() failing with "No aops
    autoMode rules found" on every session start.
    """
    manifest = json.loads(CANONICAL_MANIFEST.read_text())
    assert "autoMode" in manifest, f"autoMode key missing from {CANONICAL_MANIFEST}"
    assert manifest["autoMode"].get("soft_deny"), "autoMode.soft_deny must be non-empty"


def test_fingerprint_present_in_canonical_manifest():
    """The install fingerprint must match a live rule in the canonical source.

    LOAD-BEARING. ``is_installed()`` keys on ``AOPS_RULES_FINGERPRINT``; if no
    canonical soft_deny rule contains it, the fingerprint silently never matches
    and sessions re-install forever. This asserts the rule→slug contract so a
    rule rewrite that drops the slug fails here instead of in production.
    """
    manifest = json.loads(CANONICAL_MANIFEST.read_text())
    soft_deny = manifest["autoMode"].get("soft_deny", [])
    assert any(AOPS_RULES_FINGERPRINT in rule for rule in soft_deny), (
        f"No canonical soft_deny rule contains the fingerprint "
        f"{AOPS_RULES_FINGERPRINT!r}; is_installed() would never return True. "
        f"Update the fingerprint or the rule so they agree."
    )


def test_get_aops_rules_reads_canonical_source():
    """_get_aops_rules() returns the autoMode block from the source checkout."""
    rules = _get_aops_rules()
    assert rules is not None, "loader returned None against a populated source tree"
    assert any(AOPS_RULES_FINGERPRINT in r for r in rules.get("soft_deny", []))


def test_get_aops_rules_falls_back_to_built_manifest(tmp_path, monkeypatch):
    """Installed-plugin layout: no source templates/, only .claude-plugin/.

    Simulates the runtime tree (``<plugin>/.claude-plugin/plugin.json`` with no
    sibling source ``templates/``) and asserts the loader still finds the rules
    via the built-manifest fallback — the path the old source-only loader missed.
    """
    plugin_root = tmp_path / "aops-core"
    built = plugin_root / ".claude-plugin"
    built.mkdir(parents=True)
    (built / "plugin.json").write_text(
        json.dumps(
            {"name": "aops-core", "autoMode": {"soft_deny": [f"x {AOPS_RULES_FINGERPRINT} y"]}}
        )
    )
    # AOPS_CORE_DIR.parent / "templates" must NOT exist for this to test the fallback.
    monkeypatch.setattr(automode, "AOPS_CORE_DIR", plugin_root)
    assert not (plugin_root.parent / "templates" / "aops-core.plugin.json").exists()

    rules = _get_aops_rules()
    assert rules is not None
    assert any(AOPS_RULES_FINGERPRINT in r for r in rules["soft_deny"])


# --- Merge: never clobber CC defaults -----------------------------------------


def test_merge_preserves_cc_defaults_and_appends_aops():
    aops_rules = {"soft_deny": [f"Aops rule about `{AOPS_RULES_FINGERPRINT}`"]}
    merged = _merge_rules(CC_DEFAULTS_FIXTURE, aops_rules)

    # Every CC allow/soft_deny entry survives.
    for entry in CC_DEFAULTS_FIXTURE["allow"]:
        assert entry in merged["allow"]
    for entry in CC_DEFAULTS_FIXTURE["soft_deny"]:
        assert entry in merged["soft_deny"]
    # CC entries come first, aops appended after.
    assert (
        merged["soft_deny"][: len(CC_DEFAULTS_FIXTURE["soft_deny"])]
        == CC_DEFAULTS_FIXTURE["soft_deny"]
    )
    assert merged["soft_deny"][-1] == aops_rules["soft_deny"][0]


def test_merge_omitted_environment_falls_through_to_cc():
    """A seed that omits `environment` must not blank out CC's environment."""
    merged = _merge_rules(CC_DEFAULTS_FIXTURE, {"soft_deny": ["x"]})
    assert merged["environment"] == CC_DEFAULTS_FIXTURE["environment"]


def test_merge_dedups_exact_duplicates():
    """An aops rule identical to a CC default is not appended twice."""
    dup = CC_DEFAULTS_FIXTURE["soft_deny"][0]
    merged = _merge_rules(CC_DEFAULTS_FIXTURE, {"soft_deny": [dup]})
    assert merged["soft_deny"].count(dup) == 1


# --- is_installed fingerprint --------------------------------------------------


def _patch_home(monkeypatch, tmp_path, settings: dict):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(json.dumps(settings))
    monkeypatch.setattr(automode.Path, "home", staticmethod(lambda: home))
    return home


def test_is_installed_true_when_fingerprint_in_soft_deny(tmp_path, monkeypatch):
    _patch_home(
        monkeypatch,
        tmp_path,
        {"autoMode": {"soft_deny": [f"... `{AOPS_RULES_FINGERPRINT}` ..."]}},
    )
    assert is_installed() is True


def test_is_installed_false_on_cc_defaults_only(tmp_path, monkeypatch):
    _patch_home(monkeypatch, tmp_path, {"autoMode": CC_DEFAULTS_FIXTURE})
    assert is_installed() is False


def test_is_installed_false_when_no_settings(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setattr(automode.Path, "home", staticmethod(lambda: home))
    assert is_installed() is False


# --- install end-to-end (merge + write + idempotent fingerprint) --------------


def test_install_merges_into_settings_without_clobbering(tmp_path, monkeypatch):
    """install() adds aops rules + CC defaults while preserving existing keys.

    Mirrors the task's end-to-end requirement with a fixed CC-defaults fixture so
    it is deterministic in CI. Pre-seeds settings.json with a sentinel key and a
    CC-defaults-only autoMode (the realistic "CC installed, aops not yet" state)
    and asserts: sentinel preserved, CC defaults still present, aops rule added,
    is_installed() flips to True.
    """
    home = _patch_home(
        monkeypatch,
        tmp_path,
        {"model": "sentinel-model", "autoMode": CC_DEFAULTS_FIXTURE},
    )
    monkeypatch.setattr(automode, "_get_cc_defaults", lambda: CC_DEFAULTS_FIXTURE)

    ok, msg = install(dry_run=False)
    assert ok, msg

    written = json.loads((home / ".claude" / "settings.json").read_text())
    # Non-autoMode settings untouched.
    assert written["model"] == "sentinel-model"
    # CC defaults preserved.
    for entry in CC_DEFAULTS_FIXTURE["soft_deny"]:
        assert entry in written["autoMode"]["soft_deny"]
    # aops rule added.
    assert any(AOPS_RULES_FINGERPRINT in r for r in written["autoMode"]["soft_deny"])
    # Fingerprint now satisfied.
    assert is_installed() is True


def test_install_dry_run_writes_nothing(tmp_path, monkeypatch):
    home = _patch_home(monkeypatch, tmp_path, {"autoMode": CC_DEFAULTS_FIXTURE})
    monkeypatch.setattr(automode, "_get_cc_defaults", lambda: CC_DEFAULTS_FIXTURE)
    before = (home / ".claude" / "settings.json").read_text()

    ok, preview = install(dry_run=True)
    assert ok
    assert AOPS_RULES_FINGERPRINT in preview  # preview shows merged rules
    assert (home / ".claude" / "settings.json").read_text() == before  # unchanged
