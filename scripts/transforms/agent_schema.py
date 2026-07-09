import re

_PLUGIN_NAMESPACE_RE = re.compile(r"^plugin_[a-zA-Z0-9-]+_(.+)$")

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


def claude_mcp_to_gemini(tool_name: str) -> str:
    """Convert a Claude MCP tool name to Gemini format.

    Claude: mcp__plugin_aops-core_pkb__get_task  (or mcp__pkb__get_task)
    Gemini: mcp_pkb_get_task

    The double underscores are structural delimiters: mcp__<namespace>__<tool>.
    The namespace may include a plugin prefix (plugin_<name>_<server>) which
    must be stripped to get the bare server name that Gemini registers.
    """
    parts = tool_name.split("__", 2)
    if len(parts) == 3 and parts[0] == "mcp":
        namespace, tool = parts[1], parts[2]
        m = _PLUGIN_NAMESPACE_RE.match(namespace)
        server = m.group(1) if m else namespace
        return f"mcp_{server}_{tool}"
    return tool_name


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

    # Validate tools
    if "tools" in frontmatter:
        tools = frontmatter["tools"]
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]
            frontmatter["tools"] = tools
        elif not isinstance(tools, list):
            errors.append(
                f"Invalid tools type: {type(tools).__name__}, must be a list or comma-separated string"
            )
            tools = []

        GEMINI_BUILTIN_TOOLS = {
            "read_file",
            "write_file",
            "replace",
            "list_directory",
            "glob",
            "grep_search",
            "run_shell_command",
            "web_fetch",
            "google_web_search",
            "save_memory",
            "activate_skill",
            "ask_user",
            "enter_plan_mode",
            "complete_task",
            "write_todos",
            "update_topic",
        }

        for t in tools:
            if not isinstance(t, str):
                errors.append(f"Invalid tool type: {type(t).__name__}")
                continue
            if t not in GEMINI_BUILTIN_TOOLS and not t.startswith("mcp_"):
                errors.append(
                    f"Invalid tool name '{t}': must be a Gemini built-in or start with 'mcp_'"
                )
            if "__" in t:
                errors.append(
                    f"Invalid tool name '{t}': contains double underscores (Claude format)"
                )
            if "plugin_" in t:
                errors.append(f"Invalid tool name '{t}': contains Claude plugin namespace prefix")

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
