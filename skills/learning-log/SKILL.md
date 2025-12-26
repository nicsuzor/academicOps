---
name: learning-log
description: Log agent performance patterns to GitHub Issues. Categorizes observations and routes to appropriate issue labels.
allowed-tools: Read,Grep,Glob,Bash,mcp__gh__issue_write,mcp__gh__search_issues,mcp__gh__add_issue_comment
version: 3.0.0
permalink: skills-learning-log
---

# Learning Log Skill

Document agent behavior patterns as GitHub Issues (per AXIOMS #28: episodic content → GitHub Issues).

**Key change (v3.0)**: All observations now go to GitHub Issues in `nicsuzor/writing` repo, NOT local files.

## Workflow

### Phase 1: Search for Existing Issue

**First**: Search for existing Issue that matches this observation:

```bash
gh issue list --repo nicsuzor/writing --label "[category]" --search "[keywords]" --state open
```

Categories/labels:
- `bug` - Component-level bugs (script errors, hook crashes)
- `learning` - Pattern-level observations (agent behavior patterns)
- `experiment` - Systemic investigations (infrastructure issues)
- `devlog` - Development observations

### Phase 2: Create or Update Issue

**If matching Issue exists**: Add comment with new observation

```bash
gh issue comment [ISSUE_NUMBER] --repo nicsuzor/writing --body "## Observation [DATE]

**What**: [description]
**Context**: [when/where]
**Evidence**: [specifics]"
```

**If no matching Issue**: Create new Issue

```bash
gh issue create --repo nicsuzor/writing \
  --title "[category]: [descriptive-title]" \
  --label "[category]" \
  --body "## Initial Observation

**Date**: YYYY-MM-DD
**Error**: [brief description]
**Root Cause**: [analysis]
**Level**: component | pattern | systemic

## Evidence

[details]"
```

### Phase 3: Link to User Stories (if applicable)

Read `$ACA_DATA/projects/aops/ROADMAP.md` for User Stories table.

If observation relates to a user story, add to Issue body:
```
**User Story**: [story-name]
```

### Phase 4: Synthesis Check

When pattern emerges across multiple Issues:
1. Create/update HEURISTICS.md entry (semantic doc)
2. Close related Issues with link: "Synthesized to HEURISTICS.md H[n]"

Closed Issues remain searchable via GitHub.

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
- `name`: "Write", "Edit", "mcp__memory__store_memory"
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
- Speculate about cause ("agent or memory server may have...")
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

## Issue Labels (Categories)

| Label | Use For | Example Title |
|-------|---------|---------------|
| `bug` | Component-level bugs | `bug: task_view.py KeyError on missing field` |
| `learning` | Agent behavior patterns | `learning: agents ignoring explicit scope` |
| `experiment` | Systemic investigations | `experiment: hook context injection timing` |
| `devlog` | Development observations | `devlog: session-insights workflow` |
| `decision` | Architectural choices | `decision: GitHub Issues for episodic storage` |

**Default**: `learning` if unclear.

## Issue Format

### New Issue Body

```markdown
## Initial Observation

**Date**: YYYY-MM-DD
**Category**: bug | learning | experiment | devlog | decision
**Error/Observation**: [brief description]
**Root Cause**: [analysis, or "investigating"]
**Level**: component | pattern | systemic

## Evidence

[Detailed evidence, error messages, session references]

## Related

- User Story: [if applicable]
- Related Issues: #[number] [if applicable]
```

### Comment Format (for updates)

```markdown
## Observation YYYY-MM-DD

**What**: [description]
**Context**: [when/where]
**Evidence**: [specifics]
```

## Synthesis Workflow

When patterns emerge across Issues, synthesize to semantic docs:

### Synthesis Triggers

- Same root cause appears in 3+ Issues
- Pattern spans multiple sessions/dates
- Actionable heuristic becomes clear

### Synthesis Process

1. **Identify pattern** across related Issues
2. **Draft heuristic** following HEURISTICS.md format
3. **Add to HEURISTICS.md** with evidence references
4. **Close Issues** with comment: "Synthesized to HEURISTICS.md H[n]"

### Post-Synthesis

Closed Issues remain searchable. GitHub search finds them by:
- Label (e.g., `label:learning`)
- Keywords in title/body
- Date range

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

Phase 1 - Search:
gh issue list --repo nicsuzor/writing --label "learning" --search "instruction scope" --state open
→ Found: #42 "learning: agents ignoring explicit scope instructions"

Phase 2 - Update existing Issue:
gh issue comment 42 --repo nicsuzor/writing --body "## Observation 2025-12-14

**What**: Agent ran only 3 tests when explicitly asked to run ALL
**Context**: During TDD workflow
**Evidence**: Transcript shows 'run ALL tests' instruction followed by partial execution"

Report: "Added observation to Issue #42 - recurring pattern of agents not attending to explicit scope instructions"
```

### Example: New Issue

```
User: /log hook crashed with TypeError in prompt_router.py

Phase 1 - Search:
gh issue list --repo nicsuzor/writing --label "bug" --search "prompt_router TypeError" --state open
→ No matching issues

Phase 2 - Create new Issue:
gh issue create --repo nicsuzor/writing \
  --title "bug: prompt_router.py TypeError on None response" \
  --label "bug" \
  --body "## Initial Observation

**Date**: 2025-12-26
**Category**: bug
**Error**: TypeError: 'NoneType' object has no attribute 'get'
**Root Cause**: investigating
**Level**: component

## Evidence

Stack trace:
[error details]"

Report: "Created Issue #47 for prompt_router bug investigation"
```
