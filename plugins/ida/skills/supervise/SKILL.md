---
name: supervise
description: Supervise a composite or complex task end-to-end inside a worker container -- compose workflows via /reify, coordinate subagents with incremental git checkpoints, deliver in-session artifacts and pull requests, and queue out-of-session follow-ups. Use for autonomous multi-stage supervision. Exclude for single atomic tasks already reified on the graph (use /pull).
---

# /supervise -- End-to-End Task Supervision

Supervise a repository-scoped composite task (`type: "task"`, never `type: "epic"`) to completion inside a container session. The lead executor (`james`) composes workflows onto a combined task body, coordinates subagent reviews and parallel fan-out, commits and pushes incrementally, delivers in-session outputs, and queues out-of-session follow-ups.

## 0. Immediate Claim & Live Persistence

1. **Claim**: Claim the assigned task via `pkb_claim_task`. If invoked on an untracked directive without a task ID, create a repository-scoped task via `/q` first, then claim it.
2. **Persist**: Update the PKB task record after each completed stage or subagent chunk so progress survives session pre-emption.

## 1. In-Session Workflow Assembly (`/reify`)

- **Fast-path**: If the task already carries `## Instructions` and `## Appendix: Sources`, or specifies `invoke /<skill>`, proceed directly to planning.
- **Compose**: Otherwise, run `/reify` in-session to resolve templates across the three-tier library onto the single task body, adapting multi-stage workflows to execute within the current session.

## 2. Plan & Dialectical Review

1. **Plan**: Record the execution plan on the PKB task. When altering agent behavior, evaluate lighter instruction or workflow options before proposing mechanical enforcement.
2. **Review**: Dispatch a proportionate parallel subagent review across strategic alignment, compliance, and qualitative excellence lenses. Append a null `argdown` block (`asks: none` / `[no claim]`) to claim-free briefs.
3. **Verify**: Check returned subagent arguments per `ida:premise-check` before acting on or relaying findings. Retire completed helpers and resolve blocking findings before implementation fan-out.

## 3. Calibrated Delegation & Incremental Checkpoints

1. **Calibrated fan-out**: Delegate disjoint chunks to subagents matched by capability tier (`flagship` for complex architecture and multi-constraint synthesis; `mid-tier` for general coordination; `fast` for focused edits, template updates, and index sync). Delegate heavy reading and investigation where proportionate, taking back short cited answers so the supervisor context holds briefs, summaries, and decisions. Instruct subagents to return their final `ida:premise-check` report on exit without duplicate mid-turn status messages.
2. **Incremental checkpoint invariant**: After every chunk of subagent work:
   - Verify handbacks via `ida:premise-check` and run formatters/linters on modified files.
   - Stage and commit modified files scrubbed of private identifiers, PKB task/note/session IDs, `Task:` trailers, personal names, and private hostnames (`data-boundaries`).
   - Run `git push` immediately to survive container pre-emption, and update the PKB task record.

## 4. In-Session Delivery & Out-of-Session Follow-Ups

1. **Verify & PR**: Run full test suites, linters, builds, and an independent final diff review in session. Open and ready one cohesive pull request against the base branch with scrubbed review receipts.
2. **Out-of-session follow-ups**: Deliver everything executable in session. Create a dependent follow-up task via `/q` (under the governing component or initiative parent with `needs` edges and zero leaf `serves` edges) only when work explicitly requires a different repository (one task per repo), a different time/external wait, or a separate external agent/session (such as channel delivery).

## 5. Handover (`/dump`)

Invoke `/dump` to record the `## Report` proof, `pr_url`, and `branch`. Release as `done` when all in-session deliverables and pull requests complete (and any out-of-session work is queued), or `partial` with blocking reasons if in-session work remains unfinished. Never hold a task in `partial` or mint follow-ups to verify user installation or deployment once shipped and reported.
