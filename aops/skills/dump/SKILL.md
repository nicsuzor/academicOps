---
name: dump
description: "Session exit — one skill, three paths. Bare `/dump` (default) is\
  \ the emergency bail: fast resume task + short handover, no commit/PR/reflection.\
  \ `/dump full` is the canonical close: commit, push, PR, release_task, reflection\
  \ blocks. `/dump pause` hands back with work still IN PROGRESS: checkpoints the\
  \ bound task without concluding it."
agent: pauli
---

# /dump: Session Exit (Bail, Full Close, or Pause)

Every session exit runs through this skill. Pick a path with the first word after
`/dump`; a bare `/dump` defaults to **bail**.

| Path               | Invocation    | When                                                | Commits/PR? | Task status                            |
| ------------------ | ------------- | --------------------------------------------------- | ----------- | -------------------------------------- |
| **Bail** (default) | `/dump`       | You need a clean context NOW                        | No          | Resume task created/updated, left open |
| **Full**           | `/dump full`  | The task is genuinely done                          | Yes         | Released via `release_task`            |
| **Pause**          | `/dump pause` | Work is mid-flight — waiting on the user or blocked | No          | Stays `in_progress`, checkpointed      |

Do not guess which path fits. If the task isn't actually finished, use **bail** or
**pause** — never **full**.

## Path: Bail (default) — Emergency Handover, Fast

Perform a fast session exit by creating a resume-ready task and emitting a handover
block. Do not commit, push, create PRs, or output reflection blocks.

### 1. Write Resume Delta

Call `mcp__services__pkb__update_task` on the bound task:

- Set `session_id` to `$AOPS_SESSION_ID`. Do not modify other frontmatter or change `status`.
- Append to the task body a `## Resume <UTC-timestamp>` section containing:
  - **State**: Current state of implementation (one sentence).
  - **Next**: Next concrete action.
  - **Watch out**: Any in-flight side-effects (uncommitted files, running processes, locks).
- If no task is bound, call `mcp__services__pkb__create_task` with an appropriate `parent` task, and the resume details as the body.

### 2. Output Handover Block

Emit exactly this markdown block:

```markdown
### Emergency Handover

- **Session ID**: `$AOPS_SESSION_ID`
- **Resume Task**: `<task-id>` (<short title>)
- **Branch**: `<branch>` (uncommitted: yes/no)
- **Next**: <what to do first in the next session>
```

### 3. Exit

Terminate execution immediately after the block. Do not add trailing text.

## Path: Full — Canonical Session Close

Close a session cleanly by committing/pushing changes, filing PRs, resolving tasks,
and providing reflections. For mid-flight bails without task completion, use the
**bail** or **pause** path instead.

### Contract

