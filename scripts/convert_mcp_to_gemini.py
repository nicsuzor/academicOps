#!/usr/bin/env python3
"""
Convert Claude Code MCP configuration to Gemini CLI format.

Claude Code uses plugin-based MCP configs (.mcp.json in each plugin) plus a global
config. Gemini CLI uses a single mcpServers block in ~/.gemini/settings.json.

This script:
1. Aggregates MCP configs from all plugin .mcp.json files
2. Merges with the global mcp.json (if provided)
3. Converts to Gemini format (removes 'type' field, keeps rest)
4. Outputs merged config suitable for Gemini's settings.json

Usage:
    python convert_mcp_to_gemini.py <global_mcp.json> <output.json>
    python convert_mcp_to_gemini.py --plugins-only <output.json>
"""

import json
import os
import sys
from pathlib import Path


def convert_server_config(name: str, config: dict) -> dict | None:
    """Convert a single MCP server config from Claude to Gemini format."""
    result = {}

    # Handle HTTP-based servers
    if config.get("type") == "http":
        url = config.get("url", "")
        if url:
            result["url"] = url
        headers = config.get("headers", {})
        if headers:
            result["headers"] = headers
        return result

    # Handle stdio-based servers
    if "command" in config:
        result["command"] = config["command"]
    if "args" in config:
        result["args"] = config["args"]
    if "env" in config and config["env"]:
        result["env"] = config["env"]

    return result if result else None


def load_mcp_config(path: Path) -> dict:
    """Load MCP config from file, return empty dict if missing."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("mcpServers", {})
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load {path}: {e}", file=sys.stderr)
        return {}


def aggregate_plugin_mcps(aops_path: Path) -> dict:
    """Aggregate MCP configs from all aops-* plugin directories."""
    servers = {}

    for plugin_dir in aops_path.glob("aops-*"):
        if not plugin_dir.is_dir():
            continue

        mcp_file = plugin_dir / ".mcp.json"
        if mcp_file.exists():
            plugin_servers = load_mcp_config(mcp_file)
            servers.update(plugin_servers)
            print(f"  Loaded {len(plugin_servers)} servers from {plugin_dir.name}", file=sys.stderr)

    return servers


def convert_to_gemini(servers: dict) -> dict:
    """Convert all servers to Gemini format."""
    result = {}

    for name, config in servers.items():
        converted = convert_server_config(name, config)
        if converted:
            result[name] = converted

    return result


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    # Determine AOPS path
    aops_path = Path(os.environ.get("AOPS", Path(__file__).parent.parent))

    if sys.argv[1] == "--plugins-only":
        output_path = Path(sys.argv[2])
        global_servers = {}
    else:
        global_mcp_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
        global_servers = load_mcp_config(global_mcp_path)

    # Aggregate from plugins
    plugin_servers = aggregate_plugin_mcps(aops_path)

    # Merge: plugins take precedence over global
    all_servers = {**global_servers, **plugin_servers}

    # Convert to Gemini format
    gemini_servers = convert_to_gemini(all_servers)

    # Output
    output = {"mcpServers": gemini_servers}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Converted {len(gemini_servers)} MCP servers to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
