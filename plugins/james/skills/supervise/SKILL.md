---
name: supervise
description: Supervise an epic or complex task end-to-end within a container session -- assemble workflows via /reify, coordinate subagents with incremental git checkpoints, deliver in-session artifacts and pull requests, and queue out-of-session follow-ups. Use for autonomous epic execution, high-level task supervision, and multi-stage delivery. Exclude for single atomic tasks already reified on the graph (use pull).
---

# /supervise: End-to-End Epic Execution and Supervision

Supervise a repository-scoped epic task to completion inside a container session. The lead executor (`james`) runs this skill to reify workflows onto a combined task body, coordinate subagent reviews and fan-out, commit and push incrementally to prevent pre-emption loss, deliver in-session outputs, and wire follow-up tasks for out-of-session work.

## 0. Immediate Claim & Live PKB Persistence

1. **Claim the Task**: Claim the assigned task immediately via `pkb_claim_task`. If invoked on an untracked directive without a task ID, search existing work and create a repository-scoped tracking task via `/q`, then claim it.
2. **Continuous Persistence**: Update the PKB task record continuously after each completed stage or subagent chunk so progress and state survive session pre-emption.

## 1. In-Session Workflow Assembly (/reify)

Check the claimed task body before composing:

- **Fast-Path**: If the task already carries a composed workflow (`## Instructions` and `## Appendix: Sources`) or requires invoking a single skill (`invoke /<skill>`), skip redundant re-composition and proceed to planning.
- **Workflow Composition**: Otherwise, invoke `/reify` in-session to compose the workflow from the three-tier template library onto the single task body. Adapt multi-stage workflows to execute wholly within the current container session.

## 2. Plan & Subagent Dialectical Review

1. **Draft Execution Plan**: Draft the execution plan onto the PKB task record. When modifying agent behavior, run an enforcement-pyramid options pass against `specs/enforcement/enforcement.md` before adopting new constraints.
2. **Parallel Dialectical Review**: Dispatch a proportionate parallel subagent review across specialist lenses covering strategic direction and knowledge-base alignment, axiom and rule compliance, and qualitative output excellence. Append a null `argdown` block (`asks: none` / `[no claim]`) to claim-free briefs.
3. **Verify and Resolve**: Check returned subagent arguments per `ida:premise-check` before acting on or relaying findings. Cull completed helpers, resolve blocking findings, and apply uncontroversial fixes before implementation fan-out.

## 3. Model-Calibrated Subagent Fan-Out & Incremental Push Checkpoints

1. **Calibrated Delegation**: Fan out disjoint work chunks in parallel to appropriately sized subagent models:
   - **High-capability models**: Complex architecture, specifications, and multi-constraint synthesis.
   - **Fast lightweight models**: Focused file edits, template updates, mechanical sweeps, and index synchronization.
   - Provide complete inputs and target artifact paths in Turn-1 briefs, and instruct subagents to return their final `ida:premise-check` report cleanly on exit without duplicate mid-turn status messages.
2. **Incremental Checkpoint Invariant**: After every chunk of subagent work:
   - Verify handbacks via `ida:premise-check`.
   - Run formatting and linters on modified files.
   - Stage and commit modified files strictly scrubbed of private identifiers, PKB task/note/session IDs, `Task:` trailers, personal names, and private hostnames (`data-boundaries`).
   - Run `git push` immediately to the upstream branch so work survives container pre-emption.
   - Update the PKB task record with incremental progress.

## 4. In-Session Delivery & Out-of-Session Follow-Ups

1. **In-Session Verification**: Complete all in-session deliverables: full test suites, linters, builds, and an independent final diff review across strategic, compliance, and quality lenses.
2. **Pull Request**: Open and ready a single cohesive pull request against the base branch, attaching scrubbed review receipts.
3. **Out-of-Session Follow-Up Tasks**: Deliver everything executable in-session. Create and wire a repository-scoped follow-up task on the PKB graph (via `/q` placement with `serves` value-chain links and `needs` prerequisite edges) **only** when work explicitly requires:
   - A different repository (strictly one task per repository).
   - A different time or external wait condition.
   - A workflow-mandated separate external agent or session (such as closed-loop user-channel delivery).

## 5. Handover (/dump)

Invoke `/dump` to record the `## Report` argument proof, `pr_url`, and `branch`. Release the task as `done` when all in-session deliverables and pull requests are complete (and any out-of-session work is queued on follow-up tasks), or release as `partial` with blocking reasons if in-session deliverables remain unfinished.
