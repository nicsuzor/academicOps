import re

import yaml

_PLUGIN_NAMESPACE_RE = re.compile(r"^plugin_[a-zA-Z0-9-]+_(.+)$")


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


GEMINI_TOOL_NAME_MAP = {
    "Read": "read_file",
    "Write": "write_file",
    "Edit": "replace",
    "Glob": "glob",
    "Grep": "grep_search",
    "grep": "grep_search",
    "Bash": "run_shell_command",
    "bash": "run_shell_command",
    "Skill": "activate_skill",
    "Task": "activate_skill",
    "Agent": "activate_skill",
    "AskUserQuestion": "ask_user",
    "ExitPlanMode": "enter_plan_mode",
    "TodoWrite": "write_todos",
    "NotebookEdit": None,
    "WebFetch": "web_fetch",
    "WebSearch": "google_web_search",
    "browser_navigate": "navigate_page",
    "browser_snapshot": "take_snapshot",
    "browser_take_screenshot": "take_screenshot",
    "browser_click": "click",
    "browser_wait_for": "wait_for",
    "browser_evaluate": "evaluate_script",
    "browser_type": "type_text",
    "browser_resize": "resize_page",
}

CLAUDE_TOOL_NAME_MAP = {
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
    "navigate_page": "browser_navigate",
    "take_snapshot": "browser_snapshot",
    "take_screenshot": "browser_take_screenshot",
    "click": "browser_click",
    "wait_for": "browser_wait_for",
    "evaluate_script": "browser_evaluate",
    "type_text": "browser_type",
    "resize_page": "browser_resize",
    "browser_navigate": "browser_navigate",
    "browser_snapshot": "browser_snapshot",
    "browser_take_screenshot": "browser_take_screenshot",
    "browser_click": "browser_click",
    "browser_wait_for": "browser_wait_for",
    "browser_evaluate": "browser_evaluate",
    "browser_type": "browser_type",
    "browser_resize": "browser_resize",
}


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


def gemini_agent_schema(content: str, ctx: dict) -> str:
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content

    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return content

    if not frontmatter:
        return content

    original_tools = frontmatter.get("tools", [])
    if isinstance(original_tools, str):
        original_tools = [t.strip() for t in original_tools.split(",")]

    filtered_tools = []
    seen = set()
    for t in original_tools:
        tool_name = claude_mcp_to_gemini(t) if t.startswith("mcp__") else t
        mapped = GEMINI_TOOL_NAME_MAP.get(tool_name, tool_name)
        if mapped is not None and mapped not in seen:
            seen.add(mapped)
            filtered_tools.append(mapped)

    frontmatter["tools"] = filtered_tools
    frontmatter.pop("color", None)
    frontmatter = validate_gemini_agent_schema(frontmatter, ctx.get("filename", "agent"))
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    return f"---\n{new_frontmatter}---{parts[2]}"


def claude_agent_schema(content: str, ctx: dict) -> str:
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content

    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return content

    if not frontmatter:
        return content

    original_tools = frontmatter.get("tools", [])
    if isinstance(original_tools, str):
        original_tools = [t.strip() for t in original_tools.split(",")]

    transformed_tools = []
    for tool in original_tools:
        if tool.startswith("mcp__"):
            transformed_tools.append(tool)
        elif tool.startswith("mcp_"):
            parts_ = tool.split("_", 2)
            if len(parts_) == 3:
                transformed_tools.append(f"mcp__{parts_[1]}__{parts_[2]}")
            else:
                transformed_tools.append(tool)
        else:
            transformed_tools.append(CLAUDE_TOOL_NAME_MAP.get(tool, tool))

    frontmatter["tools"] = ", ".join(transformed_tools)
    new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    return f"---\n{new_frontmatter}---{parts[2]}"
