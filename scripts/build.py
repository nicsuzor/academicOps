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
import tarfile
import zipfile
from pathlib import Path

# Add shared lib to path (assuming scripts/lib exists)
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(SCRIPT_DIR / "lib"))

try:
    from build_utils import (
        convert_mcp_to_gemini,
        convert_gemini_to_antigravity,
        safe_symlink,
        safe_copy,
        format_path_for_json,
        get_git_commit_sha,
        write_plugin_version,
    )
except ImportError as e:
    # Fallback if running from a different location without setting path correctly
    # or if lib structure is not yet fully set up in development
    print(f"Error: Could not import build_utils. {e}", file=sys.stderr)
    print(f"Sys Path: {sys.path}", file=sys.stderr)
    sys.exit(1)


# Event name mapping: Claude Code -> Gemini CLI
CLAUDE_TO_GEMINI_EVENTS = {
    "PreToolUse": "BeforeTool",
    "PostToolUse": "AfterTool",
    "UserPromptSubmit": "BeforeAgent",
    "Stop": "SessionEnd",
    # These are the same in both
    "SessionStart": "SessionStart",
    "SessionEnd": "SessionEnd",
    "SubagentStop": "AfterTool",  # Subagents are tools in Gemini, so map stop to AfterTool
    "PreCompact": "BeforeAgent",  # Map to BeforeAgent as a safe fallback
    "Notification": "BeforeAgent", # Map to BeforeAgent as a safe fallback
    # Gemini-specific (keep as-is if present)
    "BeforeTool": "BeforeTool",
    "AfterTool": "AfterTool",
    "BeforeAgent": "BeforeAgent",
}


