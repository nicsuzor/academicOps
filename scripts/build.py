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
        safe_copy,
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

    # 1. Copy content directories (not symlinks - avoids polluting canonical source)
    for item in ["skills", "lib", "GEMINI.md"]:  # not agents right now.
        src = src_dir / item
        if src.exists():
            safe_copy(src, dist_dir / item)

    # 2. Hooks (Selective copy - not symlinks to avoid source pollution)
    hooks_src = src_dir / "hooks"
    hooks_dst = dist_dir / "hooks"
    hooks_dst.mkdir(parents=True)
    if hooks_src.exists():
        for item in hooks_src.iterdir():
            if item.name == "hooks.json":
                continue
            if item.name == "gemini":
                # Don't copy gemini/ subdirectory - we use unified router.py now
                continue
            safe_copy(item, hooks_dst / item.name)

    # Copy the Unified router directly
    router_src = hooks_src / "router.py"
    if router_src.exists():
        safe_copy(router_src, hooks_dst / "router.py")

    # Create templates symlink in gemini/ so user_prompt_submit.py can find templates
    # (user_prompt_submit.py uses HOOK_DIR / "templates" where HOOK_DIR is hooks/gemini/)
    # NOTE: This symlink stays in SOURCE, not dist - it's for the gemini hook to find templates
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
    router_script_path = dist_dir / "hooks" / "router.py"

    gemini_hooks = generate_gemini_hooks(
        claude_hooks, str(aops_root), str(router_script_path)
    )

    with open(hooks_dst / "hooks.json", "w") as f:
        json.dump({"hooks": gemini_hooks}, f, indent=2)

    # 4. Generate MCP Config from Template
    template_path = src_dir / "mcp.json.template"
    mcp_config = {}

    if template_path.exists():
        print(f"Generating MCP config from {template_path.name}...")
        try:
            content = template_path.read_text()

            # Variables to substitute
            # CLAUDE_PLUGIN_ROOT: Absolute path to the plugin root (source for .mcp.json, but dist for extension really?
            # Actually for Claude Desktop it points to the source usually if dev, or installed location.
            # But here we are generating .mcp.json in SOURCE. So it should point to SOURCE src_dir.
            # For Gemini, the tasks server expects absolute paths too.
            # Let's use the src_dir (absolute) for now as that's where the python code lives for Claude to run.
            # If we are distributing, we might need to adjust this for the distributed location?
            # But the build script is running typically in a dev context or CI.
            # The user request implies we want parity.

            subs = {
                "${CLAUDE_PLUGIN_ROOT}": str(src_dir.resolve()),
                "${MCP_MEMORY_API_KEY}": os.environ.get("MCP_MEMORY_API_KEY", ""),
                "${ACA_DATA}": aca_data_path,
            }

            for key, val in subs.items():
                content = content.replace(key, val)

            mcp_config = json.loads(content)

            # Write back to source .mcp.json for Claude
            mcp_json_path = src_dir / ".mcp.json"
            with open(mcp_json_path, "w") as f:
                json.dump(mcp_config, f, indent=2)
            print(f"✓ Updated {mcp_json_path}")

            # Prepare for Gemini Extension (convert to gemini format if needed)
            # The template is in Standard MCP format ("mcpServers": {...})
            # convert_mcp_to_gemini handles the "mcpServers" key wrapper or direct dict.
            servers_config = mcp_config.get("mcpServers", mcp_config)
            gemini_mcps = convert_mcp_to_gemini(servers_config)

        except Exception as e:
            print(f"Error processing template {template_path}: {e}", file=sys.stderr)
            # Fallback to empty if failed? Or exit?
            # Better to show error but maybe not crash build if it's partial?
            # Let's re-raise to fail build if strict
            raise
    else:
        print(f"Warning: Template {template_path} not found. Skipping MCP generation.")

    # Validation/Fallback: If task_manager was not in template, we might be missing it.
    # But the user said "we should read from ... template", implying template is source of truth.
    # So we don't manually inject it anymore.

    # 4b. Load Manifest Base (plugin.json)
    plugin_json_path = src_dir / ".claude-plugin" / "plugin.json"
    manifest_base = {}
    if plugin_json_path.exists():
        try:
            with open(plugin_json_path) as f:
                manifest_base = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {plugin_json_path}")

    # 5. Build Sub-Agents from agents/ directory
    # Format: https://geminicli.com/docs/extensions/reference/#sub-agents
    sub_agents = []
    agents_dir = src_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            try:
                # Parse frontmatter to get name, description
                content = agent_file.read_text()
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml

                    frontmatter = yaml.safe_load(parts[1])
                    if "name" in frontmatter:
                        agent_name = frontmatter["name"]
                        sub_agents.append(
                            {
                                "name": agent_name,
                                "description": frontmatter.get(
                                    "description", f"Agent {agent_name}"
                                ),
                                "uri": f"file://${{extensionPath}}/agents/{agent_file.name}",
                                # Pass through other fields if needed, e.g. model
                                "model": frontmatter.get("model"),
                            }
                        )

                        # ALSO create a Skill for this agent (auto-generated)
                        # This allows invoke via activate_skill(name="agent-name")
                        skill_dir = dist_dir / "skills" / agent_name
                        skill_dir.mkdir(parents=True, exist_ok=True)

                        # Read content
                        text = agent_file.read_text()

                        # Dynamic replacement for Gemini compatibility
                        # 1. Task(subagent_type=...) -> activate_skill(name=...)
                        text = text.replace(
                            "Task(subagent_type=", "activate_skill(name="
                        )
                        text = text.replace(
                            "Task(subagent_type=", "activate_skill(name="
                        )

                        # 2. Skill(skill=...) -> activate_skill(name=...)
                        text = text.replace("Skill(skill=", "activate_skill(name=")
                        text = text.replace("Skill(skill=", "activate_skill(name=")

                        # 3. Update descriptive text references
                        text = text.replace("Task() tool", "activate_skill() tool")
                        text = text.replace("`Task(`", "`activate_skill(`")
                        text = text.replace("`Skill(`", "`activate_skill(`")

                        # Write modified content
                        with open(skill_dir / "SKILL.md", "w") as f:
                            f.write(text)
            except Exception as e:
                print(f"Warning: Failed to parse agent {agent_file}: {e}")

    # 6. Build Final Manifest
    # Start with base keys we care about
    manifest = {
        "name": manifest_base.get("name", "aops-core"),
        "version": manifest_base.get("version", "0.1.0"),
        "description": manifest_base.get("description", "AcademicOps Core Framework"),
        "mcpServers": gemini_mcps,
        "hooks": gemini_hooks,
        # NOTE: subAgents disabled - Gemini CLI doesn't support them yet.
        # The agent Skills are still generated (see loop above) and can be invoked
        # via activate_skill(). Re-enable this line when Gemini adds subagent support:
        # "subAgents": sub_agents,
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

    # 1. Copy content directories (not symlinks - avoids polluting canonical source)
    for item in ["skills"]:
        src = src_dir / item
        if src.exists():
            safe_copy(src, dist_dir / item)

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
