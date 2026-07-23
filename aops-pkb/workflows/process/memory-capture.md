---
id: memory-capture
kind: process
category: fragment
description: Store durable findings — discoveries, decisions, root causes — to the PKB so they outlive the session
requires: []
pairs-with: [investigation, handover]
conflicts: []
version: 1.0.0
permalink: workflows-process-memory-capture
---

# Process fragment: Memory Capture

**Composable fragment.** Most process templates that discover information
should include this at session end or before task completion.

## Pattern

1. **Identify findings** — what did you learn, discover, or decide that isn't
   already obvious from the code/task itself?
2. **Store to PKB** as a memory, tagged for retrieval.
3. **Write durable artifacts** if findings warrant persistence beyond a memory
   entry (e.g. a durable markdown doc).

## Storage Hierarchy

| What              | Primary storage                 | Also store to |
| ----------------- | ------------------------------- | ------------- |
| Epics/projects    | Task manager (`epic`/`project`) | PKB           |
| Tasks/issues      | GitHub Issues                   | PKB           |
| Durable knowledge | Markdown files                  | PKB           |
| Session findings  | Task body updates               | PKB           |

PKB is the universal semantic index — write to the primary store, then also
index it in PKB.

## When to Include

Debugging that reveals a root cause; design decisions and rationale; research
findings; framework learnings; any "aha moment" worth preserving.

## When to Skip

- Pure information lookups, no discoveries.
- The task only executed existing instructions with no new findings.
- Findings are already captured in the task body (this fragment is for
  cross-session persistence, not duplication).
