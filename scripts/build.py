#!/usr/bin/env python3
"""
Simple Build script for AcademicOps plugins.
Assembles dist versions of the plugins based on client-specific files.
"""

import argparse
import os
import shutil
import re
import json
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

        import json
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDES]

            rel_root = Path(root).relative_to(src_dir)
            dst_root = dist_dir / rel_root
            dst_root.mkdir(parents=True, exist_ok=True)

            for file in files:
                if file in EXCLUDES:
                    continue

                src_file = Path(root) / file

                if file.endswith(".template.json"):
                    stem = file[:-14]
                    
                    with open(src_file) as f:
                        template = json.load(f)
                        
                    data = template.get("__base__", {}).copy()
                    client_data = template.get(client, {})
                    
                    for k, v in client_data.items():
                        if isinstance(v, dict) and k in data and isinstance(data[k], dict):
                            data[k].update(v)
                        else:
                            data[k] = v
                            
                    if stem == "mcp" and client == "antigravity":
                        if "mcpServers" in data and "pkb" in data["mcpServers"]:
                            # Workaround for antigravity-cli#390: agy doesn't resolve ${extensionPath}
                            # and runs MCP servers from the workspace cwd, so relative paths fail.
                            # For GitHub users who don't run `make install-agy`, we must use bash -c
                            # with tilde expansion to the default install location.
                            data["mcpServers"]["pkb"]["args"] = [
                                "-c",
                                f"~/.gemini/config/plugins/{plugin_name}/scripts/run-mcp.sh"
                            ]
                    elif stem == "hooks" and client == "antigravity":
                        if "hooks" in data:
                            for events in data["hooks"].values():
                                for event in events:
                                    for hook in event.get("hooks", []):
                                        if "command" in hook:
                                            hook["command"] = hook["command"].replace("${AGY_PLUGIN_ROOT}", ".")
                            
                    # determine destination
                    if stem == plugin_name:
                        if client == "claude":
                            dst_file = dist_dir / ".claude-plugin" / "plugin.json"
                        else:
                            dst_file = dist_dir / "plugin.json"
                    elif stem == "hooks":
                        dst_file = dist_dir / "hooks.json"
                    elif stem == "mcp":
                        if client == "claude":
                            dst_file = dist_dir / ".mcp.json"
                        else:
                            dst_file = dist_dir / "mcp_config.json"
                    else:
                        dst_file = dist_dir / rel_root / f"{stem}.json"
                        
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(dst_file, "w") as f:
                        json.dump(data, f, indent=2)
                    continue
                    
                # Skip the old specific files that might still be lingering
                if any(file.endswith(suffix) for suffix in [
                    ".claude.json", ".agy.json",
                    ".claude-plugin.json", ".antigravity-plugin.json"
                ]):
                    continue
                    
                # Handle commands to skills for agy
                if rel_root.parts and rel_root.parts[0] == "commands" and file.endswith(".md"):
                    if client == "antigravity":
                        skill_name = file[:-3]
                        dst_file = dist_dir / "skills" / f"cmd-{skill_name}" / "SKILL.md"
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        content = src_file.read_text(encoding="utf-8")
                        content = re.sub(r"(?m)^type:\s*command\s*$", "type: skill", content)
                        dst_file.write_text(content, encoding="utf-8")
                    else:
                        dst_file = dist_dir / file
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                    continue

                dst_file = dst_root / file
                dst_file.parent.mkdir(parents=True, exist_ok=True)
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
