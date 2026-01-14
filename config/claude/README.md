# Global Claude Configuration

This directory contains global MCP server configurations that are not plugin-specific.

## MCP Servers in mcp.json

**gh** - GitHub Copilot MCP server (general development tool)

**zot** - Zotero reference management service (research tool, may move to aops-tools in future)

**osb** - OSB service (TBD - document purpose or remove if deprecated)

## Plugin-Specific MCP Servers

Framework MCP servers have been migrated to their respective plugins:

- **aops-core**: gemini, memory (see `aops-core/.mcp.json`)
- **aops-tools**: context7, outlook, playwright (see `aops-tools/.mcp.json`)

See `aops-core/specs/plugin-architecture.md` for the complete plugin component documentation.

## Removed Servers

**task_manager** - Removed (deprecated, implementation archived in `archived/skills/tasks/`)
