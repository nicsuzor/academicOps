#!/usr/bin/env -S uv run python
"""
Build script for AcademicOps extensions.
Generates dist/aops-gemini, dist/aops-claude, dist/aops-tools-gemini, dist/aops-tools-claude, and dist/antigravity.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

# Add shared lib to path (assuming scripts/lib exists)
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.append(str(SCRIPT_DIR / "lib"))

sys.path.insert(0, str(SCRIPT_DIR))

try:
    from build_utils import (
        convert_mcp_to_gemini,
        get_git_commit_sha,
        safe_copy,
        safe_symlink,
        write_plugin_version,
    )
    from transforms.agent_schema import claude_mcp_to_gemini, validate_gemini_agent_schema
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

# Directory/file names that are local build detritus and must never be packaged
# into a plugin artifact. mypy/ruff/pytest caches in particular contain files
# with characters (e.g. '@') that the Cowork upload validator rejects as
# "invalid characters" in the zip path.
BUILD_DETRITUS_NAMES = {
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".venv",
    ".uv-cache",
    ".git",
    ".DS_Store",
}


def sanitize_version(version: str) -> str:
    """Sanitize version for semver compliance.

    Converts PEP 440 dev versions (.devN) and legacy -testing.N
    formats to semver pre-release format (-dev.N).
    """

    # Replace -testing.N with -dev.N
    if "-testing." in version:
        return version.replace("-testing.", "-dev.")
    # Replace PEP 440 .devN with semver -dev.N
    version = re.sub(r"\.dev(\d+)", r"-dev.\1", version)
    return version


# Cowork-only content markers. Skill and command sources wrap Cowork-specific
# instructions in <!-- cowork:only --> ... <!-- /cowork:only -->. The cowork
# build keeps the content (drops the markers); every other build drops both
# the markers and the content. See aops-core/skills/cowork-sync/SKILL.md for
# the runtime semantics these blocks describe.
_COWORK_OPEN = "<!-- cowork:only -->"
_COWORK_CLOSE = "<!-- /cowork:only -->"
_COWORK_BLOCK_RE = re.compile(
    r"\n*[ \t]*"
    + re.escape(_COWORK_OPEN)
    + r"[ \t]*\n(.*?)\n*[ \t]*"
    + re.escape(_COWORK_CLOSE)
    + r"[ \t]*\n*",
    re.DOTALL,
)


def _process_cowork_markers(text: str, platform: str) -> str:
    """Apply cowork-only marker handling for the given build platform.

    - platform == "cowork": replace the block with its content (markers stripped,
      surrounded by one blank line so neighbouring sections stay separated).
    - any other platform: remove the markers AND the content between them, leaving
      a single blank line where the block used to be.
    """
    if platform == "cowork":
        return _COWORK_BLOCK_RE.sub(lambda m: "\n\n" + m.group(1).strip() + "\n\n", text)
    return _COWORK_BLOCK_RE.sub("\n\n", text)


def _git_build_metadata(aops_root: Path) -> str:
    """SemVer build metadata (`+g<sha>[.dirty]`) for the current HEAD, or ''.

    The `g` prefix keeps the identifier alphanumeric and follows `git describe`
    convention. Build metadata is ignored for version precedence (SemVer 2.0
    §10), so this is safe to append unconditionally without affecting ordering.
    """
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if sha.returncode != 0 or not sha.stdout.strip():
            return ""
        meta = f"g{sha.stdout.strip()}"
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=aops_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if dirty.returncode == 0 and dirty.stdout.strip():
            meta += ".dirty"
        return meta
    except FileNotFoundError:
        return ""


def _with_build_metadata(version: str, aops_root: Path) -> str:
    """Append `+g<sha>[.dirty]` if not already present.

    If the working tree is dirty AND the input version has no pre-release
    identifier, the dirty marker is promoted into a pre-release suffix that
    bumps the patch (so `0.3.27` + dirty → `0.3.28-dev.0+g<sha>.dirty`).
    Without this, a dirty build at a clean stable tag would produce e.g.
    `0.3.27+g<sha>.dirty`, which semver §10 treats as equal precedence to
    `0.3.27` itself — meaning a build accidentally tagged as a release
    would beat every legitimate `-dev.N` pre-release downstream. See the
    `v0.3.27+g39ac1ed9.dirty` release incident on nicsuzor/aops.
    """
    if "+" in version:
        return version
    meta = _git_build_metadata(aops_root)
    if not meta:
        return version
    if ".dirty" in meta:
        # git describe --dirty at a clean tag emits `v0.3.27-dirty`; strip it so
        # the promotion check below can fire on what is still a stable base.
        version = version.removesuffix("-dirty")
        if "-" not in version:
            v_parts = version.split(".")
            if len(v_parts) == 3 and all(p.isdigit() for p in v_parts):
                major, minor, patch = v_parts
                version = f"{major}.{minor}.{int(patch) + 1}-dev.0"
    return f"{version}+{meta}"


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
                    return _with_build_metadata(sanitize_version(version), aops_root)
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
            return _with_build_metadata(sanitize_version(desc), aops_root)
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
            return _with_build_metadata(stable_tags[0].lstrip("v"), aops_root)
        if tags:
            return _with_build_metadata(sanitize_version(tags[0].lstrip("v")), aops_root)
    except Exception:
        pass

    return "0.1.0"


# The shipped aops-core hook deps are declared in the TRACKED source file
# aops-core/pyproject.toml (epic-267fe017). The build reads that file and stamps
# the version (+ trims hooks for cowork); there is no longer an inline pyproject
# string literal here that could drift from the real file.
AOPS_CORE_PYPROJECT_PLACEHOLDER_VERSION = "0.0.0"

# Matches the `version = "..."` line under [project] (placeholder in source).
_PYPROJECT_VERSION_RE = re.compile(r'(?m)^(version\s*=\s*)"[^"]*"')
# Matches the hatch wheel `packages = [...]` line (single-line list as authored).
_PYPROJECT_PACKAGES_RE = re.compile(r"(?m)^packages\s*=\s*\[[^\]]*\]")


def generate_aops_core_pyproject(
    version: str, platform: str = "claude", aops_root: Path | None = None
) -> str:
    """Return aops-core/pyproject.toml content with the build version stamped in.

    Reads the tracked source manifest at ``aops-core/pyproject.toml`` (the single
    source of truth for shipped hook deps) and substitutes the placeholder
    version with the real build version.

    The cowork build ships NO hooks (the shared aops-core hook stack serves the
    Cowork surface when aops-core is installed from the dist marketplace — see
    task aops-04075740 / mem-fe29111a). With no ``hooks/`` package on disk,
    listing it under hatch's wheel packages would break ``uv sync --frozen`` at
    runtime, so for the cowork platform the ``hooks`` package is trimmed from the
    wheel packages list, leaving only ``lib``.
    """
    if aops_root is None:
        aops_root = SCRIPT_DIR.parent
    src_pyproject = aops_root / "aops-core" / "pyproject.toml"
    if not src_pyproject.exists():
        raise FileNotFoundError(
            f"Required source manifest {src_pyproject} not found — "
            "cannot build aops-core without it (epic-267fe017)"
        )
    content = src_pyproject.read_text()

    content, n_ver = _PYPROJECT_VERSION_RE.subn(rf'\g<1>"{version}"', content, count=1)
    if n_ver != 1:
        raise ValueError(
            f"Could not stamp version into {src_pyproject} (no [project] version line)"
        )

    if platform == "cowork":
        content, n_pkg = _PYPROJECT_PACKAGES_RE.subn('packages = ["lib"]', content, count=1)
        if n_pkg != 1:
            raise ValueError(
                f"Could not trim hooks package for cowork in {src_pyproject} "
                "(no wheel packages line)"
            )
    return content


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


def _generate_antigravity_hooks_json(src_path: Path, dst_path: Path) -> None:
    """Transform hooks.json for Antigravity CLI (agy).

    Antigravity supports only 4 hook events: PreToolUse, PostToolUse,
    PreInvocation, PostInvocation.  It needs ${extensionPath} instead of
    ${CLAUDE_PLUGIN_ROOT} for path references.

    Event mapping (Claude Code → agy):
      UserPromptSubmit → PreInvocation  (fires before each agent invocation)
      Stop             → PostInvocation (fires after each agent invocation)

    Events not in AGY_EVENT_MAP and not in VALID_AGY_EVENTS are dropped.
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

    # Events that agy natively supports (no name transformation needed)
    VALID_AGY_EVENTS = (
        "PreToolUse",
        "PostToolUse",
        "PreInvocation",
        "PostInvocation",
    )

    # Invocation/Stop events use a DIFFERENT registration shape than tool events.
    # Per https://antigravity.google/docs/hooks#supported-events, the
    # PreInvocation/PostInvocation (and Stop) handlers must be a FLAT handler list
    # directly under the event key:
    #     "PreInvocation": [{"type": "command", "command": "...", "timeout": N}]
    # The matcher/hooks[] wrapper is ONLY for PreToolUse/PostToolUse. When the
    # invocation events were wrapped in the tool-event shape, agy phantom-logged
    # "executing command" (json_hook_caller.go:144) but never spawned the process
    # — the PreInvocation context-injection hook silently never fired (the agy
    # PreInvocation no-op symptom). Emitting the flat list makes the hook fire.
    FLAT_LIST_AGY_EVENTS = ("PreInvocation", "PostInvocation", "Stop")

    # Claude Code events that must be renamed for agy compatibility
    AGY_EVENT_MAP = {
        "UserPromptSubmit": "PreInvocation",
        "Stop": "PostInvocation",
    }

    # Defence-in-depth timeout floors for agy (ms). The real cold-start fix is the
    # venv prebuild in `make install-agy`; this floor is a safety net so that if a
    # venv prebuild is ever skipped/failed, the first PreToolUse cold `uv run`
    # build does not blow the timeout and produce a spurious "Tool call denied by
    # jsonhook__..." (aops-7697a478). With a warm venv the hook returns in <100ms,
    # so a higher ceiling costs nothing in steady state.
    AGY_TIMEOUT_FLOOR_MS = {
        "PreToolUse": 15000,
    }

    def _transform_hook(hook: dict, output_event: str) -> dict:
        """Rewrite a single command hook for agy (path, client flag, event arg, timeout)."""
        new_hook = dict(hook)
        if "command" in new_hook:
            cmd = new_hook["command"]
            cmd = cmd.replace(
                "${CLAUDE_PLUGIN_ROOT}",
                "$HOME/.gemini/antigravity-cli/plugins/aops-core",
            )
            cmd = cmd.replace("--client claude", "--client agy")
            cmd = f"{cmd} {output_event}"
            new_hook["command"] = cmd
        # Raise the timeout to the agy floor (defence-in-depth for cold-start;
        # never lower an already-higher source value).
        floor = AGY_TIMEOUT_FLOOR_MS.get(output_event)
        if floor is not None and new_hook.get("timeout", 0) < floor:
            new_hook["timeout"] = floor
        return new_hook

    src_hooks = config["hooks"]
    agy_hooks: dict = {}

    for event, hook_list in src_hooks.items():
        if event.endswith("-disabled"):
            continue

        # Rename Claude-only events to their agy equivalents
        output_event = AGY_EVENT_MAP.get(event, event)

        if output_event not in VALID_AGY_EVENTS:
            continue

        if output_event in FLAT_LIST_AGY_EVENTS:
            # FLAT handler list directly under the event key — no matcher/hooks[]
            # wrapper. agy only spawns invocation/Stop hooks in this shape.
            flat_hooks = []
            for hook_entry in hook_list:
                # A source entry without a 'hooks' key simply contributes no handlers.
                for hook in (
                    hook_entry.get("hooks") or []
                ):  # allow-fallback: a source hook entry may carry no nested 'hooks' list
                    flat_hooks.append(_transform_hook(hook, output_event))
            if flat_hooks:
                agy_hooks[output_event] = flat_hooks
            continue

        # PreToolUse / PostToolUse: keep the matcher/hooks[] wrapper shape.
        transformed_hooks = []
        for hook_entry in hook_list:
            new_entry = {}
            for key, value in hook_entry.items():
                if key == "hooks":
                    new_entry[key] = [_transform_hook(hook, output_event) for hook in value]
                else:
                    new_entry[key] = value
            transformed_hooks.append(new_entry)

        if transformed_hooks:
            agy_hooks[output_event] = transformed_hooks

    with open(dst_path, "w") as f:
        json.dump({"hooks": agy_hooks}, f, indent=2)
        f.write("\n")
    print(f"  ✓ Generated Antigravity hooks.json with {len(agy_hooks)} events")


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
        # User interaction / planning / todos (Claude built-ins → agy native)
        # AskUserQuestion was the original gap that caused junior to fail load
        # validation; the others are listed here so future agents using them are
        # also translated correctly. NotebookEdit has no agy equivalent → drop.
        "AskUserQuestion": "ask_user",
        "ExitPlanMode": "enter_plan_mode",
        "TodoWrite": "write_todos",
        "NotebookEdit": None,
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
                tool_name = claude_mcp_to_gemini(t) if t.startswith("mcp__") else t
                mapped = GEMINI_TOOL_NAME_MAP.get(tool_name, tool_name)
                if mapped is not None:
                    filtered.append(mapped)
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
            tool_name = claude_mcp_to_gemini(t) if t.startswith("mcp__") else t
            mapped = GEMINI_TOOL_NAME_MAP.get(tool_name, tool_name)
            if mapped is not None and mapped not in seen:
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
        "claude": {},
    }

    platform_map = mappings.get(
        platform, {}
    )  # allow-fallback: default to no-op for unrecognized platforms
    for abstract, concrete in platform_map.items():
        text = text.replace(abstract, concrete)

    # 2. Dynamic replacement for Gemini/Claude compatibility (Task/Skill)
    if platform == "gemini":
        # Replace Claude plugin path variable with Gemini equivalent
        text = text.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")

        text = re.sub(
            r"mcp__[a-zA-Z0-9_-]+__[a-zA-Z0-9_-]*",
            lambda m: claude_mcp_to_gemini(m.group(0)),
            text,
        )

        # Task(subagent_type=...) -> activate_skill(name=...)
        text = text.replace("Task(subagent_type=", "activate_skill(name=")
        # Skill(skill=...) -> activate_skill(name=...)
        text = text.replace("Skill(skill=", "activate_skill(name=")
        # Update descriptive text references
        text = text.replace("Task() tool", "activate_skill() tool")
        text = text.replace("`Task(`", "`activate_skill(`")
        text = text.replace("`Skill(`", "`activate_skill(`")

    elif platform == "antigravity":
        # agy (Antigravity 2.0) is Claude-tool-compatible: agents ship with Claude
        # tool names (no frontmatter/body transformation). It uses Claude Code hook
        # event names (PreToolUse etc.) but its own plugin root path. ${extensionPath}
        # is not defined in agy; hooks hardcode this same path, so we match it here.
        text = text.replace(
            "${CLAUDE_PLUGIN_ROOT}", "$HOME/.gemini/antigravity-cli/plugins/aops-core"
        )

    return text