def _generate_gemini_hooks_json(src_path: Path, dst_path: Path) -> None:
    """Transform hooks.json from Claude Code format to Gemini CLI format.

    Gemini CLI reads hooks from <extension>/hooks/hooks.json with:
    - Different event names (BeforeTool vs PreToolUse, etc.)
    - ${extensionPath} variable instead of ${CLAUDE_PLUGIN_ROOT}
    """
    try:
        with open(src_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Could not read hooks.json: {e}")
        return

    if "hooks" not in config:
        print("Warning: hooks.json has no 'hooks' key")
        return

    src_hooks = config["hooks"]
    gemini_hooks: dict = {}

    for claude_event, hook_list in src_hooks.items():
        # Skip disabled hooks
        if claude_event.endswith("-disabled"):
            continue

        # Map event name
        gemini_event = CLAUDE_TO_GEMINI_EVENTS.get(claude_event, claude_event)

        # Skip events that don't exist in Gemini
        # Valid Gemini events: SessionStart, BeforeAgent, BeforeTool, AfterTool, SessionEnd
        # SubagentStop is NOT a valid Gemini event - do not include it
        VALID_GEMINI_EVENTS = (
            "SessionStart",
            "BeforeAgent",
            "BeforeTool",
            "AfterTool",
            "SessionEnd",
        )
        if gemini_event not in VALID_GEMINI_EVENTS:
            print(f"  Skipping unsupported Gemini event: {claude_event}")
            continue

        # Transform hook commands
        transformed_hooks = []
        for hook_entry in hook_list:
            new_entry = {}
            for key, value in hook_entry.items():
                if key == "hooks":
                    new_hooks = []
                    for hook in value:
                        new_hook = dict(hook)
                        if "command" in new_hook:
                            # Replace Claude variable with Gemini variable
                            cmd = new_hook["command"]
                            cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")

                            # Ensure we use the correct client flag for Gemini
                            cmd = cmd.replace("--client claude", "--client gemini")

                            # Also ensure PYTHONPATH is set correctly for Gemini
                            if "PYTHONPATH=" in cmd and "${extensionPath}" in cmd:
                                # Simplify: use uv run --directory which handles PYTHONPATH
                                cmd = cmd.replace(
                                    "PYTHONPATH=${extensionPath} uv run python",
                                    "uv run --directory ${extensionPath} python"
                                )
                            new_hook["command"] = cmd
                        new_hooks.append(new_hook)
                    new_entry[key] = new_hooks
                else:
                    new_entry[key] = value
            transformed_hooks.append(new_entry)

        gemini_hooks[gemini_event] = transformed_hooks

    # Write Gemini-compatible hooks.json
    gemini_config = {"hooks": gemini_hooks}
    with open(dst_path, "w") as f:
        json.dump(gemini_config, f, indent=2)
    print(f"  ✓ Generated Gemini hooks.json with {len(gemini_hooks)} events")


def build_aops_core(aops_root: Path, dist_root: Path, aca_data_path: str):
    """Build the aops-core extension."""
    print("Building aops-core...")
    plugin_name = "aops-core"
    src_dir = aops_root / plugin_name
    dist_dir = dist_root / plugin_name

    # Write version info for tracking
    commit_sha = get_git_commit_sha(aops_root)
    if commit_sha:
        write_plugin_version(src_dir, commit_sha)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Copy content directories (not symlinks - avoids polluting canonical source)
    # Include markdown files needed by hydration (SKILLS.md, AXIOMS.md, etc.)
    for item in [
        "skills",
        "agents",
        "lib",
        "GEMINI.md",
        "SKILLS.md",
        "AXIOMS.md",
        "HEURISTICS.md",
        "RULES.md",
        "REMINDERS.md",
        "INDEX.md",
        "WORKFLOWS.md",
        "INSTALLATION.md",
    ]:
        src = src_dir / item
        if src.exists():
            safe_copy(src, dist_dir / item)

    # 1b. Copy root-level scripts needed by skills (e.g., audit skill)
    # These scripts are at $AOPS/scripts/ and referenced by SKILL.md files
    scripts_src = aops_root / "scripts"
    scripts_dst = dist_dir / "scripts"
    if scripts_src.exists():
        scripts_dst.mkdir(parents=True, exist_ok=True)
        # Copy specific scripts needed by skills
        for script_name in [
            "audit_framework_health.py",
            "check_skill_line_count.py",
            "check_orphan_files.py",
        ]:
            src = scripts_src / script_name
            if src.exists():
                safe_copy(src, scripts_dst / script_name)

    # 2. Hooks (Selective copy - not symlinks to avoid source pollution)
    hooks_src = src_dir / "hooks"
    hooks_dst = dist_dir / "hooks"
    hooks_dst.mkdir(parents=True)
    if hooks_src.exists():
        for item in hooks_src.iterdir():
            if item.name == "hooks.json":
                # Handle hooks.json separately - transform for Gemini
                continue
            if item.name == "gemini":
                # Don't copy gemini/ subdirectory - we use unified router.py now
                continue
            safe_copy(item, hooks_dst / item.name)

    # Copy the Unified router directly
    router_src = hooks_src / "router.py"
    if router_src.exists():
        safe_copy(router_src, hooks_dst / "router.py")

    # Generate Gemini-compatible hooks.json
    # Gemini CLI looks for hooks/hooks.json with different event names
    hooks_json_src = hooks_src / "hooks.json"
    if hooks_json_src.exists():
        _generate_gemini_hooks_json(hooks_json_src, hooks_dst / "hooks.json")

    # 3. Generate Hooks Config / Extension Manifest
    # If a source gemini-extension.json exists, we use it as a template and perform substitution.
    # Otherwise, we generate from hooks.json (legacy/fallback).

    src_extension_json = src_dir / "gemini-extension.json"
    dist_extension_json = dist_dir / "gemini-extension.json"

    if src_extension_json.exists():
        print(f"Generating extension manifest from {src_extension_json.name}...")
        try:
            content = src_extension_json.read_text()

            # We NO LONGER perform substitution here for ${AOPS} and ${ACA_DATA}
            # Gemini CLI handles these natively in the manifest.

            # Write JSON to dist
            with open(dist_extension_json, "w") as f:
                f.write(content)

            # We also need to write a dummy hooks.json or rely on the extension manifest entirely?
            # Gemini reads extension manifest. hooks.json is for older separate hook config?
            # If the manifest has "hooks", we are good.

        except Exception as e:
            print(f"Error processing extension template: {e}", file=sys.stderr)
            raise
    else:
        print(
            f"Error: {src_extension_json} not found. This file is required for the build.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 4. Generate MCP Config from Template
    template_path = src_dir / "mcp.json.template"
    mcp_config = {}

    if template_path.exists():
        print(f"Generating MCP config from {template_path.name}...")
        try:
            content = template_path.read_text()

            # We NO LONGER perform substitution here for ${AOPS}, ${ACA_DATA}, etc.
            # These should remain as placeholders in the generated .mcp.json

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
            
            # Transform for Gemini: replace ${CLAUDE_PLUGIN_ROOT} with ${extensionPath}
            gemini_servers_config = json.loads(
                json.dumps(servers_config).replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")
            )
            
            gemini_mcps = convert_mcp_to_gemini(gemini_servers_config)

            # Update extension manifest with generated MCPs
            if dist_extension_json.exists():
                try:
                    with open(dist_extension_json, "r") as f:
                        manifest = json.load(f)

                    # Merge MCPs (template takes precedence or just add missing?)
                    # Let's override/update with template values as they are the source of truth for MCPs
                    current_mcps = manifest.get("mcpServers", {})
                    # We want to preserve existing ones if they aren't in template?
                    # No, user wants template to be source of truth.
                    # But the source gemini-extension.json has task_manager placeholders too.
                    # Let's just merge, with template overwriting.
                    manifest["mcpServers"] = {**current_mcps, **gemini_mcps}

                    with open(dist_extension_json, "w") as f:
                        json.dump(manifest, f, indent=2)
                    print(f"✓ Updated {dist_extension_json} with MCP config")
                except Exception as e:
                    print(f"Error updating manifest with MCPs: {e}", file=sys.stderr)

        except Exception as e:
            print(f"Error processing template {template_path}: {e}", file=sys.stderr)
            # Fallback to empty if failed? Or exit?
            # Better to show error but maybe not crash build if it's partial?
            # Let's re-raise to fail build if strict
            raise
    else:
        print(f"Warning: Template {template_path} not found. Skipping MCP generation.")

    # Inject hooks into gemini-extension.json manifest
    # This is handled by discovery of hooks/hooks.json by Gemini CLI
    pass

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
    # They are also automatically discovered by Gemini CLI from agents/ directory
    agents_dir = src_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            try:
                # ALSO create a Skill for this agent (auto-generated)
                # This allows invoke via activate_skill(name="agent-name")
                
                # Parse frontmatter to get name
                content = agent_file.read_text()
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1])
                    if "name" in frontmatter:
                        agent_name = frontmatter["name"]
                        skill_dir = dist_dir / "skills" / agent_name
                        skill_dir.mkdir(parents=True, exist_ok=True)

                        # Read content
                        text = agent_file.read_text()

                        # Dynamic replacement for Gemini compatibility
                        # 1. Task(subagent_type=...) -> activate_skill(name=...)
                        text = text.replace(
                            "Task(subagent_type=", "activate_skill(name="
                        )

                        # 2. Skill(skill=...) -> activate_skill(name=...)
                        text = text.replace("Skill(skill=", "activate_skill(name=")

                        # 3. Update descriptive text references
                        text = text.replace("Task() tool", "activate_skill() tool")
                        text = text.replace("`Task(`", "`activate_skill(`")
                        text = text.replace("`Skill(`", "`activate_skill(`")

                        # 4. Tool calls (Gemini CLI format)
                        text = text.replace("Read(", "read_file(")
                        text = text.replace("Write(", "write_file(")
                        text = text.replace("Edit(", "replace(")
                        text = text.replace("ls(", "list_directory(")
                        text = text.replace("Glob(", "glob(")
                        text = text.replace("grep(", "search_file_content(")

                        # Write modified content
                        with open(skill_dir / "SKILL.md", "w") as f:
                            f.write(text)
            except Exception as e:
                print(f"Warning: Failed to parse agent {agent_file}: {e}")

    # Manifest already generated in step 3.

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


