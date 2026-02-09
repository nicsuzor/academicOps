#!/usr/bin/env python3
"""
Bump the version using git tags (dynamic versioning).
"""

import subprocess
import sys
from pathlib import Path


def get_current_version(aops_root: Path) -> str:
    # Use build.py logic to get current version
    script_path = aops_root / "scripts" / "build.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--version"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def bump_version(aops_root: Path):
    old_version = get_current_version(aops_root)
    parts = old_version.split(".")
    if len(parts) != 3:
        # Handle cases like 0.1.38.dev1
        parts = parts[:3]
        if len(parts) != 3:
            print(f"Error: version '{old_version}' is not in semver format.")
            sys.exit(1)

    # Bump patch version
    major, minor, patch = parts
    new_version = f"{major}.{minor}.{int(patch) + 1}"
    tag_name = f"v{new_version}"

    print(f"Bumping version from {old_version} to {new_version}...")

    # Create git tag
    try:
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"release {tag_name}"], check=True)
        print(f"Successfully created tag {tag_name}")
        
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        branch = branch_result.stdout.strip()
        print(f"Remember to push atomically: git push origin {branch} {tag_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating tag: {e}")
        sys.exit(1)

    return new_version


if __name__ == "__main__":
    aops_root = Path(__file__).parent.parent.resolve()
    bump_version(aops_root)
