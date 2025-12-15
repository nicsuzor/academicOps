---
name: learning-log
description: Log agent performance patterns to thematic learning files. Categorizes observations, matches to experiments, and routes to appropriate tracking files.
allowed-tools: Read,Grep,Glob,Edit,Write,Bash
version: 2.0.0
permalink: skills-learning-log
---

# Learning Log Skill

Document agent behavior patterns with appropriate abstraction level routing. Creates chronological log entries, matches to active experiments, and routes to bugs/patterns/experiments based on issue type.

## Three-Phase Workflow

### Phase 1: Append to LOG.md

**Always first**: Create append-only entry in `$ACA_DATA/projects/aops/learning/LOG.md`

```markdown
### YYYY-MM-DD HH:MM | [category] | [descriptive-slug]

**Error**: [brief description]
**Investigation**: [for file errors - see File Error Investigation Protocol; omit for non-file errors]
**Root Cause**: [why it happened - must cite investigation evidence if available]
**Abstraction Level**: component | pattern | systemic
**Related**: [file path if matched, "pending" if creating new]
```

**Entry title format**:
- **Category**: The failure mode category matching target learning file:
  - `skill-bypass` → skill-bypass.md
  - `verification-skip` → verification-skip.md
  - `instruction-ignore` → instruction-ignore.md
  - `validation-bypass` → validation-bypass.md
  - `external` → external issue, not framework
- **Descriptive slug**: kebab-case description of what happened (e.g., `task-file-direct-write`, `framework-command-namespace-collision`)

**For file-related errors**: Complete the File Error Investigation Protocol (below) BEFORE filling in Root Cause.

### Phase 2: Match to Active Experiments

Search `$ACA_DATA/projects/aops/experiments/` for experiments that:
- Are not marked complete/decided (check Decision section)
- Have hypothesis related to the observed behavior

**If match found**:
1. Append observation to experiment's Results section with date
2. Update LOG.md entry's "Related" field

### Phase 3: Route by Abstraction Level

Determine the appropriate level and route accordingly:

| Level | Criteria | Action |
|-------|----------|--------|
| `component` | Specific, reproducible bug in named script/file | Create/update `bugs/[component].md` |
| `pattern` | Behavioral pattern across agents/sessions | Append to `learning/[theme].md` |
| `systemic` | Infrastructure issue needing investigation | Create/update experiment |

#### Component-Level (bugs/)

For specific script errors (e.g., task_view.py fails, hook crashes):
- Check if `$ACA_DATA/projects/aops/bugs/[component].md` exists
- If yes: append new observation
- If no: create with bmem frontmatter
- **Delete when fixed** (per framework conventions)

#### Pattern-Level (learning/)

For behavioral patterns (e.g., agents ignoring instructions):
- Route to existing thematic file based on tags
- Use standard entry format (see below)

#### Systemic-Level (experiments/)

For issues needing investigation:
1. **Search first**: Look for thematically similar experiments
2. **If related experiment exists**: Update that experiment, don't create new
3. **If no match**: Create `experiments/[date]-[topic].md`
4. **Consolidation rule**: When creating new, actively look for experiments to merge. Rename/consolidate as understanding improves.

## File Error Investigation Protocol

**When error involves file operations** (wrong path, wrong content, unexpected file creation/modification):

Before completing the **Root Cause** field in Phase 1, **investigate**:

### 1. Identify Affected Files

Get specific path(s) from the error description.

### 2. Check File Modification Time

```bash
stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" <file_path>
# Or for multiple files:
ls -la <directory>
```

### 3. Find Sessions Active Around That Time

Use session_reader to find sessions in 30-minute window before file mtime:

```bash
# List recent sessions for this project
ls -lt ~/.claude/projects/-Users-suzor-writing/*.jsonl | head -10
```

Or use Python:
```python
from lib.session_reader import find_sessions
from datetime import datetime, timedelta
sessions = find_sessions(project="writing", since=file_mtime - timedelta(minutes=30))
```

### 4. Search Sessions for Write/Edit Operations

Look for tool_use blocks with:
- `name`: "Write", "Edit", "mcp__bmem__write_note"
- `input.file_path` or `input.path` matching affected file

```bash
# Quick grep for path in recent sessions
grep -l "affected/path" ~/.claude/projects/-Users-suzor-writing/*.jsonl
```

### Investigation Results Format

Include in LOG.md entry:

```markdown
**Investigation**:
- File mtime: [timestamp]
- Sessions checked: [session-id-prefixes] ([N] sessions in window)
- Found: session [id] used [Tool]("[path]") at [time]
```

Or if inconclusive:

```markdown
**Investigation**:
- File mtime: [timestamp]
- Sessions checked: [ids] ([N] sessions)
- Found: No matching Write/Edit operations in checked sessions
```

### Critical Rule

**If investigation is inconclusive, state that explicitly.** Do NOT:
- Speculate about cause ("agent or bmem may have...")
- Attribute without evidence
- Skip investigation for file-related errors

## Root Cause Verification Requirement

**For ANY root cause claim**: You must have direct evidence, not inference.

❌ **WRONG**: "Investigation confirmed hook IS working (file not written)" - without actually checking if file exists
✅ **RIGHT**: Run `ls -la <path>` or equivalent verification before claiming outcome

**Claims requiring verification**:
- "File was/wasn't written" → Check with `ls -la`
- "Hook blocked/allowed operation" → Check both hook output AND actual outcome
- "Error was X not Y" → Reproduce or cite exact error message

**If you cannot verify, say "Unverified" in Root Cause field.**

---

## Abstraction Level Judgment

**Key principle**: Match abstraction to likely intervention specificity.

