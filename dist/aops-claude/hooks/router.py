#!/usr/bin/env python3
"""
Minimal Hook Router for aops-extras.
Injects ida-reminder.md and ida-hydrate.md for Claude Code and Antigravity.
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Minimal hook router")
    parser.add_argument("client", nargs="?", default="", help="client (e.g. agy or claude)")
    parser.add_argument("event", nargs="?", default="", help="event (e.g. PostInvocation, Stop)")
    args = parser.parse_args()

    client = args.client
    event = args.event

    raw_input = {}
    if not sys.stdin.isatty():
        try:
            raw_input = json.load(sys.stdin)
        except json.JSONDecodeError:
            pass

    if not event:
        event = raw_input.get("hook_event_name", "")

    # Identify client based on event if still missing (fallback)
    if not client:
        if event in ("Stop", "SubagentStop", "UserPromptSubmit"):
            client = "claude"
        elif event in ("PostInvocation", "PreInvocation"):
            client = "agy"

    plugin_root = Path(__file__).resolve().parent.parent
    templates_dir = plugin_root / "templates"

    def get_template(name):
        path = templates_dir / name
        if path.exists():
            return path.read_text().strip()
        return f"<!-- {name} not found -->"

    reminder_content = get_template("ida-reminder.md")
    hydrate_content = get_template("ida-hydrate.md")

    output = {}

    if client == "agy":
        if event == "PostInvocation":
            output = {
                "terminationBehavior": "force_continue",
                "injectSteps": [
                    {
                        "ephemeralMessage": reminder_content
                    }
                ]
            }
        elif event == "PreInvocation":
            output = {
                "injectSteps": [
                    {
                        "ephemeralMessage": hydrate_content
                    }
                ]
            }
    elif client == "claude":
        if event in ("Stop", "SubagentStop"):
            output = {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": reminder_content
                }
            }
        elif event == "UserPromptSubmit":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": hydrate_content
                }
            }

    if output:
        print(json.dumps(output))

if __name__ == "__main__":
    main()
