"""
Auto mode classifier rule management.

Reads aops autoMode rules from the plugin manifest — canonical SSoT is
``templates/aops-core.plugin.json`` (the editable source); the build copies it
to ``<plugin>/.claude-plugin/plugin.json``, which is what ships and what the
runtime session-start hook reads (see ``_get_aops_rules``). Fetches CC defaults
via `claude auto-mode defaults`, merges them, and installs into
~/.claude/settings.json.

Merge strategy:
  - environment: aops REPLACES CC defaults (our context is more specific).
    Rationale: CC environment strings describe a generic developer context; aops
    strings describe an academic research context with its own norms (data
    immutability, PKB-as-truth, etc.). Appending would create contradictory or
    redundant context. Replacement is safe because aops rules are designed to be
    complete — if a needed CC environment string is missing it should be added to
    plugin.json rather than relying on CC defaults.
  - allow, soft_deny: CC defaults are PRESERVED and aops rules are appended.
    Rationale: CC built-in rules encode security patterns we should not lose.
    Appending lets aops add domain-specific constraints without removing protections.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

AOPS_CORE_DIR = Path(__file__).parent.parent

# Fingerprint substring marking aops autoMode rules as installed in user
# settings. Keyed on the canonical axiom SLUG (`evidence-immutable`), not a prose
# heading: slugs are stable across rule rewrites, headings are not (the old
# fingerprint pinned the renamed P#42 heading and silently misfired). CONTRACT:
# the soft_deny rule for this axiom MUST contain this slug token. The regression
# test tests/lib/test_automode.py::test_fingerprint_present_in_canonical_manifest
# fails loudly if a rule rewrite drops it — turning a silent runtime misfire into
# a CI failure.
AOPS_RULES_FINGERPRINT = "evidence-immutable"


def _get_aops_rules() -> dict | None:
    """Load aops autoMode rules from the plugin manifest.

    Canonical SSoT is ``templates/aops-core.plugin.json`` (the editable source).
    The build copies it to ``<plugin>/.claude-plugin/plugin.json``; an installed
    plugin does not ship the source ``templates/`` tree, so the same loader must
    fall back to the built manifest sitting next to this module. Checked
    source-first so local edits win during development; at runtime only the built
    copy exists and is used.
    """
    candidates = (
        AOPS_CORE_DIR.parent / "templates" / "aops-core.plugin.json",  # source checkout (SSoT)
        AOPS_CORE_DIR / ".claude-plugin" / "plugin.json",  # built / installed plugin
    )
    for plugin_json in candidates:
        if not plugin_json.exists():
            continue
        try:
            manifest = json.loads(plugin_json.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if "autoMode" in manifest:
            return manifest["autoMode"]

    return None


def _get_cc_defaults() -> dict | None:
    """Fetch Claude Code built-in auto mode defaults."""
    if not shutil.which("claude"):
        return None
    try:
        result = subprocess.run(
            ["claude", "auto-mode", "defaults"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _merge_rules(cc_defaults: dict, aops_rules: dict) -> dict:
    """Merge CC defaults with aops rules.

    - environment: aops replaces CC defaults
    - allow, soft_deny: CC defaults + aops additions (deduplicated)
    """
    merged = {}

    # Environment: aops replaces
    merged["environment"] = aops_rules.get("environment", cc_defaults.get("environment", []))

    # Allow and soft_deny: append aops to CC defaults, skip duplicates
    for key in ("allow", "soft_deny"):
        cc_list = cc_defaults.get(key, [])
        aops_list = aops_rules.get(key, [])
        # Use set for dedup but preserve order (CC first, then aops)
        seen = set(cc_list)
        merged[key] = list(cc_list)
        for item in aops_list:
            if item not in seen:
                merged[key].append(item)
                seen.add(item)

    return merged


def _read_user_settings() -> tuple[dict, Path]:
    """Read ~/.claude/settings.json, creating if needed."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text()), settings_path
        except (json.JSONDecodeError, OSError):
            return {}, settings_path
    return {}, settings_path


def is_installed() -> bool:
    """Check if aops autoMode rules are already in user settings.

    Fingerprints on ``AOPS_RULES_FINGERPRINT`` (the ``evidence-immutable`` axiom
    slug) appearing in soft_deny. The slug is stable across prose rewrites, so —
    unlike the old exact-heading match — a rule reword does not silently break the
    check. The rule→slug contract is guarded by the regression test referenced on
    ``AOPS_RULES_FINGERPRINT``.
    """
    settings, _ = _read_user_settings()
    auto_mode = settings.get("autoMode", {})
    soft_deny = auto_mode.get("soft_deny", [])
    return any(AOPS_RULES_FINGERPRINT in rule for rule in soft_deny)


def install(dry_run: bool = False) -> tuple[bool, str]:
    """Install merged autoMode rules into ~/.claude/settings.json.

    Returns (success, message).
    """
    aops_rules = _get_aops_rules()
    if not aops_rules:
        return False, "No aops autoMode rules found"

    cc_defaults = _get_cc_defaults()
    if cc_defaults is None:
        return False, "Could not fetch CC auto-mode defaults (is `claude` CLI available?)"

    merged = _merge_rules(cc_defaults, aops_rules)

    if dry_run:
        return True, json.dumps(merged, indent=2)

    settings, settings_path = _read_user_settings()
    settings["autoMode"] = merged

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        return True, f"Installed autoMode rules to {settings_path}"
    except OSError as e:
        return False, f"Failed to write {settings_path}: {e}"


def update_polecat_defaults() -> tuple[bool, str]:
    """Update polecat/defaults/claude-settings.json with rules from plugin.json.

    This preserves non-rule keys (like 'model') in the target file.
    """
    aops_rules = _get_aops_rules()
    if not aops_rules:
        return False, "No aops autoMode rules found"

    cc_defaults = _get_cc_defaults()
    if cc_defaults is None:
        return False, "Could not fetch CC auto-mode defaults"

    merged = _merge_rules(cc_defaults, aops_rules)

    # AOPS_CORE_DIR is aops-core/
    polecat_settings_path = AOPS_CORE_DIR.parent / "polecat" / "defaults" / "claude-settings.json"
    if not polecat_settings_path.exists():
        return False, f"Polecat settings not found at {polecat_settings_path}"

    try:
        settings = json.loads(polecat_settings_path.read_text())
        settings["autoMode"] = merged
        polecat_settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        return True, f"Updated polecat defaults at {polecat_settings_path}"
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Failed to update polecat defaults: {e}"


def main():
    """CLI entry point for setup-automode."""
    if "--update-polecat" in sys.argv:
        ok, msg = update_polecat_defaults()
        print(msg)
        sys.exit(0 if ok else 1)

    dry_run = "--install" not in sys.argv
    ok, msg = install(dry_run=dry_run)
    print(msg)
    if not ok:
        sys.exit(1)
    if dry_run:
        print("\n# Preview only. Run with --install to write to ~/.claude/settings.json")


if __name__ == "__main__":
    main()
