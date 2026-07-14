#!/usr/bin/env python3
"""
Minimal Hook Router for aops-tools.
Injects ida-reminder.md and ida-hydrate.md for Claude Code and Antigravity.
"""

import argparse
import json
import os
import shlex
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
    verify_content = get_template("deliverable-verify-reminder.md")

    output = {}

    if client == "agy":
        if event == "PostInvocation":
            output = {
                "terminationBehavior": "force_continue",
                "injectSteps": [{"ephemeralMessage": reminder_content}],
            }
        elif event == "PreInvocation":
            output = {"injectSteps": [{"ephemeralMessage": hydrate_content}]}
    elif client == "claude":
        if event == "SessionStart":
            # Copy basic env vars to the Claude session via CLAUDE_ENV_FILE
            env_file = os.environ.get("CLAUDE_ENV_FILE")
            if env_file:
                basic_vars = [
                    "AOPS_SESSIONS",
                    "AOPS_BOT_GH_TOKEN",
                    "PKB_MCP_URL",
                    "PKB_MCP_TOOL_PREFIX"
                ]
                persist = {}
                session_id = raw_input.get("session_id") or raw_input.get("conversationId")
                if session_id:
                    persist["AOPS_SESSION_ID"] = session_id
                
                for var in basic_vars:
                    val = os.environ.get(var)
                    if val is not None:
                        persist[var] = val
                
                bot_token = os.environ.get("AOPS_BOT_GH_TOKEN")
                if bot_token:
                    persist.setdefault("GH_TOKEN", bot_token)
                    persist.setdefault("GITHUB_TOKEN", bot_token)
                
                try:
                    with open(env_file, "a") as f:
                        for key, value in persist.items():
                            f.write(f"export {key}={shlex.quote(value)}\n")
                except Exception as e:
                    print(f"WARNING: Failed to write to CLAUDE_ENV_FILE: {e}", file=sys.stderr)
        elif event == "Stop":
            if not raw_input.get("stop_hook_active"):
                output = {
                    "decision": "block",
                    "reason": reminder_content,
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": reminder_content,
                    },
                }
        elif event == "SubagentStop":
            if not raw_input.get("stop_hook_active"):
                output = {
                    "decision": "block",
                    "reason": verify_content,
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": verify_content,
                    },
                }
        elif event == "UserPromptSubmit":
            output = {
                "hookSpecificOutput": {"hookEventName": event, "additionalContext": hydrate_content}
            }

    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
