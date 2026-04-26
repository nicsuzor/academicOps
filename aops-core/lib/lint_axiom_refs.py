#!/usr/bin/env -S uv run python
"""Linter for Axiom and Rule references in autoMode rules.

Validates that every rule in plugin.json (and other manifests) cites an
existing Axiom (A#) and Rule (R#.#) from AXIOMS.md and RULES.md.
"""

import json
import re
import sys
from pathlib import Path


def get_axiom_ids(axioms_file: Path) -> set[str]:
    """Parse AXIOMS.md for A# IDs."""
    if not axioms_file.exists():
        return set()
    content = axioms_file.read_text()
    # Pattern: ## A1 — Title
    return set(re.findall(r"^## (A\d+)", content, re.MULTILINE))


def get_rules(rules_file: Path) -> dict[str, str]:
    """Parse RULES.md for R#.# IDs and their parent A# IDs."""
    rules = {}  # R#.# -> A#
    if not rules_file.exists():
        return rules

    current_axiom = None
    for line in rules_file.read_text().splitlines():
        # Axiom heading: ## A1 — Closure (No Other Truths)
        a_match = re.match(r"^## (A\d+)", line)
        if a_match:
            current_axiom = a_match.group(1)

        # Rule heading: ### R1.1 No invented rules
        r_match = re.match(r"^### (R\d+\.\d+)", line)
        if r_match:
            if current_axiom:
                rules[r_match.group(1)] = current_axiom
            else:
                # Rule found before any axiom heading
                pass
    return rules


def lint_manifest(
    file_path: Path, axioms: set[str], rules: dict[str, str], strict: bool = False
) -> list[str]:
    """Check a JSON manifest for valid axiom/rule references."""
    errors = []
    if not file_path.exists():
        return []

    try:
        data = json.loads(file_path.read_text())
        automode = data.get("autoMode", {})
        for key in ["soft_deny", "block", "allow"]:
            rules_list = automode.get(key, [])
            for rule_str in rules_list:
                # Format: R#.# Title (A#): ...
                r_ref_match = re.search(r"^(R\d+\.\d+)", rule_str)
                a_ref_match = re.search(r"\((A\d+)\)", rule_str)

                # Skip if it doesn't look like an aops rule at all (non-strict mode)
                if not r_ref_match and not a_ref_match:
                    if strict:
                        errors.append(
                            f"{file_path.name}: Rule string missing both R#.# and (A#): {rule_str[:50]}..."
                        )
                    continue

                if not r_ref_match:
                    errors.append(
                        f"{file_path.name}: Rule string missing R#.# label: {rule_str[:50]}..."
                    )
                    continue

                r_ref = r_ref_match.group(1)

                # Check if R#.# exists in RULES.md
                if r_ref not in rules:
                    errors.append(
                        f"{file_path.name}: Cited rule {r_ref} does not exist in RULES.md"
                    )

                # Check for (A#) back-pointer
                if not a_ref_match:
                    errors.append(f"{file_path.name}: Rule {r_ref} missing (A#) back-pointer")
                    continue

                a_ref = a_ref_match.group(1)

                # Check if A# exists in AXIOMS.md
                if a_ref not in axioms:
                    errors.append(
                        f"{file_path.name}: Cited axiom {a_ref} in rule {r_ref} does not exist in AXIOMS.md"
                    )

                # Check if R#.# belongs to A# in RULES.md
                if r_ref in rules and rules[r_ref] != a_ref:
                    errors.append(
                        f"{file_path.name}: Rule {r_ref} cites Axiom {a_ref}, but RULES.md says it belongs to {rules[r_ref]}"
                    )

    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"{file_path.name}: Failed to parse or read: {e}")

    return errors


def main() -> int:
    # Resolve project root relative to this script
    root = Path(__file__).parent.parent.parent.resolve()
    axioms_file = root / "aops-core" / "AXIOMS.md"
    rules_file = root / "aops-core" / "RULES.md"

    axioms = get_axiom_ids(axioms_file)
    rules = get_rules(rules_file)

    all_errors = []

    # 1. Check for missing files
    if not axioms:
        all_errors.append("AXIOMS.md: No axioms found or file missing")
    if not rules:
        all_errors.append("RULES.md: No rules found or file missing")

    # 2. Check RULES.md consistency (rules must sit under a valid axiom)
    for r_id, a_id in rules.items():
        if a_id not in axioms:
            all_errors.append(
                f"RULES.md: Rule {r_id} sits under Axiom {a_id} which does not exist in AXIOMS.md"
            )

    # 3. Check manifests
    # aops-core/.claude-plugin/plugin.json is STRICT
    plugin_json = root / "aops-core" / ".claude-plugin" / "plugin.json"
    all_errors.extend(lint_manifest(plugin_json, axioms, rules, strict=True))

    # polecat/defaults/claude-settings.json is NON-STRICT (contains CC defaults)
    settings_json = root / "polecat" / "defaults" / "claude-settings.json"
    all_errors.extend(lint_manifest(settings_json, axioms, rules, strict=False))

    if all_errors:
        print(f"FAIL: {len(all_errors)} axiom/rule reference issue(s) found:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("OK: All axiom and rule references are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
