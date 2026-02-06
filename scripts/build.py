#!/usr/bin/env python3
"""
Build script for AcademicOps Gemini extensions.
Generates dist/aops-core and dist/antigravity.
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
    "Notification": "BeforeAgent",  # Map to BeforeAgent as a safe fallback
    # Gemini-specific (keep as-is if present)
    "BeforeTool": "BeforeTool",
    "AfterTool": "AfterTool",
    "BeforeAgent": "BeforeAgent",
}


def get_project_version(aops_root: Path) -> str:
    """Extract the version from pyproject.toml."""
    pyproject_path = aops_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "0.1.0")
        except (ImportError, Exception):
            # Fallback regex if tomllib is missing or fails
            import re

            content = pyproject_path.read_text()
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    return "0.1.0"


# Template for aops-core pyproject.toml - version is injected at build time
AOPS_CORE_PYPROJECT_TEMPLATE = """\
[project]
name = "aops-core"
version = "{version}"
description = "Core academicOps framework - skills, agents, and hooks for research workflow automation"
requires-python = ">=3.11"
license = "MIT"
authors = [
  {{ name = "Nicolas Suzor" }}
]
keywords = ["academicOps", "research", "framework", "workflow", "mcp"]
dependencies = [
  "pyyaml>=6.0",
  "pydantic>=2.0",
  "filelock>=3.13.0",
  "fastmcp>=2.13.1,<3.0",
  "psutil>=5.9.0",
]

