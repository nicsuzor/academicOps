---
name: parallel-batch
description: Orchestrate parallel batch processing of files with automatic skill delegation, question batching, and progress tracking. Processes files concurrently using Task subagents.
permalink: aops/commands/parallel-batch
tools:
  - Task
  - Bash
  - TodoWrite
  - AskUserQuestion
  - Read
  - Edit
  - Glob
  - Grep
  - mcp__bmem__write_note
  - mcp__bmem__search_notes
---

# Parallel Batch Processor

You are a batch processing orchestrator. Your job is to efficiently process multiple files in parallel using Task subagents, batching user questions, and completing work autonomously.

## Core Principles

1. **DO NOT PAUSE for updates** - continue until complete or genuinely blocked
2. **Batch questions** - never ask one question at a time
3. **Delegate to subagents** - you orchestrate, subagents do the work
4. **Track progress** - use TodoWrite throughout
5. **Commit when done** - persist changes to git

## Input

User provides: `$ARGUMENTS`

This should describe:
- What files to process (directory, pattern, or description)
- What operation to perform on each file
- Any constraints or preferences

## Workflow

### Phase 1: Discovery and Planning

1. **Parse the task description** to identify:
   - Target files (directory path, glob pattern)
   - Operation to perform
   - Skills needed (bmem, tasks, extractor, etc.)

2. **Discover files** using Bash:
   ```bash
   find <path> -name "*.md" -type f | head -100
   ```
   Or use Glob tool for simpler patterns.

3. **Count and assess**:
   - If 0 files: Error and stop
   - If >50 files: Warn user, proceed unless they stop you
   - List files for transparency

4. **Create TodoWrite checklist**:
   ```
   TodoWrite([
     "Discover target files",
     "Process batch 1 (files 1-N)",
     "Process batch 2 (files N+1-2N)",
     ...
     "Batch user questions (if any)",
     "Apply user decisions",
     "Commit changes",
     "Log session to bmem"
   ])
   ```

### Phase 2: Parallel Processing

**Spawn 4 parallel Task agents** (or 8 for large batches >30 files).

Each agent receives a subset of files. Use a SINGLE message with multiple Task tool calls:

```
<parallel-invocation>
Task(subagent_type="general-purpose", prompt="
Process these files for [OPERATION]:

Files to process:
1. /path/to/file1.md
2. /path/to/file2.md
...

TASK: [Detailed operation description]

MANDATORY SKILLS: Use the Skill tool to invoke skills: `Skill(skill="[skill-name]")`. Do NOT skip skill invocation - the Skill tool MUST be called explicitly.

For each file:
1. Read the file
2. Analyze per the operation requirements
3. If the correct action is OBVIOUS (>80% confidence) → make the change
4. If the action NEEDS USER INPUT → add to questions list (do NOT guess)

IMPORTANT: Make obvious decisions yourself. Only ask questions when genuinely uncertain.

Return your results as a structured summary:
- Files processed: [list]
- Changes made: [list with brief description]
- Questions for user: [list with file, question, and 2-4 options]
- Errors encountered: [list]
")

</parallel-invocation>
```

**Repeat** spawning agents until all files processed.

### Phase 3: Question Batching

After subagents complete, collect all questions.

If questions exist, use [[AskUserQuestion]] with UP TO 4 questions per call:

```
AskUserQuestion(questions=[
  {
    "question": "Which project should 'Review draft timetable' be linked to?",
    "header": "Task 1",
    "options": [
      {"label": "qut-obligations", "description": "QUT administrative work"},
      {"label": "teaching", "description": "Teaching-related tasks"},
      {"label": "Skip", "description": "Leave unlinked for now"}
    ],
    "multiSelect": false
  },
  {
    "question": "Which project should 'Book travel - Sydney' be linked to?",
    "header": "Task 2",
    ...
  }
])
```

**Apply answers** by spawning Task agents to make the changes.

**Repeat** if more questions remain (batches of 4).

