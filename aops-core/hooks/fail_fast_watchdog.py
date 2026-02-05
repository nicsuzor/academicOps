#!/usr/bin/env python3
"""
PostToolUse hook: Fail-Fast Watchdog.

When a tool returns an error, reminds agent to report the error
and ask the user what to do - NOT investigate or fix infrastructure.

Implements AXIOMS #7-8 (Fail-Fast).

KNOWN LIMITATION: PostToolUse hooks don't fire for built-in tool errors
(Bash exit != 0, Read file-not-found, etc.). Claude Code bypasses PostToolUse
for these failures. However, this hook DOES work for MCP tools that return
errors in their response payload (e.g., missing config, API failures).

Exit codes:
    0: Success (always continues, may inject reminder)
"""

import sys
from pathlib import Path

# Add framework lib to path for template_loader
HOOK_DIR = Path(__file__).parent
AOPS_CORE_ROOT = HOOK_DIR.parent
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.template_loader import load_template

# Template path
FAIL_FAST_TEMPLATE = HOOK_DIR / "templates" / "fail-fast-reminder.md"

# Patterns that indicate a tool error
ERROR_INDICATORS = [
    "error",
    "Error",
    "ERROR",
    "failed",
    "Failed",
    "FAILED",
    "exception",
    "Exception",
    "not found",
    "Not found",
    "does not exist",
    "Does not exist",
    "Missing required",
    "missing required",
    "Permission denied",
    "permission denied",
    "timed out",
    "Timed out",
    "No such file",
    "cannot access",
    "Cannot access",
]


def load_fail_fast_reminder() -> str:
    """Load the fail-fast reminder message from template."""
    return load_template(FAIL_FAST_TEMPLATE)


def contains_error(text: str) -> bool:
    """Check if text contains error indicators."""
    if not text:
        return False
    return any(indicator in text for indicator in ERROR_INDICATORS)
