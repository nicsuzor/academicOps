#!/usr/bin/env python3
"""
Stop hook: Require /handover skill invocation before session end.

Blocks session until the /handover skill has been invoked.
The handover_gate.py PostToolUse hook sets the flag when skill is invoked.

Exit codes:
    0: Success (JSON output with decision field handles blocking)
"""

import json
import sys
from typing import Any

from lib.hook_utils import get_session_id
from lib.session_state import is_handover_skill_invoked
