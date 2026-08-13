# The completion line — what reaches Nic between an instruction and its result

**Status:** proposed. **Task:** `aops_a87040b8`. **Written:** 2026-08-13.

Nic delegates something and then hears nothing about it until it is finished. When
it finishes he gets exactly one line, and that line is a _pointer to a record that
already exists on disk_ — not the record itself.

That is the whole contract. Everything below is the mechanism that makes it true
rather than aspirational, and the honest account of where it is not yet proven.

## Why "one line at the end" is the wrong way to read the requirement

Scrollback is not a record. A completion report that lives only in a chat pane is
gone by tomorrow, and Nic will not remember it existed. So the deliverable is not
_a message_; it is **the mechanism that puts the line into a durable record, so
that what he reads in chat is a pointer to something already written.**

This matters because it decides the architecture. If the line were a message, the
face would compose it and the daily note would be a nice-to-have. Because the line
is a record, the daily note is a **view of the task graph**, the graph is the
source of truth, and the message is the last and least important artefact in the
chain.

## The one failure mode that matters

A suppressed channel and a channel with nothing to say look identical from Nic's
side. So the failure this spec guards against is not a crash. It is Nic quietly
ceasing to know things, with nothing in his experience marking the moment it
started.

Four independent records on this exact surface are cases of an agent reporting a
success it had not achieved — `obs_c07c32b0` (a hook reported success and returned
no path), `obs_1e941c3e` (`EnterWorktree` reported a move it half performed),
`mem-fe14d1e9` (worktree-isolated agents wrote to the parent checkout via absolute
paths), `lear_1edc63c5` (an agent completed every requested write and reported
none of it). One shape, four times: a well-formed answer that was not true, with
nothing in the answer marking it suspect.

**A completion line a worker can produce by asserting it finished is therefore
worthless.** That single constraint drives the design.

## The mechanism: two keys, neither sufficient alone

A line is written only when both of these hold, and they come from different
places on purpose:

| Key                                                                                       | What it supplies                      | Where it comes from                                  |
| ----------------------------------------------------------------------------------------- | ------------------------------------- | ---------------------------------------------------- |
| An outcome **marker** in the task's own body — `LANDED:`, `BLOCKED-ON-YOU:`, or `FAILED:` | the **wording**, which is a judgement | the worker, through the sanctioned `pkb append` path |
| The graph's own **status** agreeing with that marker's outcome class                      | the **truth**                         | the task's frontmatter, read independently           |

A worker that writes `LANDED:` on a task the graph does not have in a landed
status produces **no line at all** — not a warning, not a partial line, nothing.
A task that reaches `done` with no marker also produces nothing in a sweep,
because a status alone is not evidence that anything was delegated: tasks reach
`done` all day for reasons that were never a delegated unit.

Implementation: `lib/hooks/landed.py`. Tests: `tests/test_landed_line.py`.

### Outcome classes

Three outcomes, because a capability that can only report success is one that
hides its failures. All three land as one line in the same place.

| Marker           | Statuses the graph must have     | Rendered as                                |
| ---------------- | -------------------------------- | ------------------------------------------ |
| `LANDED`         | `done`, `review`, `merge_ready`  | `- [x] <what> (<where>) [<id>]`            |
| `BLOCKED-ON-YOU` | `blocked`, `paused`              | `- [ ] **blocked on you** — <what> [<id>]` |
| `FAILED`         | `failed`, `cancelled`, `partial` | `- [ ] **failed** — <what> [<id>]`         |

Only `LANDED` gets a tick. The other two keep the one-line contract without
claiming a completion they have not earned.

**One genuine judgement call, recorded rather than buried:** `review` and
`merge_ready` count as _landed_. In this framework a worker's handback state _is_
`review` — the work is delivered and what remains is an internal evaluator's pass,
not more work by the delegate. Nic asked to hear when the thing he asked for is
done, and it is done at handback; the task id on the line is what lets him follow
the review if he wants to. Reversible by editing one table in `landed.py`.

### Where the line goes

Its own `## Landed today` section in `$ACA_DATA/daily/YYYYMMDD-daily.md`, created
at the end of the file if absent — which puts it below the fold, where a
completed-work log belongs.

