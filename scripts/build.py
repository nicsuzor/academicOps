#!/usr/bin/env -S uv run python
"""
Build script for AcademicOps extensions.
Generates dist/aops-gemini, dist/aops-claude, dist/aops-cowork, dist/aops-tools-gemini, dist/aops-tools-claude, and dist/antigravity.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

# Add shared lib to path (assuming scripts/lib exists)
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(SCRIPT_DIR / "lib"))

try:
    from build_utils import (
        convert_mcp_to_gemini,
        get_git_commit_sha,
        safe_copy,
        safe_symlink,
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
    "Stop": ["SessionEnd", "AfterAgent"],  # Stop needs both for unified router.py handling
    # These are the same in both
    "SessionStart": "SessionStart",
    "SessionEnd": "SessionEnd",
    "SubagentStart": "BeforeTool",  # Subagents are tools in Gemini
    "SubagentStop": "AfterTool",  # Subagents are tools in Gemini
    "PreCompact": "BeforeAgent",  # Map to BeforeAgent as a safe fallback
    "Notification": "BeforeAgent",  # Map to BeforeAgent as a safe fallback
    # Gemini-specific (keep as-is if present)
    "BeforeTool": "BeforeTool",
    "AfterTool": "AfterTool",
    "BeforeAgent": "BeforeAgent",
    "AfterAgent": "AfterAgent",
}


def sanitize_version(version: str) -> str:
    """Sanitize version for semver compliance.

    Converts PEP 440 dev versions (.devN) and legacy -testing.N
    formats to semver pre-release format (-dev.N).
    """
    import re

    # Replace -testing.N with -dev.N
    if "-testing." in version:
        return version.replace("-testing.", "-dev.")
    # Replace PEP 440 .devN with semver -dev.N
    version = re.sub(r"\.dev(\d+)", r"-dev.\1", version)
    return version


def get_project_version(aops_root: Path) -> str:
    """Get the project version.

    Tries in order:
    1. uv version (dynamic versioning)
    2. git describe (for dev versions)
    3. git tags (stable version)
    4. Fallback to 0.1.0
    """
    # 1. Try uv version if uv is available and it's a uv project
    try:
        result = subprocess.run(
            ["uv", "tree", "--depth", "0"],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            # Output format: academicops v0.2.1 (...)
            for line in result.stdout.splitlines():
                if "academicops v" in line:
                    version = line.split(" v")[1].split(" ")[0]
                    return sanitize_version(version)
    except FileNotFoundError:
        pass

    # 2. Try git describe for a more accurate dev version
    try:
        # Exclude common meta-tags and ALL pre-release tags to find the base stable version
        result = subprocess.run(
            [
                "git",
                "describe",
                "--tags",
                "--always",
                "--dirty",
                "--exclude",
                "latest",
                "--exclude",
                "testing",
                "--exclude",
                "*.dev*",
                "--exclude",
                "*-dev.*",
                "--exclude",
                "*-alpha*",
                "--exclude",
                "*-beta*",
                "--exclude",
                "*-rc*",
                "--match",
                "v[0-9]*",
            ],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            desc = result.stdout.strip().lstrip("v")
            # If it's just a short SHA (no tag), it's probably 0.1.0-dev
            if len(desc) == 8 and all(c in "0123456789abcdef" for c in desc):
                return f"0.1.0-dev.0+g{desc}"

            # Convert git describe format (0.2.1-5-gabc123) to semver (0.2.2-dev.5+gabc123)
            # This logic assumes the stable tag was found because we excluded pre-releases.
            if "-" in desc:
                parts = desc.split("-")
                base = parts[0]
                # parts[1] is the number of commits since the tag
                if len(parts) >= 2 and parts[1].isdigit():
                    dev_num = parts[1]
                    sha = parts[2] if len(parts) > 2 else ""
                    dirty = ".dirty" if "dirty" in desc else ""

                    # BUMP base version to ensure dev is > stable in semver
                    # (e.g., 0.3.14-5-gabc -> 0.3.15-dev.5+gabc)
                    v_parts = base.split(".")
                    if len(v_parts) == 3:
                        major, minor, patch = v_parts
                        base = f"{major}.{minor}.{int(patch) + 1}"

                    return f"{base}-dev.{dev_num}+{sha}{dirty}"
            return sanitize_version(desc)
    except FileNotFoundError:
        pass

    # 3. Fallback to stable tags as before
    try:
        result = subprocess.run(
            ["git", "tag", "--merged", "HEAD", "--sort=-v:refname", "--list", "v0.*"],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        tags = [t.strip() for t in result.stdout.split("\n") if t.strip()]
        stable_tags = [
            t
            for t in tags
            if not any(
                s in t
                for s in [
                    "-testing",
                    ".dev",
                    "-dev.",
                    "-beta",
                    "-rc",
                    "-alpha",
                ]
            )
        ]
        if stable_tags:
            return stable_tags[0].lstrip("v")
        if tags:
            return sanitize_version(tags[0].lstrip("v"))
    except Exception:
        pass

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
    VALID_GEMINI_EVENTS = (
        "SessionStart",
        "BeforeAgent",
        "AfterAgent",
        "BeforeTool",
        "AfterTool",
        "SessionEnd",
    )
    gemini_hooks: dict = {}

    for claude_event, hook_list in src_hooks.items():
        # Skip disabled hooks
        if claude_event.endswith("-disabled"):
            continue

        # Map event name(s)
        target_events = CLAUDE_TO_GEMINI_EVENTS.get(claude_event, [claude_event])
        if isinstance(target_events, str):
            target_events = [target_events]

        for gemini_event in target_events:
            # Skip events that don't exist in Gemini
            if gemini_event not in VALID_GEMINI_EVENTS:
                print(f"  Skipping unsupported Gemini event: {gemini_event} (from {claude_event})")
                continue

            # Transform hook commands
            transformed_hooks = []
            for hook_entry in hook_list:
                new_entry = {}
                # Gemini CLI requires a 'matcher' key at the root of the hook entry
                if "matcher" not in hook_entry:
                    # SessionStart uses 'startup', AfterAgent/SessionEnd use '*', etc.
                    new_entry["matcher"] = "startup" if gemini_event == "SessionStart" else "*"

                for key, value in hook_entry.items():
                    if key == "hooks":
                        new_hooks = []
                        for hook in value:
                            new_hook = dict(hook)
                            if "command" in new_hook:
                                # Replace Claude variable with Gemini variable
                                cmd = new_hook["command"]
                                cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")
                                cmd = cmd.replace("router.py", "router.sh")

                                # Ensure we use the correct client flag for Gemini
                                cmd = cmd.replace("--client claude", "--client gemini")

                                # Gemini CLI doesn't pass hook_event_name in stdin payload like Claude does,
                                # so we append it as a CLI argument for router.py to detect the event type
                                cmd = f"{cmd} {gemini_event}"

                                new_hook["command"] = cmd
                            new_hooks.append(new_hook)
                        new_entry[key] = new_hooks
                    else:
                        new_entry[key] = value
                transformed_hooks.append(new_entry)

            if gemini_event not in gemini_hooks:
                gemini_hooks[gemini_event] = []
            gemini_hooks[gemini_event].extend(transformed_hooks)

    # Write Gemini-compatible hooks.json
    # Gemini CLI requires {"hooks": {...}} wrapper — the hooks property must be an object
    with open(dst_path, "w") as f:
        json.dump({"hooks": gemini_hooks}, f, indent=2)
        f.write("\n")
    print(f"  ✓ Generated Gemini hooks.json with {len(gemini_hooks)} events")


def validate_gemini_agent_schema(frontmatter: dict, filename: str) -> dict:
    """Validate and transform frontmatter to comply with Gemini agent schema.

    Gemini CLI agent schema requires:
    - name (required): slug format (lowercase, numbers, hyphens, underscores)
    - description (required): short description
    - kind: "local" or "remote" (default: "local")
    - tools: array of tool names
    - model: specific model or "inherit" (default: "inherit")
    - temperature: 0.0-2.0 (optional)
    - max_turns: number (default: 15)
    - timeout_mins: number (default: 5)

    Raises ValueError if required fields are missing or invalid.
    """
    import re

    errors = []

    # Validate required fields
    if "name" not in frontmatter or not frontmatter["name"]:
        errors.append("Missing required field: name")
    else:
        name = frontmatter["name"]
        # Validate slug format: lowercase letters, numbers, hyphens, underscores
        if not re.match(r"^[a-z0-9_-]+$", name):
            errors.append(
                f"Invalid name '{name}': must be lowercase with only letters, "
                "numbers, hyphens, and underscores"
            )

    if "description" not in frontmatter or not frontmatter["description"]:
        errors.append("Missing required field: description")

    if errors:
        raise ValueError(
            f"Agent '{filename}' schema validation failed:\n  - " + "\n  - ".join(errors)
        )

    # Set defaults for optional fields
    if "kind" not in frontmatter:
        frontmatter["kind"] = "local"
    elif frontmatter["kind"] not in ("local", "remote"):
        raise ValueError(
            f"Agent '{filename}': kind must be 'local' or 'remote', got '{frontmatter['kind']}'"
        )

    # Model mapping: Claude model names -> Gemini model names
    CLAUDE_TO_GEMINI_MODEL = {
        "opus": "gemini-3-pro-preview",
        "sonnet": "gemini-3-flash-preview",
        "haiku": "gemini-3-flash-preview",
        "claude-opus-4-5-20251101": "gemini-3-pro-preview",
        "claude-sonnet-4-20250514": "gemini-3-flash-preview",
    }

    if "model" not in frontmatter:
        frontmatter["model"] = "inherit"
    else:
        model = frontmatter["model"]
        # Map Claude model names to Gemini equivalents
        if model in CLAUDE_TO_GEMINI_MODEL:
            frontmatter["model"] = CLAUDE_TO_GEMINI_MODEL[model]

    # Set defaults for optional numeric fields
    if "max_turns" not in frontmatter:
        frontmatter["max_turns"] = 15

    if "timeout_mins" not in frontmatter:
        frontmatter["timeout_mins"] = 5

    # Temperature is optional, only validate if present
    if "temperature" in frontmatter:
        temp = frontmatter["temperature"]
        if not isinstance(temp, int | float) or temp < 0 or temp > 2:
            raise ValueError(
                f"Agent '{filename}': temperature must be between 0.0 and 2.0, got {temp}"
            )

    # Whitelist-and-drop: Gemini rejects unknown keys. Claude-only fields like
    # skills, subagents, mcpServers, disallowedTools, permissionMode, maxTurns
    # (camelCase), effort, background, isolation are silently stripped here.
    GEMINI_ALLOWED_KEYS = {
        "name",
        "description",
        "kind",
        "tools",
        "model",
        "temperature",
        "max_turns",
        "timeout_mins",
    }
    for key in list(frontmatter.keys()):
        if key not in GEMINI_ALLOWED_KEYS:
            del frontmatter[key]

    return frontmatter


def transform_agent_for_platform(content: str, platform: str, filename: str = "agent") -> str:
    """Transform agent markdown for a specific platform.

    For Gemini: renames mcp__* tools from frontmatter by stripping prefix,
                and validates/applies Gemini agent schema with defaults.
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

    if not frontmatter:
        return content

    original_tools = frontmatter.get("tools", [])

    # Tool name mapping: Claude Code -> Gemini CLI
    # (inverse of the Claude mapping below)
    GEMINI_TOOL_NAME_MAP = {
        # File operations (Claude Code -> Gemini)
        "Read": "read_file",
        "Write": "write_file",
        "Edit": "replace",
        "Glob": "glob",
        "Grep": "grep_search",
        "grep": "grep_search",  # lowercase variant
        # Shell execution
        "Bash": "run_shell_command",
        "bash": "run_shell_command",  # lowercase variant
        # Skills/Agents
        "Skill": "activate_skill",
        "Task": "activate_skill",
        "Agent": "activate_skill",
        # Web operations
        "WebFetch": "web_fetch",
        "WebSearch": "google_web_search",
        # Browser/Playwright (Claude Code -> Gemini chrome-devtools-mcp)
        "browser_navigate": "navigate_page",
        "browser_snapshot": "take_snapshot",
        "browser_take_screenshot": "take_screenshot",
        "browser_click": "click",
        "browser_wait_for": "wait_for",
        "browser_evaluate": "evaluate_script",
        "browser_type": "type_text",
        "browser_resize": "resize_page",
    }

    # Handle case where tools is already a string (no transformation needed for format)
    if isinstance(original_tools, str):
        if platform == "gemini":
            # Remap tool names for Gemini
            tools_list = [t.strip() for t in original_tools.split(",")]
            filtered = []
            for t in tools_list:
                # Convert double underscores to single underscores for Gemini MCP tool names
                tool_name = t.replace("__", "_")
                filtered.append(GEMINI_TOOL_NAME_MAP.get(tool_name, tool_name))
            frontmatter["tools"] = filtered  # Convert to list for Gemini schema
            # Remove 'color' field - not supported by Gemini CLI
            frontmatter.pop("color", None)
            # Validate and apply Gemini schema defaults
            frontmatter = validate_gemini_agent_schema(frontmatter, filename)
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
            return f"---\n{new_frontmatter}---{parts[2]}"
        return content

    if platform == "gemini":
        # Remap tool names for Gemini, preserving order and dropping duplicates
        # (multiple Claude tools can map to a single Gemini tool, e.g. Skill/Task/Agent
        # all collapse to activate_skill).
        filtered_tools: list[str] = []
        seen: set[str] = set()
        for t in original_tools:
            # Convert double underscores to single underscores for Gemini MCP tool names
            tool_name = t.replace("__", "_")
            # Remap to Gemini tool name if mapping exists, otherwise keep as-is
            mapped = GEMINI_TOOL_NAME_MAP.get(tool_name, tool_name)
            if mapped not in seen:
                seen.add(mapped)
                filtered_tools.append(mapped)

        frontmatter["tools"] = filtered_tools
        # Remove 'color' field - not supported by Gemini CLI
        frontmatter.pop("color", None)
        # Validate and apply Gemini schema defaults
        frontmatter = validate_gemini_agent_schema(frontmatter, filename)
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{new_frontmatter}---{parts[2]}"

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
            "Agent": "Agent",
            "WebFetch": "WebFetch",
            "WebSearch": "WebSearch",
            "TodoWrite": "TodoWrite",
            "AskUserQuestion": "AskUserQuestion",
            "NotebookEdit": "NotebookEdit",
            # Browser/Playwright (Gemini chrome-devtools-mcp -> Claude Code)
            "navigate_page": "browser_navigate",
            "take_snapshot": "browser_snapshot",
            "take_screenshot": "browser_take_screenshot",
            "click": "browser_click",
            "wait_for": "browser_wait_for",
            "evaluate_script": "browser_evaluate",
            "type_text": "browser_type",
            "resize_page": "browser_resize",
            # Passthrough for browser_* names (already canonical)
            "browser_navigate": "browser_navigate",
            "browser_snapshot": "browser_snapshot",
            "browser_take_screenshot": "browser_take_screenshot",
            "browser_click": "browser_click",
            "browser_wait_for": "browser_wait_for",
            "browser_evaluate": "browser_evaluate",
            "browser_type": "browser_type",
            "browser_resize": "browser_resize",
        }

        # Transform each tool name
        transformed_tools = []
        for tool in original_tools:
            if tool.startswith("mcp__"):
                # MCP tools keep their full name
                transformed_tools.append(tool)
            elif tool.startswith("mcp_"):
                # Convert Gemini format (mcp_server_tool) back to Claude format (mcp__server__tool)
                # We assume the first word after mcp_ is the server name.
                parts = tool.split("_", 2)
                if len(parts) == 3:
                    transformed_tools.append(f"mcp__{parts[1]}__{parts[2]}")
                else:
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
            "Grep(": "grep_search(",
            "Read tool": "read_file tool",
            "Write tool": "write_file tool",
            "Edit tool": "replace tool",
            "`Read`": "`read_file`",
            "`Write`": "`write_file`",
            "`Edit`": "`replace`",
            "`ls`": "`list_directory`",
            "`Glob`": "`glob`",
            "`Grep`": "`grep_search`",
            "Read or Grep": "read_file or grep_search",
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
        # Replace Claude plugin path variable with Gemini equivalent
        text = text.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")

        # Convert mcp__server__tool to mcp_server_tool in body (matches frontmatter)
        import re

        text = re.sub(r"mcp__([a-zA-Z0-9_-]+)__([a-zA-Z0-9_-]*)", r"mcp_\1_\2", text)

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

    # 1. Copy content — everything except known exclusions
    EXCLUDED_FROM_COPY = {
        "pyproject.toml",  # Generated with version from root
        "hooks",  # Handled separately in section 2 (Gemini hooks.json transform)
        "indices",  # PATHS.md is user config, no other generated indices
        "__pycache__",
    }

    for src_item in src_dir.iterdir():
        if src_item.name in EXCLUDED_FROM_COPY or src_item.name.startswith("."):
            continue
        if src_item.name == "agents" and src_item.is_dir():
            # Special handling for agents: transform frontmatter and translate tool calls
            dst = content_dir / src_item.name
            dst.mkdir(parents=True, exist_ok=True)
            for agent_file in src_item.glob("*.md"):
                content = agent_file.read_text()
                # Transform frontmatter (filter mcp__ tools for Gemini, apply schema)
                content = transform_agent_for_platform(content, platform, agent_file.name)
                # Translate tool calls in body text
                content = translate_tool_calls(content, platform)
                (dst / agent_file.name).write_text(content)
            print(f"  ✓ Translated and copied agents -> {dst}")
        else:
            safe_copy(src_item, content_dir / src_item.name)

    # 1a. Post-copy: translate tool names in all .md files for Gemini
    # Agents get transform_agent_for_platform above (frontmatter + body);
    # this pass catches skills, commands, lib, and top-level .md files
    # that were copied verbatim by safe_copy.
    if platform == "gemini":
        translated_count = 0
        for md_file in content_dir.rglob("*.md"):
            # Agent files are already translated in the special-cased loop above, skip them here.
            if (
                md_file.relative_to(content_dir).parts
                and md_file.relative_to(content_dir).parts[0] == "agents"
            ):
                continue
            original = md_file.read_text()
            translated = translate_tool_calls(original, platform)
            if translated != original:
                md_file.write_text(translated)
                translated_count += 1
        if translated_count:
            print(f"  ✓ Translated tool names in {translated_count} .md files")

    # 1b. Generate pyproject.toml with version from root
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

    # 2b. Copy Gemini context file (referenced by gemini-extension.json as
    # contextFileName). It lives at the repo root, not inside aops-core/.
    # GEMINI.md uses `@path` imports; resolve each referenced file once and
    # ship it alongside so Gemini's ImportProcessor can satisfy the imports.
    if platform == "gemini":
        src_gemini_md = aops_root / "GEMINI.md"
        if not src_gemini_md.exists():
            print(f"Error: {src_gemini_md} not found.", file=sys.stderr)
            sys.exit(1)
        safe_copy(src_gemini_md, dist_dir / "GEMINI.md")
        print(f"  ✓ Copied GEMINI.md -> {dist_dir / 'GEMINI.md'}")

        import re as _re

        imported = 0
        for m in _re.finditer(r"^@([^\s]+)", src_gemini_md.read_text(), flags=_re.MULTILINE):
            rel = m.group(1)
            src_import = aops_root / rel
            if src_import.exists():
                dst_import = dist_dir / rel
                dst_import.parent.mkdir(parents=True, exist_ok=True)
                safe_copy(src_import, dst_import)
                imported += 1
            else:
                print(
                    f"Warning: GEMINI.md imports {rel} but {src_import} not found.",
                    file=sys.stderr,
                )
        if imported:
            print(f"  ✓ Resolved {imported} @-imports referenced by GEMINI.md")

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
                    f.write("\n")
            except Exception as e:
                print(f"Error processing extension manifest: {e}", file=sys.stderr)
                raise
        else:
            print(f"Error: {src_extension_json} not found.", file=sys.stderr)
            sys.exit(1)

    if platform == "claude":
        src_plugin_json = src_dir / ".claude-plugin" / "plugin.json"
        dist_plugin_dir = dist_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                dist_plugin_dir.mkdir(parents=True, exist_ok=True)
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version
                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
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

            # Write .mcp.json to dist only
            if platform == "claude":
                claude_mcp_config = mcp_template.get("claude", mcp_template)
                dist_mcp_path = dist_dir / ".mcp.json"
                with open(dist_mcp_path, "w") as f:
                    json.dump(claude_mcp_config, f, indent=2)
                    f.write("\n")

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
                    with open(dist_extension_json) as f:
                        manifest = json.load(f)
                    current_mcps = manifest.get("mcpServers", {})
                    manifest["mcpServers"] = {**current_mcps, **gemini_mcps}

                    # MCP server arguments from mcp.json.template use ${extensionPath}
                    # which is correct since plugin content is at the root

                    with open(dist_extension_json, "w") as f:
                        json.dump(manifest, f, indent=2)
                        f.write("\n")
                    print(f"✓ Updated {dist_extension_json} with MCP config")

        except Exception as e:
            print(f"Error processing template {template_path}: {e}", file=sys.stderr)
            raise

    # 5. Commands (Gemini only for now as they use .toml)
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
                    "--no-gitignore",
                ],
                env=os.environ,
                check=False,
            )
        # Remove .md command files for Gemini (uses TOML format)
        for md_file in commands_dist.glob("*.md"):
            md_file.unlink()
            print(f"  - Removed {md_file.name} (Gemini uses TOML)")

    print(f"✓ Built {plugin_name} ({platform})")
    return gemini_mcps


