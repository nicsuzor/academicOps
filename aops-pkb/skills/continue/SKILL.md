---
name: continue
type: skill
category: instruction
description: Pause and hand back to the user with work still IN PROGRESS — emit a scannable resume summary and checkpoint the bound task, WITHOUT concluding. Use /end-session or /dump to finish the task completely.
triggers:
  - "pause here"
  - "hand back to the user"
  - "over to you"
  - "waiting on the user"
  - "waiting for input"
  - "pausing, work not done"
  - "checkpoint and hand back"
  - "hold for the user"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
permalink: skills/continue
---

# /continue: Pause & Hand Back (work still in progress)

The **lightweight** exit path. Use it when your work is **not done** — you need
the user's input, or you are waiting — and you want to hand control back cleanly
WITHOUT concluding the task.

This is the THIRD exit option, in addition to the two that finish the task
completely:

- `/end-session` — canonical close (commit, push, PR, release the task, reflection).
- `/dump` — emergency bail (fast resume task + short handover, no commit/PR).
- **`/continue` (this skill)** — pause only: the bound task stays `in_progress`,
  nothing is committed, pushed, released, or reviewed. It just leaves a clean,
  scannable pickup point in BOTH the chat and the task, then hands back.

Running `/continue` opens the Stop gate, so you hand back without the honesty /
handover block firing — because this skill already delivers the honest,
scannable summary those gates exist to require.

## Execution

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

Call `mcp__pkb__update_task` on the bound task:

- Set `session_id` to `$AOPS_SESSION_ID`.
- **Do NOT change `status`** — the work is ongoing; the task stays `in_progress`.
- Append the SAME `### Resume <UTC-timestamp>` block (verbatim) to the task body.

The chat summary IS the task checkpoint — write the one block to both. If no task
is bound, skip the task write and say so in the chat block.

### 3. Emit the block and exit

Print the resume block to the user, then stop. Do **not** commit, push, open a
PR, or release the task — `/continue` is a pause, not a conclusion.
