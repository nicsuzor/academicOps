---
title: Interactive in-session workflow
type: template
description: Workflow governing interactive sessions -- splitting multi-part asks, non-blocking user turns, topic tracking, clean-room fresh research, delegation through internal delegates, seam verification, and outer handover only.
tags: [workflow, interactive, in-session, delegation]
---

# Interactive In-Session Workflow

## Purpose and Scope

Governs direct user-facing interactive sessions: ask tracking, message splitting, subagent delegation, inter-agent verification, and session completion. Pure read-only lookups, PKB/graph operations, and direct questions require no separate project task or `/dump`, while still being held on the session's topic tracking so nothing drops.

## Execution Structure

1. **Non-blocking user turns & conversational posture**:
   - The user-facing coordinator spends its own turns strictly talking with the user; channel upkeep (closing or sweeping threads, routine file maintenance) runs in a background subagent, and user conversation never blocks waiting on background reports.
   - Scope ambiguous requests to the current session unless told otherwise; ask a thread or session holder for missing links rather than claiming nonexistence; challenge dubious agent answers rather than smoothing them over.
   - While the user explains context or thinks aloud, capture durable facts without interrupting, concluding prematurely, or repeating unanswered questions; follow the user when topics shift.
2. **Hold every ask by topic**:
   - Track every user ask on arrival (including in-turn questions and lookups) on the coordinator's harness todo list (resolved only once the result reaches the user) and as a checklist item on a one-level-up topic task on the graph (joining an open topic that serves the same larger problem before starting a new one).
   - For substantial, qualitatively important asks (judged on substance, not length), send the user's verbatim words to `pauli` for today's daily note as backup.
   - Maintain at most one outer project task on the graph for substantial interactive work, placed and claimed via `/q` by the internal sub-coordinator; when transitioning to asynchronous polecat workers, place repo-scoped tasks via `/q` and hand them off to `sara` (fire-and-forget `/ida:supervise` or `/ida:pull` without pre-dispatch `/reify`). Downstream workers and subagents never mint extra tasks for the session's work.
3. **Split multi-part messages & route cleanly**:
   - Before briefing anyone, split multi-part user messages into discrete parts (decisions to record, lookups, outside-world research, discussion, execution). Each brief carries only its own verbatim part and message ID; omit parts routed elsewhere rather than summarizing them across briefs.
   - Pre-creation overlap checks route directly to `pauli` before minting a task via `/q`.
   - Internal delegates route PKB/planning to `pauli`, in-session execution exclusively to `james`, and isolated polecat dispatch exclusively to `sara`. Default subagent invocations to the `fast` tier, escalating only when complexity warrants.
   - **Clean-room `fresh-research`**: For outside-world fact-finding (what tools, methods, or external practices exist), brief a fresh web-only agent with the user's verbatim question and message ID alone -- passing zero PKB notes, repository state, or prior reports so existing assumptions do not bias findings. Separate any follow-on judgment about our own setup into a distinct discussion step worked from the checked research.
4. **Seam verification**:
   - Every inter-agent report and handback uses clean Argdown prose only and undergoes face-of-record compliance review at the seam per `premise-check` (zero _de novo_ fact-checking); any result drawing `REVISE` during review must be revised and re-reviewed before handback.
5. **Outer handover**:
   - Only the user-facing coordinator runs `/dump` upon completing the outer task; subagents and internal delegates never execute `/dump` or release graph tasks.

## Interactive Delegation Brief

- The user-facing coordinator sends a concise brief quoting `## Ask` verbatim with message ID and asserting a natural-language effort claim stating proportionate depth (e.g., "targeted one-file edit", "comprehensive multi-agent design").
- When warranted by stakes and blast radius, the brief specifies closing steps: logic verification (`premise-check`) first, then compliance and quality/requirements satisfaction reviews.
- The internal sub-coordinator checks effort calibration and ask fidelity, returning miscalibrated or distorted briefs for rework.
- On acceptance, the sub-coordinator runs `/q` before substantial work (or routes read-only/PKB queries through `wf-lookup`), delegates in-session work to `james`, or queues and hands off async polecat work to `sara`.
- When closing reviews apply, the sub-coordinator executes them and resolves findings; any result drawing `REVISE` must be revised and re-reviewed until it passes before handback, after which the sub-coordinator hands back solely in clean Argdown prose carrying checked conclusions (with qualifiers) and verified child verdict references per `premise-check` for the user-facing coordinator's final review before responding to the user.
