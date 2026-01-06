---
title: Parallel Batch Processing
type: spec
category: spec
status: implemented
permalink: parallel-batch-command
tags:
- framework
- commands
- parallel-processing
- task-tool
- orchestration
created: 2025-11-22
---

# Parallel Batch Processing

**Status**: Implemented (as /parallel-batch skill)
**Priority**: P1

## Workflow

```mermaid
graph TD
    A[/parallel-batch task] --> B[Parse Task Description]
    B --> C[Discover Files]
    C --> D[Create TodoWrite Checklist]
    D --> E[Chunk Files into Batches]

    E --> F[Spawn N Parallel Agents]
    F --> G1[Agent 1: Files 0-k]
    F --> G2[Agent 2: Files k-2k]
    F --> G3[Agent N: Files n-1k to nk]

    G1 --> H[Collect Results + Questions]
    G2 --> H
    G3 --> H

    H --> I{Questions?}
    I -->|Yes| J[Batch Questions to User]
    I -->|No| K[Continue]
    J --> L[Apply Answers]
    L --> K

    K --> M{More Files?}
    M -->|Yes| E
    M -->|No| N[Commit Changes]
    N --> O[Log to bmem]
```

## Problem Statement

**What manual work are we automating?**

Currently, processing multiple files (tasks, emails, documents) requires either:

1. Sequential processing (slow, context-efficient but time-consuming)
2. Ad-hoc parallel spawning (fast but requires user to manually coordinate agents)

The LOG.md entry from 2025-11-22 documents a successful pattern where an agent discovered files, then invoked 4 parallel Task agents to process them efficiently. User requested: "Standardize into general multiprocessing pattern invokable via command."

**Why does this matter?**

- **Time efficiency**: 4-8 parallel agents complete work 4-8x faster than sequential
- **Context efficiency**: Each subagent has fresh context; main thread stays lightweight
- **Consistency**: Standardized pattern ensures skills are properly invoked
- **User simplicity**: One command, user specifies task in natural language

**Who benefits?**

Nic - enables efficient bulk operations (task linking, email extraction, document review) without manual coordination of parallel agents.

## Success Criteria

**The automation is successful when**:

1. User can invoke `/parallel-batch` with a natural language task description
2. Command discovers relevant files and spawns N concurrent subagents (configurable, default 4)
3. Each subagent invokes appropriate skills for domain-specific work
4. Questions for user are batched (not asked one at a time)
5. Work continues autonomously until complete or blocked
6. Changes are committed with meaningful message
7. Session log documents what was achieved

**Quality threshold**: Should complete bulk operations without user intervention except for genuine decisions. "Update" pauses are prohibited.

## Scope

### In Scope

- Generic command that accepts natural language task description
- File discovery via Bash (find/glob patterns)
- Parallel Task agent spawning with configurable concurrency
- Skill delegation (subagents invoke specified skills)
- Batched user questions via AskUserQuestion tool
- TodoWrite progress tracking
- Git commit on completion
- Session logging

### Out of Scope

- Cross-session persistence (context window limits still apply)
- Overnight autonomous operation (see LOG.md 2025-11-22 failure)
- External orchestrator or checkpoint/resume (future work)
- Automatic retry on subagent failure (fail-fast principle)

**Boundary rationale**: Focus on single-session parallel processing. Persistence mechanisms are a separate infrastructure problem documented in LOG.md.

## Design

### Command Interface

```bash
/parallel-batch <task-description>
```

**Examples**:

```bash
/parallel-batch Link all unlinked tasks in data/tasks/inbox/ to appropriate projects
/parallel-batch Extract knowledge from email chunks in incoming/emails/2013-04/
/parallel-batch Review and tag all papers in papers/drafts/ for publication status
```

### Command Behavior

The command operates as an **orchestrator** that:

1. **Parses task description** to identify:
   - Target files (glob pattern or directory)
   - Operation to perform
   - Skills to invoke
   - Output expectations

2. **Discovers files** using Bash find/glob

3. **Creates TodoWrite checklist** with:
   - Discovery step
   - Processing batches
   - Question batching
   - Commit step
   - Logging step

4. **Spawns parallel Task agents** (default 4, max 8):
   - Each agent processes subset of files
   - Each agent invokes appropriate skill(s)
   - Agents return results/questions

5. **Batches questions** for user:
   - Collects questions from all agents
   - Presents as single AskUserQuestion with tabs
   - Applies answers and continues

6. **Repeats** until all files processed

7. **Commits** changes with descriptive message

8. **Logs** session summary to bmem

### Architecture