Not under `### My priorities`, where the first hand-written instance landed:
`tpl_daily` says of that section _"Never omit it, never fill it yourself"_
(`tpl_daily.md:53`), so an agent writing there is contradicting the template. A
dedicated machine-owned section resolves that instead of arguing with it.

The renderer does still _look_ for an existing `[<id>]` line across the whole
note, and corrects it in place if it finds one, so a line a human already parked
elsewhere is updated rather than duplicated.

### Safety properties, each load-bearing

- **Surgical.** Read, insert or replace one line, write back. Everything else is
  byte-identical, asserted on the bytes in `test_the_write_is_surgical`.
- **Serialised.** The read-modify-write happens under one exclusive `flock` held
  across the whole cycle. Concurrent whole-file writes are how this note has been
  corrupted before; `test_two_writers_at_once_both_land` runs two real processes.
- **Atomic.** Same-directory temp file plus `os.replace`, so a crash cannot leave
  a truncated 78 KB daily note.
- **Idempotent on task id.** The trigger fires per tool batch; a mechanism that
  appended each time would fill the note in a minute.
- **Re-derivable.** Every line comes from the task files alone, so a note that
  loses the section rebuilds it by running the sweep again. This is what makes the
  daily note a _view_ rather than a divergent second copy — and it is why a
  regeneration that clobbers the section is recoverable rather than a lost record.
- **Never creates a daily note through the PKB `create` path**, whose type enum
  has no `daily` value; six historical dailies sit in `brain/notes/` from exactly
  that mistake. It writes the canonical path with `type: daily` directly.

### Why the write is a filesystem write

No PKB CLI command can do it. `pkb append --section` was tested and rejected: it
stamps `**<ts> UTC** —` on what it writes, which destroys a markdown checkbox.
`pkb update` touches frontmatter only. There is no body-rewrite command. So the
renderer writes the file and then hands it to `pkb add` to refresh the index. This
is a **new sanctioned write path** — purpose-built, locked, atomic, idempotent,
reviewed — which is what `aops-c9c2e2ad`'s effect-named prohibition requires
instead of an ad-hoc agent `Write`.

_Upstream ask, not in this change:_ a `--raw` flag on `pkb append` that omits the
timestamp prefix would let this go through the PKB's own writer.

### The trigger, and why the event is load-bearing

`render_landed`, registered on **`PostToolBatch`** in `plugins/ida/hooks/handlers.py`.

`PostToolBatch` fires after a batch of tool calls and **before the model produces
its next text**. That ordering is the contract: by the time any word about the work
exists, the line is already on disk. `Stop` fires once the turn's text is written,
so a renderer wired there would always be one turn late — it would announce a
record it had not yet made.

The handler returns `None` on every path, including failure, and catches everything:
a renderer that produced an agent-visible warning or a `systemMessage` would be the
very leak this exists to close.

Also callable directly — `landed.py --task <id>` or `--sweep` — which is the route
a coordinator uses on the isolated route and the route a recovery uses.

## The silence half

### What was actually leaking

`plugins/ida/hooks/messages/quiet.user.md` shipped the line

> `ida: trimming the reply to what you actually need to see.`

`dispatch.py:263-264` promotes any `Result.user_text` to a `systemMessage`, and
`be_quiet` is registered on `PostToolBatch` — so **the suppression mechanism
announced itself to Nic roughly once per tool batch.** Being told his reply is
being trimmed is itself a mention of the delegated work.

**Fix: the file is deleted.** `load_message_pair` returns `None` for a missing
user file and `dispatch.py` then sets no `systemMessage` at all, so the absence
_is_ the suppression — a mechanism, not an instruction to be quiet.
`test_no_message_file_in_the_build_reaches_the_person` derives the check from the
build rather than a hardcoded list, so the next handler to ship a user-visible
line has to argue for it there.

### Channel inventory, graded

Evidence layers, per `wf-agentic-e2e-certification`: **computed** (the message was
built), **delivered** (the client's wire payload carried it), **seen** (a rendered
surface showed it). Only the third proves Nic saw anything.

