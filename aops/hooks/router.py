#!/usr/bin/env python3
"""
Credential Isolation SessionStart Hook Router for aops core.
Enforces structural prevention (SessionStart credential isolation) in core.
"""

import argparse
import json
import os
import shlex
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Core hook router for credential isolation")
    parser.add_argument("client", nargs="?", default="", help="client (e.g. agy or claude)")
    parser.add_argument("event", nargs="?", default="", help="event (e.g. SessionStart)")
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

    output = {}

    if event == "SessionStart" or (client == "claude" and event == "SessionStart"):
        env_file = os.environ.get("CLAUDE_ENV_FILE")
        if env_file:
            basic_vars = [
                "AOPS_SESSIONS",
                "AOPS_BOT_GH_TOKEN",
                "PKB_MCP_URL",
                "PKB_MCP_TOOL_PREFIX",
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

                persist.setdefault(
                    "GIT_SSH_COMMAND",
                    "ssh -o IdentityAgent=none -o IdentitiesOnly=yes -o IdentityFile=/dev/null",
                )
                git_config = [
                    ("url.https://github.com/.insteadOf", "git@github.com:"),
                    ("url.https://github.com/.insteadOf", "ssh://git@github.com/"),
                    ("credential.https://github.com.helper", ""),
                    (
                        "credential.https://github.com.helper",
                        '!f() { test "$1" = get && printf '
                        '"username=x-access-token\npassword=%s\n" '
                        '"${AOPS_BOT_GH_TOKEN}"; }; f',
                    ),
                ]
                persist["GIT_CONFIG_COUNT"] = str(len(git_config))
                for i, (cfg_key, cfg_val) in enumerate(git_config):
                    persist[f"GIT_CONFIG_KEY_{i}"] = cfg_key
                    persist[f"GIT_CONFIG_VALUE_{i}"] = cfg_val

            try:
                with open(env_file, "a") as f:
                    for key, value in persist.items():
                        f.write(f"export {key}={shlex.quote(value)}\n")
            except Exception as e:
                print(f"WARNING: Failed to write to CLAUDE_ENV_FILE: {e}", file=sys.stderr)
        output = {"systemMessage": "aOps plugin loaded."}
    elif event == "PostToolUse" or (client == "claude" and event == "PostToolUse"):
        tool_name = raw_input.get("tool_name")
        tool_input = raw_input.get("tool_input") or {}
        if tool_name == "Agent" and not (isinstance(tool_input, dict) and tool_input.get("run_in_background")):
            plugin_root = Path(__file__).resolve().parent.parent
            templates_dir = plugin_root / "templates"
            verify_file = templates_dir / "verify.md"
            verify_content = verify_file.read_text().strip() if verify_file.exists() else "<!-- verify.md not found -->"
            output = {
                "systemMessage": "≡ Always check subagent outputs -- they're lazy and lie often.",
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": verify_content,
                },
            }

    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
