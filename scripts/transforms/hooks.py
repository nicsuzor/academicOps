import json

CLAUDE_TO_GEMINI_EVENTS = {
    "PreToolUse": "BeforeTool",
    "PostToolUse": "AfterTool",
    "UserPromptSubmit": "BeforeAgent",
    "Stop": ["SessionEnd", "AfterAgent"],
    "SessionStart": "SessionStart",
    "SessionEnd": "SessionEnd",
    "SubagentStart": "BeforeTool",
    "SubagentStop": "AfterTool",
    "PreCompact": "BeforeAgent",
    "Notification": "BeforeAgent",
    "BeforeTool": "BeforeTool",
    "AfterTool": "AfterTool",
    "BeforeAgent": "BeforeAgent",
    "AfterAgent": "AfterAgent",
}

VALID_GEMINI_EVENTS = (
    "SessionStart",
    "BeforeAgent",
    "AfterAgent",
    "BeforeTool",
    "AfterTool",
    "SessionEnd",
)

def gemini_hooks(content: str, ctx: dict) -> str:
    try:
        config = json.loads(content)
    except json.JSONDecodeError:
        return content

    if "hooks" not in config:
        return content

    src_hooks = config["hooks"]
    gemini_hooks = {}

    for claude_event, hook_list in src_hooks.items():
        if claude_event.endswith("-disabled"):
            continue

        target_events = CLAUDE_TO_GEMINI_EVENTS.get(claude_event, [claude_event])
        if isinstance(target_events, str):
            target_events = [target_events]

        for gemini_event in target_events:
            if gemini_event not in VALID_GEMINI_EVENTS:
                continue

            transformed_hooks = []
            for hook_entry in hook_list:
                new_entry = {}
                if "matcher" not in hook_entry:
                    new_entry["matcher"] = "startup" if gemini_event == "SessionStart" else "*"

                for key, value in hook_entry.items():
                    if key == "hooks":
                        new_hooks = []
                        for hook in value:
                            new_hook = dict(hook)
                            if "command" in new_hook:
                                cmd = new_hook["command"]
                                cmd = cmd.replace("${CLAUDE_PLUGIN_ROOT}", "${extensionPath}")
                                cmd = cmd.replace("router.py", "router.sh")
                                cmd = cmd.replace("--client claude", "--client gemini")
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

    return json.dumps({"hooks": gemini_hooks}, indent=2) + "\n"
