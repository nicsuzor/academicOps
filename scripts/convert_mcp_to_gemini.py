#!/usr/bin/env python3
"""Convert Claude Code MCP configs (plugin + global) to Gemini CLI format.

Claude Code uses plugin-based MCP configs (.mcp.json in each plugin) plus a global
config. Gemini CLI uses a single mcpServers block in ~/.gemini/settings.json.

This script:
1. Aggregates MCP configs from all plugin .mcp.json files
2. Merges with the global mcp.json (if provided)
3. Converts to Gemini format (removes 'type' field, keeps rest)
4. Outputs merged config suitable for Gemini's settings.json

Claude Code format:
{
  "mcpServers": {
    "name": {
      "type": "http",  # or "stdio"
      "url": "...",
      "headers": {...},
      "command": "...",
      "args": [...],
      "env": {...}
    }
  }
}

Gemini CLI format:
{
  "mcpServers": {
    "name": {
      "url": "...",           # SSE endpoint (from Claude http type)
      "headers": {...},       # Supported
      "command": "...",       # stdio servers
      "args": [...],
      "env": {...}
    }
  }
}

Usage:
    python convert_mcp_to_gemini.py <global_mcp.json> <output.json>
    python convert_mcp_to_gemini.py --plugins-only <output.json>
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


def convert_mcp_server(name: str, config: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a single MCP server config from Claude to Gemini format.

    Returns None if server cannot be converted (with warning printed).
    """
    server_type = config.get("type", "stdio")
    result: dict[str, Any] = {}

    if server_type == "http":
        # HTTP server - copy url and headers
        if "url" not in config:
            print(f"  ⚠️  {name}: HTTP server missing 'url', skipping", file=sys.stderr)
            return None
        result["url"] = config["url"]
        if "headers" in config:
            result["headers"] = config["headers"]

    elif server_type == "stdio":
        # Stdio server - copy command, args, env
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
        print(
            f"  ⚠️  {name}: Unknown server type '{server_type}', skipping",
            file=sys.stderr,
        )
        return None

    return result


def load_mcp_config(path: Path) -> dict[str, Any]:
    """Load MCP config from file, return empty dict if missing."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("mcpServers", {})
    except (json.JSONDecodeError, IOError) as e:
        print(f"  ⚠️  Failed to load {path}: {e}", file=sys.stderr)
        return {}


def aggregate_plugin_mcps(aops_path: Path) -> dict[str, Any]:
    """Aggregate MCP configs from all aops-* plugin directories."""
    servers: dict[str, Any] = {}

    for plugin_dir in sorted(aops_path.glob("aops-*")):
        if not plugin_dir.is_dir():
            continue

        mcp_file = plugin_dir / ".mcp.json"
        if mcp_file.exists():
            plugin_servers = load_mcp_config(mcp_file)
            servers.update(plugin_servers)
            print(
                f"  ✓ Loaded {len(plugin_servers)} servers from {plugin_dir.name}",
                file=sys.stderr,
            )

    return servers


def convert_mcp_config(servers: dict[str, Any]) -> dict[str, Any]:
    """Convert all servers to Gemini format."""
    gemini_servers: dict[str, Any] = {}

    for name, config in servers.items():
        converted = convert_mcp_server(name, config)
        if converted:
            gemini_servers[name] = converted
            print(f"  ✓ {name}: converted", file=sys.stderr)

    return {"mcpServers": gemini_servers}


def main() -> int:
    """CLI entrypoint."""
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1

    # Determine AOPS path
    aops_path = Path(os.environ.get("AOPS", Path(__file__).parent.parent))

    if sys.argv[1] == "--plugins-only":
        output_path = Path(sys.argv[2])
        global_servers: dict[str, Any] = {}
        print("Aggregating plugin MCPs only...", file=sys.stderr)
    else:
        global_mcp_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])

        if not global_mcp_path.exists():
            print(
                f"Warning: Global MCP file not found: {global_mcp_path}",
                file=sys.stderr,
            )
            global_servers = {}
        else:
            print(f"Loading global MCP from {global_mcp_path}...", file=sys.stderr)
            global_servers = load_mcp_config(global_mcp_path)

    # Aggregate from plugins
    print(f"\nAggregating plugin MCPs from {aops_path}...", file=sys.stderr)
    plugin_servers = aggregate_plugin_mcps(aops_path)

    # Merge: plugins take precedence over global
    all_servers = {**global_servers, **plugin_servers}

    print(
        f"\nConverting {len(all_servers)} servers to Gemini format...", file=sys.stderr
    )
    gemini_config = convert_mcp_config(all_servers)

    # Output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(gemini_config, f, indent=2)
        f.write("\n")

    server_count = len(gemini_config.get("mcpServers", {}))
    print(f"\nConverted {server_count} MCP servers to {output_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
