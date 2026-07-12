#!/usr/bin/env python3
"""
Simple Build script for AcademicOps plugins.
Assembles dist versions of the plugins based on client-specific files.
"""

import argparse
import os
import shutil
from pathlib import Path

# Directories to exclude from copying
EXCLUDES = {
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    ".venv", ".uv-cache", ".git", ".DS_Store"
}

def build_plugin(plugin_name: str, src_dir: Path, dist_root: Path):
    print(f"Building {plugin_name}...")

    for client in ["claude", "antigravity"]:
        if plugin_name == "aops-ts" and client == "antigravity":
            continue

        dist_dir = dist_root / f"{plugin_name}-{client}"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True)

        # Determine suffixes
        hook_suffix = ".claude.json" if client == "claude" else ".agy.json"
        plugin_suffix = ".claude-plugin.json" if client == "claude" else ".antigravity-plugin.json"
        mcp_suffix = ".claude.json" if client == "claude" else ".agy.json"

        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDES]

            rel_root = Path(root).relative_to(src_dir)
            dst_root = dist_dir / rel_root
            dst_root.mkdir(parents=True, exist_ok=True)

            for file in files:
                if file in EXCLUDES:
                    continue

                src_file = Path(root) / file

                # Check for client-specific hooks file
                if file == f"hooks{hook_suffix}":
                    if client == "claude":
                        # Claude expects hooks in hooks/hooks.json
                        hooks_dir = dist_dir / "hooks"
                        hooks_dir.mkdir(exist_ok=True)
                        dst_file = hooks_dir / "hooks.json"
                    else:
                        # Antigravity expects hooks in root as hooks.json
                        dst_file = dist_dir / "hooks.json"

                # Check for client-specific plugin manifest
                elif file == f"{plugin_name}{plugin_suffix}":
                    if client == "claude":
                        # Claude expects manifest in .claude-plugin/plugin.json
                        manifest_dir = dist_dir / ".claude-plugin"
                        manifest_dir.mkdir(exist_ok=True)
                        dst_file = manifest_dir / "plugin.json"
                    else:
                        # Antigravity expects manifest in root as plugin.json
                        dst_file = dist_dir / "plugin.json"

                # Check for client-specific MCP config
                # We assume naming convention like mcp.claude.json or mcp.agy.json
                elif file == f"mcp{mcp_suffix}":
                    if client == "claude":
                        # Claude expects .mcp.json at root
                        dst_file = dist_dir / ".mcp.json"
                    else:
                        # Antigravity expects mcp_config.json at root
                        dst_file = dist_dir / "mcp_config.json"

                # Skip files intended for the other client or other templates
                elif any(file.endswith(suffix) for suffix in [
                    ".claude.json", ".agy.json",
                    ".claude-plugin.json", ".antigravity-plugin.json"
                ]):
                    continue
                else:
                    dst_file = dst_root / file

                shutil.copy2(src_file, dst_file)

        # Cleanup any empty directories that might have been left over
        for dirpath, dirnames, filenames in os.walk(dist_dir, topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)

        import tarfile
        archive_name = f"{dist_dir.name}.tar.gz"
        archive_path = dist_root / archive_name

        with tarfile.open(archive_path, "w:gz") as tar:
            if client == "claude":
                # Claude expects the directory itself inside the archive
                tar.add(dist_dir, arcname=dist_dir.name)
            else:
                # Antigravity expects contents at the root of the archive
                tar.add(dist_dir, arcname=".")

        print(f"  ✓ Built {dist_dir.name} and packaged into {archive_name}")

def generate_local_marketplace(dist_root: Path):
    """Generate the local marketplace JSON so claude can install from dist/."""
    import json
    marketplace_dir = dist_root / ".claude-plugin"
    marketplace_dir.mkdir(exist_ok=True)
    marketplace = {
        "name": "aops",
        "description": "Local dev marketplace",
        "owner": {
            "name": "Local Dev"
        },
        "plugins": [
            {
                "name": "aops-core",
                "source": "./aops-core-claude"
            },
            {
                "name": "aops",
                "source": "./aops-claude"
            },
            {
                "name": "aops-tools",
                "source": "./aops-tools-claude"
            },
            {
                "name": "aops-ts",
                "source": "./aops-ts-claude"
            }
        ]
    }
    with open(marketplace_dir / "marketplace.json", "w") as f:
        json.dump(marketplace, f, indent=2)
    print("✓ Generated local marketplace.json")

def main():
    parser = argparse.ArgumentParser(description="Simple build script for plugins")
    parser.add_argument("--plugins", nargs="+", default=["aops-core", "aops", "aops-tools", "aops-ts"], help="Plugins to build")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    dist_root = project_root / "dist"

    dist_root.mkdir(exist_ok=True)

    for plugin in args.plugins:
        src_dir = project_root / plugin
        if not src_dir.exists():
            print(f"Warning: Plugin source {src_dir} does not exist. Skipping.")
            continue
        build_plugin(plugin, src_dir, dist_root)

    generate_local_marketplace(dist_root)

if __name__ == "__main__":
    main()