def build_aops_tools(
    aops_root: Path,
    dist_root: Path,
    platform: str = "gemini",
    version: str = "0.1.0",
):
    """Build the aops-tools extension for a specific platform.

    aops-tools is a lightweight package of fungible domain skills.
    It has no hooks, agents, commands, or MCP servers — just skills and manifests.
    """
    print(f"Building aops-tools for {platform} (v{version})...")
    plugin_name = "aops-tools"
    src_dir = aops_root / plugin_name

    if not src_dir.exists():
        print(f"  ⚠️  {src_dir} not found, skipping aops-tools build")
        return

    dist_dir = dist_root / f"aops-tools-{platform}"
    content_dir = dist_dir

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # Copy skills and index files
    items_to_copy = ["skills", "SKILLS.md"]

    for item in items_to_copy:
        src = src_dir / item
        if src.exists():
            safe_copy(src, content_dir / item)

    # Gemini: generate extension manifest with version injection
    if platform == "gemini":
        src_extension_json = src_dir / "gemini-extension.json"
        dist_extension_json = dist_dir / "gemini-extension.json"
        if src_extension_json.exists():
            try:
                manifest = json.loads(src_extension_json.read_text())
                manifest["version"] = version
                with open(dist_extension_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                print(f"  ✓ Generated gemini-extension.json (v{version})")
            except Exception as e:
                print(f"Error processing extension manifest: {e}", file=sys.stderr)
                raise
        else:
            print(f"  ⚠️  No gemini-extension.json found in {src_dir}")

    # Claude: copy plugin.json with version injection
    if platform == "claude":
        src_plugin_json = src_dir / ".claude-plugin" / "plugin.json"
        dist_plugin_dir = dist_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                dist_plugin_dir.mkdir(parents=True, exist_ok=True)
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version
                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Updated and copied plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    print(f"✓ Built {plugin_name} ({platform})")


def build_aops_cowork(
    aops_root: Path,
    dist_root: Path,
    aca_data_path: str,
    version: str = "0.1.0",
):
    """Build the aops-cowork plugin for Claude Cowork.

    Cowork runs in a VM with a read-only plugin cache and cannot execute hooks
    or Python scripts. This build produces a stripped-down Claude-format plugin
    containing only the components Cowork can use:
    - skills/ (markdown procedural knowledge)
    - commands/ (slash command definitions)
    - agents/ (agent definitions)
    - .mcp.json (MCP server config)
    - .claude-plugin/plugin.json (manifest)
    - Documentation markdown files
    """
    print(f"Building aops-cowork (v{version})...")
    src_dir = aops_root / "aops-core"
    dist_dir = dist_root / "aops-cowork"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # Write version info
    commit_sha = get_git_commit_sha(aops_root)
    if commit_sha:
        write_plugin_version(src_dir, commit_sha)

    # 1. Copy only Cowork-compatible content (no hooks, lib, scripts, config)
    COWORK_INCLUDE = {
        "skills",
        "commands",
        "agents",
    }
    # Top-level markdown files to include
    COWORK_MD_INCLUDE = {
        "AXIOMS.md",
        "HEURISTICS.md",
        "TAXONOMY.md",
        "CONSTRAINTS.md",
        "agent-env-map.conf",
    }

    for src_item in src_dir.iterdir():
        if src_item.name.startswith(".") or src_item.name == "__pycache__":
            continue

        if src_item.name in COWORK_INCLUDE:
            if src_item.name == "agents" and src_item.is_dir():
                # Transform agent frontmatter for Claude format (same as claude build)
                dst = dist_dir / src_item.name
                dst.mkdir(parents=True, exist_ok=True)
                for agent_file in src_item.glob("*.md"):
                    content = agent_file.read_text()
                    content = transform_agent_for_platform(content, "claude", agent_file.name)
                    content = translate_tool_calls(content, "claude")
                    (dst / agent_file.name).write_text(content)
                print(f"  ✓ Copied agents -> {dst}")
            else:
                safe_copy(src_item, dist_dir / src_item.name)
        elif src_item.is_file() and src_item.name in COWORK_MD_INCLUDE:
            safe_copy(src_item, dist_dir / src_item.name)

    # 2. Plugin manifest — same format as Claude Code but with hooks stripped
    src_plugin_json = src_dir / ".claude-plugin" / "plugin.json"
    dist_plugin_dir = dist_dir / ".claude-plugin"
    dist_plugin_dir.mkdir(parents=True, exist_ok=True)
    if src_plugin_json.exists():
        manifest = json.loads(src_plugin_json.read_text())
        manifest["version"] = version
        manifest["name"] = "aops-cowork"
        manifest["description"] = (
            "academicOps for Cowork - skills, agents, and tools for research workflow automation"
        )
        # Cowork cannot execute hooks, so we don't reference them
        with open(dist_plugin_dir / "plugin.json", "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        print(f"  ✓ Generated plugin.json (v{version})")

    # 3. MCP config — Cowork uses the same format as Claude Code
    template_path = src_dir / "mcp.json.template"
    if template_path.exists():
        mcp_template = json.loads(template_path.read_text())
        claude_mcp_config = mcp_template.get("claude", mcp_template)
        with open(dist_dir / ".mcp.json", "w") as f:
            json.dump(claude_mcp_config, f, indent=2)
            f.write("\n")
        print("  ✓ Generated .mcp.json")

    # 3a. MCP launch scripts — .mcp.json references scripts/run-mcp.sh
    mcp_scripts = ["run-mcp.sh", "ensure-path.sh"]
    scripts_src = src_dir / "scripts"
    scripts_dst = dist_dir / "scripts"
    if scripts_src.exists():
        scripts_dst.mkdir(parents=True, exist_ok=True)
        for script_name in mcp_scripts:
            src_script = scripts_src / script_name
            if src_script.exists():
                safe_copy(src_script, scripts_dst / script_name)
        print("  ✓ Copied MCP launch scripts")

    # 4. Also include aops-tools skills if available
    tools_src = aops_root / "aops-tools" / "skills"
    if tools_src.exists():
        tools_skills_dst = dist_dir / "skills"
        # Merge tool skills into the main skills directory
        for skill_dir in tools_src.iterdir():
            dst = tools_skills_dst / skill_dir.name
            if not dst.exists():
                safe_copy(skill_dir, dst)
        tools_index = aops_root / "aops-tools" / "SKILLS.md"
        if tools_index.exists():
            # Append tools skills index to main SKILLS.md
            main_skills_md = dist_dir / "SKILLS.md"
            if main_skills_md.exists():
                with open(main_skills_md, "a") as f:
                    f.write("\n\n## Domain Tools\n\n")
                    f.write(tools_index.read_text())
        print("  ✓ Merged aops-tools skills")

    print("✓ Built aops-cowork")


def build_antigravity(aops_root: Path, dist_root: Path, all_mcps: dict):
    """Build the antigravity distribution."""
    print("Building antigravity...")
    ag_dist = dist_root / "aops-antigravity"
    if ag_dist.exists():
        shutil.rmtree(ag_dist)
    ag_dist.mkdir(parents=True)

    # 1. Global Workflows
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

    print("✓ Built antigravity dist")


def install_pkb_binary(dist_dir: Path, binary_path: Path) -> None:
    """Install pre-built binaries into a distribution directory.

    Copies pkb and aops binaries to dist_dir/bin/ and sets executable permissions.
    """
    bin_dir = dist_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    dest = bin_dir / "pkb"
    shutil.copy2(binary_path, dest)
    dest.chmod(0o755)
    print(f"  ✓ Installed pkb binary -> {dest}")

    # Install aops binary if present in the same directory
    aops_binary = binary_path.parent / "aops"
    if aops_binary.exists():
        aops_dest = bin_dir / "aops"
        shutil.copy2(aops_binary, aops_dest)
        aops_dest.chmod(0o755)
        print(f"  ✓ Installed aops binary -> {aops_dest}")


def main():
    parser = argparse.ArgumentParser(description="Build script for AcademicOps Gemini extensions.")
    parser.add_argument("--version", action="store_true", help="Print detected version and exit")
    parser.add_argument(
        "--set-version",
        type=str,
        default=None,
        help="Override the auto-detected version (e.g. '0.3.1-dev.42')",
    )
    parser.add_argument(
        "--pkb-binary",
        type=str,
        default=None,
        help="Path to pre-built pkb binary to include in dist",
    )
    parser.add_argument(
        "--target-platform",
        type=str,
        default=None,
        help="Platform label for archive naming (e.g. 'linux-x86_64', 'macos-aarch64')",
    )
    args = parser.parse_args()

    aops_root = Path(__file__).parent.parent.resolve()
    if args.version:
        print(get_project_version(aops_root))
        sys.exit(0)

    aca_data_path = os.environ.get("ACA_DATA")

    if not aca_data_path:
        print("Error: ACA_DATA environment variable must be set.")
        sys.exit(1)

    # Infer aops_root from script location
    aops_root = Path(__file__).parent.parent.resolve()
    print(f"Info: aops_root inferred to {aops_root}")
    dist_root = aops_root / "dist"

    # Get version: use --set-version override or detect from git tags
    if args.set_version:
        version = sanitize_version(args.set_version)
        print(f"Using override version: v{version}")
    else:
        version = get_project_version(aops_root)
    print(f"Building AcademicOps v{version}...")

    # Clean/Create dist
    if not dist_root.exists():
        dist_root.mkdir()

    # Generate GHA agent prompts and reusable workflows for the dist repo
    generate_gha_agents(aops_root, dist_root)
    generate_reusable_workflows(aops_root, dist_root)

    # Build components (Gemini)
    core_mcps_gemini = build_aops_core(aops_root, dist_root, aca_data_path, "gemini", version)

    # Build components (Claude)
    build_aops_core(aops_root, dist_root, aca_data_path, "claude", version)

    # Build aops-tools (domain skills package)
    build_aops_tools(aops_root, dist_root, "gemini", version)
    build_aops_tools(aops_root, dist_root, "claude", version)

    # Build Cowork plugin (stripped-down Claude-format for Cowork desktop)
    build_aops_cowork(aops_root, dist_root, aca_data_path, version)

    # Install PKB binary if provided
    pkb_binary = Path(args.pkb_binary) if args.pkb_binary else None
    if pkb_binary:
        if not pkb_binary.exists():
            print(f"Error: PKB binary not found at {pkb_binary}", file=sys.stderr)
            sys.exit(1)
        install_pkb_binary(dist_root / "aops-gemini", pkb_binary)
        install_pkb_binary(dist_root / "aops-claude", pkb_binary)

    # Build Antigravity (global config if needed)
    build_antigravity(aops_root, dist_root, core_mcps_gemini)

    # Generate marketplace.json for local dev and dist repo
    generate_marketplace(aops_root, dist_root, version)

    package_artifacts(aops_root, dist_root, version, target_platform=args.target_platform)

    # Create git tags for release (only for generic builds, not platform-specific)
    if not args.target_platform:
        create_git_tags(aops_root, version)

    print("\nBuild complete. Dist artifacts in dist/")


_GHA_OPS_SECTION = """\
## GHA Operational Rules

- **Credential Isolation (P#51)**: Use `GH_TOKEN` from environment. Never use personal credentials or `gh auth login`.
- **One review only**: File a single `gh pr review` — do not post separate comments. Put everything in the review body.
- **Be specific**: Reference file paths, line numbers, and axiom numbers (e.g. `utils.py:45 — P#8 violation`).
- **Depth over breadth**: One well-analysed finding beats seven surface nits.
- **Conservative fixes**: If a fix might change intended behaviour, comment instead.
- **No manual lint/style fixes**: Automated tooling handles that; focus on substance.\
"""

_GHA_TRAILER_MAP: dict[str, tuple[str, str]] = {
    "enforcer": ("Review-By", "aops-enforcer"),
    "qa": ("QA-By", "aops-qa"),
}


def _parse_agent_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter delimited by '---' lines.

    Returns (frontmatter_dict, body_text).
    Only parses simple scalar key: value lines (not lists or nested).
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5 :]  # skip "\n---\n"

    frontmatter: dict = {}
    for line in fm_text.splitlines():
        if ": " in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, val = line.partition(": ")
            frontmatter[key.strip()] = val.strip()

    return frontmatter, body


def _strip_agent_body_h1(body: str) -> str:
    """Strip the leading '# Heading' line from an agent body, if present."""
    lines = body.lstrip("\n").splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        remaining = lines[1:]
        if remaining and remaining[0] == "\n":
            remaining = remaining[1:]
        return "".join(remaining)
    return body.lstrip("\n")


def generate_gha_agents(aops_root: Path, dist_root: Path) -> None:
    """Generate GHA agent prompts from canonical aops-core/agents/ sources.

    Reads enforcer.md and qa.md — the review agents —
    transforms them for GitHub Actions context (no plugin, axioms inlined),
    and writes to dist/gha-agents/.

    dev-standards.md and framework-ops.md are Claude Code-only subagents
    and are intentionally excluded.
    """
    print("\nGenerating GHA agent prompts...")
    agents_src = aops_root / "aops-core" / "agents"
    axioms_path = aops_root / "aops-core" / "AXIOMS.md"
    gha_out = dist_root / "gha-agents"
    gha_out.mkdir(parents=True, exist_ok=True)

    if not axioms_path.exists():
        print(f"  ✗ {axioms_path} not found — skipping GHA agent generation")
        return

    _, axioms_body = _parse_agent_frontmatter(axioms_path.read_text())
    axioms_body = axioms_body.strip()

    # Review agents only — dev-standards and framework-ops are CC-only subagents
    review_agents = ["enforcer", "qa"]

    for agent_name in review_agents:
        src_path = agents_src / f"{agent_name}.md"
        if not src_path.exists():
            print(f"  ⚠ {src_path} not found, skipping")
            continue

        frontmatter, body = _parse_agent_frontmatter(src_path.read_text())
        description = frontmatter.get("description", agent_name)

        # Strip the canonical "# {Name} Agent" heading — replaced by
        # the description-derived identity header.
        body_content = _strip_agent_body_h1(body).strip()

        trailer_key, trailer_value = _GHA_TRAILER_MAP.get(
            agent_name, ("Review-By", f"aops-{agent_name}")
        )

        sections = [
            f"# {description}",
            "",
            body_content,
            "",
            "---",
            "",
            _GHA_OPS_SECTION,
            "",
            "When pushing fixes, commit with the required trailer:",
            "",
            "```bash",
            "git add -A",
            f'git commit -m "fix: address review findings\\n\\n{trailer_key}: {trailer_value}"',
            "git push",
            "```",
            "",
            "---",
            "",
            "## Framework Axioms",
            "",
            "<!-- Source: aops-core/AXIOMS.md — regenerate via `scripts/build.py` if axioms change -->",
            "",
            "The following principles are always active, regardless of domain context.",
            "",
            axioms_body,
            "",
        ]

        out_path = gha_out / f"{agent_name}.agent.md"
        out_path.write_text("\n".join(sections))
        print(f"  ✓ {out_path.relative_to(aops_root)}")


# --- Reusable GHA Workflow Generation ---

_DIST_REPO = "nicsuzor/aops"

_GHA_WORKFLOW_AGENTS: dict[str, dict[str, str | bool | int]] = {
    "enforcer": {
        "display_name": "Enforcer Review",
        "description": "Universal standards enforcer — axiom compliance reviewer",
        "can_push": True,
        "tools": "Bash,Edit,Read,Write",
        "trailer": "Enforcer-By: agent",
        "timeout": 30,
    },
    "qa": {
        "display_name": "QA Verification",
        "description": "Independent end-to-end verification before completion",
        "can_push": False,
        "tools": "Bash,Read",
        "trailer": "QA-By: agent",
        "timeout": 45,
    },
}

# Template uses __PLACEHOLDER__ style to avoid conflicts with GitHub ${{ }} expressions
# and shell { } grouping syntax.
_GHA_WORKFLOW_TEMPLATE = """\
# Agent: __DISPLAY_NAME__
# __DESCRIPTION__
# Prompt: gha-agents/__AGENT_NAME__.agent.md (generated from aops-core/agents/__AGENT_NAME__.md)
#
# Reusable workflow. Call from other repos:
#   uses: __DIST_REPO__/.github/workflows/agent-__AGENT_NAME__.yml@main

name: "Agent: __DISPLAY_NAME__"

on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: 'PR number to review'
        type: string
        required: true
      ref:
        description: 'Git ref to checkout'
        type: string
        required: true
  workflow_call:
    inputs:
      pr_number:
        description: 'PR number to review'
        type: string
        required: true
      ref:
        description: 'Git ref to checkout'
        type: string
        required: true
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN:
        required: true

jobs:
  __JOB_ID__:
    name: __DISPLAY_NAME__
    runs-on: ubuntu-latest
    timeout-minutes: __TIMEOUT__
    concurrency:
      group: agent-__AGENT_NAME__-${{ inputs.pr_number }}
      cancel-in-progress: true
    permissions:
      contents: __CONTENTS_PERM__
      pull-requests: write
      statuses: write
      id-token: write
      issues: write
      actions: read
    steps:
      # Checkout the caller's repo (the PR under review)
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ inputs.ref }}

      # Checkout dist repo for the generated agent prompt
      - uses: actions/checkout@v4
        with:
          repository: __DIST_REPO__
          path: .aops-dist
          sparse-checkout: gha-agents/__AGENT_NAME__.agent.md

      - name: Loop detection
        id: loop-check
        run: |
          LAST_MSG=$(git log -1 --format='%B')
          if echo "$LAST_MSG" | grep -qE '(Review-By|Audit-By|QA-By|Enforcer-By|Merge-Prep-By):'; then
            echo "Last commit was from an agent — skipping to avoid loop"
            echo "skip=true" >> "$GITHUB_OUTPUT"
          else
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Read agent prompt
        if: steps.loop-check.outputs.skip != 'true'
        id: prompt
        run: |
          PROMPT=$(cat .aops-dist/gha-agents/__AGENT_NAME__.agent.md)
          {
            echo "prompt<<AGENT_EOF"
            echo "$PROMPT"
            echo "AGENT_EOF"
          } >> "$GITHUB_OUTPUT"

      - name: Run __DISPLAY_NAME__
        if: steps.loop-check.outputs.skip != 'true'
        uses: anthropics/claude-code-action@v1
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            ${{ steps.prompt.outputs.prompt }}

            ---

            Review PR #${{ inputs.pr_number }} in repository ${{ github.repository }}.

            1. Read `.agents/CORE.md` from the repo root (if it exists) for local project context.
            2. Run `gh pr view ${{ inputs.pr_number }}` to understand the PR.
            3. Run `gh pr diff ${{ inputs.pr_number }}` to see the changes.
            4. Apply the review protocol from your instructions above.
            5. Use `gh pr review` to file your review (APPROVE or REQUEST_CHANGES).
               Start the review body with `## __DISPLAY_NAME__` for identification.

            If you push fixes, use commit trailer: `__TRAILER__`

            PR ref: ${{ inputs.ref }}
          claude_args: '--allowed-tools "__TOOLS__"'
"""


def generate_reusable_workflows(aops_root: Path, dist_root: Path) -> None:
    """Generate reusable GHA workflows for the dist repo.

    For each review agent (enforcer, qa), generates a workflow YAML
    that can be called from other repos:
        uses: nicsuzor/aops/.github/workflows/agent-enforcer.yml@main

    Each workflow checks out the dist repo for the generated agent prompt
    (from dist/gha-agents/), so no private repo access is needed.
    """
    print("\nGenerating reusable GHA workflows...")
    gha_agents_dir = dist_root / "gha-agents"
    workflows_out = dist_root / ".github" / "workflows"
    workflows_out.mkdir(parents=True, exist_ok=True)

    for agent_name, config in _GHA_WORKFLOW_AGENTS.items():
        agent_file = gha_agents_dir / f"{agent_name}.agent.md"
        if not agent_file.exists():
            print(f"  ⚠ {agent_file} not found, skipping workflow for {agent_name}")
            continue

        job_id = str(config["display_name"]).lower().replace(" ", "-")
        contents_perm = "write" if config["can_push"] else "read"

        workflow = _GHA_WORKFLOW_TEMPLATE
        workflow = workflow.replace("__DIST_REPO__", _DIST_REPO)
        workflow = workflow.replace("__AGENT_NAME__", agent_name)
        workflow = workflow.replace("__DISPLAY_NAME__", str(config["display_name"]))
        workflow = workflow.replace("__DESCRIPTION__", str(config["description"]))
        workflow = workflow.replace("__JOB_ID__", job_id)
        workflow = workflow.replace("__TIMEOUT__", str(config["timeout"]))
        workflow = workflow.replace("__CONTENTS_PERM__", contents_perm)
        workflow = workflow.replace("__TOOLS__", str(config["tools"]))
        workflow = workflow.replace("__TRAILER__", str(config["trailer"]))

        out_path = workflows_out / f"agent-{agent_name}.yml"
        out_path.write_text(workflow)
        print(f"  ✓ {out_path.relative_to(aops_root)}")


def generate_marketplace(aops_root: Path, dist_root: Path, version: str):
    """Generate marketplace.json for both local dev and dist repo consumption.

    Reads the template from templates/marketplace.json and produces two outputs:
    1. .claude-plugin/marketplace.json — for local dev (paths: ./dist/aops-claude)
    2. dist/marketplace.json — for the dist repo (paths: ./aops-claude)
    """
    template_path = aops_root / "templates" / "marketplace.json"
    if not template_path.exists():
        print("  ⚠ templates/marketplace.json not found, skipping marketplace generation")
        return

    with open(template_path) as f:
        data = json.load(f)

    # Get cowork version (may differ from core version)
    cowork_plugin_json = dist_root / "aops-cowork" / ".claude-plugin" / "plugin.json"
    cowork_version = version
    if cowork_plugin_json.exists():
        with open(cowork_plugin_json) as f:
            cowork_version = json.load(f).get("version", version)

    # Inject versions
    for plugin in data.get("plugins", []):
        if plugin.get("name") == "aops-core":
            plugin["version"] = version
        elif plugin.get("name") == "aops-cowork":
            plugin["version"] = cowork_version

    # 1. Dist repo version (sources point to ./aops-claude, ./aops-cowork)
    dist_marketplace_dir = dist_root / ".claude-plugin"
    dist_marketplace_dir.mkdir(parents=True, exist_ok=True)
    dist_marketplace = dist_marketplace_dir / "marketplace.json"
    with open(dist_marketplace, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"  ✓ Generated {dist_marketplace} (for dist repo)")

    # 2. Local dev version (sources point to ./dist/aops-claude, ./dist/aops-cowork)
    local_data = json.loads(json.dumps(data))  # deep copy
    for plugin in local_data.get("plugins", []):
        source = plugin.get("source", "")
        if source.startswith("./"):
            plugin["source"] = f"./dist/{source[2:]}"
    local_marketplace_dir = aops_root / ".claude-plugin"
    local_marketplace_dir.mkdir(parents=True, exist_ok=True)
    local_marketplace = local_marketplace_dir / "marketplace.json"
    with open(local_marketplace, "w") as f:
        json.dump(local_data, f, indent=2)
        f.write("\n")
    print(f"  ✓ Generated {local_marketplace} (for local dev)")


def package_artifacts(
    aops_root: Path, dist_root: Path, version: str, target_platform: str | None = None
):
    """Package the built components into archives for release.

    If target_platform is set (e.g. 'linux-x86_64'), produces platform-specific archives:
    - aops-gemini-linux-x86_64.tar.gz
    - aops-claude-linux-x86_64.tar.gz

    Otherwise produces generic archives:
    - aops-gemini-v{version}.tar.gz
    - aops-claude-v{version}.tar.gz
    - aops-antigravity-v{version}.tar.gz

    Plus 'latest' symlinks for generic archives.
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

    if target_platform:
        # Map our platform labels to Gemini CLI convention
        # Gemini CLI expects: {platform}.{arch}.{name}.tar.gz
        # Our labels: linux-x86_64, macos-aarch64
        # Gemini labels: linux/darwin, x64/arm64
        platform_map = {
            "linux-x86_64": ("linux", "x64"),
            "macos-aarch64": ("darwin", "arm64"),
        }
        gemini_os, gemini_arch = platform_map.get(target_platform, (None, None))

        if gemini_os:
            # Gemini archive: {platform}.{arch}.{name}.tar.gz (Gemini CLI convention)
            gemini_archive = dist_root / f"{gemini_os}.{gemini_arch}.aops-core.tar.gz"
        else:
            gemini_archive = dist_root / f"aops-gemini-{target_platform}.tar.gz"
        with tarfile.open(gemini_archive, "w:gz") as tar:
            tar.add(dist_root / "aops-gemini", arcname=".", filter=_source_filter)
        print(f"  ✓ Packaged {gemini_archive.name}")

        # Claude archive: keep existing naming (not consumed by Gemini CLI)
        claude_archive = dist_root / f"aops-claude-{target_platform}.tar.gz"
        with tarfile.open(claude_archive, "w:gz") as tar:
            tar.add(dist_root / "aops-claude", arcname="aops-claude", filter=_source_filter)
        print(f"  ✓ Packaged {claude_archive.name}")
        return

    # Generic archives (no platform-specific binary)
    # 1. aops-core.tar.gz (generic fallback for Gemini CLI)
    # Named to match extension name in gemini-extension.json
    # gemini-extension.json must be at archive root (arcname=".")
    gemini_archive = dist_root / "aops-core.tar.gz"
    with tarfile.open(gemini_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-gemini", arcname=".", filter=_source_filter)
    print(f"  ✓ Packaged {gemini_archive.name}")

    # 2. aops-claude-v{version}.tar.gz
    claude_archive = dist_root / f"aops-claude-v{version}.tar.gz"
    with tarfile.open(claude_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-claude", arcname="aops-claude", filter=_source_filter)
    print(f"  ✓ Packaged {claude_archive.name}")
    safe_symlink(claude_archive, dist_root / "aops-claude-latest.tar.gz")

    # 3. aops-cowork-v{version}.tar.gz
    cowork_dir = dist_root / "aops-cowork"
    if cowork_dir.exists():
        cowork_archive = dist_root / f"aops-cowork-v{version}.tar.gz"
        with tarfile.open(cowork_archive, "w:gz") as tar:
            tar.add(cowork_dir, arcname="aops-cowork", filter=_source_filter)
        print(f"  ✓ Packaged {cowork_archive.name}")
        safe_symlink(cowork_archive, dist_root / "aops-cowork-latest.tar.gz")

    # 4. aops-antigravity-v{version}.tar.gz
    antigravity_archive = dist_root / f"aops-antigravity-v{version}.tar.gz"
    with tarfile.open(antigravity_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-antigravity", arcname=".", filter=_source_filter)
    print(f"  ✓ Packaged {antigravity_archive.name}")
    safe_symlink(antigravity_archive, dist_root / "aops-antigravity-latest.tar.gz")


def create_git_tags(aops_root: Path, version: str):
    """Create git tags for release: v{version} and latest.

    Tags are created pointing to HEAD. If tags already exist, they are updated.
    Note: Tags are local only - push atomically with the branch (e.g., `git push origin main v{version} latest`) to publish.
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
        print("  ✓ Created tag: latest")
    else:
        print(f"  ✗ Failed to create tag latest: {result.stderr}")

    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=aops_root,
        capture_output=True,
        text=True,
    ).stdout.strip()

    print(f"  Note: Push atomically with: git push origin {branch} {version_tag} latest")


if __name__ == "__main__":
    main()
