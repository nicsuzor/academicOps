---
name: batch-review
category: instruction
description: Parallel batch processing with quality gates, critic review, and QA verification
required-skills:
  - framework
scope:
  - Processing multiple files in parallel
  - Batch operations with quality control
  - Review tasks requiring parallel agents
  - Any work where multiple items need consistent treatment
---

# Batch Review Workflow Template

This workflow combines parallel batch processing with supervisor quality gates: plan review, parallel execution, question batching, and QA verification.

## Workflow Compliance

1. Plan (define operation, get critic review, document acceptance criteria)
2. Parallel execution (spawn 4-8 agents on file subsets)
3. Question batching (collect uncertainties, batch ask user)
4. QA verification (independent verification of outcomes)
5. Done = all files processed + changes committed + pushed

---

## ITERATION UNIT

One batch cycle = process file subset → collect results → batch questions → apply answers

Each cycle:
1. Spawn parallel agents on file subset (4-8 agents)
2. Collect results: changes made, questions raised, errors
3. Batch questions to user (max 4 per AskUserQuestion)
4. Apply user decisions via new agent spawns
5. Commit and push before next batch

---

## QUALITY GATE

Before proceeding to next batch:

- [ ] All agents in batch reported results
- [ ] All questions for this batch answered
- [ ] User decisions applied
- [ ] Changes committed and pushed
- [ ] No unhandled errors remaining

---

## PHASE 1: DISCOVERY AND PLANNING

### 1.1 Parse Task Description

Extract from `$ARGUMENTS`:
- Target files (directory path, glob pattern)
- Operation to perform on each file
- Skills needed for the operation

### 1.2 Discover Files

```
Task(subagent_type="Explore", prompt="
Find all files matching the task description.

Target: {directory or pattern}
Operation: {what to do with files}

Use Glob or Bash find to list all matching files.

Report:
- Total file count
- File list (first 50 if many)
- Estimated batches needed (files / 4)
")
```

**Validation:**
- If 0 files: Error and stop
- If >50 files: Warn user, proceed unless they stop
- If >100 files: Suggest splitting across sessions

### 1.3 Get Critic Review of Plan

```
Task(subagent_type="critic", model="haiku", prompt="
Review this batch processing plan:

Files to process: {count}
Operation: {description}
Batches: {count / 4}
Skills required: {skills}

Check for:
- Is the operation well-defined?
- Are there edge cases that might cause inconsistent treatment?
- Could parallel processing cause conflicts (same file by 2 agents)?
- Is the batch size appropriate?
- Are the required skills available?
")
```

**If critic returns REVISE**: Address issues before proceeding.

---

## PHASE 2: PARALLEL PROCESSING

### Spawn Parallel Agents

Spawn **4 parallel Task agents** (or 8 for batches >30 files).

Use a SINGLE message with multiple Task tool calls:

```
Task(subagent_type="general-purpose", prompt="
Process these files for {operation}:

Files to process:
1. {file1}
2. {file2}
...

**FIRST**: Invoke Skill(skill='{required-skill}') to load standards.

TASK: {detailed operation description}

For each file:
1. Read the file
2. Analyze per the operation requirements
3. If the correct action is OBVIOUS (>80% confidence) → make the change
4. If the action NEEDS USER INPUT → add to questions list (do NOT guess)

IMPORTANT: Make obvious decisions yourself. Only ask questions when genuinely uncertain.

Return your results as structured summary:
- Files processed: [list]
- Changes made: [list with brief description]
- Questions for user: [list with file, question, and 2-4 options]
- Errors encountered: [list]
")
```

**Repeat** spawning agents until all files processed.

---

## PHASE 3: QUESTION BATCHING

After all agents complete, collect all questions.

### Batch Questions to User

Use AskUserQuestion with UP TO 4 questions per call:

```
AskUserQuestion(questions=[
  {
    "question": "{question from agent 1}",
    "header": "File 1",
    "options": [
      {"label": "{option1}", "description": "{description1}"},
      {"label": "{option2}", "description": "{description2}"},
      {"label": "Skip", "description": "Leave unchanged for now"}
    ],
    "multiSelect": false
  },
  {
    "question": "{question from agent 2}",
    "header": "File 2",
    ...
  }
])
```

### Apply User Decisions

Spawn Task agents to apply user's answers:

```
Task(subagent_type="general-purpose", prompt="
Apply these user decisions:

1. File: {file1}, Decision: {user_choice1}
2. File: {file2}, Decision: {user_choice2}
...

For each decision, make the change as specified.
Report what was changed.
")
```

**Repeat** if more questions remain (batches of 4).

---

## PHASE 4: COMMIT AND VERIFY

### Commit Changes

```
Task(subagent_type="general-purpose", prompt="
Commit all changes from this batch processing session.

1. Run: git add -A
2. Run: git status (show what will be committed)
3. Create commit with message describing the batch operation
4. Push to remote

Report:
- Files changed
- Commit hash
- Push status
")
```

### QA Verification

```
Task(subagent_type="general-purpose", prompt="
Verify the batch processing results.

**Acceptance Criteria** (from Phase 0):
{list acceptance criteria}

Verification:
1. Sample 3-5 processed files
2. Check each matches the expected outcome
3. Verify no files were missed
4. Check for consistency across processed files

Report:
- Sampled files and verification result
- Any inconsistencies found
- APPROVED or REJECTED with reasons
")
```

---

## COMPLETION CRITERIA

Batch review complete when:
- All files in scope processed
- All user questions answered and decisions applied
- QA verification passed
- Changes committed and pushed
- Summary report provided to user

---

## Subagent Prompt Templates

### For Knowledge Extraction

```
Process these files to extract valuable knowledge:

Files: {file_list}

**FIRST**: Invoke Skill(skill="extractor") to assess importance, then Skill(skill="remember") to store.

For each file:
1. Read content
2. Apply extractor skill criteria
3. If valuable → save with remember skill
4. If not valuable → skip (no question needed)
5. If uncertain → add to questions

Return: processed files, entities created, questions for uncertain cases
```

### For Categorization/Tagging

```
Process these files to add appropriate tags/categories:

Files: {file_list}

**FIRST**: Invoke Skill(skill="remember") for memory server operations.

For each file:
1. Read content
2. Identify appropriate tags based on {criteria}
3. If obvious → add tags
4. If multiple valid options → add to questions

Return: processed files, tags added, questions for ambiguous cases
```

### For Content Review

```
Process these files to review for {criteria}:

Files: {file_list}

**FIRST**: Invoke Skill(skill="framework") to load conventions.

For each file:
1. Read content
2. Check against {criteria}
3. If compliant → note as passing
4. If violation found → report with file:line
5. If uncertain → add to questions

Return: files reviewed, violations found, questions for ambiguous cases
```

---

## Error Handling

- **File not found**: Log error, continue with remaining files
- **Agent fails**: Log error, report at end, don't retry
- **Skill not invoked**: Agent output is suspect - note in report
- **Git commit fails**: Report error, user resolves manually

---

## Concurrency Guidelines

- **Default**: 4 parallel agents
- **Large batches (>30 files)**: 8 parallel agents
- **Very large (>100 files)**: Warn user, suggest splitting

---

## Example Invocation

```
/supervise batch-review Review all markdown files in data/tasks/ and ensure each has valid YAML frontmatter with required fields (title, status, priority)
```
