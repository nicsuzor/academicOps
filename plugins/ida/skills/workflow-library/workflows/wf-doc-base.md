---
title: Doc task base
type: template
description: Foundation for tasks changing instruction text or documentation in a repository -- write and prove without wording tests, push a draft PR, and run independent review ending in a PR verdict.
tags: [base, task, docs, instructions, composite]
---

- **GOAL:** <one sentence>
- **ACCEPTANCE CRITERIA:** <one line each, observable outcomes>
  - <criterion>
  - <criterion>
- [ ] **OUTPUT:** <repository and base branch the PR targets>
- **REPORT:** Update the task via `/dump` in place (current state only; tick `[x]` items only with inline primary evidence and citation).

## Stages

1. **Write and prove**: Read target files in full and edit to satisfy the acceptance criteria. Write **no tests** for documentation or instruction text, and never assert wording. Prove agent-facing instruction text (agent definitions, skills, workflow templates, rules, axioms, commands, `AGENTS.md`) via a fresh agent run that follows it; check documentation via independent agent review against project standards. Record design-stage specification changes in the PKB and deliver them with implementation in one PR (never a code-less spec PR).
2. **Push and draft PR**: Push the branch and open or update a draft PR (`gh pr create --draft`) explaining what was done and the approach taken (no line-by-line diff detail, no private PKB/session trailers, follow project PR templates). Mark ready (`gh pr ready`) only after the independent check passes and proportionate review posts to the PR thread. Record `pr_url` and release `done`.
3. **Review and verdict** (separate task or fresh reviewing agent; omit for minor docs repairs or trivial chores): Run proportionate independent review against acceptance criteria and project rules, push in-place fixes for trivial defects if warranted, post verdicts to the PR, and execute one outcome:
   - **Rejected**: Close PR with review, mark work task `cancelled` with reason, release review `failed`.
   - **Revisions needed**: Post unmet criteria to PR, leave open, release `failed` with root cause; mint no follow-up tasks.
   - **Handoff after reviewer edits**: Leave PR open without marking merge-ready, release `partial` with explanation.
   - **Reviewed / Ready for Decision**: Clean review with no reviewer code edits and green checks -- mark ready (`gh pr ready`), post review link and CI receipts with a merge recommendation, release `done`, and do not merge.

## Composition

Structure as one task with internal subtasks when executable in one session, or as a composite parent task with two sequential child tasks (Child 1: Stages 1--2 drafting and proof; Child 2: Stage 3 independent review with `needs: [<child_1_id>]`), never loose siblings under an external parent. When a change spans both a specification and executable code, build and verify both together in one PR.

## Output Contract

- **Stages 1--2**: Fresh-agent execution proof (for instruction text) or independent review (for documentation), plus open PR URL recorded on the task.
- **Stage 3**: Independent review verdicts posted on the PR, any in-place fix commits, and one verdict executed.

## When to Include

Any task delivering changes to repository documentation or agent-facing instruction text as a reviewed PR.
