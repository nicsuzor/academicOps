---
title: Interactive in-session workflow
type: template
description: Workflow governing all in-session and interactive work -- with strictly one outer task placed and claimed on the PKB graph, delegation through the internal coordinator, verification at all seams, and outer handover dump only.
tags: [workflow, interactive, in-session, delegation]
---

# Interactive In-Session Workflow

## Purpose and Scope

Applies to all in-session and interactive work. Governs task creation boundaries, subagent delegation, inter-agent verification, and session completion ceremonies.

## Applicability

- **Governs interactive sessions**: This workflow governs any interactive session communicating directly with the user.
- **Exemption for lookups and questions**: The requirement to create a task explicitly does not apply to pure lookup tasks or questions. The agent must handle pure lookups and questions directly without creating a task on the task graph and without executing `/james:dump` (using lookup-only execution).

## Execution Structure

1. **Single outer task**:
   - Requiring strictly one outer task on the task graph for the interactive topic.
   - The outer task is placed and claimed on the PKB graph (via PKB MCP / `pauli`) on behalf of the interactive session before substantial work begins. The user-facing coordinator strictly delegates and verifies, creating no tasks directly.
   - When an interactive request transitions to asynchronous container execution, the coordinator places repo-scoped task(s) on the PKB graph and dispatches to containers running `/james:supervise` (container `/james:supervise` composes workflows inline in-session).
   - Downstream workers and subagents below the sub-coordinator must never create additional tasks on the task graph for this work.

2. **Delegation pipeline**:
   - Middle steps are unspecified except that the user-facing coordinator delegates to an internal delegate first.
   - The internal delegate delegates through to the custodian (`pauli`), review supervisor (`james`), or container dispatch as appropriate for the work. Dispatched containers run `/james:supervise` for repo-scoped epic tasks or `/james:pull` for plain leaf tasks.
   - No subagent or internal delegate may create child or auxiliary tasks on the task graph.

3. **Seam verification**:
   - Handback and verification is required at all seams between agents.
   - Every inter-agent report and handback must carry a parser-valid Argdown argument per `james:premise-check`.

4. **Outer handover and dump**:
   - Only the user-facing coordinator runs the handover `/james:dump` sequence upon completion of the outer task.
   - Subagents and internal delegates do not execute `/james:dump` or release tasks on the graph.

### Interactive Delegation to Sub-Coordinator

- The user-facing coordinator formulates a concise brief quoting `## Ask` verbatim with message ID.
- The coordinator asserts an effort claim stating the proportionate depth of work in natural language (e.g. "targeted one-file edit", "comprehensive multi-agent design", "lightweight inspection").
- When proportionate to task stakes, risk, and blast radius, the brief specifies closing steps: logic check (`james:premise-check`) first, then compliance (`rbg`) and quality/requirements satisfaction (`marsha`) reviews.
- The sub-coordinator evaluates the brief for effort calibration and ask fidelity; if ill-calibrated or containing unasked exclusions, the sub-coordinator returns the brief for rework.
- On acceptance, the sub-coordinator places or resumes the topic task on the PKB graph before substantial work (searching open and closed tasks to resume, reopen, or create the topic task), or handles pure lookups directly in-turn with zero task creation. When work transitions to asynchronous container execution, the sub-coordinator places repo-scoped task(s) on the PKB graph and dispatches containers running `/james:supervise` without pre-composing task workflows in the interactive session.
- If closing steps were specified, the sub-coordinator executes the reviews, resolves findings, and hands back the completed report with checked Argdown premises and `Relay:` lines.
- The user-facing coordinator performs a final look over the handback before responding to the user.
