from .agent_schema import claude_mcp_to_gemini


def _translate_tool_calls(text: str, platform: str) -> str:
    """Translate abstract tool calls to platform-specific names."""
    # 1. Platform-specific mappings
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
        text = text.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")

        import re

        text = re.sub(
            r"mcp__[a-zA-Z0-9_-]+__[a-zA-Z0-9_-]*",
            lambda m: claude_mcp_to_gemini(m.group(0)),
            text,
        )

        text = text.replace("Task(subagent_type=", "activate_skill(name=")
        text = text.replace("Skill(skill=", "activate_skill(name=")
        text = text.replace("Task() tool", "activate_skill() tool")
        text = text.replace("`Task(`", "`activate_skill(`")
        text = text.replace("`Skill(`", "`activate_skill(`")

    return text


def translate_tool_calls_claude(content: str, ctx: dict) -> str:
    return _translate_tool_calls(content, "claude")


def translate_tool_calls_gemini(content: str, ctx: dict) -> str:
    return _translate_tool_calls(content, "gemini")
