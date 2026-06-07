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
    script_path = aops_root / "scripts" / "build.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


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


# --- Prerelease / tag helpers ---------------------------------------------------
#
# Stable versions are owned by release-please (see .release-please-manifest.json).
# Prereleases are NOT: they are hand-cut testing builds, tagged vX.Y.Z-<label>.N,
# which build-extension.yml ships as a `--prerelease` GitHub Release without
# touching main. We compute the prerelease BASE from the latest *stable* git tag
# in the current MAJOR.MINOR series — NOT from the manifest (which can lag behind
# hand-pushed tags) and NOT from a naive max over all tags (the tag namespace
# carries stray vX.Y.Z lines, e.g. old v1.0.0 experiments). This preserves the
# semver invariant the installers need: a prerelease sorts ABOVE the last stable
# in its series and BELOW the next stable.

_STABLE_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _git_tags(aops_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "tag", "--list"],
        capture_output=True,
        text=True,
        cwd=aops_root,
        check=True,
    )
    return [t.strip() for t in result.stdout.splitlines() if t.strip()]


def latest_stable_patch(aops_root: Path, major: int, minor: int) -> int | None:
    """Highest PATCH of a stable vMAJOR.MINOR.PATCH tag in the series, or None."""
    best: int | None = None
    for tag in _git_tags(aops_root):
        m = _STABLE_TAG_RE.match(tag)
        if not m:
            continue
        tmaj, tmin, tpat = (int(g) for g in m.groups())
        if tmaj == major and tmin == minor and (best is None or tpat > best):
            best = tpat
    return best


def next_prerelease(
    aops_root: Path,
    current: str,
    label: str = "beta",
    base_override: str | None = None,
) -> str:
    """Compute the next ``X.Y.Z-<label>.N`` prerelease version (auto-incrementing N)."""
    if base_override:
        base_version = base_override.lstrip("v")
    else:
        base = re.split(r"[-+]", current)[0]
        parts = (base.split(".") + ["0", "0", "0"])[:3]
        major, minor, patch = (int(p) for p in parts)
        last = latest_stable_patch(aops_root, major, minor)
        # One patch above the latest shipped stable in this series; if the series
        # has no stable tag yet, fall back to the current base patch.
        base_patch = last + 1 if last is not None else patch
        base_version = f"{major}.{minor}.{base_patch}"

    pre_re = re.compile(rf"^v{re.escape(base_version)}-{re.escape(label)}\.(\d+)$")
    highest = -1
    for tag in _git_tags(aops_root):
        m = pre_re.match(tag)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{base_version}-{label}.{highest + 1}"


def main():
    parser = argparse.ArgumentParser(description="AcademicOps versioning utility")
    parser.add_argument("--get", action="store_true", help="Get current version")
    parser.add_argument(
        "--next", choices=["major", "minor", "patch"], default="patch", help="Suggest next version"
    )
    parser.add_argument(
        "--bump", choices=["major", "minor", "patch"], help="Perform version bump (create tag)"
    )
    parser.add_argument(
        "--prerelease",
        nargs="?",
        const="beta",
        default=None,
        metavar="LABEL",
        help="Print next prerelease version X.Y.Z-LABEL.N (default LABEL: beta)",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Override the base version for --prerelease (e.g. 0.4.0)",
    )

    args = parser.parse_args()
    aops_root = Path(__file__).parent.parent.resolve()

    current = get_current_version(aops_root)

    if args.prerelease is not None:
        print(next_prerelease(aops_root, current, label=args.prerelease, base_override=args.base))
        return

    if args.get:
        print(current)
    elif args.bump:
        next_v = bump_semver(current, args.bump)
        tag_name = f"v{next_v}"
        print(f"Bumping {current} -> {next_v}...")
        try:
            # 1. Update version in pyproject.toml
            pyproject_path = aops_root / "pyproject.toml"
            if pyproject_path.exists():
                content = pyproject_path.read_text()
                new_content = re.sub(
                    r'(version\s*=\s*")[^"]+(")', rf"\g<1>{next_v}\g<2>", content, count=1
                )
                pyproject_path.write_text(new_content)
                print("  ✓ Updated pyproject.toml")

            # 2. Update version in template files consistent with release-please config
            extra_files = [
                "templates/aops-core.gemini-extension.json",
                "templates/aops-core.plugin.json",
                "templates/aops-tools.gemini-extension.json",
                "templates/aops-tools.plugin.json",
            ]
            template_paths = []
            for rel_path in extra_files:
                p = aops_root / rel_path
                if p.exists():
                    content = p.read_text()
                    new_content = re.sub(
                        r'("version"\s*:\s*")\d+\.\d+\.\d+[^"]*(")',
                        rf"\g<1>{next_v}\g<2>",
                        content,
                        count=1,
                    )
                    p.write_text(new_content)
                    print(f"  ✓ Updated {rel_path}")
                    template_paths.append(rel_path)

            # 3. Run uv lock
            print("  Running uv lock...")
            subprocess.run(["uv", "lock"], cwd=aops_root, check=True)
            print("  ✓ Updated uv.lock")

            # 4. Commit updated files
            files_to_commit = ["pyproject.toml", "uv.lock"] + template_paths
            subprocess.run(["git", "add"] + files_to_commit, cwd=aops_root, check=True)

            commit_msg = f"chore: bump version to {next_v}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=aops_root, check=True)
            print("  ✓ Committed version bump files")

            # 5. Create tag
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