```
User: /parallel-batch <task>
         ↓
[Main Thread: Orchestrator]
    │
    ├─ 1. Parse task → identify files, operation, skills
    │
    ├─ 2. Discover files (Bash: find/ls)
    │
    ├─ 3. Create TodoWrite checklist
    │
    ├─ 4. Spawn N parallel Task agents ──┬── Agent 1: process files[0:k]
    │                                    ├── Agent 2: process files[k:2k]
    │                                    ├── Agent 3: process files[2k:3k]
    │                                    └── Agent N: process files[(N-1)k:N*k]
    │
    ├─ 5. Collect results + questions
    │
    ├─ 6. Batch questions → AskUserQuestion (if any)
    │
    ├─ 7. Apply answers, spawn more agents if needed
    │
    ├─ 8. Repeat 4-7 until complete
    │
    ├─ 9. Commit changes
    │
    └─ 10. Log to bmem
```

### Subagent Design

Each subagent receives:

- List of files to process
- Operation description
- Skills to invoke
- Return format (results + questions)

Subagent template:

```
Process these files: [file1, file2, ...]

Task: [operation description]

MANDATORY: Use [skill-name] skill for [purpose].

For each file:
1. Read file
2. [Perform operation using skill]
3. If decision is obvious → make it
4. If decision needs user input → add to questions list

Return JSON:
{
  "processed": ["file1", "file2"],
  "changes": [{"file": "...", "change": "..."}],
  "questions": [{"file": "...", "question": "...", "options": [...]}],
  "errors": []
}
```

### Question Batching

When subagents return questions, orchestrator:

1. Collects all questions from all agents
2. Groups by similarity if possible
3. Presents via AskUserQuestion with multiple questions (up to 4 per call)
4. Applies answers to corresponding files
5. Continues processing

**Example batched question**:

```
Questions collected from task linking:

Q1: Which project for "Review draft timetable"?
   [ ] qut-obligations
   [ ] teaching
   [ ] Other

Q2: Which project for "Book travel - Sydney"?
   [ ] oversight-board
   [ ] travel
   [ ] Other

Q3: Which project for "Fill in Macquarie payment form"?
   [ ] consulting-growth
   [ ] qut-obligations
   [ ] Other
```

### Error Handling

**Fail-fast cases**:

- File discovery finds 0 files → error with message
- Subagent returns error → log error, continue with remaining
- Skill invocation fails → subagent reports error, orchestrator logs

**Graceful continuation**:

- Individual file processing failures don't stop batch
- Errors collected and reported at end
- Partial progress committed if substantial

### Context Window Considerations

From LOG.md 2025-11-22 "Overnight Autonomous Processing Failed":

- Context exhaustion is real constraint
- Parallel agents help by keeping main thread lightweight
- Each subagent has fresh context
- Main thread only tracks: file list, progress, questions
- Large batches (100+ files) may require multiple sessions

