import re

# Standard agy system-prompt sections injected by the harness at load time
# (user identity, available skills, inter-agent messaging, MCP servers). Kept
# here as the single default; individual agents don't need to opt in per-file.
_AGY_INCLUDE_SECTIONS = ["user_information", "skills", "messaging", "mcp_servers"]


def build_agy_agent_json(content: str, filename: str, tool_map: dict) -> dict:
    """Build an Antigravity (agy) ``agent.json`` definition from a Claude agent .md.

    agy discovers subagents as ``agents/{name}/agent.json`` with the system
    prompt inline under ``config.customAgent.systemPromptSections`` (there is no
    sibling prompt file). ``content`` should be the ALREADY platform-transformed
    markdown (frontmatter tools remapped to agy names, body tool-calls
    translated) — re-mapping through ``tool_map`` is idempotent for names that
    are already agy-native.

    Tool remapping mirrors ``transform_agent_for_platform``'s antigravity branch:
    ``mcp__*`` tools are dropped (no agy equivalent) and any tool whose map value
    is ``None`` is dropped; order is preserved and duplicates collapsed.
    """
    import yaml

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Agent '{filename}': no YAML frontmatter found")

    frontmatter = yaml.safe_load(parts[1])
    if not frontmatter:
        raise ValueError(f"Agent '{filename}': empty or unparseable YAML frontmatter")
    body = parts[2].lstrip("\n")

    name = frontmatter.get("name") or filename.removesuffix(".md")
    if not re.match(r"^[a-z0-9_-]+$", name):
        raise ValueError(
            f"Agent '{filename}': invalid agy agent name '{name}' — must be "
            "lowercase letters, numbers, hyphens, underscores"
        )

    description = frontmatter.get("description")
    if not description:
        raise ValueError(f"Agent '{filename}': missing required field: description")

    raw_tools = frontmatter.get("tools", [])  # allow-fallback: an agent may declare no tools
    if isinstance(raw_tools, str):
        raw_tools = [t.strip() for t in raw_tools.split(",") if t.strip()]

    tool_names: list[str] = []
    seen: set[str] = set()
    for t in raw_tools:
        if not isinstance(t, str) or t.startswith("mcp__"):
            continue
        mapped = tool_map.get(t, t)
        if mapped and mapped not in seen:
            seen.add(mapped)
            tool_names.append(mapped)

    return {
        "name": name,
        "description": str(description).strip(),
        "hidden": bool(frontmatter.get("hidden", False)),  # allow-fallback: default visible
        "config": {
            "customAgent": {
                "systemPromptSections": [{"title": "Agent System Instructions", "content": body}],
                "toolNames": tool_names,
                "systemPromptConfig": {"includeSections": list(_AGY_INCLUDE_SECTIONS)},
            }
        },
    }
