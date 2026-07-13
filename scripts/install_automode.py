#!/usr/bin/env -S uv run python
"""
Merge the aops axiom rules (shipped as dist/aops-claude/axioms.jsonl by
scripts/build.py) into the user's ~/.claude/settings.json.

Claude Code's `autoMode` classifier only reads its config from
~/.claude/settings.json (merged with CC's own built-in defaults). The built
plugin therefore ships the axioms as a JSONL data file (one JSON object per
line, with `slug`/`description`/`body`/`source_file` fields) as the durable,
version-controlled transport; this script reads that file and is what actually
makes the rules take effect for a session.

Best-effort by design: any failure here should not abort a `make install-dev`
run, so this always exits 0 and just prints what happened.

Merge strategy per list:
  - environment: aops REPLACES CC defaults (our context is more specific).
  - allow, soft_deny, hard_deny: CC defaults are PRESERVED, aops entries are
    appended, duplicates skipped.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
DIST_AXIOMS_JSONL = REPO_ROOT / "dist" / "aops-claude" / "axioms.jsonl"


def _get_aops_auto_mode() -> dict | None:
    if not DIST_AXIOMS_JSONL.exists():
        return None
    try:
        soft_deny = []
        for line in DIST_AXIOMS_JSONL.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            axiom = json.loads(line)
            soft_deny.append(f"{axiom['slug']}: {axiom['description']}")
    except (json.JSONDecodeError, KeyError, OSError):
        return None
    return {"soft_deny": soft_deny} if soft_deny else None


def _get_cc_defaults() -> dict | None:
    if not shutil.which("claude"):
        return None
    try:
        result = subprocess.run(
            ["claude", "auto-mode", "defaults"], capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _merge(cc_defaults: dict, aops_rules: dict) -> dict:
    merged = {"environment": aops_rules.get("environment", cc_defaults.get("environment", []))}
    for key in ("allow", "soft_deny", "hard_deny"):
        cc_list = cc_defaults.get(key, [])
        aops_list = aops_rules.get(key, [])
        seen = set(cc_list)
        merged[key] = list(cc_list)
        for item in aops_list:
            if item not in seen:
                merged[key].append(item)
                seen.add(item)
    return merged


def main() -> int:
    aops_rules = _get_aops_auto_mode()
    if not aops_rules:
        print(f"  (no autoMode rules in {DIST_AXIOMS_JSONL} — skipping settings.json merge)")
        return 0

    cc_defaults = _get_cc_defaults()
    if cc_defaults is None:
        print("  (could not fetch `claude auto-mode defaults` — skipping settings.json merge)")
        return 0

    merged = _merge(cc_defaults, aops_rules)

    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"  (could not read {settings_path}: {e} — skipping settings.json merge)")
        return 0

    settings["autoMode"] = merged
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    except OSError as e:
        print(f"  (could not write {settings_path}: {e} — skipping settings.json merge)")
        return 0

    print(
        f"✓ Merged {len(aops_rules.get('soft_deny', []))} aops axiom rule(s) into {settings_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
