# MCP Server Scope

All MCP servers are registered at **project-local scope** only, via `.claude/settings.json` in each repo.
Nothing is registered at user-global scope (`~/.claude.json` / `~/.claude/settings.json`).

PKB and framework tools come via the `aops-core` plugin — no additional MCP registration needed.

## Available Servers

### zot — Zotero

```json
{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "fastmcp",
    "run",
    "http://services-new.stoat-musical.ts.net:8024/mcp"
  ]
}
```

**Use in:** academic writing repos, literature review projects.

### osb — Oversight Board

```json
{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "fastmcp",
    "run",
    "http://services-new.stoat-musical.ts.net:8025/mcp"
  ]
}
```

**Use in:** legal/policy research repos, OSB case analysis.

### outlook / omcp — Outlook Email & Calendar

```json
{
  "type": "stdio",
  "command": "uvx",
  "args": ["fastmcp", "run", "http://nicwin.stoat-musical.ts.net:8023/mcp"]
}
```

**Use in:** email/admin workflow repos.
Note: `omcp` and `outlook` point to the same endpoint — use one name only.

### hass — Home Assistant

```json
{
  "type": "http",
  "url": "http://camus.stoat-musical.ts.net:8086/mcp"
}
```

**Use in:** home automation repos only.

### context7 — Library Documentation

Available as the `context7@claude-plugins-official` plugin — no MCP entry needed.
Add as explicit MCP only if the plugin is not enabled in that project.

### playwright — Browser Automation

Available as the `playwright@claude-plugins-official` plugin — no MCP entry needed.
Add as explicit MCP only if the plugin is not enabled in that project.

## Example Project Settings

```json
{
  "mcpServers": {
    "zot": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "fastmcp",
        "run",
        "http://services-new.stoat-musical.ts.net:8024/mcp"
      ]
    },
    "osb": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "fastmcp",
        "run",
        "http://services-new.stoat-musical.ts.net:8025/mcp"
      ]
    }
  }
}
```
