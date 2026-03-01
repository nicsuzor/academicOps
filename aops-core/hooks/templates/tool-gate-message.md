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

✕ **Gate Check ({mode})** - `{tool_name}`
The academicOps framework requires strict compliance with a quality assurance workflow, even for simple and minor tasks.

**Current status**:
{gate_status}

**Missing**: {missing_gates}

**To proceed**: {next_instruction}
