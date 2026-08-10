"""Tool vocabulary and translation mapping for academicOps client adapters."""

import re
import tomllib
from pathlib import Path
from typing import Any

from build.errors import BuildError

_TOOL_MAP_PATH = Path(__file__).resolve().parent / "tool_map.toml"
_VALID_NAME_RE = re.compile(r"^[a-z0-9-]+$")


def load_tool_config(
    path: Path = _TOOL_MAP_PATH,
) -> tuple[list[str], dict[str, list[str]]]:
    """Loads accepted agy tool vocabulary and Claude -> agy tool map from TOML."""
    if not path.exists():
        raise BuildError(f"Tool map declaration not found: {path}")

    try:
        data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise BuildError(f"{path}: failed to parse TOML: {e}") from e

    accepted_tools = data.get("accepted_tools")
    if accepted_tools is None and "vocabulary" in data and isinstance(data["vocabulary"], dict):
        accepted_tools = data["vocabulary"].get("accepted_tools")
    if not isinstance(accepted_tools, list) or not all(isinstance(x, str) for x in accepted_tools):
        raise BuildError(f"{path}: 'accepted_tools' must be a list of strings")

    tool_map_raw = data.get("tool_map")
    if not isinstance(tool_map_raw, dict):
        raise BuildError(f"{path}: 'tool_map' must be a dictionary")

    tool_map: dict[str, list[str]] = {}
    for k, v in tool_map_raw.items():
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            raise BuildError(f"{path}: tool_map entry for {k!r} must be a list of strings")
        tool_map[k] = v

    return accepted_tools, tool_map


def validate_agent_name_and_desc(name: Any, description: Any, file_path: Path) -> str:
    if not name or not isinstance(name, str) or not _VALID_NAME_RE.match(name):
        raise BuildError(
            f"{file_path}: invalid agent name {name!r} — must be lowercase letters and hyphens only (no colons, underscores, or uppercase)"
        )
    if not description or not isinstance(description, str) or not description.strip():
        raise BuildError(f"{file_path}: missing required frontmatter field 'description'")
    return name


def process_agent_tools_agy(
    raw_tools: Any,
    has_tools_key: bool,
    agent_name: str,
    file_path: Path,
    accepted_tools: list[str],
    tool_map: dict[str, list[str]],
) -> list[str]:
    """Translates source agent frontmatter 'tools' into agy's accepted tool list."""
    if not has_tools_key:
        # Absence semantics: emit the full accepted vocabulary explicitly
        return list(accepted_tools)

    tools_list: list[str] = []
    if isinstance(raw_tools, str):
        tools_list = [t.strip() for t in raw_tools.split(",") if t.strip()]
    elif isinstance(raw_tools, list):
        tools_list = [str(t).strip() for t in raw_tools if isinstance(t, str) and str(t).strip()]

    if not tools_list:
        raise BuildError(f"{file_path}: agent {agent_name!r} has empty 'tools' list (tools: [])")

    expanded: list[str] = []
    for tool_name in tools_list:
        if tool_name.startswith("mcp__"):
            # MCP is implicit on agy; omitted from frontmatter tools list
            continue
        elif tool_name in tool_map:
            expanded.extend(tool_map[tool_name])
        else:
            raise BuildError(
                f"{file_path}: agent {agent_name!r} has unknown/unmappable tool {tool_name!r}"
            )

    seen: set[str] = set()
    final_tools: list[str] = []
    for t in expanded:
        if t not in seen:
            seen.add(t)
            final_tools.append(t)

    if not final_tools:
        raise BuildError(f"{file_path}: agent {agent_name!r} tool expansion yielded 0 tools")

    accepted_set = set(accepted_tools)
    for t in final_tools:
        if t not in accepted_set:
            raise BuildError(
                f"{file_path}: agent {agent_name!r} emitted tool {t!r} which is not in agy accepted tool vocabulary"
            )

    return final_tools


def process_agent_tools_claude(
    raw_tools: Any,
    has_tools_key: bool,
    agent_name: str,
    file_path: Path,
    tool_map: dict[str, list[str]],
) -> list[str] | None:
    """Validates and formats source agent frontmatter 'tools' for Claude Code."""
    if not has_tools_key:
        # Absence semantics: leave unset (inherits everything)
        return None

    tools_list: list[str] = []
    if isinstance(raw_tools, str):
        tools_list = [t.strip() for t in raw_tools.split(",") if t.strip()]
    elif isinstance(raw_tools, list):
        tools_list = [str(t).strip() for t in raw_tools if isinstance(t, str) and str(t).strip()]

    if not tools_list:
        raise BuildError(f"{file_path}: agent {agent_name!r} has empty 'tools' list (tools: [])")

    final_tools: list[str] = []
    seen: set[str] = set()
    for tool_name in tools_list:
        if tool_name.startswith("mcp__") or tool_name in tool_map:
            if tool_name not in seen:
                seen.add(tool_name)
                final_tools.append(tool_name)
        else:
            raise BuildError(
                f"{file_path}: agent {agent_name!r} has unknown/unmappable tool {tool_name!r}"
            )

    if not final_tools:
        raise BuildError(f"{file_path}: agent {agent_name!r} tool expansion yielded 0 tools")

    return final_tools
