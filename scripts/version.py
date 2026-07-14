#!/usr/bin/env python3
"""
Simple versioning utility for AcademicOps.
Supports getting current version and computing next prerelease version.
"""

import argparse
import re
import subprocess
from pathlib import Path

def get_pyproject_version(aops_root: Path) -> str:
    pyproject_path = aops_root / "pyproject.toml"
    if not pyproject_path.exists():
        return "0.1.0"
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    return "0.1.0"

def _git_build_metadata(aops_root: Path) -> str:
    try:
        sha_res = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if sha_res.returncode != 0:
            return ""
        sha = sha_res.stdout.strip()
        if not sha:
            return ""
        
        dirty_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        is_dirty = dirty_res.returncode == 0 and bool(dirty_res.stdout.strip())
        return f"g{sha}{'.dirty' if is_dirty else ''}"
    except Exception:
        return ""

def get_current_version(aops_root: Path) -> str:
    version = get_pyproject_version(aops_root)
    if "+" in version:
        return version
    meta = _git_build_metadata(aops_root)
    if not meta:
        return version
    if "dirty" in meta and "-" not in version:
        # Bump patch to dev version if dirty and not a prerelease
        parts = version.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            major, minor, patch = parts
            version = f"{major}.{minor}.{int(patch) + 1}-dev.0"
    return f"{version}+{meta}"

_STABLE_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

def _git_tags(aops_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "tag", "--list"],
            capture_output=True,
            text=True,
            cwd=aops_root,
            check=True,
        )
        return [t.strip() for t in result.stdout.splitlines() if t.strip()]
    except Exception:
        return []

def latest_stable_patch(aops_root: Path, major: int, minor: int) -> int | None:
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
    if base_override:
        base_version = base_override.lstrip("v")
    else:
        base = re.split(r"[-+]", current)[0]
        parts = (base.split(".") + ["0", "0", "0"])[:3]
        major, minor, patch = (int(p) for p in parts)
        last = latest_stable_patch(aops_root, major, minor)
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

    if args.prerelease is not None:
        current = get_current_version(aops_root)
        print(next_prerelease(aops_root, current, label=args.prerelease, base_override=args.base))
        return

    if args.get:
        print(get_current_version(aops_root))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
