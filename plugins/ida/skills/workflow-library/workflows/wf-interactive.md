---
title: Interactive in-session workflow
type: template
description: Workflow governing all in-session and interactive work -- applicable only to Ida, with strictly one outer task created by Face Ida, delegation through Sub-Ida, verification at all seams, and outer handover dump only.
tags: [workflow, interactive, in-session, ida, delegation]
---

# Interactive In-Session Workflow

## Purpose and Scope

Applies to all in-session and interactive work. Governs task creation boundaries, subagent delegation, inter-agent verification, and session completion ceremonies.

## Applicability

- **Applicable only to Ida**: This workflow governs the user-facing session led by `ida`.
- **Exemption for lookups and questions**: The requirement to create a task explicitly does not apply to pure lookup tasks or questions. The agent must handle pure lookups and questions directly without creating a task on the task graph and without executing `/dump`.

## Execution Structure

1. **Single outer task**:
   - Requiring strictly one outer task on the task graph.
   - The outer task is created solely by the agent that talks directly to the user (Face Ida).
   - Downstream agents and subagents must never create additional tasks on the task graph for this work.

2. **Delegation pipeline**:
   - Middle steps are unspecified except that Face Ida must delegate to Sub-Ida first (`ida:ida`).
   - Sub-Ida delegates through to `pauli`, `james`, or `sara` as appropriate for the work.
   - No subagent (Sub-Ida, Pauli, James, or Sara) may create child or auxiliary tasks on the task graph.

3. **Seam verification**:
   - Handback and verification is required at all seams between agents.
   - Every inter-agent report and handback must carry an Argdown argument in the correct format per the `premise-check` standard.

4. **Outer handover and dump**:
   - Only Face Ida runs the handover `/dump` sequence upon completion of the outer task.
   - Subagents and internal delegates do not execute `/dump` or release tasks on the graph.