def build_aops_tools(aops_root: Path, dist_root: Path, aca_data_path: str):
    """Build the aops-tools extension."""
    print("Building aops-tools...")
    plugin_name = "aops-tools"
    src_dir = aops_root / plugin_name
    dist_dir = dist_root / plugin_name

    # Write version info for tracking
    commit_sha = get_git_commit_sha(aops_root)
    if commit_sha:
        write_plugin_version(src_dir, commit_sha)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Copy content directories (not symlinks - avoids polluting canonical source)
    for item in ["skills"]:
        src = src_dir / item
        if src.exists():
            safe_copy(src, dist_dir / item)

    # 1.5 Generate MCP Config from Template (Added to fix bug)
    template_path = src_dir / "mcp.json.template"
    if template_path.exists():
        print(f"Generating MCP config from {template_path.name}...")
        try:
            content = template_path.read_text()

            # We NO LONGER perform substitution here for ${AOPS}, etc.
            # These should remain as placeholders in the generated .mcp.json

            mcp_config = json.loads(content)

            # Write back to source .mcp.json for Claude
            mcp_json_path = src_dir / ".mcp.json"
            with open(mcp_json_path, "w") as f:
                json.dump(mcp_config, f, indent=2)
            print(f"✓ Updated {mcp_json_path}")

        except Exception as e:
            print(f"Error processing template {template_path}: {e}", file=sys.stderr)
            raise
    else:
        print(f"Warning: Template {template_path} not found. Skipping MCP generation.")

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

    # Copy Workflows from aops-core/workflows
    workflows_src = aops_root / "aops-core" / "workflows"
    if workflows_src.exists():
        for item in workflows_src.iterdir():
            if item.is_file() and not item.name.startswith("."):
                safe_copy(item, global_workflows / item.name)

    # Copy Commands as Workflows from aops-core/commands
    commands_src = aops_root / "aops-core" / "commands"
    if commands_src.exists():
        for item in commands_src.iterdir():
            if item.is_file() and not item.name.startswith("."):
                safe_copy(item, global_workflows / item.name)

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
    tools_mcps = build_aops_tools(aops_root, dist_root, aca_data_path)

    # Aggregate MCPs for Antigravity (global config if needed)
    # Note: Antigravity usually uses project-specific mcp, but we can generate a global one too
    # setup.sh generated ~/.gemini/antigravity/mcp_config.json
    all_mcps = {**core_mcps, **tools_mcps}

    build_antigravity(aops_root, dist_root, all_mcps)

    package_artifacts(aops_root, dist_root)

    print("\nBuild complete. Dist artifacts in dist/")


