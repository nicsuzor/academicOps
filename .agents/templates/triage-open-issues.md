---
title: Triage open GitHub issues
type: template
kind: process
category: maintenance
status: active
description: Work down a repository's open-issue backlog in bounded batches — close what is verifiably fixed, land the small live fixes, annotate the rest — select when the ask is "deal with the open issues"; not for a single named issue, and not for planning new work
tags: [github, issues, triage, backlog, maintenance, batch]
---

> [!IMPORTANT]
> Close, never delete. An issue closed on a guess is worse than one left open — it removes the
> only record that the problem was ever reported.

A backlog of hundreds of open issues is not one task. It is an indefinite number of small ones,
most of which are already fixed and nobody has checked. This template is the loop that finds out.

## Inputs

- **The repository**, and the **integration branch** every fix must end up on.
- Optionally a **selector** narrowing the backlog (a label, an age, a milestone). With none, take
  the oldest issues first — they are the most likely to be already fixed.

## One pass

A pass is bounded on purpose: roughly ten issues, one worker, one branch. It ends with the
integration branch green and the batch fully dispositioned. Run passes until the backlog is empty
or the yield stops justifying them.

1. **Take a slice.** The oldest N open issues matching the selector. Where several touch the same
   subsystem, keep them in one slice — that is what lets passes run in parallel without two
   workers editing the same files.

2. **Give every issue in the slice a disposition.** There are exactly three:
   - **Already resolved or obsolete** — verify it against the current code, then close it with a
     one-line reason naming what you checked. The reason is the whole point: a bare close is
     unauditable.
   - **A small live bug you can finish inside this pass** — fix it, and close the issue on the fix.
   - **Anything larger, ambiguous, or blocked** — leave it open with a comment saying concretely
     what it is still waiting on. Deferring is a real disposition; silence is not.

   If you cannot verify a claim, annotate. Never close on a guess.

3. **Land the work.** Branch off the integration branch, keep the pass's changes in one branch,
   and merge it in. A pull request left open is not done. The suite must be green when the pass
   ends — a fix that would redden the integration branch is annotated on its issue rather than
   landed.

4. **Record the pass** where the next one will look: the issues closed, the issues annotated, what
   merged, and the suite's state. Without that, the next pass re-walks the same issues.

## Running passes in parallel

Two or three at once is the practical ceiling. Slice by subsystem so their diffs do not overlap,
give each its own branch, and merge them one at a time — resolving conflicts between fixes is
cheaper than untangling a shared branch.

## Guards

- **Verification is per-issue, not per-batch.** "The suite is green" is not evidence that issue
  #123 is fixed.
- **A stated reason on every close.** Someone reopening it in six months needs to know what was
  checked and when.
- **Do not widen the slice mid-pass.** A pass that grows to fifty issues finishes none of them.
- **Write permission is not admin.** Assume you cannot delete issues or rewrite history; say so
  rather than working around it.
