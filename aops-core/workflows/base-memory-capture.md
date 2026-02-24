---
id: base-memory-capture
category: base
---

# Base: Memory Capture

**Composable base pattern.** Most workflows that discover information should include this.

## Pattern

At session end or before task completion:

1. **Identify findings**: What did you learn, discover, or decide?
2. **Store to PKB**: `mcp__pkb__create_memory(title="...", body="...", tags=[...])`
3. **Write durable artifacts**: If findings warrant persistence beyond memory, write to `$ACA_DATA`

## Storage Hierarchy

All findings flow through this hierarchy:

| What                  | Primary Storage                                      | Also Store To |
| --------------------- | ---------------------------------------------------- | ------------- |
| **Epics/projects**    | Task Manager MCP (`type="epic"` or `type="project"`) | PKB    |
| **Tasks/issues**      | GitHub Issues (`gh issue create`)                    | PKB    |
| **Durable knowledge** | `$ACA_DATA/` markdown files                          | PKB    |
| **Session findings**  | Task body updates                                    | PKB    |

**Key principle**: PKB is the **universal index** for semantic search. Write to your primary storage AND PKB.

## Invocation

Use the `/remember` skill which handles both markdown AND PKB writes:

```
Skill(skill="remember")
```

The skill ensures:

- Markdown written to correct `$ACA_DATA` location
- PKB synced for semantic retrieval
- Wikilinks created for graph connectivity

## When to Skip

- [[simple-question]] - pure information lookup, no discoveries
- Task only executed existing instructions with no new findings
- Findings already captured in task body (memory capture is for cross-session persistence)

## When to Include

- Debugging that reveals root causes
- Design decisions and rationale
- Research findings
- Framework learnings
- Any "aha moment" worth preserving
