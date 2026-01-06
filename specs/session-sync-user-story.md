---
title: Session-End Sync User Story
type: spec
category: spec
status: requirement
created: 2025-12-29
permalink: session-sync-user-story
tags:
  - spec
  - user-story
  - session-insights
  - tasks
  - sync
---

# Session-End Sync

**Status**: Requirement

## User Story

> As the user, when I finish a session with Claude Code, I want the insights from that session to update not only our personal knowledge base, but also any related tasks/sub-tasks and the daily.md file. Different levels of detail should be kept for different places (don't duplicate the same info), but we should try to keep things in sync where we can easily match them up.

## Problem Statement

Currently, session-insights extracts accomplishments and updates daily.md, but:

1. Related task files aren't updated with progress/completion
2. Sub-task checklists don't get marked as done
3. No linking between daily accomplishments and the tasks they relate to
4. User must manually sync task status after sessions

## Relationship to session-insights

This **extends** the existing session-insights skill (Step 3). After session-insights updates daily.md with accomplishments, this adds:

1. **Task matching** → find related tasks
2. **Checklist updates** → mark sub-tasks complete
3. **Cross-linking** → connect daily.md ↔ task files

**Sequencing**: session-insights Step 3 (daily.md update) happens first, then task sync runs on those accomplishments.

## Information Distribution (No Duplication)

| Location       | What Goes There        | Level of Detail                            |
| -------------- | ---------------------- | ------------------------------------------ |
| daily.md       | Accomplishment summary | One-line per item with `[x]` and task link |
| Task file body | Progress notes         | Session reference, brief context           |
| Task checklist | Completion markers     | `[x]` items with `[completion:: DATE]`     |
| Learning files | Framework patterns     | Only if framework-relevant insight         |

**Key principle**: Each piece of information lives in ONE place. Cross-references link them.

## Task File Format (Verified)

Based on actual task files in `$ACA_DATA/tasks/inbox/`:

```yaml
# Frontmatter
priority: 1-3
project: slug
status: inbox
task_id: YYYYMMDD-hash
title: Task name
```

```markdown
## Checklist

- [x] Completed item [completion:: 2025-12-17]
- [ ] Incomplete item
```

**Verified conventions**:

- Checklist section header: `## Checklist`
- Completion format: `[completion:: YYYY-MM-DD]`
- Status in frontmatter, not checklist

## Cross-Linking Pattern

In daily.md (added by this extension):

```markdown
## [[academicOps]] → [[projects/aops]]

- [x] Implemented session-sync → [[tasks/inbox/20251229-abc123.md]]
```

In task file (appended to body):

```markdown
## Progress

- 2025-12-29: Completed initial implementation. See [[sessions/20251229-daily.md]]
```

## Matching Strategy

Per [[HEURISTICS#H12a]]: The solution to matching is ALWAYS to give the agent enough context to make the decision. Never algorithmic matching.

### How It Works

1. Agent receives: session transcript (accomplishments extracted)
2. Agent receives: relevant task files (via semantic search or project filter)
3. Agent decides: which tasks relate to which accomplishments, which sub-tasks were completed

The agent understands meaning. "Implemented session sync" and "Add session-end sync feature" are the same work - the agent knows this without fuzzy string algorithms.

### Surfacing Relevant Tasks

Use semantic search to find candidate tasks:

```
mcp__memory__retrieve_memory(query="session accomplishment text")
```

Then give the agent both the transcript and the task files. Let it make the match.

### Confidence

Agent should be conservative: prefer no match over wrong match. If uncertain, note in daily.md without linking.

## Task Search Scope

Search locations:

- `$ACA_DATA/tasks/inbox/*.md` - active tasks
- `$ACA_DATA/tasks/archived/*.md` - recently archived (may have just-completed sub-tasks)

## Graceful Degradation

| Scenario                  | Behavior                                          |
| ------------------------- | ------------------------------------------------- |
| No matching task found    | Accomplishment in daily.md only, no link          |
| Low-confidence match      | Note in daily.md: "possibly related to [[task]]?" |
| Unexpected task format    | Skip that task, log warning, continue             |
| Memory server unavailable | Skip semantic matching, use explicit/project only |

## Update Mechanism

- **Checklist updates**: Use tasks skill `task_item_add.py` or direct Edit with `[completion:: DATE]`
- **Progress notes**: Direct Edit to append to task body
- **daily.md links**: Extend session-insights' existing daily.md update

This maintains tasks skill authority for checklist operations while allowing progress notes via Edit.

## Acceptance Criteria

1. After session-insights runs, high-confidence task matches have updated checklists
2. daily.md accomplishments link to source tasks when match is confident
3. No information is duplicated (summary in daily, details in task)
4. Matching is conservative (prefer no match over wrong match)
5. User can trace: daily accomplishment → task → sub-task completed
6. No task content deleted or corrupted
7. Unexpected formats logged, not crashed

## Constraints

- ❌ NEVER delete task content
- ❌ NEVER mark parent tasks complete automatically (only sub-tasks)
- ❌ NEVER modify tasks on low-confidence matches
- ✅ Append progress to task body (## Progress section)
- ✅ Mark sub-task items as `[x]` with `[completion:: DATE]`
- ✅ Link daily.md items to tasks when match is high-confidence

## Relationships

### Extends

- [[session-insights-skill]] - Adds task sync to existing workflow (Step 3)

### Uses

- [[tasks-skill]] - For checklist format conventions
- Memory server - For semantic task matching

### Informs

- [[dashboard-skill]] - Dashboard shows task progress