[tool.hatch.build.targets.wheel]
packages = ["lib", "hooks", "mcp_servers"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""


def generate_aops_core_pyproject(version: str) -> str:
    """Generate the aops-core pyproject.toml content with the given version."""
    return AOPS_CORE_PYPROJECT_TEMPLATE.format(version=version)


def generate_files_md(dist_dir: Path, platform: str) -> None:
    """Generate FILES.md listing all files in the distribution.

    Creates a simple file listing for the plugin distribution,
    using relative paths from the plugin root.
    """
    files_md = dist_dir / "indices" / "FILES.md"
    files_md.parent.mkdir(parents=True, exist_ok=True)

    # Collect all files recursively
    all_files = sorted(
        p.relative_to(dist_dir)
        for p in dist_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )

    # Build the content
    content = f"""---
name: files-index
title: Plugin Files Index ({platform})
category: reference
type: generated
description: Auto-generated file listing for {platform} plugin distribution
---

# Plugin Files Index

Auto-generated during build. Lists all files in this plugin distribution.

## File Count

Total files: {len(all_files)}

## File Tree

```
"""
    for f in all_files:
        content += f"{f}\n"

    content += "```\n"

    files_md.write_text(content)
    print(f"  ✓ Generated FILES.md ({len(all_files)} files)")


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
                            cmd = cmd.replace(
                                "${CLAUDE_PLUGIN_ROOT}", "${extensionPath}"
                            )

                            # Ensure we use the correct client flag for Gemini
                            cmd = cmd.replace("--client claude", "--client gemini")

                            # Also ensure PYTHONPATH is set correctly for Gemini
                            if "PYTHONPATH=" in cmd and "${extensionPath}" in cmd:
                                # Simplify: use uv run --directory which handles PYTHONPATH
                                cmd = cmd.replace(
                                    "PYTHONPATH=${extensionPath} uv run python",
                                    "env -u VIRTUAL_ENV uv run --directory ${extensionPath} python",
                                )
                            else:
                                # For other uv run commands, also prepend env -u VIRTUAL_ENV
                                cmd = cmd.replace(
                                    "uv run",
                                    "env -u VIRTUAL_ENV uv run",
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


def transform_agent_for_platform(content: str, platform: str) -> str:
    """Transform agent markdown for a specific platform.

    For Gemini: filters out mcp__* tools from frontmatter since they're Claude-specific.
    For Claude: converts YAML array tools to comma-separated string with PascalCase names.
    """
    # Split frontmatter from body
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content

    import yaml

    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return content

    if not frontmatter or "tools" not in frontmatter:
        return content

    original_tools = frontmatter.get("tools", [])

    # Handle case where tools is already a string (no transformation needed for format)
    if isinstance(original_tools, str):
        if platform == "gemini":
            # Filter mcp__ tools from comma-separated string
            tools_list = [t.strip() for t in original_tools.split(",")]
            filtered = [t for t in tools_list if not t.startswith("mcp__")]
            if filtered != tools_list:
                frontmatter["tools"] = ", ".join(filtered)
                new_frontmatter = yaml.dump(
                    frontmatter, default_flow_style=False, sort_keys=False
                )
                return f"---\n{new_frontmatter}---{parts[2]}"
        return content

    if platform == "gemini":
        # Filter out mcp__* tools (Claude-specific MCP tool names)
        filtered_tools = [t for t in original_tools if not t.startswith("mcp__")]
        if filtered_tools != original_tools:
            frontmatter["tools"] = filtered_tools
            new_frontmatter = yaml.dump(
                frontmatter, default_flow_style=False, sort_keys=False
            )
            return f"---\n{new_frontmatter}---{parts[2]}"
        return content

    elif platform == "claude":
        # Claude Code requires:
        # 1. Comma-separated string (not YAML array)
        # 2. PascalCase tool names for built-in tools

        # Tool name mapping: generic/Gemini -> Claude Code
        TOOL_NAME_MAP = {
            # File operations
            "read_file": "Read",
            "write_file": "Write",
            "replace": "Edit",
            "list_directory": "Glob",
            "glob": "Glob",
            "grep": "Grep",
            "search_file_content": "Grep",
            # Shell execution
            "bash": "Bash",
            "run_shell_command": "Bash",
            # Skills/Agents
            "activate_skill": "Skill",
            # Web operations
            "web_fetch": "WebFetch",
            "web_search": "WebSearch",
            # Already correct names (passthrough)
            "Read": "Read",
            "Write": "Write",
            "Edit": "Edit",
            "Glob": "Glob",
            "Grep": "Grep",
            "Bash": "Bash",
            "Skill": "Skill",
            "Task": "Task",
            "WebFetch": "WebFetch",
            "WebSearch": "WebSearch",
            "TodoWrite": "TodoWrite",
            "AskUserQuestion": "AskUserQuestion",
            "NotebookEdit": "NotebookEdit",
        }

        # Transform each tool name
        transformed_tools = []
        for tool in original_tools:
            if tool.startswith("mcp__"):
                # MCP tools keep their full name
                transformed_tools.append(tool)
            else:
                # Map to Claude Code name, or keep original if not in map
                transformed_tools.append(TOOL_NAME_MAP.get(tool, tool))

        # Convert to comma-separated string
        tools_string = ", ".join(transformed_tools)
        frontmatter["tools"] = tools_string

        # Rebuild the content with the new frontmatter
        new_frontmatter = yaml.dump(
            frontmatter, default_flow_style=False, sort_keys=False
        )
        return f"---\n{new_frontmatter}---{parts[2]}"

    return content


def translate_tool_calls(text: str, platform: str) -> str:
    """Translate abstract tool calls to platform-specific names."""
    # 1. Platform-specific mappings
    # We map call notation, descriptive notation, and backticked notation
    mappings = {
        "gemini": {
            "Read(": "read_file(",
            "Write(": "write_file(",
            "Edit(": "replace(",
            "ls(": "list_directory(",
            "Glob(": "glob(",
            "Grep(": "search_file_content(",
            "Read tool": "read_file tool",
            "Write tool": "write_file tool",
            "Edit tool": "replace tool",
            "`Read`": "`read_file`",
            "`Write`": "`write_file`",
            "`Edit`": "`replace`",
            "`ls`": "`list_directory`",
            "`Glob`": "`glob`",
            "`Grep`": "`search_file_content`",
            "Read or Grep": "read_file or search_file_content",
        },
        "claude": {
            "Read(": "read_file(",
            "Write(": "write_file(",
            "Edit(": "replace(",
            "ls(": "list_directory(",
            "Glob(": "glob(",
            "Grep(": "grep(",
            "Read tool": "read_file tool",
            "Write tool": "write_file tool",
            "Edit tool": "replace tool",
            "`Read`": "`read_file`",
            "`Write`": "`write_file`",
            "`Edit`": "`replace`",
            "`ls`": "`list_directory`",
            "`Glob`": "`glob`",
            "`Grep`": "`grep`",
            "Read or Grep": "read_file or grep",
        },
    }

    platform_map = mappings.get(platform, mappings["gemini"])
    for abstract, concrete in platform_map.items():
        text = text.replace(abstract, concrete)

    # 2. Dynamic replacement for Gemini/Claude compatibility (Task/Skill)
    if platform == "gemini":
        # Task(subagent_type=...) -> activate_skill(name=...)
        text = text.replace("Task(subagent_type=", "activate_skill(name=")
        # Skill(skill=...) -> activate_skill(name=...)
        text = text.replace("Skill(skill=", "activate_skill(name=")
        # Update descriptive text references
        text = text.replace("Task() tool", "activate_skill() tool")
        text = text.replace("`Task(`", "`activate_skill(`")
        text = text.replace("`Skill(`", "`activate_skill(`")

    return text


def build_aops_core(
    aops_root: Path,
    dist_root: Path,
    aca_data_path: str,
    platform: str = "gemini",
    version: str = "0.1.0",
):
    """Build the aops-core extension for a specific platform."""
    print(f"Building aops-core for {platform} (v{version})...")
    plugin_name = "aops-core"
    src_dir = aops_root / plugin_name

    # Platform-specific dist dir. New naming: use 'aops-{platform}' as the dist folder
    # so consumers see 'aops-gemini' / 'aops-claude' instead of 'aops-core-gemini'.
    dist_dir = dist_root / f"aops-{platform}"

    # Content goes directly into dist_dir (no nested subfolder)
    content_dir = dist_dir

    # Write version info for tracking (always to source)
    commit_sha = get_git_commit_sha(aops_root)
    if commit_sha:
        write_plugin_version(src_dir, commit_sha)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Copy content directories
    # Note: pyproject.toml is generated, not copied (version from root)
    # Note: hooks/ is handled separately in section 2 (Gemini hooks.json transform)
    # Note: indices/ excluded - FILES.md is generated dynamically, PATHS.md is user config
    items_to_copy = [
        "skills",
        "agents",
        "commands",
        "lib",
        "mcp_servers",
        "workflows",
        "framework",
        "SKILLS.md",
        "AXIOMS.md",
        "HEURISTICS.md",
        "RULES.md",
        "REMINDERS.md",
        "INDEX.md",
        "WORKFLOWS.md",
        "INSTALLATION.md",
        "uv.lock",
    ]

    # Gemini-only items
    if platform == "gemini":
        items_to_copy.extend(["GEMINI.md"])

    for item in items_to_copy:
        src = src_dir / item
        if src.exists():
            if item == "agents" and src.is_dir():
                # Special handling for agents: transform frontmatter and translate tool calls
                dst = content_dir / item
                dst.mkdir(parents=True, exist_ok=True)
                for agent_file in src.glob("*.md"):
                    content = agent_file.read_text()
                    # Transform frontmatter (filter mcp__ tools for Gemini)
                    content = transform_agent_for_platform(content, platform)
                    # Translate tool calls in body text
                    content = translate_tool_calls(content, platform)
                    (dst / agent_file.name).write_text(content)
                print(f"  ✓ Translated and copied agents -> {dst}")
            else:
                safe_copy(src, content_dir / item)

    # 1a. Generate pyproject.toml with version from root
    pyproject_content = generate_aops_core_pyproject(version)
    pyproject_path = content_dir / "pyproject.toml"
    pyproject_path.write_text(pyproject_content)
    print(f"  ✓ Generated pyproject.toml (v{version})")

    # 1b. Copy root-level scripts
    scripts_src = aops_root / "scripts"
    scripts_dst = content_dir / "scripts"
    if scripts_src.exists():
        scripts_dst.mkdir(parents=True, exist_ok=True)
        for script_name in [
            "audit_framework_health.py",
            "check_skill_line_count.py",
            "check_orphan_files.py",
        ]:
            src = scripts_src / script_name
            if src.exists():
                safe_copy(src, scripts_dst / script_name)

    # 2. Hooks
    hooks_src = src_dir / "hooks"
    hooks_dst = dist_dir / "hooks"
    hooks_dst.mkdir(parents=True)
    if hooks_src.exists():
        for item in hooks_src.iterdir():
            if item.name == "hooks.json" and platform == "gemini":
                # Handle hooks.json separately for Gemini
                continue
            if item.name == "gemini":
                # Don't copy gemini/ subdirectory
                continue
            # Hooks also go into content_dir for execution, but Gemini discovery
            # might need them in dist_dir/hooks/hooks.json
            safe_copy(item, content_dir / "hooks" / item.name)

    # Generate Gemini-compatible hooks.json in dist_dir/hooks/ for discovery
    if platform == "gemini":
        hooks_json_src = hooks_src / "hooks.json"
        if hooks_json_src.exists():
            _generate_gemini_hooks_json(hooks_json_src, hooks_dst / "hooks.json")

    # 3. Extension Manifest / Plugin Info
    if platform == "gemini":
        src_extension_json = aops_root / "gemini-extension.json"
        dist_extension_json = dist_dir / "gemini-extension.json"

        if src_extension_json.exists():
            print(f"Generating extension manifest from {src_extension_json.name}...")
            try:
                manifest = json.loads(src_extension_json.read_text())
                manifest["version"] = version

                # Fix up task_manager path if it was using the repo-root format
                # (where aops-core is a subdirectory, but in dist it is the root)
                if "mcpServers" in manifest and "task_manager" in manifest["mcpServers"]:
                    args = manifest["mcpServers"]["task_manager"].get("args", [])
                    new_args = [
                        a.replace(
                            "${extensionPath}/aops-core",
                            "${extensionPath}",
                        )
                        for a in args
                    ]
                    manifest["mcpServers"]["task_manager"]["args"] = new_args

                with open(dist_extension_json, "w") as f:
                    json.dump(manifest, f, indent=2)
            except Exception as e:
                print(f"Error processing extension manifest: {e}", file=sys.stderr)
                raise
        else:
            print(f"Error: {src_extension_json} not found.", file=sys.stderr)
            sys.exit(1)

    if platform == "claude":
        src_plugin_json = src_dir / ".claude-plugin" / "plugin.json"
        dist_plugin_json = dist_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version
                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                print(f"  ✓ Updated and copied plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    # 4. Generate MCP Config from Template
    template_path = src_dir / "mcp.json.template"
    gemini_mcps = {}

    if template_path.exists():
        print(f"Generating MCP config from {template_path.name}...")
        try:
            content = template_path.read_text()
            mcp_template = json.loads(content)

            # Select platform-specific config if available
            if platform in mcp_template:
                mcp_config = mcp_template[platform]
            else:
                mcp_config = mcp_template

            # Write back to source .mcp.json for Claude
            # This ensures dev-mode Claude has a valid config
            mcp_json_path = src_dir / ".mcp.json"
            claude_mcp_config = mcp_template.get("claude", mcp_template)
            with open(mcp_json_path, "w") as f:
                json.dump(claude_mcp_config, f, indent=2)

            # If Claude dist, copy .mcp.json
            if platform == "claude":
                safe_copy(mcp_json_path, dist_dir / ".mcp.json")

            # Prepare for Gemini Extension
            if platform == "gemini":
                servers_config = mcp_config.get("mcpServers", mcp_config)
                # Replace variables for Gemini if they came from a Claude-style template
                gemini_servers_json = json.dumps(servers_config)
                gemini_servers_json = gemini_servers_json.replace(
                    "${CLAUDE_PLUGIN_ROOT}", "${extensionPath}"
                )

                gemini_servers_config = json.loads(gemini_servers_json)
                gemini_mcps = convert_mcp_to_gemini(gemini_servers_config)

                if dist_extension_json.exists():
                    with open(dist_extension_json, "r") as f:
                        manifest = json.load(f)
                    current_mcps = manifest.get("mcpServers", {})
                    manifest["mcpServers"] = {**current_mcps, **gemini_mcps}

                    # MCP server arguments from mcp.json.template use ${extensionPath}
                    # which is correct since plugin content is at the root

                    with open(dist_extension_json, "w") as f:
                        json.dump(manifest, f, indent=2)
                    print(f"✓ Updated {dist_extension_json} with MCP config")

        except Exception as e:
            print(f"Error processing template {template_path}: {e}", file=sys.stderr)
            raise

    # 5. Build Sub-Agents (Skills)
    if platform == "gemini":
        agents_dir = src_dir / "agents"
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                try:
                    content = agent_file.read_text()
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import yaml

                        frontmatter = yaml.safe_load(parts[1])
                        if "name" in frontmatter:
                            agent_name = frontmatter["name"]
                            skill_dir = content_dir / "skills" / agent_name
                            skill_dir.mkdir(parents=True, exist_ok=True)

                            text = agent_file.read_text()
                            text = translate_tool_calls(text, "gemini")

                            with open(skill_dir / "SKILL.md", "w") as f:
                                f.write(text)
                except Exception as e:
                    print(f"Warning: Failed to parse agent {agent_file}: {e}")

    # 6. Commands (Gemini only for now as they use .toml)
    if platform == "gemini":
        commands_dist = content_dir / "commands"
        convert_script = aops_root / "scripts" / "convert_commands_to_toml.py"
        if convert_script.exists():
            subprocess.run(
                [
                    sys.executable,
                    str(convert_script),
                    "--output-dir",
                    str(commands_dist),
                ],
                env=os.environ,
                check=False,
            )
        # Remove .md command files for Gemini (uses TOML format)
        for md_file in commands_dist.glob("*.md"):
            md_file.unlink()
            print(f"  - Removed {md_file.name} (Gemini uses TOML)")

    # 7. Generate FILES.md dynamically
    generate_files_md(dist_dir, platform)

    print(f"✓ Built {plugin_name} ({platform})")
    return gemini_mcps


def build_antigravity(aops_root: Path, dist_root: Path, all_mcps: dict):
    """Build the antigravity distribution."""
    print("Building antigravity...")
    ag_dist = dist_root / "aops-antigravity"
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
    # NOTE: Antigravity doesn't use rules directly yet - setup.sh links from source to .agent/rules.
    # Keeping this comment for future reference if we want to distribute rules from dist.

    print("✓ Built antigravity dist")


def main():
    aca_data_path = os.environ.get("ACA_DATA")

    if not aca_data_path:
        print("Error: ACA_DATA environment variable must be set.")
        sys.exit(1)

    # Infer aops_root from script location
    aops_root = Path(__file__).parent.parent.resolve()
    print(f"Info: aops_root inferred to {aops_root}")
    dist_root = aops_root / "dist"

    # Get version from pyproject.toml
    version = get_project_version(aops_root)
    print(f"Building AcademicOps v{version}...")

    # Clean/Create dist
    if not dist_root.exists():
        dist_root.mkdir()

    # Build components (Gemini)
    core_mcps_gemini = build_aops_core(
        aops_root, dist_root, aca_data_path, "gemini", version
    )

    # Build components (Claude)
    build_aops_core(aops_root, dist_root, aca_data_path, "claude", version)

    # Build Antigravity (global config if needed)
    build_antigravity(aops_root, dist_root, core_mcps_gemini)

    package_artifacts(aops_root, dist_root, version)

    # Create git tags for release
    create_git_tags(aops_root, version)

    print("\nBuild complete. Dist artifacts in dist/")


def package_artifacts(aops_root: Path, dist_root: Path, version: str):
    """Package the built components into archives for release.

    Creates three archives:
    - aops-gemini-v{version}.tar.gz
    - aops-claude-v{version}.tar.gz
    - aops-antigravity-v{version}.tar.gz

    Plus 'latest' symlinks for each.
    """
    print("\nPackaging artifacts for release...")

    # Filter for packaging to exclude noise
    def _source_filter(tarinfo):
        exclude = [
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".git",
        ]
        if any(x in tarinfo.name for x in exclude):
            return None
        return tarinfo

    # 1. aops-gemini.tar.gz (single generic archive for Gemini CLI)
    # Per gemini-packaging-guide.md: gemini-extension.json must be at archive root
    # Using arcname="." puts content at root, not nested in a subdirectory
    gemini_archive = dist_root / "aops-gemini.tar.gz"
    with tarfile.open(gemini_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-gemini", arcname=".", filter=_source_filter)
    print(f"  ✓ Packaged {gemini_archive.name}")
    # Also create versioned copy for reference
    versioned_gemini = dist_root / f"aops-gemini-v{version}.tar.gz"
    shutil.copy(gemini_archive, versioned_gemini)

    # 2. aops-claude-v{version}.tar.gz
    claude_archive = dist_root / f"aops-claude-v{version}.tar.gz"
    with tarfile.open(claude_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-claude", arcname="aops-claude", filter=_source_filter)
    print(f"  ✓ Packaged {claude_archive.name}")
    safe_symlink(claude_archive, dist_root / "aops-claude-latest.tar.gz")

    # 3. aops-antigravity-v{version}.tar.gz
    antigravity_archive = dist_root / f"aops-antigravity-v{version}.tar.gz"
    with tarfile.open(antigravity_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-antigravity", arcname=".", filter=_source_filter)
    print(f"  ✓ Packaged {antigravity_archive.name}")
    safe_symlink(antigravity_archive, dist_root / "aops-antigravity-latest.tar.gz")


def create_git_tags(aops_root: Path, version: str):
    """Create git tags for release: v{version} and latest.

    Tags are created pointing to HEAD. If tags already exist, they are updated.
    Note: Tags are local only - push with `git push origin v{version} latest` to publish.
    """
    print("\nCreating git tags...")

    version_tag = f"v{version}"

    # Create/update version tag
    result = subprocess.run(
        ["git", "tag", "-f", version_tag],
        cwd=aops_root,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  ✓ Created tag: {version_tag}")
    else:
        print(f"  ✗ Failed to create tag {version_tag}: {result.stderr}")

    # Create/update 'latest' tag
    result = subprocess.run(
        ["git", "tag", "-f", "latest"],
        cwd=aops_root,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  ✓ Created tag: latest")
    else:
        print(f"  ✗ Failed to create tag latest: {result.stderr}")

    print("  Note: Push tags with: git push origin --tags")


if __name__ == "__main__":
    main()
