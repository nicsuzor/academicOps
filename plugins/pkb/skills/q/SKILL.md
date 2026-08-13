---
name: q
type: command
description: Quick-queue a thought, ask, or fragment onto the task graph.
allowed-tools: [Skill, AskUserQuestion, mcp__services__pkb__create_task]
---

# /q — Quick Queue

Invoke `pauli` with the a simple instruction to silently capture the the user's
intent by creating one or more new tasks in the 'inbox' state.

**CAPTURE ONLY**:

- **NO PLANNING**: your job here is to capture the user intent on the graph
  quickly and without interrupting. o not decompose the task.
- **Place the incoming task under an appropriate parent node**. Do not insert new tasks under complete or stale
  parent nodes.
- **Never park tasks in a catch-all, and never leave them unparented.** Everything
  belongs somewhere real on the graph. A node with no parent is an orphan the next
  sweep has to chase, and a junk-drawer parent is an orphan that does not show up
  as one — which is worse.

**RETURN Task ID and title** in the following format:

```
- Queued [TASK-ID] - [TASK-TITLE] (under [ PARENT TASK-ID ]))
... [ Repeat if necessary ]
```
