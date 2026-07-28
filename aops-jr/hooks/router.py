#!/usr/bin/env python3
"""
Face Discipline Hook Router for aops-jr.
Injects reminder context for interactive head (SubagentStop, UserPromptSubmit, PostToolUse, agy).
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Face discipline hook router for aops-jr")
    parser.add_argument("client", nargs="?", default="", help="client (e.g. agy or claude)")
    parser.add_argument("event", nargs="?", default="", help="event (e.g. PostInvocation, SubagentStop)")
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

    if not client:
        if event in ("Stop", "SubagentStop", "UserPromptSubmit", "PostToolUse"):
            client = "claude"
        elif event in ("PostInvocation", "PreInvocation"):
            client = "agy"

    plugin_root = Path(__file__).resolve().parent.parent
    repo_root = plugin_root.parent
    templates_dir = repo_root / "templates"
    if not templates_dir.exists():
        templates_dir = plugin_root / "templates"

    def get_template(name):
        path = templates_dir / name
        if path.exists():
            return path.read_text().strip()
        return f"<!-- {name} not found -->"

    handover_content = get_template("handover.md")
    hydrate_content = get_template("hydrate.md")
    verify_content = get_template("verify.md")
    honesty_content = get_template("honesty.md")

    output = {}

    if client == "agy":
        if event == "PostInvocation":
            output = {
                "terminationBehavior": "force_continue",
                "injectSteps": [{"ephemeralMessage": handover_content}],
            }
        elif event == "PreInvocation":
            output = {"injectSteps": [{"ephemeralMessage": hydrate_content}]}
    elif client == "claude":
        if event == "PostToolUse":
            tool_name = raw_input.get("tool_name")
            tool_input = raw_input.get("tool_input") or {}
            if tool_name == "Agent" and not (isinstance(tool_input, dict) and tool_input.get("run_in_background")):
                output = {
                    "systemMessage": "≡ Always check subagent outputs -- they're lazy and lie often.",
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": verify_content,
                    },
                }

        elif event == "SubagentStop":
            if not raw_input.get("stop_hook_active"):
                output = {
                    "systemMessage": f"≡ **Output honestly in the required format** (dbg: {raw_input.get('agent_id', 'no agent_id')}, {raw_input.get('agent_type', 'no agent_type')})",
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": honesty_content,
                    },
                }

        elif event == "UserPromptSubmit":
            output = {
                "systemMessage": f"≡ **Don't forget to hydrate.**",
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": hydrate_content,
                },
            }

    if output:
        debug_message = [
            f"    {k}: {v}"
            for k, v in raw_input.items()
            if k in ["agent_type", "agent_id", "tool_name", "background_tasks"]
        ]
        if background_tasks := raw_input.get("background_tasks"):
            debug_message.append(f"    background_tasks: {len(background_tasks)}")
        debug_message = "<-- hook debug. vars: " + "\n".join(debug_message) + "-->"
        output["systemMessage"] = "\n".join([debug_message, output.get("systemMessage", "")]).strip()
        print(json.dumps(output))


if __name__ == "__main__":
    main()
