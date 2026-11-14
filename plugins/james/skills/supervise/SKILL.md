---
name: supervise
description: Coordinate a task or repository-scoped epic end-to-end in-session across any repository with PKB MCP access -- resolve workflows via james:workflow-library, delegate to specialist subagents with incremental git checkpoints, verify reports via james:premise-check, and close via /james:dialectical-review and /james:dump. Use for in-session execution, multi-stage coordination, and multi-agent fan-out. Exclude for single pre-scoped atomic leaf tasks (use james:pull).
---

# /supervise: In-Session Task Execution and Supervision

Coordinate end-to-end execution across any repository with PKB MCP access using an in-session coordinator (`james`) and specialist subagents (`pauli`, `rbg`, `marsha`), without requiring `ida` or `rbg` plugins. Repository-local `.agents/rules/` and `specs/` apply when present in the target workspace and are optional in external repositories.

## 0. Immediate Claim & Live PKB Persistence

1. **Claim the Task**: Claim the assigned task via `pkb_claim_task`. If invoked on an untracked directive without a task ID, search the PKB via `pkb` MCP tools (or delegate placement to `pauli`) to reuse or create and claim a repository-scoped tracking task.
2. **Continuous Persistence**: Update the PKB task record after each completed stage or subagent chunk so progress and acceptance state survive session pre-emption.

## 1. Inline Workflow Assembly (`james:workflow-library`)

Inspect the claimed task body before composing:

- **Fast-Path**: If the task already carries a composed workflow (`## Instructions` and `## Appendix: Sources`) or specifies a single skill (`invoke /<skill>`), proceed directly to planning.
- **Dynamic Composition**: Otherwise, resolve and compose workflow templates inline using `james:workflow-library` in strict precedence **Project > PKB > Universal** (higher tiers shadow lower tiers completely; never merge text across tiers). Adapt multi-stage templates to execute within the current session; when the target repository has no project-tier templates, resolve from PKB and Universal tiers.

## 2. Plan & Parallel Dialectical Review

1. **Draft Execution Plan**: Record the execution plan on the PKB task. When modifying agent-shaping behavior and `specs/enforcement/enforcement.md` exists in the target workspace, evaluate least-invasive enforcement options against it before adopting heavier constraints.
2. **Parallel Dialectical Review**: Run a proportionate review via `/james:dialectical-review` across strategic fit (`pauli`), compliance (`rbg` against universal PKB rules and optional repo-local `.agents/rules/`), and qualitative quality (`marsha`). Append the null `argdown` block (`asks: none` / `[no claim]`) to claim-free subagent briefs.
3. **Verify and Resolve**: Because `james` runs no automatic prompt hearsay gate, inspect every incoming peer or subagent report qualitatively and record verdicts on claim reports via `james:premise-check` (`verdict.py --judged-file <path>`) before acting on or relaying findings. Cull completed helpers, resolve blocking findings, and apply uncontroversial fixes before implementation fan-out.

## 3. Model-Calibrated Fan-Out & Incremental Push Checkpoints

1. **Calibrated Delegation**: Fan out disjoint chunks in parallel to calibrated subagent models:
   - **High-capability models**: Complex architecture, specifications, and multi-constraint synthesis.
   - **Lightweight models**: Focused file edits, template updates, sweeps, and index synchronization.
   - Supply complete inputs, constraints, and target artifact paths in Turn-1 briefs; require only deliverables the subagent holds on exit, ending with a `james:premise-check` `argdown` block.
2. **Incremental Checkpoint Invariant**: After every subagent chunk:
   - Verify claim handbacks qualitatively and via `james:premise-check` (`verdict.py --judged-file <path>`).
   - Run formatters, linters, and relevant checks available in the target repository.
   - Stage specific modified files and commit cleanly, scrubbing private identifiers, PKB IDs, session trailers, personal names, and private hostnames for public repositories (`data-boundaries`).
   - Run `git push` incrementally to the upstream branch when working on a remote branch so progress survives pre-emption.
   - Update the PKB task record with incremental progress.

## 4. Closing Delivery & Follow-Ups

1. **In-Session Verification**: Complete all executable deliverables in-session -- test suites, linters, builds, and a closing `/james:dialectical-review` on the final diff.
2. **Pull Request**: When delivering to a pull request, open or update a single cohesive PR against the base branch with scrubbed review receipts.
3. **Out-of-Session Follow-Ups**: Deliver everything executable in-session. Create and wire follow-up tasks directly via `pkb` MCP tools (or delegate graph wiring to `pauli`) only when remaining work explicitly requires a different repository (one task per repository), a deferred time or external wait condition, or a separate external session.

## 5. Handover (`/james:dump`)

Invoke `/james:dump` to commit and push final changes, capture durable facts, record the `## Report` `argdown` proof (`pr_url` and `branch` where applicable), and release the task (`done` when all in-session deliverables complete, or `partial` with blocking reasons if unfinished).
