#!/usr/bin/env python3
"""
Stop hook: Require /handover skill invocation before session end.

Blocks session until the /handover skill has been invoked.
The handover_gate.py PostToolUse hook sets the flag when skill is invoked.

Exit codes:
    0: Success (JSON output with decision field handles blocking)
"""
