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

⏸️ **Gate Check ({mode})** - `{tool_name}`

The framework tracks work through gates to help you:
- **Task binding**: Links work to a trackable task for progress visibility and handover
- **Critic review**: Gets a second opinion on your plan before execution
- **Custodiet**: Periodic scope check to catch drift early

**Current status**:
{gate_status}

**Missing**: {missing_gates}

**To proceed**: {next_instruction}

**Bypass**: User can prefix prompt with `.` for quick fixes that skip gates.

*Gates exist to help you succeed, not to block you. They catch scope drift, enable clean handovers, and make work visible.*
