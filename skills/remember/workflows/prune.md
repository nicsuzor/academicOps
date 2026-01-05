---
title: Prune Workflow
type: automation
permalink: prune-workflow
tags:
  - memory
  - workflow
  - maintenance
---

# Prune Workflow

Aggressively clean knowledge base by consolidating related files, removing low-value files, and extracting and organising knowledge.

**Philosophy**: Knowledge base must be tended to regularly.
- Information added at different times should be consolidated; knowledge base should be up to date.
- Knowledge base should contain ONLY things worth searching for.
- project files should tell current state without requiring changelog archaeology.
- Reduce file count while preserving essential knowledge.

## Classification Criteria

### DELETE (No extraction)

Files with zero lasting value:

- Raw email transcripts ("Thank you!", "See attached")
- Pure scheduling (meeting times, locations)
- Auto-generated noise (confirmations, password resets)
- Orphaned coordination ("Let me know if that works")
- Duplicates where content exists elsewhere

**Test**: Would you ever search for this? If "no way" → DELETE

### CONSOLIDATE (Time based logs)

Guidelines for consolidating time-based observations and progress logs into an organized knowledge base.

#### Single Source of Truth

- [principle] Each project should have ONE main file that captures current state #architecture
- [principle] Readers should not need to hunt through multiple files to understand a project #usability
- [principle] Time-based logs exist to feed the main file, not as permanent artifacts #workflow
- [anti-pattern] Multiple files tracking the same thing from different angles causes confusion #redundancy

#### Analyze Before Acting

- [technique] Spawn parallel agents to analyze different areas simultaneously #efficiency
- [technique] Create DELETE and KEEP lists with reasons before executing #safety
- [technique] Read files to understand their actual status, not just their names #accuracy
- [principle] Be aggressive in recommendations but careful in execution #balance


#### What Makes Files Deletable

- [criterion] Session logs where work is complete and observations are in project files #completed-work
- [criterion] Phase completion reports superseded by consolidated documentation #superseded
- [criterion] Plans that were executed (keep only outcomes, not the planning) #executed-plans
- [criterion] Bug fixes that are complete and no longer need tracking #resolved-issues
- [criterion] Partially implemented ideas that were abandoned and cause confusion #abandoned
- [criterion] Duplicate versions (abridged/full pairs - keep one) #duplicates
- [criterion] Empty or stub files with no substantive content #empty
- [criterion] Historical travel/logistics notes with no ongoing relevance #obsolete
- [criterion] Code references that belong in code repos, not knowledge bases #wrong-location

#### What to Keep Separate

- [keep] Meeting records, file notes, user written records
- [keep] Main project file (single source of truth) #core
- [keep] Active investigations still in progress #active-work
- [keep] Reference guides actively consulted during work #reference
- [keep] Learning logs and pattern digests (institutional memory) #learning

#### Consolidation Patterns

- [pattern] Extract key observations from session logs into main file's Observations section #extraction
- [pattern] Move completed implementation details to "Recent Activity" or "Changelog" #history
- [pattern] Summarize rather than copy verbatim - compress information #compression
- [pattern] Archive granular files (like meeting transcripts) but keep summaries accessible #archival
- [pattern] Rename unclear files to reflect actual content #clarity

### EXTRACT_DELETE

Files with mostly noise but some facts worth keeping:

- Contact files with scheduling noise → extract role/affiliation
- Project coordination → extract decisions/outcomes
- Event logistics → extract what happened/who attended

**Process**:
1. Identify target file (existing contact/project)
2. Extract facts as observations
3. Append to target file
4. Delete source via `git rm`

**Test**: Is there ONE fact worth adding to another file? Extract it, then DELETE.

### KEEP

Files with lasting value:

- Substantive prose (notes, reflections, analysis)
- Contemporaneous notes (file notes, meeting notes, transcripts, etc)
- Research content (literature notes, findings)
- Strategic context (why decisions were made)
- Relationship substance (collaboration history)

**Test**: Is this actual prose, meeting/file notes, or substantive content? → KEEP

## Execution Strategy

- Use parallel agents
- Commit in logical chunks with descriptive messages
- Track file count reduction as metric


### Phase 1: Discovery

1. Count total files to establish baseline
2. Identify main directories/projects to analyze
3. Spawn parallel agents to analyze different areas
4. Each agent produces DELETE/KEEP recommendations with reasons

### Phase 2: Triage by Category

For each file:
1. Read completely
2. Classify: DELETE | EXTRACT_DELETE | KEEP

**Green Flags (Files Likely to Keep):**
- [flag] Main project file matching directory name (e.g., `buttermilk/buttermilk.md`) #core
- [flag] Files with "Architecture", "Specification", "Overview" (reference docs) #reference
- [flag] Learning logs and digests (institutional memory) #learning
- [flag] Files from current week (likely active work) #recent

**Consolidate then delete:**
- Session logs → extract to main file → delete session
- Phase reports → summarize in main file → delete phases
- Implementation plans with completed outcomes → note completion → delete plan

**DO NOT extract**:
- Scheduling logistics
- Ephemeral coordination
- Pleasantries

**Review before action:**
- Files with unclear status
- Potentially active investigations
- Files that might be referenced elsewhere


## Decision Tree

```
Is it substantive prose/notes?
├─ Yes → KEEP
└─ No → Is there any fact worth saving?
         ├─ Yes → EXTRACT_DELETE
         └─ No → DELETE
```

## Safety

- All deletions via `git rm` (recoverable)
- Commit after each batch
- Can always `git checkout` to recover
