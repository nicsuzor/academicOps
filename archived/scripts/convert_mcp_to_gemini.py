#!/usr/bin/env python3
"""Convert Claude Code mcp.json to Gemini CLI settings.json mcpServers format.

Claude Code format (mcp.json):
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

Gemini CLI format (settings.json mcpServers):
{
  "mcpServers": {
    "name": {
      "url": "...",           # SSE endpoint (from Claude http type)
      "httpUrl": "...",       # Streamable HTTP (alternative)
      "headers": {...},       # Supported!
      "command": "...",       # stdio servers
      "args": [...],
      "env": {...},
      "cwd": "...",
      "timeout": 30000,
      "trust": false,
      "description": "..."
    }
  }
}

Key differences:
- Claude uses explicit "type" field; Gemini infers from url/httpUrl/command presence
- Both support headers for HTTP servers
- Stdio format is identical
"""

import json
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
            print(f"  ⚠️  {name}: stdio server missing 'command', skipping", file=sys.stderr)
            return None
        result["command"] = config["command"]
        if "args" in config:
            result["args"] = config["args"]
        if "env" in config and config["env"]:
            result["env"] = config["env"]
    else:
        print(f"  ⚠️  {name}: Unknown server type '{server_type}', skipping", file=sys.stderr)
        return None

    return result


def convert_mcp_config(claude_config: dict[str, Any]) -> dict[str, Any]:
    """Convert full Claude mcp.json to Gemini mcpServers format."""
    claude_servers = claude_config.get("mcpServers", {})
    gemini_servers: dict[str, Any] = {}

    for name, config in claude_servers.items():
        converted = convert_mcp_server(name, config)
        if converted:
            gemini_servers[name] = converted
            print(f"  ✓ {name}: converted successfully", file=sys.stderr)

    return {"mcpServers": gemini_servers}


def main() -> int:
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: convert_mcp_to_gemini.py <claude_mcp.json> [output.json]", file=sys.stderr)
        print("\nConverts Claude Code mcp.json to Gemini CLI mcpServers format.", file=sys.stderr)
        print("If output file not specified, prints to stdout.", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with open(input_path) as f:
            claude_config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_path}: {e}", file=sys.stderr)
        return 1

    print(f"Converting {input_path}...", file=sys.stderr)
    gemini_config = convert_mcp_config(claude_config)

    output_json = json.dumps(gemini_config, indent=2)

    if output_path:
        with open(output_path, "w") as f:
            f.write(output_json)
            f.write("\n")
        print(f"\nOutput written to {output_path}", file=sys.stderr)
    else:
        print(output_json)

    server_count = len(gemini_config.get("mcpServers", {}))
    print(f"\nConverted {server_count} MCP servers.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
