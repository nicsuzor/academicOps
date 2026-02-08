---
name: tool-gate-message
title: Tool Gate Block/Warn Message
category: template
description: |
  Unified message for tool gate block/warn.
  Replaces inline message building in gates.py.
  Variables:
    {mode} - "warn" or "block"
    {tool_name} - Name of the tool being blocked
    {tool_category} - Category of the tool (read_only, write, etc.)
    {missing_gates} - Comma-separated list of missing gates
    {gate_status} - Formatted gate status lines
    {next_instruction} - What the agent should do next
---

⚠️ **GATE BLOCKED ({mode})**

**Tool**: `{tool_name}` ({tool_category})
**Missing**: {missing_gates}

{gate_status}

**Next**: {next_instruction}
