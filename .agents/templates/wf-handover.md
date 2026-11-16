---
alias:
- wf-handover-wf-handover
- wf-handover
created: 2026-07-20T07:23:27.016490035+00:00
id: wf-handover
last_modified: 2026-08-27T18:33:56.965409770+00:00
modified: 2026-08-27T18:33:56.965407265+00:00
permalink: wf-handover
tags:
- wf-template
- v0.4
- module-f
title: wf-handover
type: template
---

## What this step does

Work is NOT complete until `git push` succeeds, a PR is filed, and reflection is provided. Using mutating tools after this gate opens resets it.

## Pattern

1. **Complete all file changes.**
2. **Run quality gates** -- run verification and QA checks by independent agents proportionate to stakes.
3. **Update task status** (workers release `done` when complete, `partial` when own acceptance items remain, `failed` on check failure; never release as `review`) and release the claim. Workers never create or name follow-up tasks.
4. **Codify learnings** -- file an issue or memory entry if something durable was learned (`/remember`). Knowledge notes are CURRENT STATE ONLY: record current truths, never historical provenance lists (`sources:` arrays) or chronological retrospectives.
5. **Commit, push, file PR** -- the mechanical crossing:
   - Stage specific files (never blanket `add -A`).
   - Commit message states _why_, not _what_. Commits to public repositories must never carry PKB IDs or `Task:`/`Epic:`/`Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record.
   - **Name the base explicitly -- `gh pr create --draft --base <ref>`.** With no `--base`, `gh pr create` targets the repository's **default branch**, which is routinely not the line the work was cut from. Establish which branch is the active line, state it, and never let the CLI default decide for you. A wrong base is silent: the PR still reads `MERGEABLE`, the commits it lists are all genuinely on the branch, and the only symptom is an implausibly large diff -- so the failure arrives disguised as a review-scope problem, and merging it drags a whole release line into the default branch. Worker PRs open as a draft (`gh pr create --draft`) and are marked ready for review (`gh pr ready`) only after the independent check passes and proportionate review by independent agents is posted to the PR thread, without waiting for approval. Write a PR description that explains what was done and the approach taken, keeping it scannable and easy to understand; do not list every single change in detail (the diff provides that), and follow project PR style or templates where defined.
   - **Consolidated feature branch (`bundle/<slug>` or `feat/<slug>`)** -- related work (tasks under an epic, tasks touching overlapping surfaces, or PR consolidation sweeps) gathers on a shared feature branch targeting `dev`. Once a constituent `polecat/<id>` branch passes its three-lens diff review (strategic fit, compliance, quality), merge it directly into the shared feature branch without waiting for user approval, open or update the consolidated PR into `dev`, immediately close any superseded standalone donor PR with a comment linking to the consolidated PR, and run the compliance description-only check (`## RBG Review: PASS`, "is this stupid?") on the consolidated PR pre-approval.
   - **Spec-then-build lifecycle (one PR, opened by the build)** -- Stage 1 records its design, any drafted spec change, and its independent agent review verdicts in a PKB note the Stage 2 task points to; Stage 1 commits no plan or design file, opens no PR, and never puts a spec to the user for approval on its own. A following Stage 2 build commits the spec change alongside the implementation on its constituent branch, merging into the shared feature branch after three-lens diff `PASS` (or opening a standalone draft PR into `dev` when isolated with zero overlap).
   - **Standalone PR exception** (isolated single-task change with zero overlap or authorized hotfix): push to `polecat/<id>` or `task/<id>-<slug>`, open its draft PR into `dev` (`gh pr create --draft --base dev`), and mark ready (`gh pr ready`) once its three-lens diff review and checks pass.
6. **Output a structured reflection** -- minimum fields: Outcome, Accomplishments -- under an `## Framework Reflection` H2 heading, held to the same fields and heading every session so the next reader can scan it without re-deriving what happened.
7. **Summary of work, last output** -- what was done and tasks worked. Nothing follows this in the transcript.

## Quick Exit

If no work was done this session, skip straight to the summary -- do not fabricate a commit or reflection for zero-diff sessions.

## Declared stakes

Two-way door in the sense that a bad commit can be reverted -- but the _absence_ of this gate is effectively one-way: an abandoned session with no PR and no task update is often never picked back up. That asymmetry is why this gate is close to mandatory rather than optional, unlike standalone verification steps.
