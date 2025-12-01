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

### 1. Run Validation Script

```bash
cd ~/writing && uv run python bmem_tools.py validate 2>&1
```

This outputs errors like:
```
WARNING: data/projects/file.md:24 Unknown observation category: [meeting]
ERROR: data/goals/file.md: Missing required frontmatter field: title
```

### 2. Extract Files with Errors

Parse output to get unique files with errors/warnings:
```bash
cd ~/writing && uv run python bmem_tools.py validate 2>&1 | grep -oP '(?<=: )data/[^:]+' | sort -u
```

### 3. Create Batches

Split files into batches of 10. Calculate number of batches needed.

### 4. Spawn Agents (8 concurrent max)

Use a SINGLE message with multiple Task tool calls to spawn up to 8 agents in parallel:

```
Task(
  subagent_type="bmem-validator",
  model="haiku",
  prompt="Process these files: [list of 10 files]"
)
```

### 5. Collect Results

After each wave of 8 agents completes:
- Aggregate error counts
- Track files processed
- Re-run validation to confirm fixes

### 6. Report

Final summary:
- Total files processed
- Total errors fixed
- Remaining errors (if any)

## Agent Prompt Template

For each batch, send this prompt to bmem-validator agent:

```
Process these bmem files for validation and fixing:

Files:
1. /home/nic/writing/data/path/to/file1.md
2. /home/nic/writing/data/path/to/file2.md
...

Return summary of files processed, errors found, and fixes applied.
```

## Example

```
/bmem-validate ~/writing/data/contacts 15
```

Validates all .md files in contacts/ with 15 files per agent batch.