def build_aops_core(
    aops_root: Path,
    dist_root: Path,
    aca_data_path: str,
    platform: str = "gemini",
    version: str = "0.1.0",
):
    """Build the aops-core extension for a specific platform.

    Supported platforms: "claude", "gemini", "antigravity", "cowork".
    The "cowork" platform is a sibling of "claude" — same plugin layout
    (`.claude-plugin/plugin.json` + `.mcp.json`) but with cowork-only skill
    content kept (markers stripped), the cowork-sync skill included, and a
    distinct plugin manifest naming the artifact `aops-cowork`. Unlike "claude",
    the cowork build ships NO hooks: aops-core (installed into Cowork from the
    dist marketplace) supplies the one shared hook stack for both surfaces, so
    bundling hooks here would double-fire every lifecycle hook (task-04075740).
    """
    print(f"Building aops-core for {platform} (v{version})...")
    plugin_name = "aops-core"
    src_dir = aops_root / plugin_name

    # Cowork is built like Claude (same plugin contract, MCP layout, tool name
    # transforms). transform_platform is what we hand to agent/tool transformers
    # so the agent tools and tool-name translations match the Claude rules.
    transform_platform = "claude" if platform == "cowork" else platform

    # Platform-specific dist dir. New naming: use 'aops-{platform}' as the dist folder
    # so consumers see 'aops-gemini' / 'aops-claude' / 'aops-cowork' instead of
    # 'aops-core-gemini'.
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
        "pyproject.toml",  # Generated from template in 1b (version + dep list)
        "uv.lock",  # Regenerated in 1b to stay in sync with the new pyproject
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
                content = transform_agent_for_platform(content, transform_platform, agent_file.name)
                # Translate tool calls in body text
                content = translate_tool_calls(content, transform_platform)
                (dst / agent_file.name).write_text(content)
            print(f"  ✓ Translated and copied agents -> {dst}")
        else:
            safe_copy(src_item, content_dir / src_item.name)

    # 1a-axioms. Co-ship the framework axioms INTO the plugin payload so the
    # @-imports in rbg.md / marsha.md resolve at runtime in a deployed plugin
    # (where ${CLAUDE_PLUGIN_ROOT}/../ is outside the payload). The single SSoT
    # at .agents/rules/AXIOMS.md remains the only hand-maintained copy.
    axioms_src_dir = aops_root / ".agents" / "rules"
    axioms_dst_dir = content_dir / ".agents" / "rules"
    AXIOM_FILES = ("AXIOMS.md", "AXIOMS-REVIEW.md")
    for axiom_file in AXIOM_FILES:
        src = axioms_src_dir / axiom_file
        if not src.exists():
            raise FileNotFoundError(
                f"Required axiom file {src} not found — cannot build plugin without it"
            )
        dst = axioms_dst_dir / axiom_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        safe_copy(src, dst)
    print(f"  ✓ Co-shipped {len(AXIOM_FILES)} axiom file(s) -> {axioms_dst_dir}")

    # 1a-pre. Drop the cowork-sync skill on every platform except cowork.
    # The skill describes the PKB ↔ native task-list mirror that only Cowork's
    # harness uses; the same source file would be misleading on claude/gemini/agy.
    if platform != "cowork":
        cowork_sync_dir = content_dir / "skills" / "cowork-sync"
        if cowork_sync_dir.exists():
            shutil.rmtree(cowork_sync_dir)
            print(f"  - Dropped cowork-sync skill (not for {platform})")

    # 1a. Post-copy: translate tool names in all .md files for Gemini/Antigravity.
    # Agents get transform_agent_for_platform above (frontmatter + body);
    # this pass catches skills, commands, lib, and top-level .md files
    # that were copied verbatim by safe_copy. Antigravity needs the
    # ${CLAUDE_PLUGIN_ROOT} replacement but no tool-name changes.
    if platform in ("gemini", "antigravity"):
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

    # 1a-cowork. Process cowork-only markers across every .md file copied above.
    # For platform == "cowork", the markers are stripped and the wrapped content
    # is kept; for every other platform, both the markers and the content go away.
    # Agent files were copied via a separate text path, so we cover them here too.
    cowork_processed = 0
    for md_file in content_dir.rglob("*.md"):
        original = md_file.read_text()
        if _COWORK_OPEN not in original:
            continue
        processed = _process_cowork_markers(original, platform)
        if processed != original:
            md_file.write_text(processed)
            cowork_processed += 1
    if cowork_processed:
        verb = "kept" if platform == "cowork" else "stripped"
        print(f"  ✓ {verb.capitalize()} cowork-only blocks in {cowork_processed} .md file(s)")

    # 1b. Stamp the tracked aops-core/pyproject.toml (the in-tree SSoT for shipped
    # hook deps, epic-267fe017) with the build version and write it into the dist
    # payload, then lock against that stamped copy so pyproject.toml and uv.lock
    # ship in lockstep. aops-core/uv.lock is NOT tracked — it is generated here
    # per-platform (the cowork variant trims the hooks package). `uv sync --frozen`
    # at runtime then installs exactly what the manifest declared, no drift.
    pyproject_content = generate_aops_core_pyproject(version, platform, aops_root)
    pyproject_path = content_dir / "pyproject.toml"
    pyproject_path.write_text(pyproject_content)
    print(f"  ✓ Stamped pyproject.toml (v{version}) from aops-core/pyproject.toml")

    subprocess.run(["uv", "lock"], cwd=content_dir, check=True)
    print("  ✓ Regenerated uv.lock from pyproject.toml")

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
    #
    # The cowork build ships NO hooks. Installing aops-core into Cowork from the
    # `nicsuzor/aops` main `dist` marketplace makes Cowork fire the standard
    # aops-core hook stack (empirically confirmed by Nic — mem-fe29111a /
    # task-04075740). Shipping hooks here too would register the Stop /
    # PreToolUse / etc. router a SECOND time and fire every lifecycle hook
    # twice. aops-cowork is therefore an additive, hooks-free layer: one shared
    # hook stack (aops-core) serves both Claude Code and Cowork.
    # Bind hooks_src / hooks_dst unconditionally so the gemini/antigravity
    # hooks.json generation below (which only runs for non-cowork platforms)
    # has statically-known Paths, not possibly-Unbound names.
    hooks_src = src_dir / "hooks"
    hooks_dst = dist_dir / "hooks"
    if platform != "cowork":
        hooks_dst.mkdir(parents=True)
        if hooks_src.exists():
            for item in hooks_src.iterdir():
                if item.name in BUILD_DETRITUS_NAMES:
                    # safe_copy's ignore filters children, not a top-level cache dir
                    # passed as src — skip detritus dirs here so they never enter the build.
                    continue
                if item.name == "hooks.json" and platform in ("gemini", "antigravity"):
                    # Handle hooks.json separately for Gemini/Antigravity
                    continue
                if item.name == "gemini":
                    # Don't copy gemini/ subdirectory
                    continue
                # Hooks also go into content_dir for execution, but Gemini discovery
                # might need them in dist_dir/hooks/hooks.json
                safe_copy(item, content_dir / "hooks" / item.name)
    else:
        print("  - Skipped hooks for cowork (aops-core supplies the shared hook stack)")

    # Generate platform-compatible hooks.json
    if platform == "gemini":
        hooks_json_src = hooks_src / "hooks.json"
        if hooks_json_src.exists():
            _generate_gemini_hooks_json(hooks_json_src, hooks_dst / "hooks.json")
    elif platform == "antigravity":
        # Antigravity uses Claude Code event names (PreToolUse, PostToolUse, etc.)
        # but needs ${extensionPath} instead of ${CLAUDE_PLUGIN_ROOT}
        hooks_json_src = hooks_src / "hooks.json"
        if hooks_json_src.exists():
            _generate_antigravity_hooks_json(hooks_json_src, dist_dir / "hooks.json")

    # 2b. Copy Gemini context file (referenced by gemini-extension.json as
    # contextFileName). It lives at the repo root, not inside aops-core/.
    # GEMINI.md uses `@path` imports; resolve each referenced file once and
    # ship it alongside so Gemini's ImportProcessor can satisfy the imports.
    if platform == "gemini":
        src_gemini_md = aops_root / "GEMINI.md"
        if not src_gemini_md.exists():
            print(f"Error: {src_gemini_md} not found.", file=sys.stderr)
            sys.exit(1)

        import re as _re

        # Read and clean GEMINI.md: stop packaging project-local CORE.md
        # Use regex to strip @.agents/CORE.md from the distributed version
        original_content = src_gemini_md.read_text()
        cleaned_content = _re.sub(
            r"^@\.agents/CORE\.md\s*$", "", original_content, flags=_re.MULTILINE
        )
        (dist_dir / "GEMINI.md").write_text(cleaned_content)
        print(f"  ✓ Copied and cleaned GEMINI.md -> {dist_dir / 'GEMINI.md'}")

        imported = 0
        for m in _re.finditer(r"^@([^\s]+)", original_content, flags=_re.MULTILINE):
            rel = m.group(1)
            if rel == ".agents/CORE.md":
                # Skip project-local context in plugin distribution
                continue
            if Path(rel).is_absolute() or ".." in rel:
                print(
                    f"Warning: Skipping unsafe import path in GEMINI.md: {rel}",
                    file=sys.stderr,
                )
                continue
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
        src_extension_json = aops_root / "templates" / "aops-core.gemini-extension.json"
        dist_extension_json = dist_dir / "gemini-extension.json"
        root_extension_json = aops_root / "gemini-extension.json"

        if src_extension_json.exists():
            print(f"Generating extension manifest from {src_extension_json.name}...")
            try:
                manifest = json.loads(src_extension_json.read_text())
                manifest["version"] = version

                with open(dist_extension_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")

                # Also save to repository root
                with open(root_extension_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print("  ✓ Generated gemini-extension.json at root and dist")
            except Exception as e:
                print(f"Error processing extension manifest: {e}", file=sys.stderr)
                raise
        else:
            print(f"Error: {src_extension_json} not found.", file=sys.stderr)
            sys.exit(1)

    if platform in ("claude", "cowork"):
        # Both use the same plugin contract (.claude-plugin/plugin.json); cowork
        # ships from a distinct template so its `name`, `description`, and
        # keywords are tuned for the Cowork variant.
        template_name = (
            "aops-core.cowork-plugin.json" if platform == "cowork" else "aops-core.plugin.json"
        )
        src_plugin_json = aops_root / "templates" / template_name
        dist_plugin_dir = dist_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                dist_plugin_dir.mkdir(parents=True, exist_ok=True)
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                # Hygiene: strip marketplace-only and deprecated fields
                # Leaked 'source' and 'category' cause issues in local cache
                manifest.pop("source", None)
                manifest.pop("category", None)
                # 'userConfig' is no longer used (env resolution moved to run-mcp.sh)
                manifest.pop("userConfig", None)

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Updated and hygienically copied plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    if platform == "antigravity":
        src_plugin_json = aops_root / "templates" / "aops-core.antigravity-plugin.json"
        dist_plugin_json = dist_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Generated plugin.json -> {dist_plugin_json}")
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

            # Write .mcp.json for Claude-shaped builds (claude + cowork).
            # Cowork uses the same plugin contract: a single `.mcp.json` at the
            # archive root, pointed to by `plugin.json.mcpServers`.
            if platform in ("claude", "cowork"):
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
                    for server, config in gemini_mcps.items():
                        if server in current_mcps:
                            existing = current_mcps[server]
                            existing.update({k: v for k, v in config.items() if k != "env"})
                            existing_env = existing.get("env") or {}
                            existing_env.update(config.get("env") or {})
                            if existing_env:
                                existing["env"] = existing_env
                        else:
                            current_mcps[server] = config
                    manifest["mcpServers"] = current_mcps

                    # MCP server arguments from mcp.json.template use ${extensionPath}
                    # which is correct since plugin content is at the root

                    with open(dist_extension_json, "w") as f:
                        json.dump(manifest, f, indent=2)
                        f.write("\n")
                    print(f"✓ Updated {dist_extension_json} with MCP config")

            # Prepare for Antigravity 2.0 Plugin
            if platform == "antigravity":
                servers_config = mcp_config.get("mcpServers", mcp_config)
                # Replace variables if they came from a Claude-style template
                ag_servers_json = json.dumps(servers_config)
                ag_servers_json = ag_servers_json.replace(
                    "${CLAUDE_PLUGIN_ROOT}", "${extensionPath}"
                )

                ag_servers_config = json.loads(ag_servers_json)
                ag_mcp_config = {"mcpServers": ag_servers_config}

                dist_mcp_path = dist_dir / "mcp_config.json"
                with open(dist_mcp_path, "w") as f:
                    json.dump(ag_mcp_config, f, indent=2)
                    f.write("\n")
                print(f"✓ Generated mcp_config.json -> {dist_mcp_path}")

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
        # Strip cowork-only blocks from generated .toml files. The convert
        # script reads from `aops-core/commands/*.md` source — bypassing the
        # staged copies that were already stripped by the cowork-marker pass —
        # so without this post-step the markers leak into the Gemini TOML.
        toml_stripped = 0
        for toml_file in commands_dist.glob("*.toml"):
            original = toml_file.read_text()
            if _COWORK_OPEN not in original:
                continue
            processed = _process_cowork_markers(original, platform)
            if processed != original:
                toml_file.write_text(processed)
                toml_stripped += 1
        if toml_stripped:
            print(f"  ✓ Stripped cowork-only blocks in {toml_stripped} .toml command(s)")
        # Remove .md command files for Gemini (uses TOML format)
        for md_file in commands_dist.glob("*.md"):
            md_file.unlink()
            print(f"  - Removed {md_file.name} (Gemini uses TOML)")

    # 6. Anti-drift regression guard. Catches the class of defect that left
    # rbg + marsha grounding verdicts on a stale `old_axioms.md` decoy because
    # the canonical axioms were never shipped into the plugin payload (#aops-75543e66).
    # Two checks: (a) every plugin-relative @-import in a shipped agent must
    # resolve inside the payload; (b) no axiom-shaped decoy may ship anywhere
    # outside .agents/rules/.
    _assert_plugin_imports_resolve(content_dir, platform)
    _assert_no_axiom_decoys(content_dir)

    print(f"✓ Built {plugin_name} ({platform})")
    return gemini_mcps


_PLUGIN_ROOT_VAR_RE = re.compile(r"@\$\{(?:CLAUDE_PLUGIN_ROOT|extensionPath)\}/([^\s`'\"<>]+)")
# Decoy patterns: an axiom-shaped name carrying a staleness/version marker —
# `old_axioms.md`, `axioms_old.md`, `axioms_v1.md`, `legacy_axioms.md`,
# `archived-axioms.md`, etc. Legitimate per-skill axiom files (e.g.
# `skills/research/axioms.md` for academic-axioms corollaries) are NOT decoys
# because they have no staleness marker and live inside an active skill folder.
_AXIOM_NAME_RE = re.compile(r"axioms?", re.IGNORECASE)
_DECOY_MARKER_RE = re.compile(
    r"(?:^|[_\-.])(?:old|legacy|archive[d]?|deprecated|backup|copy|v\d+|orig|original|prev|previous)(?:$|[_\-.])",
    re.IGNORECASE,
)


def _assert_plugin_imports_resolve(content_dir: Path, platform: str) -> None:
    """Fail the build if any shipped agent @-imports a path absent from the payload.

    Walks every agent .md under content_dir/agents/, extracts each
    @${CLAUDE_PLUGIN_ROOT}/<rel> or @${extensionPath}/<rel> reference, and
    asserts the relative path exists at content_dir/<rel>. Catches the
    rbg/marsha dangling axiom-import regression directly: the plugin payload
    IS the resolution scope at runtime, so an unresolvable import means a
    review agent will silently fall back to whatever a `find` lands on.
    """
    agents_dir = content_dir / "agents"
    if not agents_dir.exists():
        return
    failures: list[str] = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        text = agent_file.read_text(encoding="utf-8")
        for match in _PLUGIN_ROOT_VAR_RE.finditer(text):
            rel = match.group(1).rstrip(".,;:)")
            if rel.startswith("../") or "/../" in rel:
                failures.append(
                    f"{agent_file.relative_to(content_dir)}: import @${{...}}/{rel} "
                    "escapes the plugin payload (parent-of-root path)"
                )
                continue
            target = content_dir / rel
            if not target.exists():
                failures.append(
                    f"{agent_file.relative_to(content_dir)}: import @${{...}}/{rel} "
                    f"does not resolve in payload (expected {target})"
                )
    if failures:
        raise RuntimeError(
            f"Plugin import resolution guard failed for {platform}:\n  - " + "\n  - ".join(failures)
        )


def _assert_no_axiom_decoys(content_dir: Path) -> None:
    """Fail the build if any axiom-shaped file ships outside .agents/rules/.

    The canonical axioms live at .agents/rules/AXIOMS.md and
    .agents/rules/AXIOMS-REVIEW.md (co-shipped at build time). Any other
    axiom-shaped file in the payload is a decoy that a fallback `find` could
    surface to a review agent (this happened: aops-core/old_axioms.md shipped
    for months and rbg grounded verdicts on it after the canonical import
    dangled, #aops-75543e66).
    """
    allowed_rel = {
        Path(".agents/rules/AXIOMS.md"),
        Path(".agents/rules/AXIOMS-REVIEW.md"),
    }
    decoys: list[str] = []
    for md_file in content_dir.rglob("*.md"):
        rel = md_file.relative_to(content_dir)
        if rel in allowed_rel:
            continue
        stem = md_file.stem
        if not _AXIOM_NAME_RE.search(stem):
            continue
        # axiom-shaped name. Two flagging conditions:
        #   1. Name carries a staleness/version marker (the actual decoy class).
        #   2. Name lives at the plugin root (any axiom file at top level is
        #      a tripwire for `find` fallbacks regardless of marker).
        if _DECOY_MARKER_RE.search(stem) or rel.parent == Path("."):
            decoys.append(str(rel))
    if decoys:
        raise RuntimeError(
            "Axiom decoy guard failed — these axiom-shaped files would ship "
            "outside .agents/rules/ and could be mis-loaded by a review agent:\n  - "
            + "\n  - ".join(decoys)
        )


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
        src_extension_json = aops_root / "templates" / f"{plugin_name}.gemini-extension.json"
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
        src_plugin_json = aops_root / "templates" / f"{plugin_name}.plugin.json"
        dist_plugin_dir = dist_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                dist_plugin_dir.mkdir(parents=True, exist_ok=True)
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                # Hygiene: strip marketplace-only and deprecated fields
                # Leaked 'source' and 'category' cause issues in local cache
                manifest.pop("source", None)
                manifest.pop("category", None)
                # 'userConfig' is no longer used (env resolution moved to run-mcp.sh)
                manifest.pop("userConfig", None)

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Updated and hygienically copied plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    # Antigravity: generate plugin.json with version injection
    if platform == "antigravity":
        src_plugin_json = aops_root / "templates" / f"{plugin_name}.antigravity-plugin.json"
        dist_plugin_json = dist_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Generated plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    print(f"✓ Built {plugin_name} ({platform})")


def build_aops_extras(
    aops_root: Path,
    dist_root: Path,
    platform: str = "gemini",
    version: str = "0.1.0",
):
    """Build the aops-extras extension for a specific platform.

    aops-extras is a lightweight package of replaceable technology-specific skills
    (dbt, Streamlit, Python plotting/stats). It has no hooks, agents, commands, or
    MCP servers — just skills and manifests. Mirrors build_aops_tools exactly.
    """
    print(f"Building aops-extras for {platform} (v{version})...")
    plugin_name = "aops-extras"
    src_dir = aops_root / plugin_name

    if not src_dir.exists():
        print(f"  ⚠️  {src_dir} not found, skipping aops-extras build")
        return

    dist_dir = dist_root / f"aops-extras-{platform}"
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
        src_extension_json = aops_root / "templates" / f"{plugin_name}.gemini-extension.json"
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
        src_plugin_json = aops_root / "templates" / f"{plugin_name}.plugin.json"
        dist_plugin_dir = dist_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                dist_plugin_dir.mkdir(parents=True, exist_ok=True)
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                # Hygiene: strip marketplace-only and deprecated fields
                # Leaked 'source' and 'category' cause issues in local cache
                manifest.pop("source", None)
                manifest.pop("category", None)
                # 'userConfig' is no longer used (env resolution moved to run-mcp.sh)
                manifest.pop("userConfig", None)

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Updated and hygienically copied plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    # Antigravity: generate plugin.json with version injection
    if platform == "antigravity":
        src_plugin_json = aops_root / "templates" / f"{plugin_name}.antigravity-plugin.json"
        dist_plugin_json = dist_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Generated plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    print(f"✓ Built {plugin_name} ({platform})")


def build_aops_ts(
    aops_root: Path,
    dist_root: Path,
    platform: str = "claude",
    version: str = "0.1.0",
):
    """Build the aops-ts extension for a specific platform.

    aops-ts is a tiny, opt-in package: a single SessionStart hook that brings
    Tailscale up in remote/cloud sessions so tailnet services (e.g. the PKB MCP
    at *.ts.net) resolve. It is intentionally standalone — a self-contained bash
    hook with no router/Python/uv dependency — so it can be enabled on its own,
    independent of aops-core. Only the Claude platform is built; the tailnet
    bring-up targets Claude Code on the web.
    """
    print(f"Building aops-ts for {platform} (v{version})...")
    plugin_name = "aops-ts"
    src_dir = aops_root / plugin_name

    if not src_dir.exists():
        print(f"  ⚠️  {src_dir} not found, skipping aops-ts build")
        return

    dist_dir = dist_root / f"aops-ts-{platform}"
    content_dir = dist_dir

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # Copy the hook payload (and docs) verbatim. Hooks are auto-discovered by
    # Claude Code from hooks/hooks.json — no manifest declaration needed.
    items_to_copy = ["hooks", "README.md"]
    for item in items_to_copy:
        src = src_dir / item
        if src.exists():
            safe_copy(src, content_dir / item)

    # Claude: copy plugin.json with version injection + marketplace-field hygiene.
    if platform == "claude":
        src_plugin_json = aops_root / "templates" / f"{plugin_name}.plugin.json"
        dist_plugin_dir = dist_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if src_plugin_json.exists():
            try:
                dist_plugin_dir.mkdir(parents=True, exist_ok=True)
                manifest = json.loads(src_plugin_json.read_text())
                manifest["version"] = version

                # Hygiene: strip marketplace-only and deprecated fields that
                # otherwise trip CC's "Unrecognized keys" install validation.
                manifest.pop("source", None)
                manifest.pop("category", None)
                manifest.pop("userConfig", None)

                with open(dist_plugin_json, "w") as f:
                    json.dump(manifest, f, indent=2)
                    f.write("\n")
                print(f"  ✓ Updated and hygienically copied plugin.json -> {dist_plugin_json}")
            except Exception as e:
                print(f"Error processing plugin.json: {e}", file=sys.stderr)
        else:
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)

    print(f"✓ Built {plugin_name} ({platform})")


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
        "--tag",
        action="store_true",
        help="Create git tags for the release",
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
    build_aops_core(aops_root, dist_root, aca_data_path, "gemini", version)

    # Build components (Claude)
    build_aops_core(aops_root, dist_root, aca_data_path, "claude", version)

    # Build components (Cowork) — Claude-shaped plugin layout, manifest pinned
    # to `aops-cowork`, cowork-only blocks kept, cowork-sync skill included.
    # Ships NO hooks: aops-core (installed into Cowork from the dist marketplace)
    # provides the shared hook stack; bundling hooks here would double-fire them.
    build_aops_core(aops_root, dist_root, aca_data_path, "cowork", version)

    # Build aops-tools (domain skills package)
    build_aops_tools(aops_root, dist_root, "gemini", version)
    build_aops_tools(aops_root, dist_root, "claude", version)

    # Build aops-extras (replaceable technology-specific skills package)
    build_aops_extras(aops_root, dist_root, "gemini", version)
    build_aops_extras(aops_root, dist_root, "claude", version)

    # Build aops-ts (opt-in Tailscale bring-up hook — Claude/web only)
    build_aops_ts(aops_root, dist_root, "claude", version)

    # Build components (Antigravity)
    build_aops_core(aops_root, dist_root, aca_data_path, "antigravity", version)
    build_aops_tools(aops_root, dist_root, "antigravity", version)
    build_aops_extras(aops_root, dist_root, "antigravity", version)

    # Generate the single root marketplace.json (sources ./dist/aops-*)
    generate_marketplace(aops_root, dist_root, version)

    # Emit the LOCAL-dev cowork plugin (dist/aops-coworklocal, name
    # aops-coworklocal) + its isolated academicOps-cowork marketplace. The
    # PUBLISHED plugin (dist/aops-cowork, name aops-cowork) stays a clean plugin
    # for the github dist marketplaces; the local copy takes a distinct name so a
    # developer's `make install-cowork` never clobbers an installed aops-cowork.
    build_coworklocal_plugin(aops_root, dist_root, version)

    # PKB ships as a remote MCP server (run-mcp.sh resolves PKB_MCP_URL); no
    # per-platform binary is bundled, so packaging is platform-independent.
    package_artifacts(aops_root, dist_root, version)

    if args.tag or os.environ.get("GITHUB_ACTIONS") == "true":
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
    axioms_path = aops_root / ".agents" / "rules" / "AXIOMS.md"
    axioms_review_path = aops_root / ".agents" / "rules" / "AXIOMS-REVIEW.md"
    gha_out = dist_root / "gha-agents"
    gha_out.mkdir(parents=True, exist_ok=True)

    if not axioms_path.exists():
        print(f"  ✗ {axioms_path} not found — skipping GHA agent generation")
        return

    _, axioms_body = _parse_agent_frontmatter(axioms_path.read_text())
    axioms_body = _strip_agent_body_h1(axioms_body).strip()

    if not axioms_review_path.exists():
        raise FileNotFoundError(
            f"{axioms_review_path} not found — required for review agent prompts"
        )
    _, axioms_review_body = _parse_agent_frontmatter(axioms_review_path.read_text())
    axioms_review_body = _strip_agent_body_h1(axioms_review_body).strip()

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

        shared_err_handling_path = aops_root / ".github" / "agents" / "shared-error-handling.md"
        if not shared_err_handling_path.exists():
            raise FileNotFoundError(
                f"Required file not found: {shared_err_handling_path}. "
                "Cannot build GHA agents without Anti-Silent-Failure rule."
            )
        shared_err_handling_body = shared_err_handling_path.read_text().strip()

        trailer_key, trailer_value = _GHA_TRAILER_MAP.get(
            agent_name, ("Review-By", f"aops-{agent_name}")
        )

        sections = [
            f"# {description}",
            "",
            *([shared_err_handling_body, ""] if shared_err_handling_body else []),
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
            "<!-- Source: .agents/rules/AXIOMS.md — regenerate via `scripts/build.py` if axioms change -->",
            "",
            "The following principles are always active, regardless of domain context.",
            "",
            axioms_body,
            "",
        ]

        sections.extend(
            [
                "---",
                "",
                "## Review Questions",
                "",
                "<!-- Source: .agents/rules/AXIOMS-REVIEW.md — regenerate via `scripts/build.py` if axioms change -->",
                "",
                axioms_review_body,
                "",
            ]
        )

        out_path = gha_out / f"{agent_name}.agent.md"
        out_path.write_text("\n".join(sections))
        print(f"  ✓ {out_path.relative_to(aops_root)}")


# --- Reusable GHA Workflow Generation ---

_DIST_REPO = "nicsuzor/academicOps"

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
#   uses: __DIST_REPO__/.github/workflows/agent-__AGENT_NAME__.yml@dist

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
          ref: dist
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
    """Generate reusable GHA workflows for the published distribution.

    For each review agent (enforcer, qa), generates a workflow YAML
    that can be called from other repos:
        uses: nicsuzor/academicOps/.github/workflows/agent-enforcer.yml@dist

    Each workflow checks out nicsuzor/academicOps for the generated agent
    prompt (from `gha-agents/` at the repo root), so no private repo access
    is needed.
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
    """Generate the single Claude marketplace.json at the repo root.

    Reads templates/marketplace.json — whose plugin sources are root-relative
    ./dist/aops-* — injects the build version, and writes one
    .claude-plugin/marketplace.json at the repo root. ONE file, ONE convention:
    plugins live under dist/ in every consumer, so ./dist/aops-claude resolves
    correctly whether the marketplace root is the local repo (`marketplace add
    <repo-root>`, build output in repo/dist/) or the published `dist` branch (the
    publish step copies this file to the dist-branch root → dist:dist/aops-claude).

    aops-cowork is not installable via marketplace on personal Anthropic accounts
    (no marketplace mechanism there); it ships as `aops-cowork-v{version}.zip` for
    manual upload. The entry is retained so its version stays in lockstep.
    """
    template_path = aops_root / "templates" / "marketplace.json"
    if not template_path.exists():
        raise FileNotFoundError(f"templates/marketplace.json not found at {template_path}")

    with open(template_path) as f:
        data = json.load(f)

    # Inject the build version into every plugin entry (template uses __VERSION__).
    for plugin in data.get("plugins", []):
        plugin["version"] = version

    marketplace_dir = aops_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    marketplace = marketplace_dir / "marketplace.json"
    with open(marketplace, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"  ✓ Generated {marketplace} (sources ./dist/aops-*)")


def build_coworklocal_plugin(aops_root: Path, dist_root: Path, version: str):
    """Emit the LOCAL-dev cowork plugin (dist/aops-coworklocal) + its marketplace.

    One cowork build, two artifacts that differ ONLY in name:
      • dist/aops-cowork — the PUBLISHED plugin (name `aops-cowork`), resolved by
        the github dist marketplaces via `./dist/aops-cowork`. An ordinary
        published plugin: it carries NO marketplace.json of its own.
      • dist/aops-coworklocal — a rename-only COPY (name `aops-coworklocal`) for
        local development. `make package-cowork` zips it for manual upload and
        `make install-cowork` adds it as a local-directory marketplace. The
        distinct name keeps a developer's local build in its own plugin/skill
        namespace so it never clobbers an installed `aops-cowork`.

    The ISOLATED `academicOps-cowork` marketplace (name from
    templates/marketplace-cowork.json, plugin source "./") is written INTO
    dist/aops-coworklocal so `claude plugin marketplace add dist/aops-coworklocal`
    resolves the co-located plugin.json — a local-directory marketplace that
    survives Cowork restarts (github-source marketplaces get nuked; see the
    install-cowork Makefile note).

    Must run AFTER build_aops_core(platform="cowork", ...), which builds
    dist/aops-cowork. The marketplace.json is excluded from the manual-upload zip
    so that artifact stays a pure plugin payload.
    """
    published_dir = dist_root / "aops-cowork"
    published_plugin_json = published_dir / ".claude-plugin" / "plugin.json"
    if not published_plugin_json.exists():
        raise FileNotFoundError(
            f"dist/aops-cowork/.claude-plugin/plugin.json missing at {published_plugin_json} "
            "— run build_aops_core(platform='cowork') before build_coworklocal_plugin()"
        )

    template_path = aops_root / "templates" / "marketplace-cowork.json"
    if not template_path.exists():
        raise FileNotFoundError(f"templates/marketplace-cowork.json not found at {template_path}")

    # Rename-only copy of the published plugin → the local-dev variant.
    local_dir = dist_root / "aops-coworklocal"
    if local_dir.exists():
        shutil.rmtree(local_dir)
    shutil.copytree(published_dir, local_dir)

    # The local variant differs from the published aops-cowork plugin only in
    # name (its own plugin/skill namespace) and the install-guidance description.
    local_plugin_json = local_dir / ".claude-plugin" / "plugin.json"
    with open(local_plugin_json) as f:
        manifest = json.load(f)
    manifest["name"] = "aops-coworklocal"
    manifest["description"] = (
        "academicOps for Cowork Local — only install this one if Cowork won't "
        "install the normal academicOps packages."
    )
    with open(local_plugin_json, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Isolated academicOps-cowork marketplace (lists aops-coworklocal, source ./).
    with open(template_path) as f:
        data = json.load(f)

    # Inject the build version into every plugin entry (template uses __VERSION__),
    # keeping the cowork plugin in version lockstep with the rest of the build.
    # A missing/empty plugins list is a broken template, so fail fast rather than
    # silently emit an empty marketplace.
    plugins = data.get("plugins")
    if not plugins:
        raise ValueError(f"{template_path} has no 'plugins' — cannot generate cowork marketplace")
    for plugin in plugins:
        plugin["version"] = version

    marketplace = local_dir / ".claude-plugin" / "marketplace.json"
    with open(marketplace, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(
        f"  ✓ Built dist/aops-coworklocal (name aops-coworklocal) + isolated "
        f"marketplace {data.get('name')!r}"
    )


def package_artifacts(aops_root: Path, dist_root: Path, version: str):
    """Package the built components into platform-independent archives for release.

    PKB ships as a remote MCP server (no bundled per-platform binary), so a
    single set of generic archives serves every platform:
    - aops-core.tar.gz / aops-tools.tar.gz (Gemini CLI install names)
    - aops-claude-v{version}.tar.gz / aops-tools-claude-v{version}.tar.gz

    Plus 'latest' symlinks for the Claude archives.
    """
    print("\nPackaging artifacts for release...")

    # Filter for packaging to exclude noise
    def _source_filter(tarinfo):
        if any(part in BUILD_DETRITUS_NAMES for part in Path(tarinfo.name).parts):
            return None
        return tarinfo

    # Generic archives (no platform-specific binary)
    # Strip SemVer build metadata (+gSHA[.dirty]) from filenames only; it lives
    # inside plugin.json. Filenames stay clean for tooling that mangles `+`.
    fs_version = version.split("+", 1)[0]

    # 1. aops-core.tar.gz (generic fallback for Gemini CLI)
    # Named to match extension name in gemini-extension.json
    # gemini-extension.json must be at archive root (arcname=".")
    gemini_archive = dist_root / "aops-core.tar.gz"
    with tarfile.open(gemini_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-gemini", arcname=".", filter=_source_filter)
    print(f"  ✓ Packaged {gemini_archive.name}")

    # 1a. aops-tools.tar.gz (Gemini)
    tools_gemini_archive = dist_root / "aops-tools.tar.gz"
    if (dist_root / "aops-tools-gemini").exists():
        with tarfile.open(tools_gemini_archive, "w:gz") as tar:
            tar.add(dist_root / "aops-tools-gemini", arcname=".", filter=_source_filter)
        print(f"  ✓ Packaged {tools_gemini_archive.name}")

    # 2. aops-claude-v{version}.tar.gz
    claude_archive = dist_root / f"aops-claude-v{fs_version}.tar.gz"
    with tarfile.open(claude_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-claude", arcname="aops-claude", filter=_source_filter)
    print(f"  ✓ Packaged {claude_archive.name}")
    safe_symlink(claude_archive, dist_root / "aops-claude-latest.tar.gz")

    # 2a. aops-tools-claude-v{version}.tar.gz
    if (dist_root / "aops-tools-claude").exists():
        tools_claude_archive = dist_root / f"aops-tools-claude-v{fs_version}.tar.gz"
        with tarfile.open(tools_claude_archive, "w:gz") as tar:
            tar.add(
                dist_root / "aops-tools-claude", arcname="aops-tools-claude", filter=_source_filter
            )
        print(f"  ✓ Packaged {tools_claude_archive.name}")
        safe_symlink(tools_claude_archive, dist_root / "aops-tools-claude-latest.tar.gz")

    # 3. aops-coworklocal-v{version}.zip — manual upload artifact for Cowork.
    # Cowork on personal Anthropic accounts has no marketplace; users upload
    # plugins via Customize → Add plugins → Upload a file. The validator
    # requires `.claude-plugin/plugin.json` at the archive root, so zip from
    # *inside* the plugin directory rather than from its parent.
    #
    # The manual-upload artifact is the LOCAL-dev variant (`aops-coworklocal`,
    # built by build_coworklocal_plugin) so a developer uploading it gets a
    # plugin in its own namespace that never clobbers a published `aops-cowork`.
    # Legacy filenames (aops-cowork-v*.zip / aops-core-v{version}.zip) are kept
    # as symlinks so existing download URLs continue to resolve.
    coworklocal_dir = dist_root / "aops-coworklocal"
    if coworklocal_dir.exists():
        cowork_zip = dist_root / f"aops-coworklocal-v{fs_version}.zip"
        with zipfile.ZipFile(cowork_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(coworklocal_dir.rglob("*")):
                rel = path.relative_to(coworklocal_dir)
                if any(part in BUILD_DETRITUS_NAMES for part in rel.parts):
                    continue
                # The isolated academicOps-cowork marketplace manifest is for the
                # local `make install-cowork` path only; the manual-upload zip must
                # stay a pure plugin payload (.claude-plugin/plugin.json at root).
                if rel.parts == (".claude-plugin", "marketplace.json"):
                    continue
                zf.write(path, arcname=str(rel))
        print(f"  ✓ Packaged {cowork_zip.name} (Cowork manual upload)")
        safe_symlink(cowork_zip, dist_root / "aops-coworklocal-latest.zip")
        # Backward-compat aliases for the historical zip names + 'latest'
        # symlinks (pre-split marketing surface and the aops-cowork-v* name).
        safe_symlink(cowork_zip, dist_root / "aops-cowork-latest.zip")
        legacy_zip = dist_root / f"aops-core-v{fs_version}.zip"
        safe_symlink(cowork_zip, legacy_zip)
        safe_symlink(cowork_zip, dist_root / "aops-core-latest.zip")

    # 4. aops-antigravity-v{version}.tar.gz
    antigravity_archive = dist_root / f"aops-antigravity-v{fs_version}.tar.gz"
    with tarfile.open(antigravity_archive, "w:gz") as tar:
        tar.add(dist_root / "aops-antigravity", arcname=".", filter=_source_filter)
    print(f"  ✓ Packaged {antigravity_archive.name}")
    safe_symlink(antigravity_archive, dist_root / "aops-antigravity-latest.tar.gz")

    # 4a. aops-tools-antigravity-v{version}.tar.gz
    if (dist_root / "aops-tools-antigravity").exists():
        tools_antigravity_archive = dist_root / f"aops-tools-antigravity-v{fs_version}.tar.gz"
        with tarfile.open(tools_antigravity_archive, "w:gz") as tar:
            tar.add(dist_root / "aops-tools-antigravity", arcname=".", filter=_source_filter)
        print(f"  ✓ Packaged {tools_antigravity_archive.name}")
        safe_symlink(tools_antigravity_archive, dist_root / "aops-tools-antigravity-latest.tar.gz")


def create_git_tags(aops_root: Path, version: str):
    """Create git tags for release: v{version} and latest.

    Tags are created pointing to HEAD. If tags already exist, they are updated.
    Note: Tags are local only - push atomically with the branch (e.g., `git push origin main v{version} latest`) to publish.
    """
    print("\nCreating git tags...")

    # Strip build metadata for git tag — `+` is awkward in tag refs.
    version_tag = f"v{version.split('+', 1)[0]}"

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
