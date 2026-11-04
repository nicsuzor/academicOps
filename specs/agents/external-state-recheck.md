---
title: External State Verification and Recheck
status: ready
type: spec
tags: [knowledge-base, external-state, verification, github, custodian]
---

# External State Verification and Recheck

Defines the protocol and tool authority under which the knowledge base custodian exercises qualitative judgment to verify external GitHub artifact state (pull requests, issues, releases) when there is a reasonable likelihood that external state has progressed since last recorded, while leaving records untouched when consistent and preserving scheduled workflows as the sole owners of systematic sweeps.

## User stories

### US-1 Targeted verification of mutable external state

As a knowledge base custodian, I want to verify external state via targeted read-only queries when there is a reasonable likelihood it has progressed since last updated, so that reported status and strategic guidance reflect current reality rather than stale local notes.

- **AC-1.1** Given a task record, note, or strategic deliberation referring to an external GitHub artifact (such as a pull request, issue, or release), when the custodian evaluates, relies upon, or reports on that state and there is a reasonable likelihood that external state has progressed since the record's last update, then the custodian queries current external state before reporting or acting upon it.
- **AC-1.2** Given an external artifact whose recorded state shows no indication or likelihood of having changed, when the custodian encounters or processes the record, then the custodian leaves the record unchanged and relies on existing state without speculative re-verification.

### US-2 Boundary preservation with scheduled routine sweeps

As a framework operator, I want routine and systematic reconciliation sweeps to remain strictly within scheduled sweep workflows, so that the knowledge base custodian does not duplicate systematic sweeps or incur unnecessary execution overhead during normal planning and curation.

- **AC-2.1** Given normal execution of planning, curation, or reporting tasks, when the custodian performs their duties, then the custodian does not execute systematic, broad, or bulk sweeps of external repositories or task sets.
- **AC-2.2** Given scheduled sweep workflows owned by periodic maintenance (such as the daily reconciliation workflow), when those workflows execute, then they systematically sweep and reconcile external state across repositories independently of the custodian's in-turn targeted verifications.

### US-3 Tool authority harmonization for read-only GitHub inspection

As a knowledge base custodian, I want explicit instruction authority to execute targeted read-only `gh` CLI commands, so that I can inspect external GitHub state when warranted without violating persona boundaries.

- **AC-3.1** Given access to the GitHub command-line interface (`gh`), when the custodian requires current external state for a pull request, issue, or release, then the custodian executes read-only inspection commands (such as `gh pr view`, `gh release view`, `gh issue view`) directly.
- **AC-3.2** Given the custodian's core role boundaries restricting general shell execution, code edits, and filesystem searches, when the custodian operates, then general shell execution, source code modifications, and repository artifact searches remain prohibited, resolving "PKB graph only" to permit targeted read-only GitHub inspection while keeping implementation work out of scope.

## Design

### Targeted Verification Contract

The custodian operates under the Single Source of Truth and Current State Only principles. When evaluating, reporting on, or making strategic decisions based on external artifacts:

1. **Trigger Condition**: Verification is triggered by qualitative judgment when there is a reasonable likelihood that external state has changed since last recorded (e.g., pending approvals, open release blockers, in-flight issue resolutions).
2. **Default Inaction**: When recorded state appears consistent and there is no indication that external state has moved, the default is to leave records untouched and refrain from speculative re-checking.
3. **Execution Mechanism**: The custodian uses targeted read-only GitHub queries (`gh pr view`, `gh release view`, `gh issue view`) to inspect current reality.

### Sweep Ownership Boundary

Routine reconciliation is divided between continuous maintenance and periodic sweeps:

1. **Periodic Sweeps Owned by Scheduled Workflows**: Comprehensive sweeps across repositories and task sets are owned exclusively by scheduled maintenance workflows (such as daily reconciliation steps).
2. **Non-Duplication by Custodian**: The custodian does not execute broad, batch, or unsolicited scans of external repositories. Custodian checks are strictly targeted, single-item verifications motivated by specific in-turn reporting or dependency needs.

### Tool Authority Harmonization

Deployment settings already grant the custodian `Bash(gh *)`. The persona definition's previous wording ("PKB graph only -- never searches the filesystem, repo, or shell for artifacts" and "A request that needs anything outside the PKB graph (repo, shell, filesystem artefacts) goes back undone") presented an instruction-level barrier. This specification resolves the wording:

1. **Explicit Permission**: Targeted read-only inspection of GitHub state via `gh` is authorized when external state may have moved.
2. **Maintained Prohibitions**: Prohibitions against searching local filesystems, editing source code, running build pipelines, or executing general shell commands remain fully in effect. Implementation tasks and code modifications continue to be rejected or routed to worker agents.

## Proportional Intervention Options Pass

In accordance with `specs/enforcement/enforcement.md`, mechanisms to address stale external state reporting were evaluated across the enforcement pyramid from least-invasive to most-invasive:

