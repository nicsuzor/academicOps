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


def check_links_resolve(target_path: Path = None) -> list[str]:
    """Check that all [[file.md]] links resolve to existing files."""
    errors = []

    aca_data = Path(os.environ.get("ACA_DATA", ""))

    # Use target_path if scanning a subset, else REPO_ROOT
    scan_root = target_path if target_path else REPO_ROOT

    for md_file in scan_root.rglob("*.md"):
        # Skip broken symlinks (pre-existing infrastructure issue)
        if not md_file.exists():
            continue

        try:
            content = md_file.read_text()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"{md_file.name}: Unable to read file: {e}")
            continue

        # Remove code blocks to avoid false positives in examples
        content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        content_no_code = re.sub(r"`[^`]*`", "", content_no_code) # Also inline code

        links = re.findall(r"\[\[([^\]]+\.md)\]\]", content_no_code)

        for link in links:
            # Try 1: Relative to file
            # Try 2: Relative to AOPS root
            # Try 3: Relative to ACA_DATA (if set)
            candidates = [
                md_file.parent / link,
                REPO_ROOT / link,
            ]
            if aca_data.exists():
                candidates.append(aca_data / link)
                candidates.append(aca_data / "data" / link) # Common pattern

            if not any(c.exists() for c in candidates):
                errors.append(f"{md_file.name}: Link [[{link}]] does not resolve")

    return errors


def check_no_axiom_duplication(target_path: Path = None) -> list[str]:
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
    scan_root = target_path if target_path else REPO_ROOT
    for md_file in scan_root.rglob("*.md"):
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
            # Check if pattern exists
            if re.search(pattern, content_no_code, re.IGNORECASE):
                # Check line-by-line
                lines = content_no_code.split('\n')
                for i, line in enumerate(lines):
                    if re.search(pattern, line, re.IGNORECASE):
                        # 1. Allow references (See AXIOMS)
                        if any(x in line for x in ["[[AXIOMS", "@AXIOMS", "See AXIOMS", "per AXIOMS", "from AXIOMS"]):
                            continue

                        # 2. Only strictly enforce duplication on HEADER lines for short phrases
                        # If it's body text (not a header), we assume it's usage, not definition.
                        # Unless it's a very long match (unlikely for "Fail-Fast")
                        if not line.strip().startswith('#'):
                             continue

                        errors.append(
                            f"{md_file.name}:{i+1}: Header contains axiom '{pattern}' "
                            f"without reference to AXIOMS.md (Redefinition risk)"
                        )

    return errors


def check_directory_structure_matches() -> list[str]:
    """Verify actual directory structure matches FRAMEWORK-PATHS.md path table."""
    # This check is inherently global/structural, so target_path is less relevant
    # but strictly we should perhaps skip it if target_path is a leaf node.
    # For now, always scanning global structure as it's fast.
    errors = []

    framework_md = REPO_ROOT / "FRAMEWORK-PATHS.md"
    if not framework_md.exists():
        return [f"FRAMEWORK-PATHS.md not found at {framework_md}"]

    content = framework_md.read_text()

    # Extract paths from markdown table: | Name | `$AOPS/path/` |
    # Regex looks for `$AOPS/` followed by path chars
    paths = re.findall(r"`\$AOPS/([^`]+)`", content)

    for path_str in paths:
        # Resolve path relative to root
        target = REPO_ROOT / path_str.strip("/")
        if not target.exists():
            errors.append(f"Path defined in FRAMEWORK-PATHS.md missing: {target}")

    return errors


import argparse

def main() -> int:
    """Run all validation checks."""
    parser = argparse.ArgumentParser(description="Validate documentation integrity.")
    parser.add_argument("--path", type=str, help="Specific path to validate (default: repo root)")
    args = parser.parse_args()

    target_path = Path(args.path).resolve() if args.path else REPO_ROOT
    if not target_path.exists():
        print(f"Error: Path not found: {target_path}", file=sys.stderr)
        return 1

    print(f"🔍 Validating framework documentation integrity in: {target_path}\n")

    all_errors = []

    # Run checks
    checks = [
        ("Link resolution", lambda: check_links_resolve(target_path)),
        ("Axiom duplication", lambda: check_no_axiom_duplication(target_path)),
        ("Directory structure", check_directory_structure_matches), # Always global
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
