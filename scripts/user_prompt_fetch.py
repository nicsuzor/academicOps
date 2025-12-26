#!/usr/bin/env python3
"""
Fetch user prompts from Cloudflare worker endpoint.

Usage:
    uv run python scripts/user_prompt_fetch.py [--limit N] [--json] [--hostname FILTER]

Requires PROMPT_LOG_API_KEY environment variable.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def fetch_prompts() -> list[dict]:
    """
    Fetch prompts from Cloudflare worker endpoint.

    Returns:
        List of prompt objects with key, timestamp, content fields.

    Raises:
        RuntimeError: If API key missing or request fails.
    """
    token = os.environ.get("PROMPT_LOG_API_KEY")
    if not token:
        raise RuntimeError("PROMPT_LOG_API_KEY not set")

    curl_command = [
        "curl",
        "-sf",
        "-H", f"Authorization: Bearer {token}",
        "https://prompt-logs.nicsuzor.workers.dev/read",
    ]

    result = subprocess.run(
        curl_command,
        capture_output=True,
        timeout=10,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Fetch failed: {result.stderr.decode()}")

    return json.loads(result.stdout.decode())


def parse_prompt(entry: dict) -> dict:
    """Parse a prompt entry, extracting nested JSON content if present."""
    content = entry.get("content", "")
    timestamp_ms = int(entry.get("timestamp", "0"))

    # Try to parse content as JSON
    try:
        data = json.loads(content)
        return {
            "timestamp": data.get("timestamp", ""),
            "hostname": data.get("hostname", "unknown"),
            "project": data.get("project", "unknown"),
            "session_id": data.get("session_id", ""),
            "prompt": data.get("prompt", content),
            "cwd": data.get("cwd", ""),
        }
    except (json.JSONDecodeError, TypeError):
        # Plain text content
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return {
            "timestamp": dt.isoformat(),
            "hostname": "unknown",
            "project": "unknown",
            "session_id": "",
            "prompt": content,
            "cwd": "",
        }


def main():
    parser = argparse.ArgumentParser(description="Fetch prompts from Cloudflare")
    parser.add_argument("--limit", "-n", type=int, default=20, help="Number of recent prompts (default: 20)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--hostname", "-H", help="Filter by hostname")
    parser.add_argument("--project", "-p", help="Filter by project")
    parser.add_argument("--all", "-a", action="store_true", help="Show all prompts")
    args = parser.parse_args()

    try:
        raw_prompts = fetch_prompts()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse all prompts
    prompts = [parse_prompt(p) for p in raw_prompts]

    # Apply filters
    if args.hostname:
        prompts = [p for p in prompts if args.hostname.lower() in p["hostname"].lower()]
    if args.project:
        prompts = [p for p in prompts if args.project.lower() in p["project"].lower()]

    # Limit results (most recent)
    if not args.all:
        prompts = prompts[-args.limit:]

    # Output
    if args.json:
        print(json.dumps(prompts, indent=2))
    else:
        print(f"Total: {len(raw_prompts)} prompts | Showing: {len(prompts)}\n")
        for p in prompts:
            ts = p["timestamp"][:19] if p["timestamp"] else "N/A"
            host = p["hostname"][:12]
            proj = p["project"][:12]
            sess = p["session_id"][:8] if p["session_id"] else "--------"
            prompt = p["prompt"][:50].replace("\n", " ")
            print(f"{ts} | {host:12} | {proj:12} | {sess} | {prompt}...")


if __name__ == "__main__":
    main()
