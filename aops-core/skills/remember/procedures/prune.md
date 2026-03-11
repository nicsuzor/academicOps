---
title: Prune Workflow
type: automation
category: instruction
permalink: prune-workflow
tags: [memory, workflow, maintenance]
---

# Prune Workflow

Aggressively clean knowledge base by consolidating related files, removing low-value files, and organizing knowledge.

**Philosophy**: Knowledge base must be tended to regularly.

- Only keep things worth searching for.
- Project files should tell current state.
- Reduce file count while preserving essential knowledge.

**Detailed procedures and criteria**: See **[[prune-details]]**.

## Classification Categories

1. **DELETE (No extraction)**: Raw transcripts, scheduling, noise, duplicates. No search value.
2. **CONSOLIDATE (Time based logs)**: Move completed session observations to the main project file. SSoT focus.
3. **EXTRACT_DELETE**: Extract one fact (roles, outcomes) and add it to a target file, then delete the source.
4. **KEEP**: Substantive prose, research content, strategic context, file notes, meeting notes.

## Execution Strategy

- **Phase 1: Discovery**: Establish baseline, identify main directories, and spawn parallel agents for analysis.
- **Phase 2: Triage by Category**: Classify each file (DELETE | EXTRACT_DELETE | KEEP) using content analysis and decision tree.
- **Safety**: Use `git rm` for all deletions and commit after each batch to ensure recovery.

**Decision Tree Summary**:

- Substantive prose/notes? → **KEEP**
- Any fact worth saving? → **EXTRACT_DELETE**
- Otherwise → **DELETE**

**Metrics**: Track file count reduction. Commit in logical chunks with descriptive messages.
