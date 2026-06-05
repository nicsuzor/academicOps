---
name: dump
type: skill
category: instruction
description: Emergency session bail — fast resume task + short handover, no commit/PR/reflection. For when you (or the user) need a clean context now. Use /end-session for canonical close.
triggers:
  - "emergency handoff"
  - "emergency handover"
  - "bail"
  - "dump"
  - "out of context"
  - "context full"
  - "need clean context"
  - "interrupted, need to restart"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
permalink: skills/dump
---

# /dump: Emergency Handover (Fast Bail)

Perform a fast session exit by creating a resume-ready task and emitting a handover block. Do not commit, push, create PRs, or output reflection blocks.

## Execution

### 1. Write Resume Delta

Call `mcp_pkb_update_task` on the bound task:

- Set `session_id` to `$AOPS_SESSION_ID`. Do not modify other frontmatter or change `status`.
- Append to the task body a `## Resume <UTC-timestamp>` section containing:
  - **State**: Current state of implementation (one sentence).
  - **Next**: Next concrete action.
  - **Watch out**: Any in-flight side-effects (uncommitted files, running processes, locks).
- If no task is bound, call `mcp_pkb_create_task` with parent `"adhoc-sessions"`, `priority=3`, and the resume details as the body.

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
