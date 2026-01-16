#!/usr/bin/env python3
"""
PostToolUse hook: Sync closed bd issues with learnings to memory server.

When an agent closes a bd issue with a reason (learnings), this hook
automatically stores the issue content in the memory server for semantic search.

This strengthens the synthesis flow:
    bd observations → patterns emerge → remember skill → semantic docs → close issue
                                                                              ↓
                                                          (this hook) → memory server

Only issues with close_reason (documented learnings) are synced, keeping
the semantic index focused on valuable insights.

Exit codes:
    0: Success (continues execution)
    Non-zero: Hook error (logged, does not block)
"""

import json
import re
import subprocess
import sys
from typing import Any


def extract_issue_ids_from_command(command: str) -> list[str]:
    """Extract issue IDs from a bd close command.

    Args:
        command: Bash command string

    Returns:
        List of issue IDs found in the command
    """
    # Match patterns like: bd close ns-abc, bd close ns-abc ns-def
    # Also handles: bd close ns-abc --reason "..."
    if "bd close" not in command and "bd close" not in command:
        return []

    # Extract the command portion after "bd close"
    match = re.search(r"bd\s+close\s+(.+?)(?:--|$)", command)
    if not match:
        # Try without flags - just capture issue IDs
        match = re.search(r"bd\s+close\s+([\w-]+(?:\s+[\w-]+)*)", command)

    if not match:
        return []

    # Split on whitespace and filter to valid issue ID patterns
    potential_ids = match.group(1).strip().split()
    # Issue IDs are typically like: ns-abc, aops-1234, etc.
    issue_ids = [id for id in potential_ids if re.match(r"^[\w]+-[\w]+$", id)]

    return issue_ids


def fetch_issue_details(issue_id: str) -> dict[str, Any] | None:
    """Fetch issue details using bd show.

    Args:
        issue_id: The issue ID to fetch

    Returns:
        Issue details dict, or None if fetch fails
    """
    try:
        result = subprocess.run(
            ["bd", "show", issue_id, "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return None

        # Parse JSON output - bd show returns a list with one item
        data = json.loads(result.stdout)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def format_memory_content(issue: dict[str, Any]) -> str:
    """Format issue data for memory storage.

    Creates a searchable representation focusing on learnings.

    Args:
        issue: Issue details dict

    Returns:
        Formatted content string for memory storage
    """
    parts = []

    # Title is always included
    title = issue.get("title", "Untitled")
    parts.append(f"# {title}")

    # Issue type and priority for context
    issue_type = issue.get("issue_type", "task")
    priority = issue.get("priority", "P2")
    parts.append(f"\nType: {issue_type} | Priority: P{priority}")

    # Description if present
    description = issue.get("description", "")
    if description:
        parts.append(f"\n## Description\n{description}")

    # The key learning - close_reason
    close_reason = issue.get("close_reason", "")
    if close_reason:
        parts.append(f"\n## Learning/Outcome\n{close_reason}")

    # Closed date for temporal context
    closed_at = issue.get("closed_at", "")
    if closed_at:
        # Extract just the date portion
        date_part = closed_at.split("T")[0] if "T" in closed_at else closed_at
        parts.append(f"\nClosed: {date_part}")

    return "\n".join(parts)


def store_to_memory(content: str, issue: dict[str, Any]) -> bool:
    """Store content to memory server via HTTP MCP API.

    Calls the memory MCP server directly via HTTP JSON-RPC.

    Args:
        content: Formatted content to store
        issue: Original issue for metadata

    Returns:
        True if storage succeeded, False otherwise
    """
    import os
    import urllib.request
    import urllib.error

    # Memory server configuration from aops-core/.mcp.json
    memory_url = "http://services.stoat-musical.ts.net:8026/mcp"
    auth_token = os.environ.get(
        "MEMORY_MCP_TOKEN",
        "07f203bcc6fbe9a410d9850336f8ff9c73a64c3d0e7802e3450ce39b139f5d67",
    )

    # Build tags
    tags = [
        "bd-issue",
        "closed",
        f"type:{issue.get('issue_type', 'task')}",
    ]

    # Add priority tag
    priority = issue.get("priority")
    if priority is not None:
        tags.append(f"priority:P{priority}")

    # Build metadata
    metadata = {
        "source": "bd-issue",
        "issue_id": issue.get("id", ""),
        "issue_type": issue.get("issue_type", "task"),
        "closed_at": issue.get("closed_at", ""),
    }

    # MCP JSON-RPC request format
    request_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "store_memory",
            "arguments": {
                "content": content,
                "tags": tags,
                "metadata": metadata,
            },
        },
    }

    try:
        req = urllib.request.Request(
            memory_url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            # Check for successful response
            return "error" not in result

    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return False


def main() -> None:
    """Main hook entry point."""
    # Read input from stdin
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        sys.exit(0)

    # Only process Bash tool calls
    tool_name = input_data.get("tool_name") or input_data.get("toolName", "")
    if tool_name != "Bash":
        print(json.dumps({}))
        sys.exit(0)

    # Get the command
    tool_input = input_data.get("tool_input") or input_data.get("toolInput", {})
    command = tool_input.get("command", "")

    # Check if this is a bd close command
    if "bd close" not in command:
        print(json.dumps({}))
        sys.exit(0)

    # Extract issue IDs
    issue_ids = extract_issue_ids_from_command(command)
    if not issue_ids:
        print(json.dumps({}))
        sys.exit(0)

    # Process each closed issue
    synced_count = 0
    skipped_count = 0

    for issue_id in issue_ids:
        issue = fetch_issue_details(issue_id)
        if not issue:
            continue

        # Only sync if there's a close_reason (documented learning)
        close_reason = issue.get("close_reason", "")
        if not close_reason:
            skipped_count += 1
            continue

        # Format and store
        content = format_memory_content(issue)
        if store_to_memory(content, issue):
            synced_count += 1

    # Build output message
    if synced_count > 0:
        msg = f"✓ Synced {synced_count} closed issue(s) with learnings to memory"
        if skipped_count > 0:
            msg += f" ({skipped_count} skipped - no close_reason)"
        output = {"systemMessage": msg}
    else:
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
