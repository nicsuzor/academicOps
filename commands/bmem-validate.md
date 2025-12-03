---
name: bmem-validate
description: Validate and fix bmem files in parallel batches using haiku agents
permalink: commands/bmem-validate
tools:
  - Task
  - Bash
  - TodoWrite
  - Read
  - Glob
---

# bmem Batch Validator

Orchestrate parallel validation of bmem files using up to 8 concurrent agents.

## Usage

```
/bmem-validate [path] [batch-size]
```

- `path`: Directory to scan (default: ~/writing/data)
- `batch-size`: Files per agent (default: 10)

## Workflow

### Phase 1: Discovery

1. **Run validation script**:
```bash
cd ~/writing && uv run python scripts/bmem_tools.py validate 2>&1
```

2. **Extract files with ERRORs** (focus on errors, not warnings):
```bash
cd ~/writing && uv run python scripts/bmem_tools.py validate 2>&1 | grep -E '^ERROR:' | grep -oP '(?<=: )data/[^:]+' | sort -u
```

3. **Count and assess**:
   - If 0 files: Report success, stop
   - If >100 files: Warn user, proceed in waves

4. **Create TodoWrite checklist** with batch tracking

### Phase 2: Parallel Processing

**Spawn up to 8 parallel Task agents** using `subagent_type="bmem-validator"`.

Each agent receives 10 files. Use a SINGLE message with multiple Task tool calls:

```
Task(
  subagent_type="bmem-validator",
  model="haiku",
  prompt="Fix bmem validation errors in these files:

Files to process:
1. /home/nic/writing/data/context/file1.md
2. /home/nic/writing/data/context/file2.md
...

TASK: Fix bmem validation errors. Common issues:
- Invalid permalinks (must be lowercase alphanumeric with hyphens only, NO slashes)
- H1 heading must match frontmatter title exactly
- Missing ## Observations or ## Relations sections
- Invalid relation syntax (must be '- relation_type [[Target]]' format)

MANDATORY: Use Skill tool first: Skill(skill='bmem') to load format rules.

For each file:
1. Read the file
2. Identify validation errors
3. Fix them using Edit tool
4. Track what was fixed

Return structured summary:
- Files processed: [count]
- Errors fixed: [list with file and fix description]
- Errors encountered: [any failures]
")
```

### Phase 3: Verification

After agents complete:
1. Re-run validation to confirm fixes
2. If errors remain, spawn another wave
3. Report final counts

### Phase 4: Completion

1. Update TodoWrite - mark complete
2. Report to user:
   - Files processed
   - Errors fixed
   - Remaining errors (if any)

## Concurrency Guidelines

- **Default**: 4 parallel agents
- **Large batches (>40 files)**: 8 parallel agents
- **Very large (>100 files)**: Process in waves of 80

## Anti-Patterns to Avoid

❌ Skipping Skill invocation in subagent prompts
❌ Processing sequentially instead of parallel
❌ Forgetting to verify fixes with re-validation
