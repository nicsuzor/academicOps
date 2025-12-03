---
name: learning-log
description: Log agent performance patterns to thematic learning files. Categorizes observations, finds similar patterns via bmem, and appends structured entries.
---

# Learning Log Skill

Document agent behavior patterns in thematic learning files. Transform user observations into structured entries with pattern categorization and knowledge linking.

## Quick Start

When invoked with an observation:

1. **Categorize** - Assign pattern tags based on observation content
2. **Link** - Search bmem for related patterns
3. **Route** - Select target thematic file based on tags
4. **Format** - Create structured entry
5. **Append** - Add to appropriate thematic file

## Pattern Tags and File Routing

| Tags | Target File |
|------|-------------|
| #verify-first, #overconfidence, #validation, #incomplete-task | `verification-discipline.md` |
| #instruction-following, #scope, #literal, #user-request | `instruction-following.md` |
| #git-safety, #no-verify, #validation-bypass, #pre-commit | `git-and-validation.md` |
| #skill-invocation, #tool-usage, #mcp, #bmem-integration | `skill-and-tool-usage.md` |
| #tdd, #testing, #test-contract, #fake-data | `test-and-tdd.md` |
| #success, #tdd-win, #workflow-success (or Type is Success) | `technical-wins.md` |

**Default**: `verification-discipline.md` if no clear match.

**Target path**: `$ACA_DATA/projects/aops/learning/[file].md`

## Entry Format

```markdown
## [Brief Title]

**Date**: YYYY-MM-DD | **Type**: Success/Failure | **Pattern**: #tag1 #tag2

**What**: [One sentence - what happened]
**Why**: [One sentence - significance]
**Lesson**: [One sentence - actionable takeaway]
```

## Workflow

### 1. Receive Observation

Accept description from /log command. Can be:
- Success: "Agent correctly used task scripts"
- Failure: "Test failed with file not found error"
- Pattern: "Agent asked before using --no-verify"

### 2. Categorize

Classify as Success or Failure based on markers:

**Success markers**: "worked", "correctly", "successfully", "as expected"
**Failure markers**: "failed", "error", "bug", "wrong", "didn't work"

If both present, classify as Failure.

### 3. Assign Tags

Choose 1-3 relevant tags from the table above. Primary tag determines file routing.

### 4. Link Knowledge (bmem)

Search for related patterns:
```
mcp__bmem__search_notes(query="[key terms from observation]", project="main")
```

Include relevant cross-references in entry if found.

### 5. Format Entry

Create entry following the format specification above.

### 6. Validate Target File

Before appending:
1. Verify file exists at `$ACA_DATA/projects/aops/learning/[file].md`
2. Check frontmatter has: title, permalink, type, tags
3. If invalid - HALT with error

### 7. Append Entry

Use Edit tool to append formatted entry to end of file.

### 8. Report

Confirm:
- File selected
- Tags assigned
- Cross-references found (if any)
- Entry appended

## Constraints

**DO ONE THING**: This skill documents observations only. It does NOT:
- Fix reported issues
- Implement solutions
- Debug problems (use framework-debug skill for that)

**VERIFY-FIRST**: Before categorizing, review observation carefully. Never categorize on keywords alone.

## Example

```
User: /log Agent correctly used task scripts instead of writing files directly

Workflow:
1. Categorize: Success (markers: "correctly")
2. Tags: #workflow-success #tool-usage
3. bmem search: "task scripts task management"
4. Target file: technical-wins.md (success type)
5. Format entry:
   ## Agent Used Task Scripts Correctly
   **Date**: 2025-12-03 | **Type**: Success | **Pattern**: #workflow-success #tool-usage
   **What**: Agent invoked task_add.py script instead of writing task markdown directly.
   **Why**: Follows documented task management architecture requiring script-only write access.
   **Lesson**: Script-based task operations working as designed.
6. Validate technical-wins.md
7. Append entry
8. Report: "Logged to technical-wins.md with #workflow-success #tool-usage"
```
