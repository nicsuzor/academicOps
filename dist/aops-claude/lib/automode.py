"""
Auto mode classifier rule management.

Reads aops autoMode rules from plugin.json (or fallback automode-rules.json),
fetches CC defaults via `claude auto-mode defaults`, merges them, and installs
into ~/.claude/settings.json.

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


def _get_aops_rules() -> dict | None:
    """Load aops autoMode rules from plugin.json or fallback config."""
    # Primary: plugin.json autoMode field
    plugin_json = AOPS_CORE_DIR / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        try:
            manifest = json.loads(plugin_json.read_text())
            if "autoMode" in manifest:
                return manifest["autoMode"]
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: standalone automode-rules.json
    rules_json = AOPS_CORE_DIR / "config" / "automode-rules.json"
    if rules_json.exists():
        try:
            rules = json.loads(rules_json.read_text())
            return {k: v for k, v in rules.items() if k in ("environment", "allow", "soft_deny")}
        except (json.JSONDecodeError, OSError):
            pass

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

    Uses the presence of "P#42" in soft_deny as a fingerprint for aops rules.
    LOAD-BEARING: If the P#42 rule text is renamed or removed from plugin.json,
    this fingerprint silently breaks — sessions will re-install on every start
    (if P#42 text no longer contains "P#42") or never re-install after a rule
    reset (if P#42 disappears entirely). Update this fingerprint string if the
    P#42 rule identifier changes.
    """
    settings, _ = _read_user_settings()
    auto_mode = settings.get("autoMode", {})
    soft_deny = auto_mode.get("soft_deny", [])
    return any("P#42" in rule for rule in soft_deny)


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


def main():
    """CLI entry point for setup-automode."""
    dry_run = "--install" not in sys.argv
    ok, msg = install(dry_run=dry_run)
    print(msg)
    if not ok:
        sys.exit(1)
    if dry_run:
        print("\n# Preview only. Run with --install to write to ~/.claude/settings.json")


if __name__ == "__main__":
    main()