def package_artifacts(aops_root: Path, dist_root: Path):
    """Package the built components into archives for release."""
    print("\nPackaging artifacts for release...")

    # 1. aops-core-gemini.tar.gz
    core_gemini_path = dist_root / "aops-core-gemini.tar.gz"
    with tarfile.open(core_gemini_path, "w:gz") as tar:
        tar.add(dist_root / "aops-core", arcname=".")
    print(f"  ✓ Packaged {core_gemini_path.name}")

    # 2. aops-tools-gemini.tar.gz
    tools_gemini_path = dist_root / "aops-tools-gemini.tar.gz"
    with tarfile.open(tools_gemini_path, "w:gz") as tar:
        tar.add(dist_root / "aops-tools", arcname=".")
    print(f"  ✓ Packaged {tools_gemini_path.name}")

    # 3. aops-antigravity.zip
    antigravity_zip_path = dist_root / "aops-antigravity.zip"
    with zipfile.ZipFile(antigravity_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        ag_src = dist_root / "antigravity"
        for root, _, files in os.walk(ag_src):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(ag_src))
    print(f"  ✓ Packaged {antigravity_zip_path.name}")

    # Filter for source packaging to exclude noise
    def _source_filter(tarinfo):
        exclude = [
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".git",
            "gemini-extension.json",
            "GEMINI.md",
        ]
        if any(x in tarinfo.name for x in exclude):
            return None
        return tarinfo

    # 4. aops-core-claude.tar.gz (from source)
    core_claude_path = dist_root / "aops-core-claude.tar.gz"
    with tarfile.open(core_claude_path, "w:gz") as tar:
        tar.add(aops_root / "aops-core", arcname="aops-core", filter=_source_filter)
    print(f"  ✓ Packaged {core_claude_path.name}")

    # 5. aops-tools-claude.tar.gz (from source)
    tools_claude_path = dist_root / "aops-tools-claude.tar.gz"
    with tarfile.open(tools_claude_path, "w:gz") as tar:
        tar.add(aops_root / "aops-tools", arcname="aops-tools", filter=_source_filter)
    print(f"  ✓ Packaged {tools_claude_path.name}")


if __name__ == "__main__":
    main()
