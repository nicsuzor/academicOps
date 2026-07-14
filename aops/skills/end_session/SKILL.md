---
name: end_session
description: "Canonical session close \u2014 commit, push, PR, release_task, reflection\
  \ blocks, handover. Use /dump for emergency bail (no commit/PR/reflection)."
agent: pauli
---

# /end-session: Canonical Session Close and Handover

Close a session cleanly by committing/pushing changes, filing PRs, resolving tasks, and providing reflections. For mid-flight bails without task completion, use `/dump` instead.

## Contract

- Output a 5–10 line markdown block (see [the Handover Block](#6-handover-block)) and write structured session data via `release_task`.

## Execution Path

Determine if session was Read-only (no mutating tools used, no tasks modified/created) or Full-form (modifying).

### Read-only Path

Print `Output: none — read-only Q&A` and exit.

### Full-form Path (Standard Close)

#### 1. Resolve Bound Task

Identify the active task, in priority order: (1) the `$AOPS_TASK_ID` env var — authoritative, auto-populated — falling back if unset to the git branch name's segment after the last `/` (e.g. `polecat/aops-1f9ec7b0` → `aops-1f9ec7b0`; do not read or synthesise a filesystem-state file); (2) an explicit task ID argument; (3) otherwise `release_task` auto-creates an ad-hoc task.

<!-- cowork:only -->

#### 1.5. Reconcile native task list with PKB (Cowork only)

Run `TaskList()` and reconcile mirrored tasks. For each native task marked `completed` carrying `PKB <id>` (excluding the bound parent task), if the PKB task is not terminal, call `mcp__services__pkb__complete_task`.

<!-- /cowork:only -->

#### 2. Version Control

If files changed, commit, push, and open a PR against **this repo's default working branch** — `dev` for academicOps (`main` is publish-only), otherwise the repo's own default (do not copy the `dev` convention onto a repo that has no `dev` branch). Write a PR body that describes the change for its reviewer; skip merge-gate / do-not-merge / "awaiting Nic" banners — branch protection is the real gate, so a banner warns nobody who can act on it. Canonical rule: [[framework-conventions-summary#pr-body-conventions]].

#### 3. Update Project Breadcrumb

Resolve the parent epic and project node from the bound task, then use `mcp__services__pkb__append` to add a line to the project file's **Active Epics** section: `- [[<epic-id>]] — <epic title> (task [[<bound-task-id>]], PR <url-or-'none'>)`.

#### 4. Release Task

Verify all child tasks are in terminal states (`done`, `cancelled`, `superseded`, `archived`) before closing the parent, then call `release_task` with `id`, `status`, `session_id="$AOPS_SESSION_ID"`, whichever of `pr_url`, `branch`, `issue_url`, `follow_up_tasks` apply, and a `release_summary` (result-oriented, self-contained, naming specific resources/issues like `org/repo#NNN`, <= 500 chars).

- **Choose `status: merge_ready` vs `status: review` deliberately** (they are not interchangeable — see the canonical protocol in [[taxonomy#status-values-and-transitions]]). Use **`status: merge_ready`** when you opened a PR and the task is now parked on that PR's review/merge — set `pr_url`. Use **`status: review`** only when the task is parked on a _human decision_ (it needs Nic's or an agent's judgment/direction before it can proceed) — not merely because a PR is open. A reconcile sweep may auto-close a merged `status: merge_ready` task, but it will **never** auto-close a `status: review` task; mis-tagging a PR-parked task as `status: review` leaves it stuck, and mis-tagging a decision-parked task as `status: merge_ready` invites a wrong auto-close.

#### 5. Output Reflection Blocks

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
- `## Output` must carry a real artefact link (PR/commit URL); if there genuinely is none, write `Output: none — <reason>`. No link and no explicit "none" → end-session does not pass.

#### 6. Handover Block

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

#### 7. Thread Pickup (for >=2 follow-up tasks)

If leaving multiple distinct follow-up threads, append:

```markdown
### Thread Pickup: what next?

- **Thread A** — `/pull <task-id>` (<short title>): <one-line action / why it's next>
- **Thread B** — `/pull <task-id>` (<short title>): <one-line action / dependency>
```

#### 8. Exit

Terminate execution immediately after the handover or thread pickup blocks. Do not add trailing text.
