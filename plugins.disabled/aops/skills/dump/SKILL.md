---
name: dump
description: "Session exit — one skill, four paths. Bare `/dump` is the emergency bail: resume task plus a short handover, nothing committed. `/dump full` is the canonical close: commit, push, PR, release. `/dump partial` hands back attempted work with the refused decisions named. `/dump pause` hands control back with the work still in progress."
---

# Dump — Session Exit

Every session exit runs through this skill. The first word after `/dump` picks the path; bare `/dump` means **bail**.

| Path        | When                                            | Commits or PR | Task ends at                      |
| ----------- | ----------------------------------------------- | ------------- | --------------------------------- |
| **bail**    | You need a clean context now                    | No            | Left open, resume delta appended  |
| **full**    | The task is genuinely done                      | Yes           | Released                          |
| **partial** | You attempted the rest but refused some choices | Yes, if code  | Released at `partial`             |
| **pause**   | Mid-flight — waiting on the user, or blocked    | No            | Stays `in_progress`, checkpointed |

Do not guess. If the task is not actually finished, the path is bail, pause, or partial — never full.

Terminate immediately after emitting the block for your path. Add no trailing text.

## Bail — emergency handover

1. Update the bound task: set the session id, change nothing else in the frontmatter, and append a `## Resume <UTC-timestamp>` section with **State** (one sentence), **Next** (the concrete next action), and **Watch out** (in-flight side effects — uncommitted files, running processes, locks). With no task bound, create one under an appropriate parent carrying the same content.

2. Emit:

```markdown
### Emergency Handover

- **Resume Task**: `<task-id>` (<short title>)
- **Branch**: `<branch>` (uncommitted: yes/no)
- **Next**: <what to do first next session>
```

## Full — canonical close

A read-only session (nothing mutated, no task touched) prints `Output: none — read-only Q&A` and exits.

Otherwise:

1. **Commit, push, and open a pull request** if files changed. Write the body for its reviewer.

2. **Release the task.** Verify every child is terminal first. Release with the session id, whichever of pull-request URL, branch, issue URL, and follow-up tasks apply, and a result-oriented summary under 500 characters that names its specific resources and stands alone.

   Choose the release status deliberately. **Parked on a pull request's review or merge** is not the same as **parked on a human decision**: a reconcile sweep will auto-close the first once the PR merges and will never auto-close the second. Mis-tag a PR-parked task as decision-parked and it is stranded; mis-tag a decision-parked task as PR-parked and it is auto-closed wrongly.

3. **Emit, for each task worked:**

```markdown
## Tasks worked: <task-id> (<precis>) — <created | updated | completed | cancelled | referenced>

**Outcome**: success | partial | failure
**Output**: <PR or artefact URL> (description)
**Accomplishments**: <what you completed, or `none`>
**Issues filed**: <issue or task URLs, precis only, or `none`>

- **Primary Task**: `<task-id>` (<short title>)
- **Branch**: `<branch>`
- **Issue**: <url or "none">
```

4. **Then the summary:**

```markdown
## Session handover: (description)

**What you asked**: <the original instruction, with its deliverables and constraints>
**Summary**: <the release summary>
**Self-evaluation**: <at most two sentences>
**Follow-ups**: `<task-id> (<short title>)` — omit if none
```

Every linked entity carries its stable identifier and a parenthesised precis. `Output` carries a real artefact link, or an explicit `none — <reason>`; neither present means the full path did not run.

## Partial — refuse and attempt

1. Commit what you wrote and push it. If the deliverable is a pull request, open it as a draft.
2. Update the task: set the session id and append `## Deliberately deferred`, listing the decisions you refused and the acceptance criteria still unmet.
3. Release at `partial` with a summary of what was completed and what was refused. File follow-up tasks for the deferred work and link them.
4. Emit the full-path blocks, marked `partial`, pointing at the deferred items.

## Pause — hand back, still in progress

The lightweight exit: your work is not done, you need input or you are waiting, and you want to hand control back without concluding anything. Nothing is committed, pushed, released, or reviewed.

Write **one** block for a reader returning with no memory of the session — short bullets, every id and branch named in a handful of words:

```markdown
### Resume <UTC-timestamp>

- **You asked**: <the original ask, one sentence>
- **So far**: <2–4 bullets: what was decided>
- **I did**: <what you actually did, with evidence references>
- **Next**: <the single recommended next step, phrased so it can be acted on or approved>
- **Waiting on / watch out**: <the blocker; any in-flight side effects>
```

Append that same block verbatim to the bound task with the session id set and **the status untouched** — the work is ongoing. The chat summary _is_ the task checkpoint. With no task bound, skip the write and say so in the block.