| Level | Mechanism Category | Evaluation and Disposition |
| :- | :- | :- |
| 1 | `doctrine only` | **Rejected.** Universal axioms (`Single Source of Truth`, `Current State Only`, `Honest Epistemics`) require stating current truth, but failed in practice because the custodian's agent definition explicitly prohibited shell and external inspection tools. |
| 2 | `instructions` (`imperative`) | **Adopted.** Refining instructions in `plugins/ida/agents/pauli.md` to authorize targeted, read-only `gh` CLI checks when external state is suspected of having moved, while preserving the prohibition on general shell execution and filesystem searches. This least-invasive one-step move resolves the contradiction without adding code or mechanical overhead. |
| 3 | `JIT injection` | **Evaluated.** Injecting reminders prior to reporting external status was considered. Unnecessary and invasive; qualitative judgment in the persona instructions is sufficient. |
| 4 | `structural` | **Evaluated.** `Bash(gh *)` is already granted in runtime permissions. Adding mechanical regex guards or wrapper tools would violate `no-over-engineering` and `judgment-non-delegable`. |
| 5 | `process` | **Evaluated.** Composite review workflows (`wf-strategic-fit`, `wf-review`) provide post-hoc verification on PRs but do not prevent stale status reports during live interactive sessions. |
| 6 | `post-hoc` | **Evaluated.** Periodic reconciliation sweeps detect background drift, but do not provide fresh state at the moment an agent prepares a release report or decision brief. |

### Evidence for the Move

On 2026-11-04, the knowledge base custodian reported a release as blocked and waiting on user approval for a pull request. In reality, the pull request had already been approved and merged earlier. The custodian's report was derived entirely from stale knowledge base records written before the merge; the custodian could not verify GitHub state because persona instructions stated "never searches the filesystem, repo, or shell for artifacts" and required requests needing anything outside the graph to go back undone, despite `Bash(gh *)` being available in runtime settings.

## Enforcement Map Coordinates

Per `specs/enforcement/enforcement-map.md § 3`, single-carrier persona instructions reside in `plugins/ida/agents/pauli.md` and are referenced in the `Detail` coordinates of existing governing rules in `specs/ENFORCEMENT-MAP.md`:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| [Axiom: Single Source of Truth](../plugins/rbg/skills/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact without duplication, retiring or repairing conflicting knowledge base content on sight. | instructions, structural, process | imperative, protection, required gate | `build/build.py:42-95`, `plugins/ida/skills/dump/SKILL.md`, `plugins/ida/agents/pauli.md:152-154`, `plugins/ida/skills/remember/SKILL.md:10-48`, `wf-reconcile.md:15-50` |
| [Project Rule: Current State Only](../.agents/rules/current-state-only.md) -- Deprecated files are deleted; instructions and code state current state only with no historical narratives. | instructions, process | imperative, required gate | `.agents/rules/current-state-only.md:1-20`, `plugins/ida/agents/pauli.md:46-47,152-154`, `plugins/rbg/agents/rbg.md:16-44`, `.github/PULL_REQUEST_TEMPLATE.md:1-40` |
| [Axiom: Do One Thing](../plugins/rbg/skills/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, then return without exceeding authority. | instructions, structural, process | imperative, scoped, required gate | `plugins/rbg/skills/axioms/do-one-thing.md:9-21`, `plugins/ida/agents/ida.md:28-34`, `plugins/ida/agents/pauli.md:19-33`, `plugins/ida/agents/james.md:10-35`, `plugins/ida/agents/sara.md:14-40` (`build/tool_map.toml`), `plugins/ida/skills/pull/SKILL.md:14-39`, `wf-task-base.md:1-45` |
| [Axiom: Proportionate](../plugins/rbg/skills/axioms/proportionate.md) -- Build the least mechanism that meets the request across its class, weighing risk by likelihood × consequence. | instructions, process | imperative, required gate | `plugins/rbg/skills/axioms/proportionate.md:9-13`, `plugins/ida/agents/pauli.md:59`, `plugins/ida/skills/q/SKILL.md:10`, `plugins/ida/skills/reify/SKILL.md:8`, `plugins/rbg/agents/rbg.md:23-29`, `wf-strategic-fit.md:16-39`, `wf-review.md:53` |

## Outcome-Level Build Criteria

The Stage 2 build implementation must satisfy the following verifiable criteria:

- [ ] **BC-1 (Targeted External State Verification)**: The custodian uses qualitative judgment to double-check external state (pull requests, releases, issues) with a reasonable likelihood of having changed since last updated, before reporting on or relying on that state, while leaving records unchanged when nothing appears off (`plugins/ida/agents/pauli.md`).
- [ ] **BC-2 (Ownership Boundary with Scheduled Sweeps)**: Routine systematic sweeping of repositories and task sets remains the exclusive responsibility of scheduled reconciliation workflows (e.g. daily note sweeps); the custodian instructions explicitly prohibit duplicating routine sweeps (`plugins/ida/agents/pauli.md`).
- [ ] **BC-3 (Tool Permission Harmonization)**: The agent definition permits targeted, read-only `gh` CLI commands to inspect GitHub state, resolving previous "PKB graph only / never the shell" phrasing while maintaining strict prohibitions on general shell execution, source code edits, and local filesystem searching (`plugins/ida/agents/pauli.md`).