**In-session route:**

| # | Channel                                                                                                                                 | Disposition                                                                                                 | Evidence layer reached                                                 |
| - | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 1 | ida's own prose                                                                                                                         | **instruction only** — `quiet.md` tells the agent to be silent; nothing stops it being loud                 | computed. This is the largest remaining leak and it is not mechanical. |
| 2 | `systemMessage` from `quiet.user.md`                                                                                                    | **suppressed mechanically** — file deleted                                                                  | delivered (the hook's wire payload no longer carries the key)          |
| 3 | `systemMessage` from orchestrate `session_start` (`"Credentials isolated."`, a Python literal, not a `.user.md`)                        | **not suppressed** — fires at session start, unrelated to any delegation                                    | computed                                                               |
| 4 | `systemMessage` from orchestrate `honesty.user.md` on `Stop`                                                                            | **inert for workers** — `honest_output` exempts `ida:ida`, and `SubagentStop` registration is commented out | computed                                                               |
| 5 | Push notifications / remote control (`agentPushNotifEnabled: true`, `remoteControlAtStartup: true` in `~/junior/.claude/settings.json`) | **not addressed** — client-level, outside the hook layer                                                    | **unproven.** Not measured. A disclosed leak.                          |
| 6 | The parent's rendered subagent progress indicator                                                                                       | **cannot be suppressed** from here                                                                          | **unproven.** A disclosed leak.                                        |

**Isolated route:**

| # | Channel                                                                                        | Disposition                                                                                   | Evidence layer reached                                                      |
| - | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 7 | Container stdout/stderr                                                                        | **structurally silent** — lands in the detached tmux pane. Nothing reached the caller unasked | **delivered** (observed: the launch returned only the caller's own `echo`s) |
| 8 | `dispatch`'s own §4 Report (task id, title, session, mode) returning into the caller's context | **instruction only** — the coordinator must not relay it                                      | computed                                                                    |

## Named gaps, disclosed rather than smoothed

1. **Channels 1, 5 and 6 are not mechanically suppressed.** 1 is instruction-only;
   5 and 6 were not measured at all. A silence claim that inspects only a
   transcript has not tested the notification channel.
2. **The isolated route has a completion-visibility lag of up to ~5 minutes.** A
   container cannot mount `$ACA_DATA` (the mount list in `polecat/cli.py:1044-1104`
   contains no path under `/home/nic/brain`, and the in-container `ACA_DATA` is the
   constant `/data`), and it has no `pkb` binary. Its PKB writes go to the **remote**
   MCP server and reach `/home/nic/brain` only via `brain-sync`/cron.
   _Why the contract still holds:_ the standing rule that PKB reads on this host go
   through the local CLI means the coordinator cannot learn of completion before
   the local graph does — so the renderer cannot be late relative to the message.
   _Where it breaks:_ a coordinator that checks status over the remote MCP instead
   would know before the line could be written. That dependency is real and is the
   reason the local-CLI rule is load-bearing here rather than merely tidy.
3. **`review`-as-landed is a judgement, not a derivation** (above).
4. **A defect found on the way, filed not fixed:** the dispatch skill's documented
   `tmux new-session -d` still gives the process a TTY, so `cli.py:1415-1416`
   computes `is_interactive = True`, polecat adds `-it`, and the `claude` lane runs
   the interactive TUI instead of `--print`. `POLECAT_PRINT_TIMEOUT` (`cli.py:998-1000`)
   is inside an `agent_cmd == "agy"` branch, so the claude lane has no wall-clock
   ceiling either. Out of scope here.

## Out of scope, stated so it is not mistaken for an omission

- Re-homing `specs/adhd/surface-contract.md`. It exists on no remote branch
  (verified: `git show origin/dev:specs/adhd/surface-contract.md` → _does not
  exist_). This spec cites the rulings on `aops-fef39347` instead.
- Ruling on whether the surface contract governs non-interactive polecat
  user-notices. The evidence is in the inventory above; the ruling is not written
  here.
- Fixing the polecat interactive-detection defect (gap 4).
- Any change to `aops_33c99996` or its subtree.
