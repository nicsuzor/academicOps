#!/usr/bin/env -S uv run python
"""
Versioning utility for AcademicOps.
Supports getting current version and suggesting/performing bumps.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_current_version(aops_root: Path) -> str:
    # Try to get version from scripts/build.py
    script_path = aops_root / "scripts" / "build.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        # Fallback to reading pyproject.toml directly
        pyproject_path = aops_root / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
    return "0.1.0"


def bump_semver(version: str, part: str = "patch") -> str:
    # If it's already a pre-release (e.g., 0.3.14-dev.42),
    # the "next" stable version is just the base version (0.3.14)
    # unless we explicitly want to jump to the next major/minor.
    is_prerelease = "-" in version or "+" in version
    base_version = re.split(r"[-+]", version)[0]

    if is_prerelease and part == "patch":
        # Current: 0.3.14-dev.42 -> Next: 0.3.14
        return base_version

    parts = base_version.split(".")
    # Ensure we have 3 parts
    while len(parts) < 3:
        parts.append("0")

    major, minor, patch = map(int, parts[:3])

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def main():
    parser = argparse.ArgumentParser(description="AcademicOps versioning utility")
    parser.add_argument("--get", action="store_true", help="Get current version")
    parser.add_argument(
        "--next", choices=["major", "minor", "patch"], default="patch", help="Suggest next version"
    )
    parser.add_argument(
        "--bump", choices=["major", "minor", "patch"], help="Perform version bump (create tag)"
    )

    args = parser.parse_args()
    aops_root = Path(__file__).parent.parent.resolve()

    current = get_current_version(aops_root)

    if args.get:
        print(current)
    elif args.bump:
        next_v = bump_semver(current, args.bump)
        tag_name = f"v{next_v}"
        print(f"Bumping {current} -> {next_v}...")
        try:
            subprocess.run(["git", "tag", "-a", tag_name, "-m", f"release {tag_name}"], check=True)
            print(f"Created tag {tag_name}")

            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            print(f"Run: git push origin {branch} {tag_name}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Default is --next patch
        print(bump_semver(current, args.next))


if __name__ == "__main__":
    main()
