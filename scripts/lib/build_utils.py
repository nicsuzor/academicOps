import os
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def format_path_for_json(path: str) -> str:
    """Ensure path is absolute and normalized."""
    return str(Path(path).resolve())


def convert_mcp_server_to_gemini(
    name: str, config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Convert a single MCP server config from Claude to Gemini format."""
    server_type = config.get("type", "stdio")
    result: Dict[str, Any] = {}

    if server_type == "http":
        if "url" not in config:
            print(f"  ⚠️  {name}: HTTP server missing 'url', skipping", file=sys.stderr)
            return None
        result["url"] = config["url"]
        if "headers" in config:
            result["headers"] = config["headers"]

    elif server_type == "stdio":
        if "command" not in config:
            print(
                f"  ⚠️  {name}: stdio server missing 'command', skipping",
                file=sys.stderr,
            )
            return None
        result["command"] = config["command"]
        if "args" in config:
            result["args"] = config["args"]
        if "env" in config and config["env"]:
            result["env"] = config["env"]
    else:
        # Fallback: if it already looks like a gemini config (no type, has command/url)
        if "command" in config or "url" in config:
            return config
        print(
            f"  ⚠️  {name}: Unknown server type '{server_type}', skipping",
            file=sys.stderr,
        )
        return None

    return result


def convert_mcp_to_gemini(servers: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a dictionary of MCP servers to Gemini format."""
    gemini_servers = {}
    for name, config in servers.items():
        converted = convert_mcp_server_to_gemini(name, config)
        if converted:
            gemini_servers[name] = converted
    return gemini_servers


def convert_gemini_to_antigravity(servers: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Gemini MCP config to Antigravity format (url -> serverUrl)."""
    ag_servers = {}
    for name, config in servers.items():
        new_config = config.copy()
        if "url" in new_config:
            new_config["serverUrl"] = new_config.pop("url")
        ag_servers[name] = new_config
    return ag_servers


def safe_symlink(src: Path, dst: Path):
    """Create a symlink, removing the destination if it exists."""
    if dst.is_symlink() or dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()

    if not dst.parent.exists():
        dst.parent.mkdir(parents=True)

    os.symlink(src, dst)
    print(f"  Linked {src.name} -> {dst}")


def generate_gemini_hooks(
    claude_hooks: Dict[str, Any], aops_path: str, router_script_path: str
) -> Dict[str, Any]:
    """Generate Gemini hooks configuration from Claude hooks."""

    CLAUDE_TO_GEMINI = {
        "SessionStart": ["SessionStart"],
        "PreToolUse": ["BeforeTool"],
        "PostToolUse": ["AfterTool"],
        "UserPromptSubmit": ["BeforeAgent"],
        "Stop": ["SessionEnd", "AfterAgent"],
        "Notification": ["Notification"],
        "PreCompact": ["PreCompress"],
    }
    MATCHERS = {"SessionStart": "startup", "SessionEnd": "exit|logout"}

    gemini_hooks = {}

    # Ensure paths are absolute (converts /home/nic/src/... to /home/nic/src/...)
    # But router_script_path passed in should already be the dist path usually

    for c_event, g_events in CLAUDE_TO_GEMINI.items():
        if c_event in claude_hooks:
            # Extract timeout from the first hook definition in Claude config
            # Claude format: { "SessionStart": [{"hooks": [{"timeout": 5000}]}] } or similar deep nesting
            try:
                # Based on create_extension.py interrogation of structure
                timeout = (
                    claude_hooks[c_event][0].get("hooks", [{}])[0].get("timeout", 5000)
                )
            except (IndexError, KeyError, TypeError):
                timeout = 5000  # Default

            for g_event in g_events:
                matcher = MATCHERS.get(g_event, "*")
                if g_event not in gemini_hooks:
                    gemini_hooks[g_event] = []

                gemini_hooks[g_event].append(
                    {
                        "matcher": matcher,
                        "hooks": [
                            {
                                "name": "aops-router",
                                "type": "command",
                                "command": f"AOPS={aops_path} AOPS_SESSIONS={aops_path}/.gemini/sessions python3 {router_script_path} {g_event}",
                                "timeout": timeout,
                            }
                        ],
                    }
                )
    return gemini_hooks
