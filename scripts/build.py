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
AOPS_CORE_PYPROJECT_TEMPLATE = '''\
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
]

[tool.hatch.build.targets.wheel]
packages = ["lib", "hooks", "mcp_servers"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''


def generate_aops_core_pyproject(version: str) -> str:
    """Generate the aops-core pyproject.toml content with the given version."""
    return AOPS_CORE_PYPROJECT_TEMPLATE.format(version=version)


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
                new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
                return f"---\n{new_frontmatter}---{parts[2]}"
        return content

    if platform == "gemini":
        # Filter out mcp__* tools (Claude-specific MCP tool names)
        filtered_tools = [t for t in original_tools if not t.startswith("mcp__")]
        if filtered_tools != original_tools:
            frontmatter["tools"] = filtered_tools
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
            return f"---\n{new_frontmatter}---{parts[2]}"
        return content

    elif platform == "claude":
        # Claude Code requires:
        # 1. Comma-separated string (not YAML array)
        # 2. PascalCase tool names for built-in tools

        # Tool name mapping: generic/Gemini -> Claude Code
        TOOL_NAME_MAP = {
            "read_file": "Read",
            "write_file": "Write",
            "replace": "Edit",
            "list_directory": "Glob",
            "glob": "Glob",
            "grep": "Grep",
            "search_file_content": "Grep",
            "bash": "Bash",
            "run_shell_command": "Bash",
            "activate_skill": "Skill",
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
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
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
    aops_root: Path, dist_root: Path, aca_data_path: str, platform: str = "gemini", version: str = "0.1.0"
):
    """Build the aops-core extension for a specific platform."""
    print(f"Building aops-core for {platform} (v{version})...")
    plugin_name = "aops-core"
    src_dir = aops_root / plugin_name
    
    # Platform-specific dist dir
    dist_dir = dist_root / f"{plugin_name}-{platform}"

    # Write version info for tracking (always to source)
    commit_sha = get_git_commit_sha(aops_root)
    if commit_sha:
        write_plugin_version(src_dir, commit_sha)

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Copy content directories
    # Note: pyproject.toml is generated, not copied (version from root)
    items_to_copy = [
        "skills",
        "agents",
        "commands",
        "lib",
        "mcp_servers",
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
                dst = dist_dir / item
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
                safe_copy(src, dist_dir / item)

    # 1a. Generate pyproject.toml with version from root
    pyproject_content = generate_aops_core_pyproject(version)
    pyproject_path = dist_dir / "pyproject.toml"
    pyproject_path.write_text(pyproject_content)
    print(f"  ✓ Generated pyproject.toml (v{version})")

    # 1b. Copy root-level scripts
    scripts_src = aops_root / "scripts"
    scripts_dst = dist_dir / "scripts"
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
            safe_copy(item, hooks_dst / item.name)

    # Generate Gemini-compatible hooks.json
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
            mcp_config = json.loads(content)

            # Write back to source .mcp.json for Claude
            mcp_json_path = src_dir / ".mcp.json"
            with open(mcp_json_path, "w") as f:
                json.dump(mcp_config, f, indent=2)
            
            # If Claude dist, copy .mcp.json
            if platform == "claude":
                safe_copy(mcp_json_path, dist_dir / ".mcp.json")

            # Prepare for Gemini Extension
            if platform == "gemini":
                servers_config = mcp_config.get("mcpServers", mcp_config)
                # Replace variables for Gemini
                gemini_servers_json = json.dumps(servers_config)
                gemini_servers_json = gemini_servers_json.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")
                
                gemini_servers_config = json.loads(gemini_servers_json)
                gemini_mcps = convert_mcp_to_gemini(gemini_servers_config)

                if dist_extension_json.exists():
                    with open(dist_extension_json, "r") as f:
                        manifest = json.load(f)
                    current_mcps = manifest.get("mcpServers", {})
                    manifest["mcpServers"] = {**current_mcps, **gemini_mcps}
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
                            skill_dir = dist_dir / "skills" / agent_name
                            skill_dir.mkdir(parents=True, exist_ok=True)

                            text = agent_file.read_text()
                            text = translate_tool_calls(text, "gemini")

                            with open(skill_dir / "SKILL.md", "w") as f:
                                f.write(text)
                except Exception as e:
                    print(f"Warning: Failed to parse agent {agent_file}: {e}")

    # 6. Commands (Gemini only for now as they use .toml)
    if platform == "gemini":
        commands_dist = dist_dir / "commands"
        convert_script = aops_root / "scripts" / "convert_commands_to_toml.py"
        if convert_script.exists():
            subprocess.run(
                [sys.executable, str(convert_script), "--output-dir", str(commands_dist)],
                env=os.environ,
                check=False,
            )

    print(f"✓ Built {plugin_name} ({platform})")
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
    core_mcps_gemini = build_aops_core(aops_root, dist_root, aca_data_path, "gemini", version)

    # Build components (Claude)
    build_aops_core(aops_root, dist_root, aca_data_path, "claude", version)

    # Build Antigravity (global config if needed)
    build_antigravity(aops_root, dist_root, core_mcps_gemini)

    package_artifacts(aops_root, dist_root)

    print("\nBuild complete. Dist artifacts in dist/")


def package_artifacts(aops_root: Path, dist_root: Path):
    """Package the built components into archives for release."""
    print("\nPackaging artifacts for release...")

    # 1. aops-core-gemini.tar.gz
    core_gemini_path = dist_root / "aops-core-gemini.tar.gz"
    with tarfile.open(core_gemini_path, "w:gz") as tar:
        tar.add(dist_root / "aops-core-gemini", arcname=".")
    print(f"  ✓ Packaged {core_gemini_path.name}")
    
    # Create 'latest' symlink for Gemini
    safe_symlink(core_gemini_path, dist_root / "aops-core-gemini-latest.tar.gz")

    # 2. aops-antigravity.zip
    antigravity_zip_path = dist_root / "aops-antigravity.zip"
    with zipfile.ZipFile(antigravity_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        ag_src = dist_root / "antigravity"
        for root, _, files in os.walk(ag_src):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(ag_src))
    print(f"  ✓ Packaged {antigravity_zip_path.name}")
    
    # Create 'latest' symlink for Antigravity
    safe_symlink(antigravity_zip_path, dist_root / "aops-antigravity-latest.zip")

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

    # 3. aops-core-claude.tar.gz (from built dist)
    core_claude_path = dist_root / "aops-core-claude.tar.gz"
    with tarfile.open(core_claude_path, "w:gz") as tar:
        tar.add(dist_root / "aops-core-claude", arcname="aops-core", filter=_source_filter)
    print(f"  ✓ Packaged {core_claude_path.name}")
    
    # Create 'latest' symlink for Claude
    safe_symlink(core_claude_path, dist_root / "aops-core-claude-latest.tar.gz")


if __name__ == "__main__":
    main()
