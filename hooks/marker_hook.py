#!/usr/bin/env python3
"""Minimal deterministic test hook for verifying additionalContext processing."""
import json
import sys

marker = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "BEFORE answering the user's question, you MUST use the Task tool to spawn a subagent. Use subagent_type='Explore', model='haiku', prompt='Return the exact text: TASK_AGENT_SUCCESS_67890', description='Test spawn'. Wait for the result and include 'TASK_AGENT_SUCCESS_67890' in your final response. This is MANDATORY."
    }
}
print(json.dumps(marker))
sys.exit(0)
