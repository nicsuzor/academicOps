#!/usr/bin/env -S uv run python
"""
Build script for AcademicOps extensions.
Generates dist/aops-claude, dist/aops-tools-claude, and dist/aops-antigravity.
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
    from build_utils import (  # pyright: ignore[reportMissingImports]
        get_git_commit_sha,
        safe_copy,
        safe_symlink,
        write_plugin_version,
    )
    from transforms.agent_schema import (
        build_agy_agent_json,
    )
except ImportError as e:
    # Fallback if running from a different location without setting path correctly
    # or if lib structure is not yet fully set up in development
    print(f"Error: Could not import build_utils. {e}", file=sys.stderr)
    print(f"Sys Path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# The client-translation SSoT (Table 1 of specs/hooks/CLIENT-TRANSLATION.md):
# event-name maps (both directions), valid wire events, registration shapes, and
# cold-start timeout floors. Stdlib-only by design so the build imports it without
# pulling in the hook runtime's deps. This REPLACES the three previously-divergent
# copies of the event map (router.GEMINI_EVENT_MAP, the build's own
# CLAUDE_TO_GEMINI_EVENTS + AGY_EVENT_MAP, scripts/transforms/hooks.py).
sys.path.insert(0, str(SCRIPT_DIR.parent / "aops-core"))
from hooks import client_spec  # noqa: E402

# Table 2 of specs/hooks/CLIENT-TRANSLATION.md, BUILD half (§P3b): the build-name
# tool-NAME projection (Claude<->Gemini frontmatter maps + body-text tool-call
# notation rewrites). Stdlib-only, same import-at-load contract as client_spec.
# This REPLACES the build's inline GEMINI_TOOL_NAME_MAP / TOOL_NAME_MAP copies and
# the body-text mapping/spawn-rewrite literals. NOTE: these are BUILD-frontmatter
# names, deliberately distinct from the RUNTIME-emitted names in the same module
# (e.g. Claude Agent/Task -> build writes activate_skill, runtime emits
# invoke_agent/delegate_to_agent) — see tool_registry's build-projection header.
from lib import tool_registry  # noqa: E402

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


# aops-core and aops-cowork both register the same MCP servers (e.g. "pkb",
# see aops-core/mcp.json.template) — but Claude Code namespaces plugin-provided
# tools by the INSTALLED plugin name, so the identical server produces
# `mcp__plugin_aops-core_pkb__*` under the aops-core plugin but
# `mcp__plugin_aops-cowork_pkb__*` under aops-cowork. Agent/skill/spec source
# is authored once against the aops-core name; the cowork dist needs every
# occurrence rewritten so declared tool references (frontmatter `tools:`
# lists included) match a real runtime tool instead of silently matching
# none — the agent has no way to discover a tool whose declared name doesn't
# exist under any namespace it can see.
_AOPS_CORE_MCP_PREFIX = "mcp__plugin_aops-core_"
_AOPS_COWORK_MCP_PREFIX = "mcp__plugin_aops-cowork_"


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
# templates/aops-core.pyproject.toml (epic-267fe017). The build reads that file
# and stamps the version; there is no longer an inline pyproject string literal
# here that could drift from the real file. Not called for platform=="cowork" —
# that build ships no pyproject.toml/uv.lock at all (see build_aops_core).
AOPS_CORE_PYPROJECT_PLACEHOLDER_VERSION = "0.0.0"

# Matches the `version = "..."` line under [project] (placeholder in source).
_PYPROJECT_VERSION_RE = re.compile(r'(?m)^(version\s*=\s*)"[^"]*"')


def generate_aops_core_pyproject(
    version: str, platform: str = "claude", aops_root: Path | None = None
) -> str:
    """Return the shipped pyproject.toml content with the build version stamped in.

    All platforms that ship a pyproject.toml (``claude`` / ``antigravity``)
    read the same tracked source manifest,
    ``templates/aops-core.pyproject.toml`` (ships ``lib`` + ``hooks``), and get
    the placeholder version substituted with the real build version.

    Not called for ``cowork`` — that build ships NO hooks (the shared aops-core
    hook stack serves the Cowork surface when aops-core is installed from the
    dist marketplace — task aops-04075740 / mem-fe29111a) and has no Python
    deps of its own, so ``build_aops_core`` skips generating a pyproject.toml
    (and the matching uv.lock) for it entirely rather than trimming one down.
    """
    if aops_root is None:
        aops_root = SCRIPT_DIR.parent

    src_pyproject = aops_root / "templates" / "aops-core.pyproject.toml"
    missing_hint = "cannot build aops-core without it (epic-267fe017)"
    if not src_pyproject.exists():
        raise FileNotFoundError(
            f"Required source manifest {src_pyproject} not found — {missing_hint}"
        )
    content = src_pyproject.read_text()

    content, n_ver = _PYPROJECT_VERSION_RE.subn(rf'\g<1>"{version}"', content, count=1)
    if n_ver != 1:
        raise ValueError(
            f"Could not stamp version into {src_pyproject} (no [project] version line)"
        )
    return content


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

    def _transform_hook(hook: dict, output_event: str) -> dict:
        """Rewrite a single command hook for agy (path, client flag, event arg, timeout)."""
        new_hook = dict(hook)
        # asyncRewake is the Claude-only Stop quiet-split channel — strip it so it
        # never leaks into the agy hooks.json (agy rejects unknown fields).
        for _k in ("asyncRewake", "rewakeMessage", "rewakeSummary"):
            new_hook.pop(_k, None)
        if "command" in new_hook:
            cmd = new_hook["command"]
            # agy runs PreToolUse/PostToolUse/Pre|PostInvocation hooks with the
            # process CWD set to the plugin's install dir (verified at runtime on
            # agy 1.0.13). So a plain CWD-RELATIVE path to router.sh resolves with
            # NO path variable and NO hardcoded path. router.sh self-locates via
            # $0, so HOOK_DIR is computed correctly from the relative invocation.
            #
            # Do NOT use ${extensionPath} here: agy does NOT resolve it in native
            # plugin-format command strings (it becomes empty → `bash /hooks/
            # router.sh: No such file or directory`). That is upstream agy bug
            # google-antigravity/antigravity-cli#390 (open as of 1.0.13). Do NOT
            # use a literal $HOME/... path either: agy execs the command via argv
            # (not a shell), so $HOME would reach bash as a literal token.
            cmd = cmd.replace('"${CLAUDE_PLUGIN_ROOT}/hooks/router.sh"', "hooks/router.sh")
            cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}/hooks/router.sh", "hooks/router.sh")
            cmd = cmd.replace("--client claude", "--client agy")
            cmd = f"{cmd} {output_event}"
            new_hook["command"] = cmd
        # Raise the timeout to the agy floor (defence-in-depth for cold-start;
        # never lower an already-higher source value). The floor (agy PreToolUse =
        # 15000ms, invariant #10) is a safety net for the first cold `uv run` venv
        # build; with a warm venv the hook returns in <100ms. SSoT: client_spec.
        floor = client_spec.timeout_floor_ms("agy", output_event)
        if floor is not None and new_hook.get("timeout", 0) < floor:
            new_hook["timeout"] = floor
        return new_hook

    src_hooks = config["hooks"]
    agy_hooks: dict = {}

    for event, hook_list in src_hooks.items():
        if event.endswith("-disabled"):
            continue

        # Map the internal/Claude event name to its agy wire event via the SSoT
        # (UserPromptSubmit -> PreInvocation, Stop -> PostInvocation; tool events
        # are identity). Events with no agy equivalent map to [] and are dropped.
        # agy never fans out (each internal event -> exactly one wire event).
        wire_events = client_spec.to_wire_events("agy", event)
        if not wire_events:
            continue
        output_event = wire_events[0]

        # Invocation/Stop events use a DIFFERENT registration shape than tool
        # events (config_shape == "flat"): the handlers are a FLAT list directly
        # under the event key, NOT the matcher/hooks[] wrapper (which is ONLY for
        # PreToolUse/PostToolUse, invariant #9). When invocation events were
        # wrapped in the tool-event shape, agy phantom-logged "executing command"
        # but never spawned the process — the PreInvocation context-injection hook
        # silently never fired. Emitting the flat list makes the hook fire.
        if client_spec.config_shape("agy", output_event) == "flat":
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

    For Antigravity: remaps mcp__* tools from frontmatter to call_mcp_tool and
                      applies the Claude-to-agy tool-name map.
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

    # Handle case where tools is already a string (no transformation needed for format)
    if isinstance(original_tools, str):
        if platform == "antigravity":
            # Remap tool names for Antigravity
            tools_list = [t.strip() for t in original_tools.split(",")]
            filtered = []
            AGY_TOOL_NAME_MAP = tool_registry.BUILD_CLAUDE_TO_AGY_TOOL
            seen = set()
            for t in tools_list:
                if t.startswith("mcp__"):
                    mapped = "call_mcp_tool"
                else:
                    mapped = AGY_TOOL_NAME_MAP.get(t, t)
                if mapped is not None and mapped not in seen:
                    seen.add(mapped)
                    filtered.append(mapped)
            frontmatter["tools"] = filtered
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
            return f"---\n{new_frontmatter}---{parts[2]}"
        return content

    if platform == "antigravity":
        # Remap tool names for Antigravity, preserving order and dropping duplicates
        AGY_TOOL_NAME_MAP = tool_registry.BUILD_CLAUDE_TO_AGY_TOOL
        filtered_tools = []
        seen = set()
        for t in original_tools:
            # Drop MCP tools (starting with mcp__) on Antigravity
            if t.startswith("mcp__"):
                mapped = "call_mcp_tool"
            else:
                mapped = AGY_TOOL_NAME_MAP.get(t, t)
            if mapped is not None and mapped not in seen:
                seen.add(mapped)
                filtered_tools.append(mapped)

        frontmatter["tools"] = filtered_tools
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{new_frontmatter}---{parts[2]}"

    elif platform == "claude":
        # Claude Code requires:
        # 1. Comma-separated string (not YAML array)
        # 2. PascalCase tool names for built-in tools

        # Tool name mapping: generic -> Claude Code (SSoT: tool_registry, §P3b).
        TOOL_NAME_MAP = tool_registry.BUILD_TO_CLAUDE_TOOL

        # Transform each tool name
        transformed_tools = []
        for tool in original_tools:
            if tool.startswith("mcp__"):
                # MCP tools keep their full name
                transformed_tools.append(tool)
            elif tool.startswith("mcp_"):
                # Convert single-underscore format (mcp_server_tool) back to Claude
                # format (mcp__server__tool). We assume the first word after mcp_ is
                # the server name.
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
    # 1. Platform-specific body-text tool-call notation map (call/descriptive/
    # backticked). SSoT: tool_registry.BUILD_BODY_TOOL_NOTATION (§P3b).
    platform_map = tool_registry.BUILD_BODY_TOOL_NOTATION.get(
        platform, {}
    )  # allow-fallback: default to no-op for unrecognized platforms
    for abstract, concrete in platform_map.items():
        text = text.replace(abstract, concrete)

    # 2. Dynamic replacement for Claude/Antigravity compatibility
    if platform == "antigravity":
        # agy (Antigravity 2.0) is Claude-tool-compatible: agents ship with Claude
        # tool names (no frontmatter/body transformation). It uses Claude Code hook
        # event names (PreToolUse etc.) but its own plugin root variable.
        # ${extensionPath} resolves to the plugin's final install dir (agy resolves
        # it at load time), matching the hooks/mcp path scheme.
        text = text.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")

    return text


def copy_transform_agents(
    src_agents_dir: Path, dst_agents_dir: Path, platform: str
) -> tuple[int, int]:
    """Copy + platform-transform every agent ``.md`` from src to dst.

    The SINGLE agent-emission primitive, shared by every plugin builder
    (aops-core, aops-pkb, …) so agent output is defined once and any change
    propagates to all agent-bearing plugins automatically. For each agent:
    transform frontmatter tools, translate body tool-calls, write the ``.md``;
    for the ``antigravity`` platform additionally emit ``agents/{name}/agent.json``
    (agy subagent format, system prompt inline). Returns ``(md_count, json_count)``.

    ``platform`` is the caller's transform platform (e.g. build_aops_core passes
    ``transform_platform``, which is "claude" for the cowork build).
    """
    dst_agents_dir.mkdir(parents=True, exist_ok=True)
    md_count = 0
    json_count = 0
    for agent_file in sorted(src_agents_dir.glob("*.md")):
        content = agent_file.read_text()
        # Transform frontmatter (remap mcp__ tools for Antigravity, apply schema) …
        content = transform_agent_for_platform(content, platform, agent_file.name)
        # … and translate tool calls in the body text.
        content = translate_tool_calls(content, platform)
        (dst_agents_dir / agent_file.name).write_text(content)
        md_count += 1
        # agy (Antigravity) additionally discovers subagents as
        # agents/{name}/agent.json (system prompt inline), emitted alongside
        # the .md from the already-transformed content.
        if platform == "antigravity":
            agent_json = build_agy_agent_json(
                content, agent_file.name, tool_registry.BUILD_CLAUDE_TO_AGY_TOOL
            )
            json_dir = dst_agents_dir / agent_file.stem
            json_dir.mkdir(parents=True, exist_ok=True)
            (json_dir / "agent.json").write_text(json.dumps(agent_json, indent=2) + "\n")
            json_count += 1
    return md_count, json_count


def convert_commands_to_skills(src_commands_dir: Path, dst_skills_dir: Path, platform: str) -> int:
    """Convert command .md files to skill .md files for Antigravity (agy).

    Each command file `<name>.md` becomes `skills/<name>/SKILL.md`.
    We read the command, translate tool calls, and change frontmatter `type: command` to `type: skill`.
    """
    if not src_commands_dir.exists():
        return 0

    count = 0
    for cmd_file in sorted(src_commands_dir.glob("*.md")):
        content = cmd_file.read_text(encoding="utf-8")

        # Translate tool calls in the body
        content = translate_tool_calls(content, platform)

        # Modify frontmatter type: command -> type: skill
        content = re.sub(r"(?m)^type:\s*command\s*$", "type: skill", content)

        # Output directory: dst_skills_dir / cmd_file.stem
        skill_dir = dst_skills_dir / cmd_file.stem
        skill_dir.mkdir(parents=True, exist_ok=True)

        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        count += 1

    return count


def build_aops_core(
    aops_root: Path,
    dist_root: Path,
    aca_data_path: str,
    platform: str,
    version: str = "0.1.0",
):
    """Build the aops-core extension for a specific platform.

    Supported platforms: "claude", "antigravity", "cowork".
    The "cowork" platform is a true skills-only ADDITIVE layer on top of
    aops-core, not a second copy of it (aops-04075740 / aops-10afe69d):
    aops-core, installed into Cowork from the dist marketplace, already
    supplies every shared agent/skill/command/lib file and the one shared hook
    stack (bundling hooks here too would double-fire every lifecycle hook), so
    the cowork build ships ONLY (a) files that opt into a Cowork-specific
    paragraph via `<!-- cowork:only -->` markers — scanned across
    `aops-core/` and `aops-pkb/` (e.g. `commands/pull.md`, inherited from
    aops-core in the aops-b225ec53 extraction, and `skills/end_session/
    SKILL.md`, which followed the rest of the session-lifecycle skills into
    aops-pkb per ruling A10 (aops-7ea63b63) — markers stripped, content kept)
    — and (b) the tracked `aops-cowork/` package overlay (the `cowork-sync`
    skill). Same plugin layout as "claude" (`.claude-plugin/plugin.json` +
    `.mcp.json`), with a distinct manifest naming the artifact `aops-cowork`.

    Also ships the `ida` agent + the shared head-role charter it `@`-imports
    (co-shipped from `specs/interactive-experience/head-role-charter.md`, §1a-
    charter below) and the `narrative-digest` skill — both moved here from the
    short-lived `aops-interactive` plugin per ruling A10 (aops-7ea63b63):
    hooks don't work across plugins, and the head personality must live where
    the hooks are. `ida`'s PKB tool grants stay `mcp__plugin_aops-pkb_pkb__*`
    — aops-core doesn't own the PKB interface, it consumes aops-pkb's, same as
    before the move.
    """
    print(f"Building aops-core for {platform} (v{version})...")
    plugin_name = "aops-core"
    src_dir = aops_root / plugin_name

    # Cowork is built like Claude (same plugin contract, MCP layout, tool name
    # transforms). transform_platform is what we hand to agent/tool transformers
    # so the agent tools and tool-name translations match the Claude rules.
    transform_platform = "claude" if platform == "cowork" else platform

    # Platform-specific dist dir. New naming: use 'aops-{platform}' as the dist folder
    # so consumers see 'aops-claude' / 'aops-antigravity' / 'aops-cowork' instead of
    # 'aops-core-claude'.
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

    # EXCLUDED_FROM_COPY applies to the full-tree copy (the "else" branch below,
    # every platform except cowork) — declared here at the top of the function
    # body (rather than nested in the branch) so tests/test_build_file_completeness.py's
    # AST-based check can still find it.
    EXCLUDED_FROM_COPY = {
        "pyproject.toml",  # Generated from template in 1b (version + dep list)
        "uv.lock",  # Regenerated in 1b to stay in sync with the new pyproject
        "hooks",  # Handled separately in section 2 (per-platform hooks.json transform)
        "indices",  # PATHS.md is user config, no other generated indices
        "__pycache__",
    }

    # 1. Copy content.
    #
    # cowork is deliberately NOT a full copy of the aops-core tree: aops-core,
    # installed alongside from the main dist marketplace, already supplies every
    # shared agent/skill/command/lib file, so duplicating any of it here just
    # doubles the on-disk/token footprint for no functional gain (aops-10afe69d,
    # following on from aops-04075740's hooks removal). aops-cowork ships ONLY:
    #  (a) files that opt in via <!-- cowork:only --> markers — e.g.
    #      commands/pull.md and skills/end_session/SKILL.md carry a short
    #      Cowork-specific paragraph inline in an otherwise-shared file; and
    #  (b) the tracked aops-cowork/ package overlay (below), e.g. cowork-sync.
    # Every other platform still gets the full tree ("everything except known
    # exclusions").
    if platform == "cowork":
        # _COWORK_BLOCK_RE (not a plain substring check) so documentation that
        # merely MENTIONS the marker syntax in prose (e.g. BUILD.md explaining
        # the mechanism) doesn't get mistaken for a real, matched marker block.
        #
        # Scan aops-core AND aops-pkb: aops-pkb inherited commands/pull.md
        # (and its cowork-only native-list-mirror paragraph) from aops-core in
        # the aops-b225ec53 extraction, and skills/end_session/SKILL.md (and
        # ITS cowork-only paragraph) followed the rest of the session-lifecycle
        # skills into aops-pkb per ruling A10 (aops-7ea63b63, dissolving the
        # short-lived aops-interactive plugin) — aops-pkb has no cowork
        # platform build of its own, so this is the only place its marker
        # content ships into dist/aops-cowork/. If another extracted plugin
        # ever needs a cowork-only paragraph, add its source root here too.
        marker_roots = [src_dir]
        for sibling_name in ("aops-pkb",):
            sibling_src_dir = aops_root / sibling_name
            if sibling_src_dir.exists():
                marker_roots.append(sibling_src_dir)

        def _cowork_marker_files(root: Path) -> list[Path]:
            return sorted(
                p
                for p in root.rglob("*.md")
                if not any(
                    part in BUILD_DETRITUS_NAMES or part.startswith(".")
                    for part in p.relative_to(root).parts
                )
                and _COWORK_BLOCK_RE.search(p.read_text())
            )

        copied_rel_names = []
        for root in marker_roots:
            for marker_file in _cowork_marker_files(root):
                rel = marker_file.relative_to(root)
                dst = content_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                content = marker_file.read_text()
                if rel.parts[0] == "agents":
                    content = transform_agent_for_platform(
                        content, transform_platform, marker_file.name
                    )
                content = translate_tool_calls(content, transform_platform)
                dst.write_text(content)
                copied_rel_names.append(str(rel))
        if copied_rel_names:
            print(f"  ✓ Copied {len(copied_rel_names)} cowork-marker file(s): {copied_rel_names}")

        # The pkb MCP server (.mcp.json, generated in section 4) launches via
        # scripts/run-mcp.sh, which sources ensure-path.sh. aops-pkb/scripts/ is
        # the sole tracked copy of this launcher pair (single-source-of-truth —
        # aops-core carries no scripts/run-mcp.sh or scripts/ensure-path.sh of
        # its own); the antigravity build of aops-pkb copies the same two files
        # via its own full-tree copy (build_aops_pkb §1).
        pkb_scripts_src = aops_root / "aops-pkb" / "scripts"
        mcp_launcher_dst = content_dir / "scripts"
        mcp_launcher_dst.mkdir(parents=True, exist_ok=True)
        for script_name in ("run-mcp.sh", "ensure-path.sh"):
            safe_copy(pkb_scripts_src / script_name, mcp_launcher_dst / script_name)
    else:
        for src_item in src_dir.iterdir():
            if src_item.name in EXCLUDED_FROM_COPY or src_item.name.startswith("."):
                continue
            if src_item.name == "commands" and platform == "antigravity":
                continue
            if src_item.name == "agents" and src_item.is_dir():
                # Special handling for agents: transform frontmatter and translate
                # tool calls (+ emit agy agent.json). Shared primitive — see
                # copy_transform_agents.
                dst = content_dir / src_item.name
                _md_n, agy_json_count = copy_transform_agents(src_item, dst, transform_platform)
                print(f"  ✓ Translated and copied agents -> {dst}")
                if agy_json_count:
                    print(f"  ✓ Emitted {agy_json_count} agy agent.json file(s) -> {dst}/<name>/")
            else:
                safe_copy(src_item, content_dir / src_item.name)

    # 1a-axioms. Co-ship the framework axioms INTO the plugin payload so the
    # @-imports in rbg.md / marsha.md resolve at runtime in a deployed plugin
    # (where ${CLAUDE_PLUGIN_ROOT}/../ is outside the payload). The single SSoT
    # at .agents/AXIOMS.md remains the only hand-maintained copy. Skipped
    # for cowork: rbg/marsha (the only @-importers) aren't shipped there.
    if platform != "cowork":
        agents_src_dir = aops_root / ".agents"
        agents_dst_dir = content_dir / ".agents"
        agent_md_files = sorted([p.name for p in agents_src_dir.glob("*.md")])
        for md_file in agent_md_files:
            src = agents_src_dir / md_file
            dst = agents_dst_dir / md_file
            dst.parent.mkdir(parents=True, exist_ok=True)
            safe_copy(src, dst)
        if agent_md_files:
            print(
                f"  ✓ Co-shipped {len(agent_md_files)} top-level agent file(s) -> {agents_dst_dir}"
            )

        axioms_src_dir = aops_root / ".agents" / "rules"
        axioms_dst_dir = content_dir / ".agents" / "rules"
        axiom_files = sorted([p.name for p in axioms_src_dir.glob("*.md")])
        for axiom_file in axiom_files:
            src = axioms_src_dir / axiom_file
            dst = axioms_dst_dir / axiom_file
            dst.parent.mkdir(parents=True, exist_ok=True)
            safe_copy(src, dst)
        print(f"  ✓ Co-shipped {len(axiom_files)} axiom/rule file(s) -> {axioms_dst_dir}")

    # 1a-charter. Co-ship the shared head-role charter — the `ida` agent
    # `@`-imports it (mirrors how axioms are co-shipped above; see
    # aops-75543e66 for the stale-decoy regression this pattern guards
    # against). The tracked SSoT stays at
    # specs/interactive-experience/head-role-charter.md; this is the only
    # copy baked into the plugin payload. Skipped for cowork: ida isn't
    # shipped there.
    if platform != "cowork":
        charter_src = aops_root / "specs" / "interactive-experience" / "head-role-charter.md"
        charter_dst = content_dir / ".agents" / "charter" / "head-role-charter.md"
        if not charter_src.exists():
            raise FileNotFoundError(
                f"Required charter file {charter_src} not found — cannot build aops-core without it"
            )
        charter_dst.parent.mkdir(parents=True, exist_ok=True)
        safe_copy(charter_src, charter_dst)
        print(f"  ✓ Co-shipped head-role-charter.md -> {charter_dst}")

    # 1a-pre. Compose the real aops-cowork package on top of the aops-core base.
    # aops-cowork is a TRACKED package (aops-cowork/), not a manifest fabricated
    # from templates/: its plugin.json and pyproject are sourced from there
    # (below), and its own content — the cowork-sync skill describing the PKB ↔
    # native task-list mirror that only Cowork's harness uses — is overlaid here.
    # That skill lives ONLY in the cowork package, so the other surfaces
    # (claude/antigravity) never see it; no drop step is needed.
    if platform == "cowork":
        cowork_pkg = aops_root / "aops-cowork"
        cowork_skills = cowork_pkg / "skills"
        if cowork_skills.is_dir():
            overlaid = 0
            for skill_dir in cowork_skills.iterdir():
                if skill_dir.name.startswith(".") or not skill_dir.is_dir():
                    continue
                safe_copy(skill_dir, content_dir / "skills" / skill_dir.name)
                overlaid += 1
            if overlaid:
                print(f"  ✓ Overlaid {overlaid} aops-cowork package skill(s) (e.g. cowork-sync)")
    else:
        # Defensive: if a stray cowork-sync ever lands in the aops-core base,
        # keep it out of the non-cowork surfaces.
        cowork_sync_dir = content_dir / "skills" / "cowork-sync"
        if cowork_sync_dir.exists():
            shutil.rmtree(cowork_sync_dir)
            print(f"  - Dropped stray cowork-sync skill (not for {platform})")

    # 1a. Post-copy: translate tool names in all .md files for Antigravity.
    # Agents get transform_agent_for_platform above (frontmatter + body);
    # this pass catches skills, commands, lib, and top-level .md files
    # that were copied verbatim by safe_copy. Antigravity needs the
    # ${CLAUDE_PLUGIN_ROOT} replacement and tool-name translations.
    if platform == "antigravity":
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

    # 1a-cowork-mcp. Rewrite the aops-core-scoped MCP tool-name prefix to the
    # aops-cowork one across every copied .md file (agent frontmatter `tools:`
    # lists included — those were written as plain text in the loop above, not
    # through transform_agent_for_platform, so they still carry the aops-core
    # name and need this pass same as everything else).
    if platform == "cowork":
        mcp_prefix_rewritten = 0
        for md_file in content_dir.rglob("*.md"):
            original = md_file.read_text()
            if _AOPS_CORE_MCP_PREFIX not in original:
                continue
            md_file.write_text(original.replace(_AOPS_CORE_MCP_PREFIX, _AOPS_COWORK_MCP_PREFIX))
            mcp_prefix_rewritten += 1
        if mcp_prefix_rewritten:
            print(
                f"  ✓ Rewrote aops-core→aops-cowork MCP tool-name prefix in "
                f"{mcp_prefix_rewritten} .md file(s)"
            )

    # 1b. Stamp the tracked source pyproject (the in-tree SSoT for shipped deps)
    # with the build version and write it into the dist payload, then lock against
    # that stamped copy so pyproject.toml and uv.lock ship in lockstep. `uv.lock`
    # is NOT tracked — it is generated here per-platform. `uv sync --frozen` at
    # runtime then installs exactly what the manifest declared, no drift.
    #
    # The cowork build ships neither a pyproject.toml nor a uv.lock: it has no
    # hooks/ (see the skip above) and no Python dependencies of its own — the
    # aops-core install co-located in the Cowork marketplace supplies the shared
    # hook stack and its dependencies. Declaring a manifest here would just be
    # dead packaging metadata for a package with nothing to install.
    if platform != "cowork":
        pyproject_source = "templates/aops-core.pyproject.toml"
        pyproject_content = generate_aops_core_pyproject(version, platform, aops_root)
        pyproject_path = content_dir / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)
        print(f"  ✓ Stamped pyproject.toml (v{version}) from {pyproject_source}")

        subprocess.run(["uv", "lock"], cwd=content_dir, check=True)
        print("  ✓ Regenerated uv.lock from pyproject.toml")
    else:
        print("  - Skipped pyproject.toml/uv.lock for cowork (no deps of its own)")

    # 1b. Copy root-level framework-maintenance scripts. Not for cowork: these
    # audit aops-core's own tree and aren't shipped there (see section 1 above).
    scripts_src = aops_root / "scripts"
    scripts_dst = content_dir / "scripts"
    if platform != "cowork" and scripts_src.exists():
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
    # Bind hooks_src / hooks_dst unconditionally so the antigravity hooks.json
    # generation below (which only runs for non-cowork platforms) has
    # statically-known Paths, not possibly-Unbound names.
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
                if item.name == "hooks.json" and platform == "antigravity":
                    # Handle hooks.json separately for Antigravity
                    continue
                safe_copy(item, content_dir / "hooks" / item.name)
    else:
        print("  - Skipped hooks for cowork (aops-core supplies the shared hook stack)")

    # Generate platform-compatible hooks.json
    if platform == "antigravity":
        # Antigravity uses Claude Code event names (PreToolUse, PostToolUse, etc.)
        # but needs ${extensionPath} instead of ${CLAUDE_PLUGIN_ROOT}
        hooks_json_src = hooks_src / "hooks.json"
        if hooks_json_src.exists():
            _generate_antigravity_hooks_json(hooks_json_src, dist_dir / "hooks.json")

    # 3. Extension Manifest / Plugin Info
    if platform in ("claude", "cowork"):
        # Both use the same plugin contract (.claude-plugin/plugin.json). claude
        # ships from a template; cowork is a REAL composed package, so its
        # manifest is the tracked aops-cowork/.claude-plugin/plugin.json (its
        # `name`, `description`, and keywords are tuned for the Cowork variant
        # and maintained as source, not fabricated here).
        if platform == "cowork":
            src_plugin_json = aops_root / "aops-cowork" / ".claude-plugin" / "plugin.json"
        else:
            src_plugin_json = aops_root / "templates" / "aops-core.plugin.json"
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
                # aops-core declares no 'userConfig'/pkb_mcp_url and no pkb MCP
                # server for the "claude" or "antigravity" platforms — the
                # aops-pkb plugin owns pkb there (HTTP transport for claude,
                # its own run-mcp.sh for antigravity). Only "cowork" still gets
                # pkb via run-mcp.sh in this template (copied in from
                # aops-pkb/scripts/ at build time), resolving the URL from the
                # env / ~/.env.local.

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
                # Pick the platform-specific block: the "claude" block injects
                # PKB_MCP_URL from userConfig; the "cowork" block omits that env
                # (Cowork's userConfig path is unreliable) and lets run-mcp.sh
                # resolve the URL. Fall back to the claude block, then the whole
                # template, if a dedicated block is absent.
                shaped_mcp_config = mcp_template.get(
                    platform, mcp_template.get("claude", mcp_template)
                )
                dist_mcp_path = dist_dir / ".mcp.json"
                with open(dist_mcp_path, "w") as f:
                    json.dump(shaped_mcp_config, f, indent=2)
                    f.write("\n")

            # Prepare for Antigravity 2.0 Plugin (native mcp_config.json).
            #
            # We ship ${extensionPath} as the SSoT path token, but agy does NOT
            # resolve it in native-format mcp_config.json, and it spawns MCP
            # servers with the WORKSPACE cwd (not the plugin dir) — so neither a
            # path variable nor a relative path resolves at runtime (verified on
            # agy 1.0.13; upstream bug google-antigravity/antigravity-cli#390,
            # open). Unlike hooks (which agy runs FROM the plugin dir, so they use
            # a cwd-relative path), MCP has no in-config escape. The `make
            # install-agy` target therefore resolves ${extensionPath} → the actual
            # install dir AFTER `agy plugin install` (a discovered path, nothing
            # hardcoded in source). Remove that step once #390 is fixed.
            if platform == "antigravity":
                servers_config = mcp_config.get("mcpServers", mcp_config)
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

    # 5. Commands (Antigravity gets commands converted to skills)
    if platform == "antigravity":
        converted = convert_commands_to_skills(
            src_dir / "commands", content_dir / "skills", platform
        )
        if converted:
            print(f"  ✓ Converted {converted} command(s) to skills for Antigravity")

    # 6. Anti-drift regression guard. Catches the class of defect that left
    # rbg + marsha grounding verdicts on a stale `old_axioms.md` decoy because
    # the canonical axioms were never shipped into the plugin payload (#aops-75543e66).
    # Two checks: (a) every plugin-relative @-import in a shipped agent must
    # resolve inside the payload; (b) no axiom-shaped decoy may ship anywhere
    # outside .agents/rules/.
    _assert_plugin_imports_resolve(content_dir, platform)
    _assert_no_axiom_decoys(content_dir)

    print(f"✓ Built {plugin_name} ({platform})")


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
    """Fail the build if any axiom-shaped file ships outside the allowed paths.

    The canonical axioms live at .agents/AXIOMS.md (co-shipped at build time),
    with per-axiom review guidance at .agents/rules/AXIOMS-REVIEW.md. Any other
    axiom-shaped file in the payload is a decoy that a fallback `find` could
    surface to a review agent (this happened: aops-core/old_axioms.md shipped
    for months and rbg grounded verdicts on it after the canonical import
    dangled, #aops-75543e66).
    """
    allowed_rel = {
        Path(".agents/AXIOMS.md"),
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
    platform: str,
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
    platform: str,
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

    aops-ts is a tiny, opt-in package with two hooks for remote/cloud sessions:
    a SessionStart hook that brings Tailscale up so tailnet services (e.g. the
    PKB MCP at *.ts.net) resolve, and a SessionEnd hook that parses the session
    transcript and rsyncs it to a tailnet host so cloud transcripts survive
    container reclamation. The bring-up hook is self-contained bash; the sync
    hook reuses aops-core's transcript.py when present (raw-JSONL fallback
    otherwise). Only the Claude platform is built; the tailnet bring-up targets
    Claude Code on the web.
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


def build_aops_pkb(
    aops_root: Path,
    dist_root: Path,
    platform: str = "claude",
    version: str = "0.1.0",
):
    """Build the aops-pkb extension for a specific platform.

    aops-pkb is the task/work-unit module: the judgment layer operating at the
    entry (dispatch-readiness) and exit (acceptance) chokepoints — capture
    (`/q`), strategic planning + decomposition (`planner`), the task-lifecycle
    spine (`/pull`, `/dispatch`), acceptance (`/verify` + `strategic-review`'s
    four-agent sign-off: james, rbg, pauli, marsha), and PKB curation
    (`/remember`, `/learn`, `/maintain`). See PKB task aops-b225ec53.

    Unlike aops-tools/aops-extras (skills-only, no agents/commands/MCP), aops-pkb
    ships agents + commands + skills + its own `pkb` MCP server registration
    (a SEPARATE plugin identity from aops-core's, so Claude Code namespaces its
    tools as `mcp__plugin_aops-pkb_pkb__*` — the 4 moved agents (james/rbg/pauli/
    marsha) and the `task-lifecycle` skill were rewritten at the source level to
    this prefix, not by a build-time rewrite, since aops-pkb is a standalone
    package rather than an aops-core overlay like aops-cowork. Other moved
    skill-body files (planner, remember) still use the bare `mcp__pkb__*` short
    form in prose — a pre-existing, functionally-fine convention — left as-is.
    It has NO hooks (the module operates outside the agent loop — no in-session
    enforcement is needed, ruling C1) and so, like aops-tools/aops-extras, ships
    no pyproject.toml/uv.lock.

    Only the "claude" platform is implemented for now (mirrors aops-ts's scope).
    Antigravity support can be added later following build_aops_core's
    pattern if this module needs to ship there.
    """
    print(f"Building aops-pkb for {platform} (v{version})...")
    plugin_name = "aops-pkb"
    src_dir = aops_root / plugin_name

    if not src_dir.exists():
        print(f"  ⚠️  {src_dir} not found, skipping aops-pkb build")
        return

    if platform not in ("claude", "antigravity"):
        print(f"  ⚠️  aops-pkb build not implemented for platform={platform!r}, skipping")
        return

    dist_dir = dist_root / f"aops-pkb-{platform}"
    content_dir = dist_dir

    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)

    # 1. Copy content. agents/ gets the same frontmatter/body transform pass as
    # build_aops_core (Claude tool-name normalisation); everything else copies
    # verbatim (no hooks, no lib/ — the module ships pure agent/skill/command
    # instructions plus its own MCP server registration). aops-pkb has no
    # cowork platform build of its own, but it inherited commands/pull.md's
    # `<!-- cowork:only -->` paragraph from aops-core (aops-b225ec53) — that
    # block is stripped below (§1a) the same way build_aops_core strips it for
    # every non-cowork platform, so it never leaks into this (claude-only) build.
    EXCLUDED_FROM_COPY = {"mcp.json.template", "__pycache__"}
    for src_item in src_dir.iterdir():
        if src_item.name in EXCLUDED_FROM_COPY or src_item.name.startswith("."):
            continue
        if src_item.name == "commands" and platform == "antigravity":
            continue
        if src_item.name == "agents" and src_item.is_dir():
            # Shared agent-emission primitive (transform + translate + agy json).
            dst = content_dir / src_item.name
            _md_n, agy_json_count = copy_transform_agents(src_item, dst, platform)
            print(f"  ✓ Translated and copied agents -> {dst}")
            if agy_json_count:
                print(f"  ✓ Emitted {agy_json_count} agy agent.json file(s) -> {dst}/<name>/")
        else:
            safe_copy(src_item, content_dir / src_item.name)

    # 1a-pre. Translate tool names in all non-agent .md files for Antigravity.
    if platform == "antigravity":
        translated_count = 0
        for md_file in content_dir.rglob("*.md"):
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

    # 1a. Strip cowork-only blocks (markers AND wrapped content) from every
    # copied .md file — this build never ships the "cowork" platform, so any
    # `<!-- cowork:only -->` paragraph inherited from aops-core (e.g.
    # commands/pull.md's native-list-mirror note) must not leak in verbatim.
    cowork_stripped = 0
    for md_file in content_dir.rglob("*.md"):
        original = md_file.read_text()
        if _COWORK_OPEN not in original:
            continue
        processed = _process_cowork_markers(original, platform)
        if processed != original:
            md_file.write_text(processed)
            cowork_stripped += 1
    if cowork_stripped:
        print(f"  ✓ Stripped cowork-only blocks in {cowork_stripped} .md file(s)")

    # 1b. Co-ship the framework axioms — rbg.md and marsha.md @-import
    # ${CLAUDE_PLUGIN_ROOT}/.agents/AXIOMS.md, which must resolve inside
    # THIS plugin's own payload at runtime (mirrors build_aops_core §1a-axioms;
    # see the aops-75543e66 stale-axiom-decoy regression this guards against).
    agents_src_dir = aops_root / ".agents"
    agents_dst_dir = content_dir / ".agents"
    agent_md_files = sorted([p.name for p in agents_src_dir.glob("*.md")])
    for md_file in agent_md_files:
        src = agents_src_dir / md_file
        dst = agents_dst_dir / md_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        safe_copy(src, dst)
    if agent_md_files:
        print(f"  ✓ Co-shipped {len(agent_md_files)} top-level agent file(s) -> {agents_dst_dir}")

    axioms_src_dir = aops_root / ".agents" / "rules"
    axioms_dst_dir = content_dir / ".agents" / "rules"
    axiom_files = sorted([p.name for p in axioms_src_dir.glob("*.md")])
    for axiom_file in axiom_files:
        src = axioms_src_dir / axiom_file
        dst = axioms_dst_dir / axiom_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        safe_copy(src, dst)
    print(f"  ✓ Co-shipped {len(axiom_files)} axiom/rule file(s) -> {axioms_dst_dir}")

    # 2. Plugin manifest. aops-pkb ships a REAL tracked plugin.json (like
    # aops-cowork), not one fabricated from templates/ (like aops-core/
    # aops-tools/aops-extras) — there is no reason to keep it out-of-tree.
    if platform == "claude":
        src_plugin_json = src_dir / ".claude-plugin" / "plugin.json"
        dist_plugin_dir = content_dir / ".claude-plugin"
        dist_plugin_json = dist_plugin_dir / "plugin.json"
        if not src_plugin_json.exists():
            print(f"Error: {src_plugin_json} not found.", file=sys.stderr)
            sys.exit(1)
        dist_plugin_dir.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(src_plugin_json.read_text())
        manifest["version"] = version
        # Hygiene: strip marketplace-only fields (same as every other plugin build).
        manifest.pop("source", None)
        manifest.pop("category", None)
        with open(dist_plugin_json, "w") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        print(f"  ✓ Updated and hygienically copied plugin.json -> {dist_plugin_json}")
    elif platform == "antigravity":
        src_plugin_json = aops_root / "templates" / f"{plugin_name}.antigravity-plugin.json"
        dist_plugin_json = content_dir / "plugin.json"
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

    # 3. Generate MCP config from the tracked mcp.json.template (own `pkb` MCP
    # server registration — a separate plugin identity from aops-core's).
    template_path = src_dir / "mcp.json.template"
    if template_path.exists():
        mcp_template = json.loads(template_path.read_text())
        mcp_config = mcp_template.get(platform, mcp_template)

        if platform == "claude":
            dist_mcp_path = dist_dir / ".mcp.json"
            with open(dist_mcp_path, "w") as f:
                json.dump(mcp_config, f, indent=2)
                f.write("\n")
            print(f"  ✓ Generated {dist_mcp_path} from mcp.json.template")
        elif platform == "antigravity":
            servers_config = mcp_config.get("mcpServers", mcp_config)
            ag_servers_json = json.dumps(servers_config)
            ag_servers_json = ag_servers_json.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")
            ag_servers_config = json.loads(ag_servers_json)
            ag_mcp_config = {"mcpServers": ag_servers_config}

            dist_mcp_path = dist_dir / "mcp_config.json"
            with open(dist_mcp_path, "w") as f:
                json.dump(ag_mcp_config, f, indent=2)
                f.write("\n")
            print(f"  ✓ Generated mcp_config.json -> {dist_mcp_path}")
    else:
        print(f"Error: {template_path} not found.", file=sys.stderr)
        sys.exit(1)

    # 4. Commands (Antigravity gets commands converted to skills)
    if platform == "antigravity":
        converted = convert_commands_to_skills(
            src_dir / "commands", content_dir / "skills", platform
        )
        if converted:
            print(f"  ✓ Converted {converted} command(s) to skills for Antigravity")

    # 5. Anti-drift regression guards (same as build_aops_core §6): every
    # plugin-relative @-import must resolve inside THIS payload, and no
    # axiom-shaped decoy may ship outside .agents/rules/.
    _assert_plugin_imports_resolve(content_dir, platform)
    _assert_no_axiom_decoys(content_dir)

    print(f"✓ Built {plugin_name} ({platform})")


def main():
    parser = argparse.ArgumentParser(description="Build script for AcademicOps extensions.")
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

    # Build components (Claude)
    build_aops_core(aops_root, dist_root, aca_data_path, "claude", version)

    # Build components (Cowork) — Claude-shaped plugin layout, manifest pinned
    # to `aops-cowork`, cowork-only blocks kept, cowork-sync skill included.
    # Ships NO hooks: aops-core (installed into Cowork from the dist marketplace)
    # provides the shared hook stack; bundling hooks here would double-fire them.
    build_aops_core(aops_root, dist_root, aca_data_path, "cowork", version)

    # Build aops-tools (domain skills package)
    build_aops_tools(aops_root, dist_root, "claude", version)

    # Build aops-extras (replaceable technology-specific skills package)
    build_aops_extras(aops_root, dist_root, "claude", version)

    # Build aops-ts (opt-in Tailscale bring-up hook — Claude/web only)
    build_aops_ts(aops_root, dist_root, "claude", version)

    # Build aops-pkb (task/work-unit module — Claude only for now, see
    # build_aops_pkb's docstring)
    build_aops_pkb(aops_root, dist_root, "claude", version)

    # Build components (Antigravity)
    build_aops_core(aops_root, dist_root, aca_data_path, "antigravity", version)
    build_aops_tools(aops_root, dist_root, "antigravity", version)
    build_aops_extras(aops_root, dist_root, "antigravity", version)
    build_aops_pkb(aops_root, dist_root, "antigravity", version)

    # Generate the single root marketplace.json (sources ./dist/aops-*)
    generate_marketplace(aops_root, dist_root, version)

    # Generate the LOCAL-dev marketplace (name `aops`, sources ./aops-*) written
    # INTO dist/ so `claude plugin marketplace add dist/` registers it under the
    # distinct `aops` name — never clobbering the released `academicOps`
    # marketplace, so a developer can tell a local build apart from the release.
    generate_local_marketplace(aops_root, dist_root, version)

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


def generate_local_marketplace(aops_root: Path, dist_root: Path, version: str):
    """Generate the LOCAL-dev Claude marketplace at dist/.claude-plugin/marketplace.json.

    Same plugin set as the root marketplace, but with TWO deliberate differences:
      • name is `aops` (not `academicOps`) so `make dev` installs land in their own
        marketplace/plugin namespace (`aops-core@aops`) — visibly distinct from the
        released `academicOps` install in `claude plugin marketplace list`.
      • plugin sources are rewritten ./dist/aops-* → ./aops-* because THIS
        marketplace root is dist/ (not the repo root), so a co-located ./aops-claude
        resolves to dist/aops-claude.

    Written under dist/ (gitignored) and skipped by the publish glob `dist/*/`
    (dot-dirs don't match), so it never reaches the dist branch. Consumed by
    `make dev` / `make install-dev` via `claude plugin marketplace add $(DIST_DIR)`.
    """
    template_path = aops_root / "templates" / "marketplace.json"
    if not template_path.exists():
        raise FileNotFoundError(f"templates/marketplace.json not found at {template_path}")

    with open(template_path) as f:
        data = json.load(f)

    data["name"] = "aops"
    data["description"] = (
        "academicOps LOCAL dev build — distinct from the released 'academicOps' marketplace"
    )
    for plugin in data.get(
        "plugins", []
    ):  # allow-fallback: template always defines plugins; empty loop is a safe no-op
        plugin["version"] = version
        src = plugin.get(
            "source", ""
        )  # allow-fallback: an entry without a source is left unrewritten
        if src.startswith("./dist/"):
            plugin["source"] = "./" + src[len("./dist/") :]

    marketplace_dir = dist_root / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    marketplace = marketplace_dir / "marketplace.json"
    with open(marketplace, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"  ✓ Generated {marketplace} (name 'aops', sources ./aops-*)")


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
    - aops-claude-v{version}.tar.gz / aops-tools-claude-v{version}.tar.gz

    Plus 'latest' symlinks for the Claude archives.
    """
    print("\nPackaging artifacts for release...")

    # Filter for packaging to exclude noise
    def _source_filter(tarinfo):
        if any(part in BUILD_DETRITUS_NAMES for part in Path(tarinfo.name).parts):
            return None
        return tarinfo

    # Strip SemVer build metadata (+gSHA[.dirty]) from filenames only; it lives
    # inside plugin.json. Filenames stay clean for tooling that mangles `+`.
    fs_version = version.split("+", 1)[0]

    # 1. aops-claude-v{version}.tar.gz
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
