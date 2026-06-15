# Supervision Mechanics

Reference detail for the supervisor's supporting mechanics — pattern memory, attention
notifications, multi-tick monitoring, status surfaces, hooks, design principles, and phase table.

## Pattern Memory Format

The ledger is your cross-tick memory. Append one row per tick (cap ~16, drop oldest): the
decision and its outcome, so the next tick can read what happened and judge what to do next.

```markdown
## Pattern Memory

| Tick (ISO)           | Decision                    | Outcome / Notes                          |
| :------------------- | :-------------------------- | :--------------------------------------- |
| 2026-05-08T02:14:00Z | dispatch task-abc to claude | preflight clean                          |
| 2026-05-08T02:43:11Z | marsha FAIL on task-abc     | tests red on docker — re-dispatching fix |
```

## User Attention Notification

Emit a single fenced YAML block when escalation conditions are met:

```
[ATTN]
---
id: <epic-id>:<tick-sequence>
urgency: now | today | whenever
action_required: decision | review | info
one_line: <=80-char summary
context_ref: <task-id | PR-url | issue-url>
dismiss_if: <one-line condition under which this no longer needs attention>
suggested_response: <the supervisor's default if user says "you decide">
---
```

All text fields must use plain English. Push `one_line` to slack/discord/email only if
`urgency` is `now` or `today` and `action_required` is `decision`.

## Multi-Tick Supervision (notify-watch)

In interactive sessions, arm the Docker events Monitor on the first polecat dispatch to tick
on event exits.

### Local Monitor Command

```
Monitor(
  description: "polecat exits",
  persistent: true,
  command: "timeout 3600 docker events --filter event=die --filter 'name=polecat-' --format '{{.Time}} {{.Actor.Attributes.name}} exit={{.Actor.Attributes.exitCode}}'"
)
```

`timeout 3600` bounds the stream to one hour per Monitor restart cycle; `persistent: true`
re-arms it automatically.
Filter out crew containers by checking container env for `POLECAT_CREW_NAME`. Stop the monitor
using `TaskStop` once in-flight tasks resolve.

### Mechanism Selection

| Situation             | Mechanism                                  |
| :-------------------- | :----------------------------------------- |
| Single worker outcome | Bash `run_in_background` with polling loop |
| Async PR states       | `Monitor` on `gh pr checks`                |
| Idle / fallback       | `ScheduleWakeup` (>= 1800s)                |
| Interactive session   | `Monitor` on `docker events`               |

## Status Display Surfaces

Read-only projections. Do not write local JSON tracking files.

- `gh pr list` / `gh pr checks`
- `gh run list`
- `$AOPS_SESSIONS/tasks.json`
- `$AOPS_SESSIONS/state/pr-state.json`
- GitHub Issues with `halt` label
- `docker events`

## Lifecycle Trigger Hooks

| Hook          | Trigger       | What it does                             |
| :------------ | :------------ | :--------------------------------------- |
| `queue-drain` | cron / manual | Starts supervisor session.               |
| `stale-check` | cron / manual | Resets timed-out tasks.                  |
| `pr-merge`    | James         | James closes completed tasks post-merge. |

## Task Assignment & Handover

- Assign tasks to appropriate worker; never to humans unless deciding a binary choice.
- Always leave a follow-up task when releasing mid-flow (`mcp__pkb__append` /
  `mcp__pkb__release_task`).

## Design Principles

- **Task File Is the Only State**: Persist all status inside the epic body (`## Pattern Memory`,
  `## Work Items`, `## Supervisor Log`).
- **Halt-on-Substitute**: Halt if worker type, deliverable type, target repository, or scope
  limits change. Do not auto-substitute.
- **Drive-by Fix Policy**: Bundle unrelated trivial fixes only if blocking, obvious, and
  describable in one sentence. Otherwise, file a separate task.
- **Keep the Pipe Flowing**: Delegate decomposition and planning to workers. Restrict supervisor
  concurrency dynamically based on rate limits.
- **Intent Authority**: When filing or decomposing tasks, leave `priority` at the uncurated
  default band — never originate a non-default band. Only Nic sets intent by express instruction.
  Canonical rule: [[framework-conventions-summary#intent-authority]].
- **PR Body Hygiene**: PR bodies describe the change for the reviewer — never carry
  do-not-merge/merge-gate/"awaiting Nic" banners. Branch protection is the enforced gate.
  Canonical rule: [[framework-conventions-summary#pr-body-conventions]].
- **Engineering Integrity**: Failing tests/validations must be resolved, not bypassed.
- **Confound Rule**: Never relay an "external blocker / not our code" verdict until a clean-room
  differential control has ruled out our own code.
- **Critic Gate**: High-risk tasks must undergo preflight validation by Pauli before dispatch.
- **Academic Integrity**: Decisions published under the user's name require human confirmation.

## Phases

| Phase          | Subagent | Execution                                                                   |
| :------------- | :------- | :-------------------------------------------------------------------------- |
| **Orient**     | (none)   | Read task body and ledger; judge whether to advance or halt; select phase.  |
| **Decompose**  | pauli    | Propose subtasks; run RBG axiomcheck. Set `superseded_by` on retired tasks. |
| **Review**     | (none)   | Halt; await human promotion to `queued`.                                    |
| **Dispatch**   | pauli    | Preflight brief, execute dispatch or chain compose/dispatch.                |
| **Pre-verify** | pauli    | Assemble minimal brief (artifact, goal, spec link).                         |
| **Verify**     | marsha   | Run validation. Return PASS, FAIL, or REVISE.                               |
| **React**      | pauli    | Recommend fix-task or halt after FAIL.                                      |
| **Halt**       | (none)   | Terminal state reached; emit summary and exit.                              |

## Deliverable Subworkflows

| Deliverable Type | Subworkflow                       | Status |
| :--------------- | :-------------------------------- | :----- |
| **Code change**  | [[instructions/code-deliverable]] | active |
