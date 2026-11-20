---
title: Interactive in-session workflow
type: template
description: Workflow governing interactive sessions -- one outer task placed and claimed via /q by the internal sub-coordinator, delegation through internal delegates, seam verification, and outer handover only.
tags: [workflow, interactive, in-session, delegation]
---

# Interactive In-Session Workflow

## Purpose and Scope

Governs direct user-facing interactive sessions: task creation boundaries, subagent delegation, inter-agent verification, and session completion. Pure read-only lookups, PKB/graph operations, and direct questions are exempt and execute directly without creating a task or running `/dump`.

## Execution Structure

1. **Single outer task**:
   - Maintain at most one outer task on the task graph for the interactive topic, placed and claimed via `/q` by the internal sub-coordinator before substantial work begins. The user-facing coordinator strictly delegates and verifies without creating tasks directly.
   - When transitioning to asynchronous worker containers, the internal sub-coordinator places repo-scoped tasks via `/q` and dispatches via `/dispatch` to `/supervise` without pre-dispatch `/reify` (containers run `/reify` in-session).
   - Downstream workers and subagents never create additional tasks on the task graph for the session's work.
2. **Delegation pipeline**:
   - The user-facing coordinator delegates first to an internal delegate.
   - Pre-creation overlap checks route directly to the PKB custodian before an outer task is minted via `/q`.
   - Internal delegates route work to the PKB custodian, review coordinator, or dispatcher as needed (`/supervise` for repo-scoped composite tasks; `/pull` for plain leaf tasks).
3. **Seam verification**:
   - Every inter-agent report and handback uses clean Argdown prose only and undergoes face-of-record compliance review at the seam per `premise-check` (zero _de novo_ fact-checking); any result drawing `REVISE` during review must be revised and re-reviewed before handback.
4. **Outer handover**:
   - Only the user-facing coordinator runs `/dump` upon completing the outer task; subagents and internal delegates never execute `/dump` or release graph tasks.

## Interactive Delegation Brief

- The user-facing coordinator sends a concise brief quoting `## Ask` verbatim with message ID and asserting a natural-language effort claim stating proportionate depth (e.g., "targeted one-file edit", "comprehensive multi-agent design").
- When warranted by stakes and blast radius, the brief specifies closing steps: logic verification (`premise-check`) first, then compliance and quality/requirements satisfaction reviews.
- The internal sub-coordinator checks effort calibration and ask fidelity, returning miscalibrated or distorted briefs for rework.
- On acceptance, the sub-coordinator runs `/q` before substantial work (or routes read-only/PKB queries through the direct lookup path with zero task creation), or queues and dispatches async container work via `/q` and `/dispatch`.
- When closing reviews apply, the sub-coordinator executes them and resolves findings; any result drawing `REVISE` must be revised and re-reviewed until it passes before handback, after which the sub-coordinator hands back solely in clean Argdown prose carrying checked conclusions (with qualifiers) and verified child verdict references per `premise-check` for the user-facing coordinator's final review before responding to the user.
