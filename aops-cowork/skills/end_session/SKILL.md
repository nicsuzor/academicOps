---
name: end_session
alias: end-session
type: skill
category: instruction
description: Canonical session close — commit, push, PR, release_task, reflection blocks, handover. Use /dump for emergency bail (no commit/PR/reflection).
triggers:
  - "save work"
  - "handover"
  - "session end"
  - "close session"
  - "wrap up"
  - "session complete"
  - "task complete"
  - "stop hook blocked"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
permalink: skills/end-session
---

# /end-session: Canonical Session Close and Handover

Close a session cleanly by committing/pushing changes, filing PRs, resolving tasks, and providing reflections. For mid-flight bails without task completion, use `/dump` instead.

## Contract

- Output a 5–10 line markdown block (see [the Handover Block](#6-handover-block)).
- Write structured session data via `release_task`.

## Execution Path

Determine if session was Read-only (no mutating tools used, no tasks modified/created) or Full-form (modifying).

### Read-only Path

1. Print: `Output: none — read-only Q&A`.
2. Exit.

### Full-form Path (Standard Close)

#### 1. Resolve Bound Task

Identify the active task:

1. `/pull`-written binding file: read first line of `$AOPS_SESSION_STATE_DIR/${AOPS_SESSION_ID}-bound-task.txt` (or `${GEMINI_SESSION_ID}-bound-task.txt`).
2. Explicit argument: task ID passed directly to command.
3. Fallback: If no binding, `release_task` will auto-create an ad-hoc task.

#### 1.5. Reconcile native task list with PKB (Cowork only)

Run `TaskList()` and reconcile mirrored tasks. For each native task marked `completed` carrying `PKB <id>` (excluding the bound parent task), if the PKB task is not terminal, call `mcp__pkb__complete_task`.

#### 2. Version Control

If files changed, commit, push, and run `gh pr create --fill --base dev` (PRs target `dev`; `main` is publish-only).

#### 3. Update Project Breadcrumb

Resolve the parent epic and project node from the bound task. Append to the project file's **Active Epics** section:

```
mcp__plugin_aops-core_pkb__append(
  id="<project-id-or-permalink>",
  section="Active Epics",
  content="- [[<epic-id>]] — <epic title> (task [[<bound-task-id>]], PR <url-or-'none'>)"
)
```

#### 4. Release Task

Verify all child tasks are in terminal states (`done`, `cancelled`, `superseded`, `archived`) before closing the parent.

Call `release_task`:

```json
mcp__plugin_aops-core_pkb__release_task(
  id="<bound-task-id>",
  status="merge_ready" | "review" | "done" | "blocked",
  session_id="$AOPS_SESSION_ID",
  pr_url="<pr-url>",
  branch="<branch-name>",
  issue_url="<issue-url>",
  follow_up_tasks=["task-xxxx"],
  release_summary="<concrete, result-oriented summary, <= 500 chars>"
)
```

- `release_summary` must be result-oriented, self-contained, and name specific resources/issues (`org/repo#NNN`).
- On success, delete `$AOPS_SESSION_STATE_DIR/${AOPS_SESSION_ID}-bound-task.txt`.

#### 5. Output Reflection Blocks

Include these three markdown headers in your response before the handover block:

```markdown
## Output

- [Artefact Link] (Description)

## Tasks worked

- <task-id> (< precis >) — <created | updated | completed | cancelled | referenced>

## Framework Reflection

- Friction points: <issue/task URLs filed via /learn; no description prose>
- Proposed improvement: <one concrete instruction or tool improvement>
- Attributable win (optional): <what worked well>
```

- All linked entities must include their stable identifiers and parenthesized precis (e.g., `task-acba1234 ( precis )`).
- These blocks are parsed into structured session metadata — see `transcript-metadata-schema.md` for the field/warning contract. `## Output` must carry a real artefact link (PR/commit URL); if there genuinely is none, write `Output: none — <reason>`. No link and no explicit "none" → end-session does not pass.

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

- **Thread A**: <action for next session>
- **Thread B**: <action / dependency>
```

#### 8. Exit

Terminate execution immediately after the handover or thread pickup blocks. Do not add trailing text.
