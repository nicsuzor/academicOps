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


def translate_mcp_tool_to_agy(tool_name: str, plugin_name: str = "") -> str:
    """Translates Claude Code MCP tool notation (mcp__server__tool) to agy format (mcp_server_tool or mcp_server_*)."""
    raw = tool_name[5:] if tool_name.startswith("mcp__") else tool_name
    parts = raw.split("__")
    if not parts or not parts[0]:
        return ""
    server_raw = parts[0]
    if ":" in server_raw:
        server_name = server_raw.split(":")[-1]
    elif plugin_name and server_raw.startswith(f"plugin_{plugin_name}_"):
        server_name = server_raw[len(f"plugin_{plugin_name}_") :]
    elif server_raw.startswith("plugin_"):
        subparts = server_raw.split("_")
        server_name = subparts[-1] if len(subparts) >= 3 else server_raw
    elif plugin_name and server_raw.startswith(f"{plugin_name}_"):
        server_name = server_raw[len(f"{plugin_name}_") :]
    else:
        server_name = server_raw

    rest = parts[1:]
    if not rest or any("*" in p for p in rest):
        tool_suffix = "*"
    else:
        tool_suffix = "_".join(rest)

    return f"mcp_{server_name}_{tool_suffix}"


def extract_agy_mcp_servers(frontmatter: dict[str, Any], plugin_name: str = "") -> list[str]:
    """Extracts unique canonical MCP server names for agy from frontmatter's mcpServers and mcp__ tools."""
    raw_mcp_servers = frontmatter.get("mcpServers")
    servers: list[str] = []

    def _add_server(s: str) -> None:
        if not s or not isinstance(s, str):
            return
        if ":" in s:
            s = s.split(":")[-1]
        if plugin_name and s.startswith(f"plugin_{plugin_name}_"):
            s = s[len(f"plugin_{plugin_name}_") :]
        elif s.startswith("plugin_"):
            parts = s.split("_")
            if len(parts) >= 3:
                s = parts[-1]
        if plugin_name and s.startswith(f"{plugin_name}_"):
            s = s[len(f"{plugin_name}_") :]

        if s and s not in servers:
            servers.append(s)

    if raw_mcp_servers:
        if isinstance(raw_mcp_servers, str):
            for item in raw_mcp_servers.split(","):
                _add_server(item.strip())
        elif isinstance(raw_mcp_servers, list):
            for item in raw_mcp_servers:
                _add_server(str(item).strip())

    for key in ("tools", "disallowedTools"):
        val = frontmatter.get(key)
        tool_list = []
        if isinstance(val, str):
            tool_list = [t.strip() for t in val.split(",") if t.strip()]
        elif isinstance(val, list):
            tool_list = [str(t).strip() for t in val if isinstance(t, str)]
        for t in tool_list:
            base_name = t.split("(", 1)[0].strip() if "(" in t else t
            if base_name.startswith("mcp__"):
                parts = base_name[5:].split("__")
                if parts and parts[0]:
                    _add_server(parts[0])

    return servers


