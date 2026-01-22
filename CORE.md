---
title: Framework Core
type: instruction
description: Essential framework tools. Tier 1 context - loaded for ALL agents.
---

# Framework Core

This file is loaded at session start. It contains ONLY essential tool references.

## MCP Tools

| Server | Purpose | Key Tools |
|--------|---------|-----------|
| `tasks` | Work tracking | `create_task`, `update_task`, `complete_task`, `get_ready_tasks`, `search_tasks` |
| `memory` | Knowledge retrieval | `retrieve_memory`, `store_memory` |
| `gemini` | Large context analysis | `ask-gemini`, `brainstorm` |
| `zot` | Literature search | `search`, `get_item` |
| `outlook` | Email/calendar | `messages_*`, `calendar_*` |
| `playwright` | Browser automation | `browser_*` |

## Task System (Quick Reference)

```python
# Find work
get_ready_tasks()           # Actionable tasks (no blockers)
search_tasks(query="...")   # Find by keyword

# Track work
create_task(title="...", project="aops", body="...")
update_task(id="...", status="active")
complete_task(id="...")
```

## Memory System (Quick Reference)

```python
# Search knowledge
retrieve_memory(query="...")  # Semantic search

# Store knowledge
Skill(skill="remember")       # Preferred: dual-writes to markdown + memory
store_memory(content="...")   # Direct memory write
```

## Git/Submodule

`$AOPS` (aops/) is a git submodule:
- Commit in submodule first: `cd aops && git add -A && git commit`
- Then update parent repo's reference

## Path Variables

- `$AOPS` = Framework source (aops/)
- `$ACA_DATA` = User data (data/aops/)

---

**For detailed workflows, heuristics, and skill instructions**: These are loaded JIT by prompt-hydrator when relevant to your task.
