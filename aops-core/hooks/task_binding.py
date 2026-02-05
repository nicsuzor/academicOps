#!/usr/bin/env python3
"""
PostToolUse hook: Bind/unbind task to session when task MCP operations occur.

Enables session observability by automatically linking every session to a task
when task routing happens. The session state records current_task, allowing
queries like "what task was this session working on?"

Triggers (bind):
- After update_task MCP tool with status="in_progress" (task claimed for work)
Note: "active" status means ready/available, not being worked on - no binding.

Triggers (unbind):
- After complete_task MCP tool (task completed)
- After complete_tasks MCP tool (batch completion)

Exit codes:
    0: Success (always - this hook doesn't block)
"""

import json
import os
import sys
from typing import Any

# Re-export from hook_utils for backwards compatibility
from lib.hook_utils import get_task_id_from_result
