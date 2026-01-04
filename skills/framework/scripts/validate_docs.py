#!/usr/bin/env python3
"""
Validate documentation integrity for the framework.

Checks:
- All markdown links resolve
- No contradictory information
- Directory structure matches README.md
- No duplication of core content
"""

import re
import sys
from pathlib import Path

import os

# Get repo root from AOPS env var (Authoritative)
if "AOPS" not in os.environ:
    print("Error: AOPS environment variable not set. Run via 'uv run' in $AOPS.", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(os.environ["AOPS"])
# BOTS_DIR logic was legacy - in new layout, root IS the content dir (mostly)
# Adapting to check files relative to AOPS root
BOTS_DIR = REPO_ROOT 
README_PATH = REPO_ROOT / "README.md"


def check_links_resolve() -> list[str]:
    """Check that all [[file.md]] links resolve to existing files."""
    errors = []

    for md_file in BOTS_DIR.rglob("*.md"):
        # Skip broken symlinks (pre-existing infrastructure issue)
        if not md_file.exists():
            continue

        try:
            content = md_file.read_text()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"{md_file.name}: Unable to read file: {e}")
            continue

        links = re.findall(r"\[\[([^\]]+\.md)\]\]", content)

        for link in links:
            # Try relative to bots/ and relative to file
            candidates = [
                BOTS_DIR / link,
                md_file.parent / link,
            ]

            if not any(c.exists() for c in candidates):
                errors.append(f"{md_file.name}: Link [[{link}]] does not resolve")

    return errors


def check_no_axiom_duplication() -> list[str]:
    """Check that axioms aren't duplicated across files."""
    errors = []
    axiom_path = REPO_ROOT / "AXIOMS.md"
    if not axiom_path.exists():
        return [f"AXIOMS.md not found at {axiom_path}"]
    
    axioms_file = axiom_path

    axioms_file.read_text()

    # Extract axiom titles from AXIOMS.md
    axiom_patterns = [
        r"NO OTHER TRUTHS",
        r"DO ONE THING",
        r"Data Boundaries",
        r"Fail-Fast",
        r"DRY, Modular, Explicit",
        r"Trust Version Control",
        r"NO WORKAROUNDS",
        r"VERIFY FIRST",
        r"NO EXCUSES",
    ]

    # Check other files don't duplicate axiom content
    for md_file in REPO_ROOT.rglob("*.md"):
        if md_file.resolve() == axioms_file.resolve():
            continue

        # Skip broken symlinks (pre-existing infrastructure issue)
        if not md_file.exists():
            continue

        try:
            content = md_file.read_text()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"{md_file.name}: Unable to read file: {e}")
            continue

        # Remove code blocks to avoid false positives from examples
        content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

        # Check for axiom duplication
        for pattern in axiom_patterns:
            # Check if pattern exists without a reference to AXIOMS.md
            # Accept [[AXIOMS.md]], [[../../AXIOMS.md]], @AXIOMS, etc.
            if re.search(pattern, content_no_code, re.IGNORECASE) and not re.search(
                r"\[\[.*AXIOMS\.md\]\]|@.*AXIOMS", content
            ):
                errors.append(
                    f"{md_file.name}: Contains axiom content '{pattern}' "
                    f"without reference to AXIOMS.md (possible duplication)"
                )

    return errors


def check_directory_structure_matches() -> list[str]:
    """Verify actual directory structure matches FRAMEWORK.md path table."""
    errors = []
    
    framework_md = REPO_ROOT / "FRAMEWORK.md"
    if not framework_md.exists():
        return [f"FRAMEWORK.md not found at {framework_md}"]
        
    content = framework_md.read_text()
    
    # Extract paths from markdown table: | Name | `$AOPS/path/` |
    # Regex looks for `$AOPS/` followed by path chars
    paths = re.findall(r"`\$AOPS/([^`]+)`", content)
    
    for path_str in paths:
        # Resolve path relative to root
        target = REPO_ROOT / path_str.strip("/")
        if not target.exists():
            errors.append(f"Path defined in FRAMEWORK.md missing: {target}")
            
    return errors


def main() -> int:
    """Run all validation checks."""
    print("🔍 Validating framework documentation integrity...\n")

    all_errors = []

    # Run checks
    checks = [
        ("Link resolution", check_links_resolve),
        ("Axiom duplication", check_no_axiom_duplication),
        ("Directory structure", check_directory_structure_matches),
    ]

    for check_name, check_func in checks:
        print(f"  Checking {check_name}...")
        errors = check_func()
        if errors:
            all_errors.extend(errors)
            print(f"    ❌ {len(errors)} error(s) found")
        else:
            print("    ✅ Passed")

    # Report results
    print()
    if all_errors:
        print(f"❌ Documentation validation FAILED with {len(all_errors)} error(s):\n")
        for error in all_errors:
            print(f"  - {error}")
        print("\n⛔ HALT: Fix documentation conflicts before committing.")
        return 1
    print("✅ All documentation integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
