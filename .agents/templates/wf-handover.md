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
2. **Run quality gates** — compose [[wf-verification]] or [[wf-qa]] proportionate to stakes.
3. **Update task status** (workers with PKB access mark done after `/pull`, partial when worker acceptance items remain, failed when a check fails; never release as review; release partial if needing help from a higher tier) and release the claim. Workers never create or name follow-up tasks.
4. **Codify learnings** — file an issue or memory entry if something durable was learned (compose [[wf-memory-capture]] / remember).
5. **Commit, push, file PR** — the mechanical crossing:
   - Stage specific files (never blanket `add -A`).
   - Commit message states _why_, not _what_. Commits to public repositories must never carry PKB IDs or `Task:`/`Epic:`/`Claude-Session:` trailers (`data-boundaries`). Task linkage is maintained in the private task record.
   - **Name the base explicitly — `gh pr create --base <ref>`.** With no `--base`, `gh pr create` targets the repository's **default branch**, which is routinely not the line the work was cut from. Establish which branch is the active line, state it, and never let the CLI default decide for you. A wrong base is silent: the PR still reads `MERGEABLE`, the commits it lists are all genuinely on the branch, and the only symptom is an implausibly large diff — so the failure arrives disguised as a review-scope problem, and merging it drags a whole release line into the default branch. If the PR was opened as a draft (such as a Stage 1 spec or design PR), mark it ready for review (`gh pr ready`) as soon as its code step completes, without waiting for approval. Write a PR description that explains what was done and the approach taken, keeping it scannable and easy to understand; do not list every single change in detail (the diff provides that), and follow project PR style or templates where defined.
   - **Epic names a shared branch** — a `## Shared feature branch: <name>` heading on the task's epic body: push to that branch, never a new one. The PR is the epic's — search open PRs on that branch first; reuse it if one exists, open it once if this is the first child to land.
   - **Spec-then-build lifecycle (one branch, one PR)** — a Stage 1 spec or design task opens a **draft** PR (`gh pr create --draft`); Stage 1 never merges on its own. A following Stage 2 build continues on Stage 1's branch and pushes to the same PR, with the spec still editable; Stage 2 marks the PR ready for review once the feature is written, without waiting for approval. Spec and feature merge together after full review.
   - **No shared branch named** (most other tasks, including every task with no epic): push to a per-task branch (`task/<id>-<slug>`) and open its own PR, or reuse an existing one.
6. **Output a structured reflection** — minimum fields: Outcome, Accomplishments — under an `## Framework Reflection` H2 heading, held to the same fields and heading every session so the next reader can scan it without re-deriving what happened.
7. **Summary of work, last output** — what was done and tasks worked. Nothing follows this in the transcript.

## Quick Exit

If no work was done this session, skip straight to the summary — do not fabricate a commit or reflection for zero-diff sessions.

## Declared stakes

Two-way door in the sense that a bad commit can be reverted — but the _absence_ of this gate is effectively one-way: an abandoned session with no PR and no task update is often never picked back up. That asymmetry is why this gate is close to mandatory rather than optional, unlike [[wf-verification]].
