#!/usr/bin/env python3
"""
Bump the version in pyproject.toml.
"""

import re
import sys
from pathlib import Path


def bump_version(aops_root: Path):
    pyproject_path = aops_root / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found.")
        sys.exit(1)

    content = pyproject_path.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        print("Error: version not found in pyproject.toml.")
        sys.exit(1)

    old_version = match.group(1)
    parts = old_version.split(".")
    if len(parts) != 3:
        print(f"Error: version '{old_version}' is not in semver format.")
        sys.exit(1)

    # Bump patch version
    major, minor, patch = parts
    new_version = f"{major}.{minor}.{int(patch) + 1}"

    new_content = content.replace(
        f'version = "{old_version}"', f'version = "{new_version}"'
    )
    pyproject_path.write_text(new_content)

    print(f"Bumped version from {old_version} to {new_version}")
    return new_version


if __name__ == "__main__":
    aops_root = Path(__file__).parent.parent.resolve()
    bump_version(aops_root)
