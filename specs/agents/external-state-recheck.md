---
title: External State Verification and Recheck
status: ready
type: spec
tags: [knowledge-base, external-state, verification, github, custodian]
---

# External State Verification and Recheck

The knowledge base stores only the last-known state of tasks and external artifacts (such as GitHub pull requests, issues, and releases), which can advance between scheduled reconciliation runs. This feature serves the user during status inquiries, blocker assessments, and planning by ensuring that when a referenced external item has a reasonable likelihood of having moved since its task or note was last updated, the knowledge base custodian verifies its live state on GitHub via targeted read-only queries before reporting or acting on it, while leaving records untouched by default when nothing appears off and keeping systematic repository sweeps in scheduled maintenance workflows.

## User stories

### US-1 Accurate status and planning when external state may have moved

As a user asking for project status, release readiness, blocker assessments, or next-step planning, I want the system to verify the live state of referenced external GitHub items (pull requests, issues, releases) when there is a reasonable likelihood they have moved since the task or note was last updated, so that reports and recommendations reflect current reality rather than stale last-known records.

- **AC-1.1** Given a task record, note, or planning discussion referring to a specific external GitHub artifact (such as a pull request, issue, or release) that has a reasonable likelihood of having changed since the record was last updated, when the knowledge base custodian evaluates, relies upon, or reports on that state for a user request, then the custodian queries live GitHub state before reporting or acting upon it.
- **AC-1.2** Given an external artifact whose recorded state shows no indication or reasonable likelihood of having changed since last updated, when the custodian encounters or processes the record, then the custodian relies on the last-known recorded state and leaves the record unchanged without speculative re-verification.

### US-2 Responsive interactive sessions without duplicating scheduled sweeps

As a user interacting with the system during a live session, I want in-turn external state checks to remain targeted to the specific items under discussion while systematic repository-wide reconciliation stays in scheduled maintenance runs, so that interactive planning and curation stay responsive without duplicating routine background sweeps.

- **AC-2.1** Given normal interactive execution of planning, curation, or reporting tasks, when the custodian checks external state, then the custodian verifies only the specific external items material to the request and does not execute systematic, broad, or bulk sweeps across repositories or task sets.
- **AC-2.2** Given scheduled maintenance workflows (such as the daily reconciliation sweep), when those workflows run, then they systematically sweep and reconcile external state across repositories independently of the custodian's targeted in-turn verifications.

### US-3 Direct verification of live GitHub items within custodian role boundaries

As a user routing planning, status, or knowledge base questions to the custodian, I want the custodian to be able to inspect specific live GitHub items via read-only queries while keeping code edits, filesystem searches, and general shell execution out of its scope, so that questions touching live GitHub state are answered accurately without bouncing back undone or blurring the boundary between curation and implementation.

- **AC-3.1** Given a status check, planning task, or curation inquiry that requires current state for a specific GitHub pull request, issue, or release, when the custodian verifies that artifact, then the custodian executes targeted read-only GitHub CLI inspection commands (such as `gh pr view`, `gh release view`, or `gh issue view`) directly rather than returning the request undone.
- **AC-3.2** Given any request requiring local filesystem searches, repository source code inspection, file modifications, or general shell command execution, when the custodian operates, then those actions remain outside the custodian's scope and are routed to a repository-capable worker or handed back.

## Design

### Targeted Verification Contract

The knowledge base records last-known state for external events rather than continuously mirroring live external systems. To fulfill user requirements for accurate status and planning without turning every interaction into a full sweep, the custodian applies qualitative judgment when evaluating, reporting on, or making strategic decisions from records referencing external GitHub artifacts:

1. **Trigger Condition**: Verification is triggered by qualitative judgment when there is a reasonable likelihood that an external artifact's state has moved since the task or note was last updated (for example, pending pull request approvals, open release blockers, or in-flight issue resolutions).
2. **Default Posture**: When recorded state appears consistent and nothing indicates that external state has moved, the default is not to update records and to refrain from speculative re-checking.
3. **Verification Mechanism**: When verification is warranted, the custodian runs targeted read-only GitHub CLI queries (`gh pr view`, `gh release view`, `gh issue view`) to inspect live state before reporting or updating the record.

### Sweep Ownership Boundary

State reconciliation is partitioned between scheduled background sweeps and targeted in-turn checks:

1. **Scheduled Workflows Own Systematic Sweeps**: Routine, comprehensive sweeps across repositories and task queues are the primary responsibility of scheduled maintenance workflows (such as the daily note reconciliation workflow).
2. **Targeted In-Turn Checks Only**: The custodian does not duplicate scheduled sweeps or run broad, batch, or unsolicited scans of external repositories. Custodian checks are strictly single-item or request-scoped verifications motivated by an active status, planning, or curation need.

### Custodian Capability and Tool Boundary

To fulfill user requests that depend on live GitHub state while preserving the custodian's separation from repository implementation work:

1. **Read-Only GitHub Query Access**: The custodian is given `Bash(gh *)` runtime permission and instruction authority to run targeted read-only `gh` inspection commands when external state may have moved.
2. **Maintained Graph-Only Boundary for Local Artifacts**: The custodian remains restricted from searching local filesystems, inspecting or editing repository source code, running build pipelines, or executing general shell commands. Any request requiring local repository or filesystem work continues to be handed back or routed to a worker agent.

## Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, mechanisms to prevent stale external state reporting were evaluated across the enforcement pyramid from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Rejected.** Universal axioms (`Single Source of Truth`, `Honest Epistemics`) require stating current truth, but failed in practice because the custodian's agent definition explicitly prohibited shell and external inspection tools. |
| 2 | `instructions` (`imperative`) | **Adopted.** Refining instructions in `plugins/ida/agents/pauli.md` to authorize targeted, read-only `gh` CLI checks when external state has a reasonable likelihood of having moved, while preserving the prohibition on general shell execution and filesystem searches. This least-invasive one-step move resolves the contradiction without adding code or mechanical overhead. |
| 3 | `JIT injection` | **Evaluated.** Injecting reminders prior to reporting external status was considered. Unnecessary and invasive; qualitative judgment in the persona instructions is sufficient. |
| 4 | `structural` | **Evaluated.** `Bash(gh *)` is already granted in runtime permissions. Adding mechanical regex guards or wrapper tools would violate `no-over-engineering` and `judgment-non-delegable`. |
| 5 | `process` | **Evaluated.** Composite review workflows (`wf-strategic-fit`, `wf-dialectical-review`) provide post-hoc verification on PRs but do not prevent stale status reports during live interactive sessions. |
| 6 | `post-hoc` | **Evaluated.** Periodic reconciliation sweeps detect background drift, but do not provide fresh state at the moment an agent prepares a release report or decision brief. |

### Evidence for the Move

When asked for release status, the knowledge base custodian reported a release as blocked and waiting on user approval for a pull request based on knowledge base records written before the pull request was approved and merged. Because the custodian's instructions prohibited all shell and external inspection commands ("never searches the filesystem, repo, or shell for artifacts") and required returning any request needing information outside the graph undone -- even though runtime settings already granted `Bash(gh *)` -- the custodian could not verify live GitHub state before reporting the stale blocker to the user.

## Enforcement Map Extract

Per `specs/enforcement/enforcement-map.md`, every row in `specs/ENFORCEMENT-MAP.md` references strictly a universal axiom from `plugins/rbg/skills/axioms/`. The custodian persona instructions (`plugins/ida/agents/pauli.md`) are carried under the following universal axiom rows:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Single Source of Truth](../../plugins/rbg/skills/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact without duplication, retiring or repairing conflicting knowledge base content on sight. | instructions, structural, process | imperative, protection, required gate | `build/build.py`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/remember/SKILL.md`, `wf-reconcile.md` |
| [Axiom: Honest Epistemics (Don't Make Shit Up)](../../plugins/rbg/skills/axioms/honest-epistemics.md) -- State unknowns explicitly, tailor claims strictly to evidence, and verify external state likely to have moved before reporting. | instructions, JIT injection, structural, process | imperative, warning, block, required gate | `plugins/rbg/skills/axioms/honest-epistemics.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/skills/premise-check/SKILL.md` |
| [Axiom: Do One Thing](../../plugins/rbg/skills/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, then return without exceeding authority. | instructions, structural, process | imperative, scoped, required gate | `plugins/rbg/skills/axioms/do-one-thing.md`, `plugins/ida/agents/ida.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/agents/james.md`, `plugins/ida/agents/sara.md` (`build/tool_map.toml`), `plugins/ida/skills/pull/SKILL.md`, `wf-task-base.md` |
| [Axiom: Proportionate](../../plugins/rbg/skills/axioms/proportionate.md) -- Build the least mechanism that meets the request across its class, weighing risk by likelihood × consequence. | instructions, process | imperative, required gate | `plugins/rbg/skills/axioms/proportionate.md`, `plugins/ida/agents/pauli.md`, `plugins/ida/skills/q/SKILL.md`, `plugins/ida/skills/reify/SKILL.md`, `plugins/rbg/agents/rbg.md`, `wf-strategic-fit.md`, `wf-dialectical-review.md` |

## Outcome-Level Build Criteria

The Stage 2 build implementation must satisfy the following verifiable criteria:

- [ ] **BC-1 (Targeted External State Verification)**: The custodian uses qualitative judgment to double-check external state (pull requests, releases, issues) with a reasonable likelihood of having changed since last updated, before reporting on or relying on that state for user requests, while leaving records unchanged when nothing appears off (`plugins/ida/agents/pauli.md`).
- [ ] **BC-2 (Ownership Boundary with Scheduled Sweeps)**: Routine systematic sweeping of repositories and task sets remains the primary responsibility of scheduled reconciliation workflows (such as daily note sweeps); the custodian instructions explicitly prohibit duplicating routine sweeps (`plugins/ida/agents/pauli.md`).
- [ ] **BC-3 (Tool Permission Harmonization)**: The agent definition permits targeted, read-only `gh` CLI commands to inspect GitHub state, resolving previous "PKB graph only / never the shell" phrasing while maintaining strict prohibitions on general shell execution, source code edits, and local filesystem searching (`plugins/ida/agents/pauli.md` and `specs/ENFORCEMENT-MAP.md`).