def process_agent_tools_agy(
    raw_tools: Any,
    has_tools_key: bool,
    agent_name: str,
    file_path: Path,
    accepted_tools: list[str],
    tool_map: dict[str, list[str]],
    plugin_name: str = "",
    raw_disallowed_tools: Any = None,
    has_disallowed_tools_key: bool = False,
) -> list[str]:
    """Translates source agent frontmatter 'tools' and 'disallowedTools' into agy's accepted tool list."""

    rejected: set[str] = set()

    if not has_tools_key:
        # Absence semantics: emit the full accepted vocabulary explicitly
        initial_tools = list(accepted_tools)
    else:
        tools_list: list[str] = []
        if isinstance(raw_tools, str):
            tools_list = [t.strip() for t in raw_tools.split(",") if t.strip()]
        elif isinstance(raw_tools, list):
            tools_list = [
                str(t).strip() for t in raw_tools if isinstance(t, str) and str(t).strip()
            ]

        if not tools_list:
            raise BuildError(
                f"{file_path}: agent {agent_name!r} has empty 'tools' list (tools: [])"
            )

        expanded: list[str] = []

        for tool_name in tools_list:
            has_scope = "(" in tool_name
            base_name = tool_name.split("(", 1)[0].strip() if has_scope else tool_name
            if base_name.startswith("mcp__"):
                translated_mcp = translate_mcp_tool_to_agy(base_name, plugin_name)
                if translated_mcp:
                    expanded.append(translated_mcp)
            elif base_name in tool_map:
                mapped = tool_map[base_name]
                if has_scope:
                    unrestricted_name = mapped[0] if mapped else "tool"
                    prefix = f"{plugin_name}/" if plugin_name else ""
                    print(
                        f"warning: {prefix}{agent_name}: '{tool_name}' scope dropped for agy; {unrestricted_name} is unrestricted"
                    )
                expanded.extend(mapped)
            elif base_name in accepted_tools:
                # Already agy-native. A `<name>.agy.md` variant writes its
                # frontmatter in agy's own vocabulary precisely so nothing has to
                # translate it; a name agy already accepts passes through as-is.
                expanded.append(base_name)
            else:
                rejected.add(tool_name)

        seen: set[str] = set()
        initial_tools = []
        for t in expanded:
            if t not in seen:
                seen.add(t)
                initial_tools.append(t)

    # Process disallowedTools if present
    denied_tools: list[str] = []
    if has_disallowed_tools_key and raw_disallowed_tools is not None:
        disallowed_list: list[str] = []
        if isinstance(raw_disallowed_tools, str):
            disallowed_list = [t.strip() for t in raw_disallowed_tools.split(",") if t.strip()]
        elif isinstance(raw_disallowed_tools, list):
            disallowed_list = [
                str(t).strip()
                for t in raw_disallowed_tools
                if isinstance(t, str) and str(t).strip()
            ]

        for tool_name in disallowed_list:
            has_scope = "(" in tool_name
            base_name = tool_name.split("(", 1)[0].strip() if has_scope else tool_name
            if base_name.startswith("mcp__"):
                translated_mcp = translate_mcp_tool_to_agy(base_name, plugin_name)
                if translated_mcp:
                    denied_tools.append(translated_mcp)
            elif base_name in tool_map:
                mapped = tool_map[base_name]
                if has_scope:
                    unrestricted_name = mapped[0] if mapped else "tool"
                    prefix = f"{plugin_name}/" if plugin_name else ""
                    print(
                        f"warning: {prefix}{agent_name}: '{tool_name}' scope dropped for agy; {unrestricted_name} is unrestricted"
                    )
                denied_tools.extend(mapped)
            else:
                rejected.add(tool_name)

    denied_set = set(denied_tools)
    rejected_set = set(rejected)
    final_tools = [t for t in initial_tools if t not in rejected_set and t not in denied_set]

    if not final_tools:
        raise BuildError(f"{file_path}: agent {agent_name!r} tool expansion yielded 0 tools")

    for t in final_tools:
        if t not in accepted_tools and not t.startswith("mcp_"):
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
    """Validates and formats source agent frontmatter 'tools' for Claude Code.

    Ignores unknown tools.
    """
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
    rejected: set[str] = set()

    for tool_name in tools_list:
        base_name = tool_name.split("(", 1)[0].strip() if "(" in tool_name else tool_name
        if base_name.startswith("mcp__") or base_name in tool_map:
            if tool_name not in seen:
                seen.add(tool_name)
                final_tools.append(tool_name)
        else:
            rejected.add(tool_name)

    if rejected:
        print(f"{file_path}: agent {agent_name!r} has unknown/unmappable tools {list(rejected)}")

    if not final_tools:
        raise BuildError(f"{file_path}: agent {agent_name!r} tool expansion yielded 0 tools")

    return final_tools