Examples:
- "task_view.py throws KeyError" → `component` (fix that script)
- "Two agents both ignored explicit user request" → `pattern` (instruction presentation issue)
- "Hooks seem to not be loading context" → `systemic` (needs investigation)

**Don't**:
- Create separate bug files for instances of the same pattern
- Lump specific script bugs into general categories

## Pattern Tags and Thematic Routing

| Tags | Target File |
|------|-------------|
| #verify-first, #overconfidence, #validation, #incomplete-task | `verification-skip.md` |
| #instruction-following, #scope, #literal, #user-request | `instruction-ignore.md` |
| #git-safety, #no-verify, #validation-bypass, #pre-commit | `validation-bypass.md` |
| #skill-invocation, #tool-usage, #mcp, #bmem-integration | `skill-bypass.md` |
| #tdd, #testing, #test-contract, #fake-data | `test-and-tdd.md` |
| #success, #tdd-win, #workflow-success | `technical-wins.md` |

**Default**: `verification-skip.md` if no clear match.

## Entry Formats

### LOG.md Entry (Phase 1)

```markdown
### YYYY-MM-DD HH:MM | [category] | [descriptive-slug]

**Error**: [brief description]
**Investigation**: [for file errors - results of investigation protocol; omit for non-file errors]
**Root Cause**: [analysis - must cite evidence from investigation if available]
**Abstraction Level**: component | pattern | systemic
**Related**: bugs/component.md | learning/theme.md | experiments/file.md
```

Categories: `skill-bypass`, `verification-skip`, `instruction-ignore`, `validation-bypass`, `external`

### Learning File Entry (Pattern Level)

```markdown
## [Brief Title]

**Date**: YYYY-MM-DD | **Type**: Success/Failure | **Pattern**: #tag1 #tag2

**What**: [One sentence - what happened]
**Why**: [One sentence - significance]
**Lesson**: [One sentence - actionable takeaway]
```

### Bug File Format (Component Level)

```markdown
---
title: [Component] Errors
type: bug
permalink: bugs-[component]
tags:
  - bug
  - [component]
---

# [Component] Errors

## Observations

### YYYY-MM-DD
- [fact] [error description] #bug
- [context] [when it occurred]
- [status] open | investigating | fixed
```

### Experiment Entry (Systemic Level)

Follow `$ACA_DATA/projects/aops/experiments/TEMPLATE.md`

## Log Consolidation Workflow

Periodically consolidate LOG.md entries into thematic learning files and archive processed entries.

### Consolidation Triggers

Any of these should trigger consolidation:

1. **Manual**: User runs `/consolidate` or asks to "consolidate logs"
2. **Threshold**: LOG.md exceeds 20 entries OR 14 days since last consolidation
3. **Pattern detection**: Same error type (by Related field) appears 3+ times

### Consolidation Process

1. **Read LOG.md** - Load all entries
2. **Group by Related field** - Cluster entries pointing to same learning file
3. **For each cluster with 2+ entries**:
   - Extract common pattern across entries
   - Check if pattern already exists in target learning file
   - If new pattern: append to learning file with consolidated evidence
   - If existing pattern: add dated observations to Evidence section
4. **Archive processed entries** - Move to `LOG-ARCHIVE.md` with consolidation date
5. **Update LOG.md** - Remove archived entries, keep header

### Consolidated Entry Format (for learning files)

```markdown
## [Pattern Title]

**Date**: [consolidation date] | **Type**: Consolidated | **Pattern**: #tag1 #tag2

**Observations** (N instances):
- [date]: [brief description]
- [date]: [brief description]

**Common Factor**: [what these instances share]
**Lesson**: [actionable takeaway]
```

### Archive Format (LOG-ARCHIVE.md)

```markdown
---
title: Framework Learning Log Archive
type: log-archive
---

# Log Archive

## Consolidated [YYYY-MM-DD]

[Entries that were consolidated on this date, preserving original format]

---
```

### Consolidation Output

After consolidation, report:
- Entries processed: N
- Patterns identified: N
- Learning files updated: [list]
- Entries archived: N

---

## Input Types

1. **Verbal description** - User describes what happened
2. **Transcript file(s)** - Path to transcript markdown
3. **Session JSONL** - First invoke `transcript` skill, then analyze
4. **Heuristic adjustment** - `adjust-heuristic H[n]: [observation]`

## Heuristic Adjustment Mode

When input contains `adjust-heuristic H[n]:`:

1. Parse heuristic ID and observation
2. Read `$AOPS/HEURISTICS.md`
3. Add dated evidence to heuristic
4. Adjust confidence if warranted
5. Also log to LOG.md and appropriate thematic file

## Constraints

**DO ONE THING**: Document observations only. Do NOT:
- Fix reported issues
- Implement solutions
- Debug problems

**VERIFY-FIRST**: Review observation carefully before categorizing.

## Example

```
User: /log agent ignored my explicit request to run ALL tests, only ran 3

Phase 1 - LOG.md:
### 2025-12-14 08:45 | instruction-ignore | partial-test-run-despite-all-request

**Error**: Agent ran only 3 tests when explicitly asked to run ALL
**Root Cause**: Agent not attending to explicit scope instruction
**Abstraction Level**: pattern
**Related**: learning/instruction-ignore.md

Phase 2 - Experiment Match:
Search experiments/ for "instruction following" → no active experiment

Phase 3 - Route:
- Level: pattern (behavioral, not script-specific)
- Tags: #instruction-following #scope
- Target: instruction-ignore.md
- Append entry

Report: "Logged to instruction-ignore.md - recurring pattern of agents not attending to explicit scope instructions"
```
