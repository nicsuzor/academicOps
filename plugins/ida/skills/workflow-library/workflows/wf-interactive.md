---
title: Interactive in-session workflow
type: template
description: Workflow governing all in-session and interactive work -- with strictly one outer task created by the user-facing coordinator, delegation through the internal delegate, verification at all seams, and outer handover dump only.
tags: [workflow, interactive, in-session, delegation]
---

# Interactive In-Session Workflow

## Purpose and Scope

Applies to all in-session and interactive work. Governs task creation boundaries, subagent delegation, inter-agent verification, and session completion ceremonies.

## Applicability

- **Governs interactive sessions**: This workflow governs any interactive session communicating directly with the user.
- **Exemption for lookups and questions**: The requirement to create a task explicitly does not apply to pure lookup tasks or questions. The agent must handle pure lookups and questions directly without creating a task on the task graph and without executing `/dump`.

## Execution Structure

1. **Single outer task**:
   - Requiring strictly one outer task on the task graph.
   - The outer task is created solely by the agent that talks directly to the user (user-facing coordinator).
   - Downstream agents and subagents must never create additional tasks on the task graph for this work.

2. **Delegation pipeline**:
   - Middle steps are unspecified except that the user-facing coordinator delegates to an internal delegate first.
   - The internal delegate delegates through to the custodian, review supervisor, or dispatcher as appropriate for the work.
   - No subagent or internal delegate may create child or auxiliary tasks on the task graph.

3. **Seam verification**:
   - Handback and verification is required at all seams between agents.
   - Every inter-agent report and handback must carry an Argdown argument in the correct format per the `premise-check` standard.

4. **Outer handover and dump**:
   - Only the user-facing coordinator runs the handover `/dump` sequence upon completion of the outer task.
   - Subagents and internal delegates do not execute `/dump` or release tasks on the graph.
