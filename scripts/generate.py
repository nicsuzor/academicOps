#!/usr/bin/env python3
"""
Manifest-driven code generator for academicOps.
Transforms canonical source into runtime-specific adapter output.
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import cast

from manifest import MANIFEST
from transforms import apply_transforms

ROOT_DIR = Path(__file__).parent.parent.resolve()
DIST_DIR = ROOT_DIR / "dist"


def sanitize_version(version: str) -> str:
    import re

    if "-testing." in version:
        return version.replace("-testing.", "-dev.")
    version = re.sub(r"\.dev(\d+)", r"-dev.\1", version)
    return version


def get_git_commit_sha(root: Path) -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if sha.returncode == 0 and sha.stdout.strip():
            return sha.stdout.strip()
    except Exception:
        pass
    return ""


def get_project_version(root: Path) -> str:
    try:
        result = subprocess.run(
            ["uv", "tree", "--depth", "0"], cwd=root, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "academicops v" in line:
                    version = line.split(" v")[1].split(" ")[0]
                    return sanitize_version(version)
    except Exception:
        pass
    return "0.1.0"


def get_output_path(src_path: Path, runtime: str) -> Path:
    """Compute the destination path based on the source prefix."""
    try:
        rel_path = src_path.relative_to(ROOT_DIR)
    except ValueError:
        rel_path = src_path

    parts = rel_path.parts
    if parts[0] == "aops-core":
        dest_root = DIST_DIR / f"aops-{runtime}"
        out_rel = Path(*parts[1:])
    elif parts[0] == "aops-tools":
        dest_root = DIST_DIR / f"aops-tools-{runtime}"
        out_rel = Path(*parts[1:])
    else:
        # Fallback for unexpected paths
        dest_root = DIST_DIR / f"other-{runtime}"
        out_rel = rel_path

    return dest_root / out_rel


def matches_exclude(path: Path, excludes: list[str]) -> bool:
    for ex in excludes:
        if path.match(ex):
            return True
        # For directory exclusions like aops-core/**/__pycache__/*
        if "__pycache__" in ex and "__pycache__" in path.parts:
            return True
        if ".*" in ex and any(p.startswith(".") for p in path.parts):
            return True
    return False


def generate_metadata(version: str, runtime: str, package: str):
    """Generate platform-specific metadata (pyproject.toml, plugin.json)."""
    dest_root = DIST_DIR / (
        f"aops-{runtime}" if package == "aops-core" else f"aops-tools-{runtime}"
    )
    dest_root.mkdir(parents=True, exist_ok=True)

    # 1. pyproject.toml
    if package == "aops-core":
        pyproject = f"""\
[project]
name = "aops-core"
version = "{version}"
description = "Core academicOps framework - skills, agents, and hooks for research workflow automation"
requires-python = ">=3.11"
license = "MIT"
authors = [
  {{ name = "Nicolas Suzor" }},
]
keywords = ["academicOps", "research", "framework", "workflow", "mcp"]
dependencies = [
  "pyyaml>=6.0",
  "pydantic>=2.0",
  "filelock>=3.13.0",
  "psutil>=5.9.0",
]

[tool.hatch.build.targets.wheel]
packages = ["lib", "hooks"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
        (dest_root / "pyproject.toml").write_text(pyproject)

    elif package == "aops-tools":
        pyproject = f"""\
[project]
name = "aops-tools"
version = "{version}"
description = "Scientific operations tools for academicOps"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "fastmcp>=2.13.1",
]

[tool.hatch.build.targets.wheel]
packages = ["skills", "lib"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
        (dest_root / "pyproject.toml").write_text(pyproject)

    # 2. Extension manifests
    src_manifest = ROOT_DIR / "templates" / f"{package}.{runtime}-extension.json"
    if runtime == "gemini" and src_manifest.exists():
        manifest = json.loads(src_manifest.read_text())
        manifest["version"] = version
        with open(dest_root / "gemini-extension.json", "w") as f:
            json.dump(manifest, f, indent=2)

    src_plugin = ROOT_DIR / "templates" / f"{package}.plugin.json"
    if runtime == "claude" and src_plugin.exists():
        claude_dir = dest_root / ".claude-plugin"
        claude_dir.mkdir(exist_ok=True)
        manifest = json.loads(src_plugin.read_text())
        manifest["version"] = version
        manifest.pop("source", None)
        manifest.pop("category", None)
        manifest.pop("userConfig", None)
        with open(claude_dir / "plugin.json", "w") as f:
            json.dump(manifest, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean", action="store_true", help="Clean dist directory before generating"
    )
    args = parser.parse_args()

    if args.clean and DIST_DIR.exists():
        print(f"Cleaning {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)

    version = get_project_version(ROOT_DIR)
    print(f"Generating academicOps version {version}...")

    written_files = set()

    for rule in MANIFEST:
        src_glob = cast(str, rule["src_glob"])
        excludes = cast(list[str], rule.get("exclude", []))
        transforms = cast(list[str], rule.get("transforms", []))
        runtimes = cast(list[str], rule.get("runtimes", []))

        # Find matches
        matches = list(ROOT_DIR.glob(src_glob))
        for match in matches:
            if not match.is_file():
                continue

            if matches_exclude(match, excludes):
                continue

            for runtime in runtimes:
                ctx = {"filename": match.name, "platform": runtime}
                out_path = get_output_path(match, runtime)
                out_path.parent.mkdir(parents=True, exist_ok=True)

                if not transforms:
                    shutil.copy2(match, out_path)
                else:
                    try:
                        # Only read text if we have transforms
                        content = match.read_text()
                        transformed = apply_transforms(content, transforms, ctx)
                        out_path.write_text(transformed)
                    except Exception as e:
                        print(f"Error transforming {match} for {runtime}: {e}")
                        continue

                written_files.add(out_path)

    # Generate metadata for both packages and runtimes
    for pkg in ["aops-core", "aops-tools"]:
        for rt in ["gemini", "claude"]:
            generate_metadata(version, rt, pkg)

    print(f"Generation complete. Wrote {len(written_files)} source files + metadata.")


if __name__ == "__main__":
    main()
