---
name: dump
description: "Session exit and handover — commit and push your work, release any claimed PKB tasks with a status report, and emit a single final handover message. Invoke whenever a session is ending, being interrupted, or work must be handed off to the next agent."
---

# Dump — Session Exit

Every session exit must provide a formal handover.

If you have hit an error, exhausted your resources, or have been asked to terminate:

- you must abort immediately, save any progress, and return with minimal explanation and a simple resume path.
- you must still provide a handover message.
- if you have a task claimed, you must release it if you can.

## Handover process

### 1. SAVE AND PUSH YOUR WORK

You are running in an isolated, _ephemeral_ environment. Any files left on your local storage will be DESTROYED.

- You must commit and push your work if you can.
- If you are blocked from pushing, you must find another way to save your work in a durable location.

### 2. RELEASE YOUR TASKS

For EACH task you have worked, starting with children:

A. **Construct your report in the following format:**

```markdown
### Task: <task-id> (<precis>) — <status: completed | cancelled | failed | in-progress >

- **Update**: [ 1-3 sentences: what you did, what you learned, what remains ]
- **Output**: [ reference to any artifacts or work produced: e.g. `<branch>` (uncommitted: yes/no) | `url` | `pkb note id` and title | `filename` (warning: local files will be destroyed on exit)]
- **Next**: `<task-id>` [ title ] | [ Plain english instructions, with just enough detail to allow the next agent to pick up the work where you left off. ]
```

B. **Release your tasks, children first:** call the PKB's `release_task` MCP tool with your session id and your concise report.

### 3. EMIT FINAL REPORT

Compile each of your reports into a single final message:

````markdown
## Handover: <agent> <session-id>

- **You asked**: <the original ask, one sentence>
- **So far**: <2–4 bullets: what was decided>
- **Output**: <PR or artefact URL> (description)
- **Next**: <the single recommended next step, phrased so it can be acted on or approved>
- **Errors**: <list any errors encountered, precis only, or `none`>
- **Self-evaluation**: <at most two sentences>
- **Waiting on / watch out**: <the blocker; any in-flight side effects>

[ Then, for each task, include its concise report from the last step. ]

```markdown
### Task: ...
```
````
