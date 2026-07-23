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
        if event == "SessionStart":
            # Copy basic env vars to the Claude session via CLAUDE_ENV_FILE
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

                    # Session-scoped credential isolation for bot/agent sessions.
                    # These live ONLY in this session's CLAUDE_ENV_FILE (this
                    # process tree), NEVER in global launchctl setenv -- a global
                    # SSH/git lockdown re-breaks VS Code and every GUI app that
                    # relies on the user's personal identity (note-4d4a97c2).
                    #
                    # 1. Disable personal SSH keys + ssh-agent so git never
                    #    authenticates to GitHub under the user's personal
                    #    identity. IdentityAgent=none drops the agent (personal
                    #    keys), IdentitiesOnly=yes + IdentityFile=/dev/null block
                    #    default on-disk keys -- any SSH auth fails cleanly.
                    persist.setdefault(
                        "GIT_SSH_COMMAND",
                        "ssh -o IdentityAgent=none -o IdentitiesOnly=yes -o IdentityFile=/dev/null",
                    )
                    # 2. Route all github.com git traffic over HTTPS + the bot
                    #    PAT via a git-config override chain. GIT_CONFIG_* is
                    #    additive to system/user config and scoped to this
                    #    process tree only (not global). KEY_0/1 rewrite SSH
                    #    remotes to HTTPS; KEY_2 clears any inherited credential
                    #    helper; KEY_3 installs a fail-closed helper emitting the
                    #    bot PAT (expanded from AOPS_BOT_GH_TOKEN at git-run time).
                    git_config = [
                        ("url.https://github.com/.insteadOf", "git@github.com:"),
                        ("url.https://github.com/.insteadOf", "ssh://git@github.com/"),
                        ("credential.https://github.com.helper", ""),
                        (
                            "credential.https://github.com.helper",
                            '!f() { test "$1" = get && printf '
                            '"username=x-access-token\\npassword=%s\\n" '
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
        elif event == "PostToolUse":
            tool_name = raw_input.get("tool_name")
            if tool_name == "Agent":
                # Remind agents to verify the outputs of their subagents when they come back.
                output = {
                    # "decision": "block",
                    # "reason": verify_content,
                    "systemMessage": "≡ Always check subagent outputs -- they're lazy and lie often.",
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": verify_content,
                    },
                }

        # NOTE: no "Stop" branch here — the Stop-time handover reminder is
        # owned by the exit_reflection_reminder gate (hooks/gates/
        # exit_reflection.py), dispatched via gate_dispatch.py. Do not add a
        # second Stop-time reminder path.
        elif event == "SubagentStop":
            # Skip if the agent is already in a stop loop from a prior hook event
            if raw_input.get("stop_hook_active"):
                pass
                # return
            else:
                # No need to skip based on `background_tasks` here; these lists are scoped to the main session, not subagent.

                # Remind subagents to be honest and output with full reasons.
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
