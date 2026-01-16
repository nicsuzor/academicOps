#!/usr/bin/env python3
"""
Backfill closed bd issues with learnings to memory server.

This script syncs all existing closed issues that have a close_reason
(documented learnings) to the memory server for semantic search.

Usage:
    uv run python scripts/backfill_closed_issues_to_memory.py [--dry-run]

Options:
    --dry-run    Show what would be synced without actually syncing
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Memory server configuration
MEMORY_URL = "http://services.stoat-musical.ts.net:8026/mcp"
AUTH_TOKEN = "07f203bcc6fbe9a410d9850336f8ff9c73a64c3d0e7802e3450ce39b139f5d67"


def get_closed_issues_with_learnings() -> list[dict[str, Any]]:
    """Fetch all closed issues that have a close_reason.

    Returns:
        List of issue dicts with close_reason
    """
    try:
        result = subprocess.run(
            ["bd", "list", "--status=closed", "--json", "--limit=1000"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            print(f"Error fetching issues: {result.stderr}", file=sys.stderr)
            return []

        issues = json.loads(result.stdout)

        # Filter to only those with close_reason
        return [i for i in issues if i.get("close_reason")]

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


def format_memory_content(issue: dict[str, Any]) -> str:
    """Format issue data for memory storage.

    Args:
        issue: Issue details dict

    Returns:
        Formatted content string for memory storage
    """
    parts = []

    title = issue.get("title", "Untitled")
    parts.append(f"# {title}")

    issue_type = issue.get("issue_type", "task")
    priority = issue.get("priority", "P2")
    parts.append(f"\nType: {issue_type} | Priority: P{priority}")

    description = issue.get("description", "")
    if description:
        parts.append(f"\n## Description\n{description}")

    close_reason = issue.get("close_reason", "")
    if close_reason:
        parts.append(f"\n## Learning/Outcome\n{close_reason}")

    closed_at = issue.get("closed_at", "")
    if closed_at:
        date_part = closed_at.split("T")[0] if "T" in closed_at else closed_at
        parts.append(f"\nClosed: {date_part}")

    return "\n".join(parts)


def store_to_memory(content: str, issue: dict[str, Any]) -> bool:
    """Store content to memory server via HTTP MCP API.

    Args:
        content: Formatted content to store
        issue: Original issue for metadata

    Returns:
        True if storage succeeded, False otherwise
    """
    tags = [
        "bd-issue",
        "closed",
        f"type:{issue.get('issue_type', 'task')}",
    ]

    priority = issue.get("priority")
    if priority is not None:
        tags.append(f"priority:P{priority}")

    metadata = {
        "source": "bd-issue",
        "issue_id": issue.get("id", ""),
        "issue_type": issue.get("issue_type", "task"),
        "closed_at": issue.get("closed_at", ""),
    }

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
            MEMORY_URL,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return "error" not in result

    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        print(f"  Error storing: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Backfill closed bd issues with learnings to memory server"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing",
    )
    args = parser.parse_args()

    print("Fetching closed issues with learnings...")
    issues = get_closed_issues_with_learnings()

    if not issues:
        print("No closed issues with learnings found.")
        return

    print(f"Found {len(issues)} closed issues with learnings.\n")

    synced = 0
    failed = 0

    for issue in issues:
        issue_id = issue.get("id", "unknown")
        title = issue.get("title", "Untitled")
        close_reason = issue.get("close_reason", "")[:80]

        print(f"[{issue_id}] {title}")
        print(f"  Learning: {close_reason}...")

        if args.dry_run:
            print("  → Would sync (dry-run)")
            synced += 1
            continue

        content = format_memory_content(issue)
        if store_to_memory(content, issue):
            print("  → Synced ✓")
            synced += 1
        else:
            print("  → Failed ✗")
            failed += 1

    print(f"\nResults: {synced} synced, {failed} failed")
    if args.dry_run:
        print("(Dry run - no actual changes made)")


if __name__ == "__main__":
    main()
