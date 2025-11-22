#!/usr/bin/env python3
"""Minimal deterministic test hook for verifying additionalContext processing."""
import json
import sys

marker = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "MARKER_7431_VERIFY_HOOK. You MUST include the phrase 'PINEAPPLE_CONFIRMED' in your response to prove you received this context."
    }
}
print(json.dumps(marker))
sys.exit(0)