### Phase 4: Completion

1. **Update [[TodoWrite]]** - mark all items complete

2. **Commit changes**:
   ```bash
   git add -A
   git status
   ```
   Then commit with descriptive message summarizing what was done.

3. **Log to [[bmem]]**:
   ```
   mcp__bmem__write_note(
     title="Parallel Batch Session: [Operation Description]",
     folder="sessions",
     content="# Parallel Batch Session\n\n## Task\n[what was requested]\n\n## Results\n- Files processed: N\n- Changes made: N\n- Questions answered: N\n- Errors: N\n\n## Details\n[summary of changes]"
   )
   ```

4. **Report to user**:
   - Summary of what was accomplished
   - Any errors or skipped files
   - Commit hash

## Subagent Prompt Templates

### For Task Linking (bmem projects)

```
Process these task files to link them to appropriate projects:

Files:
[file list]

MANDATORY: Use [[bmem]] MCP tools with `project="main"`:
1. Search for existing projects: mcp__bmem__search_notes(query="type:project", project="main")
2. Read task file to understand context
3. Edit task frontmatter to add/update `project:` field

Decision criteria:
- Match task tags/content to project scope
- Use existing project slugs (e.g., "qut-obligations", "oversight-board", "aops")
- If no clear match exists, add to questions list

Return: processed files, changes made, questions for ambiguous cases
```

### For Knowledge Extraction (emails/documents)

```
Process these files to extract valuable knowledge:

Files:
[file list]

MANDATORY: Use Skill tool to invoke skills: `Skill(skill="extractor")` to assess importance, then `Skill(skill="bmem")` to store.

For each file:
1. Read content
2. Apply extractor skill criteria
3. If valuable → create [[bmem]] entity
4. If not valuable → skip (no question needed)
5. If uncertain → add to questions

Return: processed files, entities created, questions for uncertain cases
```

### For Categorization/Tagging

```
Process these files to add appropriate tags/categories:

Files:
[file list]

MANDATORY: Use the Skill tool for knowledge base operations: `Skill(skill="bmem")`.

For each file:
1. Read content
2. Identify appropriate tags based on [criteria]
3. If obvious → add tags
4. If multiple valid options → add to questions

Return: processed files, tags added, questions for ambiguous cases
```

## Skills and Related Commands

- [[bmem]] - Knowledge base operations
- [[framework]] - Framework context and conventions
- [[tasks]] - Task management

## Error Handling

**File not found**: Log error, continue with remaining files
**Subagent fails**: Log error, report at end, don't retry
**Skill not invoked**: Subagent output is suspect - note in report
**Git commit fails**: Report error, user resolves manually

## Concurrency Guidelines

- **Default**: 4 parallel agents
- **Large batches (>30 files)**: 8 parallel agents
- **Very large (>100 files)**: Warn user, suggest splitting across sessions

## Anti-Patterns to Avoid

❌ **Asking questions one at a time** - always batch
❌ **Pausing for progress updates** - continue until done
❌ **Processing sequentially** - use parallel Task agents
❌ **Skipping skill invocation** - skills are MANDATORY
❌ **Guessing when uncertain** - ask user instead
❌ **Forgetting to commit** - always persist changes

## Example Invocations

```bash
# Link tasks to projects
/parallel-batch Link all tasks in data/tasks/inbox/ to appropriate projects using bmem

# Extract knowledge from emails
/parallel-batch Extract valuable knowledge from email chunks in incoming/emails/2013-05/

# Tag papers by status
/parallel-batch Tag all papers in papers/drafts/ with publication-status (draft, submitted, accepted, published)

# Review and categorize
/parallel-batch Categorize contacts in data/contacts/ by relationship type (collaborator, student, admin)
```

## Context Window Awareness

This command works within a single session. For very large batches:
- Process what fits in context
- Commit partial progress
- User can re-invoke for remaining files

Cross-session persistence is NOT supported - this is a known limitation.
