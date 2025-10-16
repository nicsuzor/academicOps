# Outlook MCP (omcp) Email Interaction Guide

## Overview

**CRITICAL**: The `omcp` MCP server is the ONLY supported way to interact with Outlook email. Old PowerShell scripts (`outlook-*.ps1`) are deprecated.

## Prerequisites

The omcp MCP server must be connected. If tools like `mcp__omcp__messages_search` are not available, the user may need to run `/mcp` to reconnect.

## Common Operations

### Searching Email

**Search by sender:**
```
mcp__omcp__messages_query_from(name="Dennis Redeker", limit=20)
```

**Search by subject:**
```
mcp__omcp__messages_query_subject_contains(term="DBR", limit=20)
```

**Combined search (person AND subject):**
```
mcp__omcp__messages_search(person="Dennis", subject="DBR", limit=20)
```

**Recent messages:**
```
mcp__omcp__messages_list_recent(limit=20)
```

### Advanced DASL Queries

For complex queries, use the `messages_query` tool with DASL (DAV Searching and Locating) syntax:

**Search by date range:**
```
mcp__omcp__messages_query(
  dasl='@SQL="urn:schemas:httpmail:datereceived" >= \'2025-10-01\' AND "urn:schemas:httpmail:datereceived" <= \'2025-10-09\'',
  limit=50
)
```

**Note**: Currently, omcp searches the Inbox by default. Searching Sent Items requires DASL queries or tool enhancements (see issue #80).

### Reading Messages

```
mcp__omcp__messages_get(entry_id="...")
```

## Limitations

- **Sent Items**: No convenience method yet; requires DASL or manual folder specification
- **Folder-specific search**: Limited support; see `mcp__omcp__help` for current capabilities

## See Also

- Issue #80: Email interaction migration from PowerShell to omcp
- `mcp__omcp__help` tool for full DASL query guide
