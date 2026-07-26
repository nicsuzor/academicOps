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

from gates.event import normalize
from gates.require_aops_bot_gh_token import require_aops_bot_gh_token


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
    elif event == "PreToolUse" or (client in ("claude", "agy") and event == "PreToolUse"):
        tool_name = raw_input.get("tool_name") or raw_input.get("toolName")
        interactive_tools = {"ask_question", "AskFollowupQuestion", "ask_followup_question", "Question"}
        is_headless = (
            not sys.stdin.isatty()
            or os.environ.get("NONINTERACTIVE") == "1"
            or os.environ.get("CI") == "1"
            or os.environ.get("AOPS_POLECAT_CONTAINER") == "1"
            or os.environ.get("CLAUDE_CODE_NON_INTERACTIVE") == "1"
        )
        deny_reason = None
        if tool_name in interactive_tools and is_headless:
            deny_reason = (
                "Interactive prompt ('ask_question') is forbidden in a headless / "
                "non-interactive context. Proceed automatically using fallback logic."
            )
        else:
            # Structural prevention (stays in core, per
            # specs/packaging/v0.5-modular-topology.md Finding 3): fail-closed
            # credential isolation. SessionStart above only rewrites git/gh
            # credentials `if bot_token:` — when AOPS_BOT_GH_TOKEN is unset that
            # branch is a silent no-op and ambient personal credentials stay
            # live. This gate is what makes the unset-token case fail closed
            # for the git/gh push commands it recognizes.
            verdict = require_aops_bot_gh_token(normalize(raw_input), {})
            if verdict is not None and verdict.outcome == "deny":
                deny_reason = verdict.inject_text

        if deny_reason:
            if client == "agy":
                output = {
                    "allowTool": False,
                    "denyReason": deny_reason,
                }
            else:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "permissionDecision": "deny",
                        "permissionDecisionReason": deny_reason,
                    }
                }

    if output:
        print(json.dumps(output))


if __name__ == "__main__":
    main()
