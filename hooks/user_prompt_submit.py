#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code: Pure logging hook.

This hook logs user prompts to Cloudflare worker endpoint for analytics.
Returns noop ({}) to allow hook chain to continue.

Exit codes:
    0: Success (always continues, fire-and-forget)
"""

import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file

# Paths (absolute, fail-fast if missing)
HOOK_DIR = Path(__file__).parent
PROMPT_FILE = HOOK_DIR / "prompts" / "user-prompt-submit.md"


def log_to_cloudflare(prompt: str) -> None:
    """
    Log prompt to Cloudflare worker endpoint.

    Warns to stderr if API key is missing or request fails.

    Args:
        prompt: User prompt to log
    """
    # Warn if API key missing
    token = os.environ.get("PROMPT_LOG_API_KEY")
    if not token:
        print("WARNING: PROMPT_LOG_API_KEY not set, skipping prompt logging", file=sys.stderr)
        return

    try:
        # Get system information
        hostname = socket.gethostname()
        cwd = os.getcwd()
        project = Path(cwd).name

        # Build JSON payload
        payload = {
            "prompt": prompt,
            "hostname": hostname,
            "cwd": cwd,
            "project": project,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Construct curl command
        curl_command = [
            "curl",
            "-sf",  # Silent but fail on HTTP errors
            "-X", "POST",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            "https://prompt-logs.nicsuzor.workers.dev/write",
        ]

        # Run and check for errors
        result = subprocess.run(
            curl_command,
            capture_output=True,
            timeout=5,
            check=False,  # We handle errors manually below
        )
        if result.returncode != 0:
            print(f"WARNING: Cloudflare logging failed: {result.stderr.decode()}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("WARNING: Cloudflare logging timed out", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Cloudflare logging error: {e}", file=sys.stderr)


def load_prompt_from_markdown() -> str:
    """
    Load prompt content from markdown file.

    Returns:
        Prompt content as string (stripped of markdown formatting)

    Raises:
        FileNotFoundError: If prompt file doesn't exist (fail-fast, no defaults)
    """
    # Fail-fast: no defaults, no fallbacks
    if not PROMPT_FILE.exists():
        msg = (
            f"FATAL: Prompt file missing at {PROMPT_FILE}. "
            "UserPromptSubmit hook requires this file to exist. "
            "No defaults or fallbacks allowed (AXIOM #5: Fail-Fast)."
        )
        raise FileNotFoundError(msg)

    # Read markdown file
    content = PROMPT_FILE.read_text().strip()

    # Basic validation
    if not content:
        msg = f"FATAL: Prompt file at {PROMPT_FILE} is empty."
        raise ValueError(msg)

    # Remove markdown header if present (first line starting with #)
    lines = content.split("\n")
    if lines and lines[0].startswith("#"):
        # Skip header and any following blank lines
        content_lines = []
        skip_header = True
        for line in lines[1:]:
            if skip_header and line.strip() == "":
                continue
            skip_header = False
            content_lines.append(line)
        content = "\n".join(content_lines).strip()

    return content


def main():
    """Main hook entry point - pure logging hook (noop return)."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Log user prompt to Cloudflare (fire-and-forget)
    user_prompt = input_data.get("userMessage", "")
    if user_prompt:
        log_to_cloudflare(user_prompt)

    # Build output data (noop - no additional context)
    output_data: dict[str, Any] = {}

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output JSON (noop - allows hook chain to continue)
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
