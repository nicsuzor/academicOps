#!/usr/bin/env python3
"""
Build script for AcademicOps Gemini extensions.
Generates dist/aops-core, dist/aops-tools, and dist/antigravity.
"""

import os
import sys
import shutil
import json
import subprocess
from pathlib import Path

# Add shared lib to path (assuming scripts/lib exists)
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(SCRIPT_DIR / "lib"))

try:
    from build_utils import (
        convert_mcp_to_gemini,
        convert_gemini_to_antigravity,
        generate_gemini_hooks,
        safe_symlink,
        format_path_for_json,
    )
except ImportError as e:
    # Fallback if running from a different location without setting path correctly
    # or if lib structure is not yet fully set up in development
    print(f"Error: Could not import build_utils. {e}", file=sys.stderr)
    print(f"Sys Path: {sys.path}", file=sys.stderr)
    sys.exit(1)


def build_aops_core(aops_root: Path, dist_root: Path, aca_data_path: str):
    """Build the aops-core extension."""
    print("Building aops-core...")
    plugin_name = "aops-core"
    src_dir = aops_root / plugin_name
    dist_dir = dist_root / plugin_name

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Symlinks
    for item in ["skills", "GEMINI.md"]:
        src = src_dir / item
        if src.exists():
            safe_symlink(src, dist_dir / item)

    # 2. Hooks (Selective)
    # Link hook files but exclude hooks/gemini/ subdirectory (router goes to router_gemini.py)
    hooks_src = src_dir / "hooks"
    hooks_dst = dist_dir / "hooks"
    hooks_dst.mkdir(parents=True)
    if hooks_src.exists():
        for item in hooks_src.iterdir():
            if item.name == "hooks.json":
                continue
            if item.name == "gemini":
                # Don't copy gemini/ subdirectory - router goes to hooks/router_gemini.py
                continue
            # copy files or link
            # linking is better for dev, but copying safer for dist. keeping links for now as per old script
            safe_symlink(item, hooks_dst / item.name)

    # Link the Gemini router directly to hooks/router_gemini.py (not hooks/gemini/router.py)
    gemini_router_src = hooks_src / "gemini" / "router.py"
    if gemini_router_src.exists():
        safe_symlink(gemini_router_src, hooks_dst / "router_gemini.py")

    # Create templates symlink in gemini/ so user_prompt_submit.py can find templates
    # (user_prompt_submit.py uses HOOK_DIR / "templates" where HOOK_DIR is hooks/gemini/)
    gemini_templates_link = hooks_src / "gemini" / "templates"
    if not gemini_templates_link.exists():
        safe_symlink(Path("../templates"), gemini_templates_link)

    # 3. Generate Hooks Config
    hooks_json_path = hooks_src / "hooks.json"
    claude_hooks = {}
    if hooks_json_path.exists():
        try:
            with open(hooks_json_path) as f:
                claude_hooks = json.load(f).get("hooks", {})
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {hooks_json_path}")

    # The router path inside the dist directory
    # Note: when installed, the extension runs relative to itself or absolute paths
    # We use absolute paths constructed from AOPS root to ensure it finds the file
    router_script_path = dist_dir / "hooks" / "router_gemini.py"

    gemini_hooks = generate_gemini_hooks(
        claude_hooks, str(aops_root), str(router_script_path)
    )

    with open(hooks_dst / "hooks.json", "w") as f:
        json.dump({"hooks": gemini_hooks}, f, indent=2)

    # 4. Load Manifest Base and MCPs
    plugin_json_path = src_dir / ".claude-plugin" / "plugin.json"
    manifest_base = {}
    gemini_mcps = {}

    if plugin_json_path.exists():
        try:
            with open(plugin_json_path) as f:
                manifest_base = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {plugin_json_path}")

    # Resolve MCP Servers from manifest pointer or default file
    mcp_ref = manifest_base.get("mcpServers")
    if isinstance(mcp_ref, str):
        # It's a file path relative to plugin root
        mcp_path = src_dir / mcp_ref
    else:
        # It might be inline (rare for this repo) or missing
        mcp_path = src_dir / ".mcp.json"

    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                data = json.load(f)
                # Handle both wrapped "mcpServers": {...} and direct {...} formats if they exist
                # Claude usually puts them under mcpServers key
                servers_config = data.get("mcpServers", data)
                gemini_mcps = convert_mcp_to_gemini(servers_config)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {mcp_path}")

    # Inject task_manager (always required for core)
    gemini_mcps["task_manager"] = {
        "command": "uv",
        "args": [
            "run",
            "--directory",
            str(src_dir),
            "python",
            "mcp_servers/tasks_server.py",
        ],
        "env": {"AOPS": str(aops_root), "ACA_DATA": aca_data_path},
    }

    # 5. Build Final Manifest
    # Start with base keys we care about
    manifest = {
        "name": manifest_base.get("name", "aops-core"),
        "version": manifest_base.get("version", "0.1.0"),
        "description": manifest_base.get("description", "AcademicOps Core Framework"),
        "mcpServers": gemini_mcps,
        # hooksConfig is implicit in Gemini checks for hooks/hooks.json,
        # but sometimes needed in simplified settings.
    }
    with open(dist_dir / "gemini-extension.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # 6. Commands
    commands_dist = dist_dir / "commands"
    convert_script = aops_root / "scripts" / "convert_commands_to_toml.py"
    if convert_script.exists():
        subprocess.run(
            [sys.executable, str(convert_script), "--output-dir", str(commands_dist)],
            env={**os.environ, "AOPS": str(aops_root)},
            check=False,
        )

    print(f"✓ Built {plugin_name}")
    return gemini_mcps  # Return for aggregation


def build_aops_tools(aops_root: Path, dist_root: Path):
    """Build the aops-tools extension."""
    print("Building aops-tools...")
    plugin_name = "aops-tools"
    src_dir = aops_root / plugin_name
    dist_dir = dist_root / plugin_name

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Symlinks
    for item in ["skills"]:
        src = src_dir / item
        if src.exists():
            safe_symlink(src, dist_dir / item)

    # 2. Load Manifest and MCPs
    plugin_json_path = src_dir / ".claude-plugin" / "plugin.json"
    manifest_base = {}
    gemini_mcps = {}

    if plugin_json_path.exists():
        try:
            with open(plugin_json_path) as f:
                manifest_base = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {plugin_json_path}")

    # Resolve MCP Servers
    mcp_ref = manifest_base.get("mcpServers")
    if isinstance(mcp_ref, str):
        mcp_path = src_dir / mcp_ref
    else:
        mcp_path = src_dir / ".mcp.json"

    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                data = json.load(f)
                servers_config = data.get("mcpServers", data)
                gemini_mcps = convert_mcp_to_gemini(servers_config)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {mcp_path}")

    # Remove task_manager if present (core handles it)
    if "task_manager" in gemini_mcps:
        del gemini_mcps["task_manager"]

    # 3. Build Final Manifest
    manifest = {
        "name": manifest_base.get("name", "aops-tools"),
        "version": manifest_base.get("version", "0.1.0"),
        "description": manifest_base.get("description", "AcademicOps Tools"),
        "mcpServers": gemini_mcps,
    }
    with open(dist_dir / "gemini-extension.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Built {plugin_name}")
    return gemini_mcps


def build_antigravity(aops_root: Path, dist_root: Path, all_mcps: dict):
    """Build the antigravity distribution."""
    print("Building antigravity...")
    ag_dist = dist_root / "antigravity"
    if ag_dist.exists():
        shutil.rmtree(ag_dist)
    ag_dist.mkdir(parents=True)

    # 1. Global Workflows
    # In setup.sh, it linked ~/.gemini/GEMINI.md -> global_workflows/GEMINI.md
    # Here we create the structure.
    global_workflows = ag_dist / "global_workflows"
    global_workflows.mkdir()

    # We can prepare the link target for installation time, or just leave empty dir

    # 2. MCP Config (Antigravity format)
    # Convert all gathered Gemini MCPs to Antigravity format
    ag_mcps = convert_gemini_to_antigravity(all_mcps)

    with open(ag_dist / "mcp_config.json", "w") as f:
        json.dump({"mcpServers": ag_mcps}, f, indent=2)

    # 3. Rules (AXIOMS, HEURISTICS, core.md)
    rules_dist = (
        ag_dist / "rules"
    )  # Antigravity doesn't use this directly yet, usually it's .agent/rules in project
    # But maybe we want to distribute them? The setup.sh linked them to .agent/rules.
    # We will just prepare them here if we want to support a global install later,
    # but strictly speaking setup.sh links from source to project .agent/rules.
    # Let's keep them in dist for completeness so install.py can use them from dist or source.
    # We'll stick to source for now to match setup.sh logic, but maybe put a copy here.

    print("✓ Built antigravity dist")


def main():
    aops_path_str = os.environ.get("AOPS")
    aca_data_path = os.environ.get("ACA_DATA")

    if not aops_path_str or not aca_data_path:
        # Try to infer AOPS if not set
        if not aops_path_str:
            aops_path_str = str(Path(__file__).parent.parent.resolve())
            print(f"Isnfo: AOPS not set, inferred to {aops_path_str}")

        if not aca_data_path:
            print("Error: ACA_DATA environment variable must be set.")
            sys.exit(1)

    aops_root = Path(aops_path_str).resolve()
    dist_root = aops_root / "dist"

    # Clean/Create dist
    if not dist_root.exists():
        dist_root.mkdir()

    # Build components
    core_mcps = build_aops_core(aops_root, dist_root, aca_data_path)
    tools_mcps = build_aops_tools(aops_root, dist_root)

    # Aggregate MCPs for Antigravity (global config if needed)
    # Note: Antigravity usually uses project-specific mcp, but we can generate a global one too
    # setup.sh generated ~/.gemini/antigravity/mcp_config.json
    all_mcps = {**core_mcps, **tools_mcps}

    build_antigravity(aops_root, dist_root, all_mcps)

    print("\nBuild complete. Dist artifacts in dist/")


if __name__ == "__main__":
    main()
