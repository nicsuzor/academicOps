---
name: bmem-validate
description: Validate and fix bmem files in parallel batches using haiku agents
permalink: commands/bmem-validate
---

# bmem Batch Validator

Orchestrate parallel validation of bmem files using 8 concurrent haiku agents.

## Usage

```
/bmem-validate [path] [batch-size]
```

- `path`: Directory to scan (default: ~/writing/data)
- `batch-size`: Files per agent (default: 10)

## Workflow

### 1. Discover Files

```bash
find ~/writing/data -name "*.md" -type f | shuf
```

### 2. Create Batches

Split files into batches of 10. Calculate number of batches needed.

### 3. Spawn Agents (8 concurrent max)

Use a SINGLE message with multiple Task tool calls to spawn up to 8 agents in parallel:

```
Task(
  subagent_type="bmem-validator",
  model="haiku",
  prompt="Process these files: [list of 10 files]"
)
```

### 4. Collect Results

After each wave of 8 agents completes:
- Aggregate error counts
- Track files processed
- Continue with next wave if files remain

### 5. Report

Final summary:
- Total files processed
- Total errors fixed
- Any files that failed

## Agent Prompt Template

For each batch, send this prompt to bmem-validator agent:

```
Process these bmem files for validation and fixing:

Files:
1. /path/to/file1.md
2. /path/to/file2.md
...

Return summary of files processed, errors found, and fixes applied.
```

## Example

```
/bmem-validate ~/writing/data/contacts 15
```

Validates all .md files in contacts/ with 15 files per agent batch.