- Output a 5–10 line markdown block (see [the Handover Block](#6-handover-block)) and write structured session data via `release_task`.

### Execution Path

Determine if session was Read-only (no mutating tools used, no tasks modified/created) or Full-form (modifying).

#### Read-only Sub-path

Print `Output: none — read-only Q&A` and exit.

#### Full-form Sub-path (Standard Close)

##### 1. Resolve Bound Task

Identify the active task, in priority order: (1) the `$AOPS_TASK_ID` env var — authoritative, auto-populated — falling back if unset to the git branch name's segment after the last `/` (e.g. `polecat/aops-1f9ec7b0` → `aops-1f9ec7b0`; do not read or synthesise a filesystem-state file); (2) an explicit task ID argument; (3) otherwise `release_task` auto-creates an ad-hoc task.

<!-- cowork:only -->

##### 1.5. Reconcile native task list with PKB (Cowork only)

Run `TaskList()` and reconcile mirrored tasks. For each native task marked `completed` carrying `PKB <id>` (excluding the bound parent task), if the PKB task is not terminal, call `mcp__services__pkb__complete_task`.

<!-- /cowork:only -->

##### 2. Version Control

If files changed, commit, push, and open a PR against **this repo's default working branch** — `dev` for academicOps (`main` is publish-only), otherwise the repo's own default (do not copy the `dev` convention onto a repo that has no `dev` branch). Write a PR body that describes the change for its reviewer; skip merge-gate / do-not-merge / "awaiting Nic" banners — branch protection is the real gate, so a banner warns nobody who can act on it. Canonical rule: [[framework-conventions-summary#pr-body-conventions]].

##### 3. Update Project Breadcrumb

Resolve the parent epic and project node from the bound task, then use `mcp__services__pkb__append` to add a line to the project file's **Active Epics** section: `- [[<epic-id>]] — <epic title> (task [[<bound-task-id>]], PR <url-or-'none'>)`.

##### 4. Release Task

Verify all child tasks are in terminal states (`done`, `cancelled`, `superseded`, `archived`) before closing the parent, then call `release_task` with `id`, `status`, `session_id="$AOPS_SESSION_ID"`, whichever of `pr_url`, `branch`, `issue_url`, `follow_up_tasks` apply, and a `release_summary` (result-oriented, self-contained, naming specific resources/issues like `org/repo#NNN`, <= 500 chars).

- **Choose `status: merge_ready` vs `status: review` deliberately** (they are not interchangeable — see the canonical protocol in [[taxonomy#status-values-and-transitions]]). Use **`status: merge_ready`** when you opened a PR and the task is now parked on that PR's review/merge — set `pr_url`. Use **`status: review`** only when the task is parked on a _human decision_ (it needs Nic's or an agent's judgment/direction before it can proceed) — not merely because a PR is open. A reconcile sweep may auto-close a merged `status: merge_ready` task, but it will **never** auto-close a `status: review` task; mis-tagging a PR-parked task as `status: review` leaves it stuck, and mis-tagging a decision-parked task as `status: merge_ready` invites a wrong auto-close.

##### 5. Output Reflection Blocks

Include these three markdown headers in your response before the handover block:

```markdown
## Output

- [Artefact Link] (Description)

## Tasks worked

- <task-id> (< precis >) — <created | updated | completed | cancelled | referenced>

## Framework Reflection

**Outcome**: success | partial | failure
**Accomplishments**: <what you completed — comma list, or `-` bullets, or `none`>
**Friction points**: <issue/task URLs filed via /learn; no description prose — or `none`>
**Proposed changes**: <one concrete instruction or tool improvement — or `none`>
```

- **Emit each field with its exact bold label (`**Field**:`).** `**Outcome**`, `**Accomplishments**`, `**Friction points**`, and `**Proposed changes**` are the only labels the pipeline reads, matched verbatim — plain-bullet, renamed, or free-form labels parse as nothing. The exact grammar is the SSoT in `transcript-metadata-schema.md`.
- All linked entities must include their stable identifiers and parenthesized precis (e.g., `task-acba1234 ( precis )`).
- `## Output` must carry a real artefact link (PR/commit URL); if there genuinely is none, write `Output: none — <reason>`. No link and no explicit "none" → the full path does not pass.

##### 6. Handover Block

Emit exactly this markdown block:

```markdown
### Session Handover

- **Session ID**: `$AOPS_SESSION_ID`
- **Primary Task**: `<task-id>` (<short title>)
- **PR**: <url>
- **Branch**: `<branch>`
- **Issue**: <url or "none">
- **Follow-ups**: `<task-id> (<short title>)` (or "none")

- **What you asked**: <original user instruction, including deliverables and constraints.>
- **Summary**: <release_summary value>
```

Omit lines for `PR`, `Issue`, and `Follow-ups` if they do not exist.

##### 7. Thread Pickup (for >=2 follow-up tasks)

If leaving multiple distinct follow-up threads, append:

```markdown
### Thread Pickup: what next?

- **Thread A** — `/pull <task-id>` (<short title>): <one-line action / why it's next>
- **Thread B** — `/pull <task-id>` (<short title>): <one-line action / dependency>
```

##### 8. Exit

Terminate execution immediately after the handover or thread pickup blocks. Do not add trailing text.

## Path: Pause — Hand Back, Work Still In Progress

The **lightweight** exit path. Use it when your work is **not done** — you need
the user's input, or you are waiting — and you want to hand control back cleanly
WITHOUT concluding the task: the bound task stays `in_progress`, nothing is
committed, pushed, released, or reviewed. It just leaves a clean, scannable
pickup point in BOTH the chat and the task, then hands back.

Running the pause path opens the Stop gate, so you hand back without the honesty /
handover block firing — because this path already delivers the honest,
scannable summary those gates exist to require.

### 1. Compose the resume block (ONE block — it goes to both surfaces)

Write a single block designed to orient a user who returns with **no memory** of
the session. It MUST be EASILY SCANNABLE (short bullets, plain words, every id /
branch / task named in 3–8 words). Use exactly these parts:

```markdown
### Resume <UTC-timestamp>

- **You asked**: <the user's ORIGINAL ask, one sentence>
- **So far**: <2–4 bullets: the conversation / what was decided>
- **I did**: <what you actually did this session — concrete, with evidence refs>
- **Next**: <the single recommended next step, phrased so the user can act or approve>
- **Waiting on / watch out**: <what you're blocked on; any in-flight side effects (uncommitted files, running processes)>
```

### 2. Checkpoint the bound task with the SAME block

Call `mcp__services__pkb__update_task` on the bound task:

- Set `session_id` to `$AOPS_SESSION_ID`.
- **Do NOT change `status`** — the work is ongoing; the task stays `in_progress`.
- Append the SAME `### Resume <UTC-timestamp>` block (verbatim) to the task body.

The chat summary IS the task checkpoint — write the one block to both. If no task
is bound, skip the task write and say so in the chat block.

### 3. Emit the block and exit

Print the resume block to the user, then stop. Do **not** commit, push, open a
PR, or release the task — the pause path is a pause, not a conclusion.
