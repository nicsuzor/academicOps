import json
import sys
from pathlib import Path

# Add aops-core to path so we can import lib.lint_axiom_refs
root = Path(__file__).parent.parent.parent.resolve()
if str(root / "aops-core") not in sys.path:
    sys.path.insert(0, str(root / "aops-core"))

from lib.lint_axiom_refs import get_axiom_ids, get_rules, lint_manifest


def test_lint_logic(tmp_path):
    # Setup synthetic files
    axioms_file = tmp_path / "AXIOMS.md"
    axioms_file.write_text("## A1 — Title\n## A2 — Title\n")

    rules_file = tmp_path / "RULES.md"
    rules_file.write_text("## A1\n### R1.1\n### R1.2\n## A2\n### R2.1\n")

    plugin_json = tmp_path / "plugin.json"
    plugin_json.write_text(
        json.dumps(
            {
                "autoMode": {
                    "soft_deny": ["R1.1 Title (A1): description", "R2.1 Title (A2): description"]
                }
            }
        )
    )

    axioms = get_axiom_ids(axioms_file)
    rules = get_rules(rules_file)

    # Test Pass
    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert not errors, f"Expected no errors, got: {errors}"

    # Test Fail: Missing R# in RULES.md
    plugin_json.write_text(json.dumps({"autoMode": {"soft_deny": ["R3.1 (A1): ..."]}}))
    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert any("Cited rule R3.1 does not exist in RULES.md" in e for e in errors)

    # Test Fail: Missing A# in AXIOMS.md
    plugin_json.write_text(json.dumps({"autoMode": {"soft_deny": ["R1.1 (A3): ..."]}}))
    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert any("Cited axiom A3 in rule R1.1 does not exist in AXIOMS.md" in e for e in errors)

    # Test Fail: R# sits under different A# in RULES.md
    plugin_json.write_text(json.dumps({"autoMode": {"soft_deny": ["R1.1 (A2): ..."]}}))
    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert any("Rule R1.1 cites Axiom A2, but RULES.md says it belongs to A1" in e for e in errors)

    # Test Fail: Missing back-pointer
    plugin_json.write_text(json.dumps({"autoMode": {"soft_deny": ["R1.1: description"]}}))
    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert any("missing (A#) back-pointer" in e for e in errors)

    # Test Fail: Missing R# label
    plugin_json.write_text(json.dumps({"autoMode": {"soft_deny": ["(A1): description"]}}))
    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert any("missing R#.# label" in e for e in errors)


def test_rules_consistency():
    # Synthetic data
    axioms = {"A1"}
    rules = {"R1.1": "A1", "R2.1": "A2"}  # A2 missing from axioms

    # Simulate consistency check from main
    all_errors = []
    for r_id, a_id in rules.items():
        if a_id not in axioms:
            all_errors.append(
                f"RULES.md: Rule {r_id} sits under Axiom {a_id} which does not exist in AXIOMS.md"
            )

    assert any(
        "Rule R2.1 sits under Axiom A2 which does not exist in AXIOMS.md" in e for e in all_errors
    )


def test_lint_real_files(repo_root):
    """Smoke test on real files to ensure linter passes currently."""
    axioms_file = repo_root / "aops-core" / "AXIOMS.md"
    rules_file = repo_root / "aops-core" / "RULES.md"
    plugin_json = repo_root / "aops-core" / ".claude-plugin" / "plugin.json"

    axioms = get_axiom_ids(axioms_file)
    rules = get_rules(rules_file)

    assert axioms, "AXIOMS.md should have axiom IDs"
    assert rules, "RULES.md should have rules"

    errors = lint_manifest(plugin_json, axioms, rules, strict=True)
    assert not errors, f"Linter failed on real files: {errors}"