**Mitigation**: Command reports estimated context usage and warns if batch is large. Does NOT attempt cross-session persistence (that's future infrastructure work).

## Integration Test Design

### Test Setup

```bash
# Create test task files
mkdir -p /tmp/test-parallel-batch/tasks
for i in {1..10}; do
  cat > /tmp/test-parallel-batch/tasks/task-$i.md << EOF

title: Test Task $i
type: task
status: inbox

# Test Task $i
Needs project assignment.
EOF
done

# Create test projects list
cat > /tmp/test-parallel-batch/projects.txt << EOF
project-alpha
project-beta
project-gamma
EOF
```

### Test Execution

```bash
# Run parallel-batch command
/parallel-batch Assign projects to all tasks in /tmp/test-parallel-batch/tasks/
```

### Test Validation

```python
import os
import yaml

tasks_dir = "/tmp/test-parallel-batch/tasks"
assigned = 0
for f in os.listdir(tasks_dir):
    with open(os.path.join(tasks_dir, f)) as file:
        content = file.read()
        if "project:" in content:
            assigned += 1

assert assigned >= 8, f"Expected 80%+ tasks assigned, got {assigned}/10"
print("Parallel batch test: PASS")
```

### Success Conditions

- [ ] Test initially fails (no implementation)
- [ ] Test passes after implementation
- [ ] Handles empty directory gracefully
- [ ] Handles mixed success/failure in batch
- [ ] Questions are batched (not asked per-file)
- [ ] Commit created with meaningful message
- [ ] Session logged to bmem

## Implementation Approach

### Command File Structure

`~/.claude/commands/parallel-batch.md`:

```markdown
name: parallel-batch
description: Orchestrate parallel batch processing of files with automatic skill delegation and question batching
tools:

- Task
- Bash
- TodoWrite
- AskUserQuestion
- Read
- Edit
- mcp__bmem__write_note

# Parallel Batch Processor

[Detailed orchestration instructions...]
```

### Key Implementation Details

1. **File discovery**: Use Bash `find` or `ls` based on task description
2. **Chunking**: Divide files evenly among N agents
3. **Parallel spawning**: Single message with multiple Task tool calls
4. **Result aggregation**: Parse JSON returns from subagents
5. **Question batching**: Collect, dedupe, present in groups of 4
6. **Progress tracking**: TodoWrite updated after each batch

### Technology Choices

- **Task tool**: Native Claude Code parallel agent spawning
- **Bash**: File discovery (find, ls, wc)
- **TodoWrite**: Progress tracking visible to user
- **AskUserQuestion**: Batched user decisions
- **bmem skill**: Session logging

No external scripts needed - this is pure orchestration.

## Failure Modes

### What Could Go Wrong?

1. **Failure mode**: Context exhaustion mid-batch
   - **Detection**: Agent responses degrade or fail
   - **Impact**: Incomplete processing
   - **Prevention**: Warn on large batches, keep main thread lightweight
   - **Recovery**: Commit partial progress, log remaining files

2. **Failure mode**: Subagent doesn't invoke required skill
   - **Detection**: Results lack expected structure
   - **Impact**: Poor quality processing
   - **Prevention**: MANDATORY skill invocation in subagent prompt
   - **Recovery**: Log violation, potentially re-process file

3. **Failure mode**: Question overflow (100+ questions)
   - **Detection**: AskUserQuestion becomes unwieldy
   - **Impact**: User frustration
   - **Prevention**: Batch questions in groups of 4, multiple rounds OK
   - **Recovery**: Present most important questions first

4. **Failure mode**: Git commit fails (conflicts, hooks)
   - **Detection**: Bash returns non-zero
   - **Impact**: Changes not persisted
   - **Prevention**: Check git status before commit
   - **Recovery**: Report error, user resolves manually

## Monitoring and Validation

### How do we know it's working?

**Metrics to track**:

- Files processed per minute
- Subagent success rate
- Questions per batch (lower is better = more obvious decisions)
- Context usage (main thread tokens)

**Monitoring approach**:

- TodoWrite provides real-time progress visibility
- Session log (bmem) captures final statistics
- Errors logged inline for debugging

**Validation frequency**: Review after first 3 uses, then as needed.

## Documentation Requirements

### Code Documentation

- [ ] Command file has clear orchestration instructions
- [ ] Subagent prompt template documented
- [ ] Question batching logic explained

### User Documentation

- [ ] Examples in command description
- [ ] Limitations documented (context window, no persistence)
- [ ] Troubleshooting for common issues

### Maintenance Documentation

- [ ] How to adjust concurrency
- [ ] How to add new operation types
- [ ] Known limitations and future work

## Rollout Plan

### Phase 1: Validation (Experiment)

- Implement command with task-linking use case
- Test with 10-20 tasks
- Verify question batching works
- Document in experiment log

**Criteria to proceed**: Successfully processes batch, questions batched, commit created

### Phase 2: Limited Deployment

- Use for real task-linking work
- Try with email extraction (existing use case)
- Gather feedback on usability

**Criteria to proceed**: 3 successful real-world uses

### Phase 3: Full Deployment

- Document as production command
- Add to skills/README.md
- Create additional operation templates as needed

**Rollback plan**: Remove command file, revert to ad-hoc parallel spawning

## Risks and Mitigations

**Risk 1**: Command prompt too complex for reliable parsing

- **Likelihood**: Medium
- **Impact**: Medium (wrong files processed)
- **Mitigation**: Conservative parsing, confirm file list before processing

**Risk 2**: Subagents don't return structured JSON

- **Likelihood**: Low (with clear prompt)
- **Impact**: Medium (can't aggregate results)
- **Mitigation**: Strict return format in prompt, validate responses

**Risk 3**: User overwhelmed by question batches

- **Likelihood**: Low
- **Impact**: Medium (user frustration)
- **Mitigation**: Smart defaults, "apply same answer to similar" option

## Open Questions

1. Should concurrency be user-configurable per invocation or fixed?
   - **Leaning**: Fixed at 4, allow override via `--concurrency N`

2. How to handle files that need multiple skills?
   - **Leaning**: Subagent invokes skills as needed based on operation

3. Should we track processed files to enable resume?
   - **Leaning**: No (violates no-persistence constraint), but log progress

4. Maximum batch size before warning?
   - **Leaning**: 50 files, warn above that

## Completion Checklist

Before marking this task as complete:

- [ ] All success criteria met and verified
- [ ] Integration test passes reliably
- [ ] All failure modes addressed
- [ ] Documentation complete (code, user, maintenance)
- [ ] Experiment log entry created
- [ ] No documentation conflicts introduced
- [ ] Code follows AXIOMS.md principles
- [ ] Monitoring in place and working
- [ ] Rollout plan executed successfully
- [ ] Framework STATE.md updated with progress
