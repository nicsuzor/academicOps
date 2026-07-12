---
id: handover
kind: gate
category: session
description: Session-completion gate — commit (why, not what), push, file PR, codify learnings, reflect. Work is not complete until this crosses.
door-type: two-way
stakes: Work is silently abandoned mid-flight — no git history, no PR, no task update, no traceability for the next session or reviewer.
skip-when: No file modifications were made this session, or the user explicitly requests no commit.
requires: []
pairs-with: [verification, qa, memory-capture]
version: 2.0.0
permalink: workflows-gates-handover
---

# Gate: Handover

**Work is NOT complete until `git push` succeeds, a PR is filed, and reflection
is provided.** Using mutating tools after this gate opens resets it.

## Pattern

1. **Complete all file changes.**
2. **Run quality gates** — compose [[verification]] or [[qa]] proportionate to
   stakes.
3. **Update task status** (mark done/in-progress) and release the claim.
4. **Codify learnings** — file an issue or memory entry if something durable
   was learned (compose [[memory-capture]]).
5. **Commit, push, file PR** — the mechanical crossing:
   - Stage specific files (never blanket `add -A`).
   - Commit message states _why_, not _what_; include a `Task:` trailer (and
     `Epic:` if applicable) linking the commit back to the task graph.
   - Push; open a PR (`gh pr create --fill` or reuse an existing one). For
     polecat worktrees, set status to `merge_ready` instead of pushing directly.
6. **Output a structured reflection** — minimum fields: Outcome,
   Accomplishments, Next step — under an `## Framework Reflection` H2 heading
   so it stays machine-parseable.
7. **Summary to user, last output** — what was done, tasks worked, follow-ups,
   and the resume pointer. Nothing follows this in the transcript.

## Quick Exit

If no work was done this session, skip straight to the summary — do not
fabricate a commit or reflection for zero-diff sessions.

## Declared stakes

Two-way door in the sense that a bad commit can be reverted — but the _absence_
of this gate is effectively one-way: an abandoned session with no PR and no
task update is often never picked back up. That asymmetry is why this gate is
close to mandatory rather than optional, unlike [[verification]].
