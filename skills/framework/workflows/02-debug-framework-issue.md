---
title: Debug Framework Issue
type: automation
permalink: workflow-debug-framework-issue
description: Process for diagnosing and fixing framework component failures and integration issues
---

# Workflow 2: Debug Framework Issue

**When**: Framework component failing, unexpected behavior, integration broken.

**Key principle**: Use **controlled tests in /tmp** to run experiments and validate hypotheses. Read **Claude session logs** to understand agent behavior.

**Steps**:

1. **Reproduce the issue with controlled test**
   - Run test with `--debug` flag (fixture does this automatically)
   - Test runs in `/tmp/claude-test-*` directory (controlled environment)
   - Required env vars (`AOPS`, `ACA_DATA`) must be set (fail-fast if missing)
   - Document exact steps to trigger issue
   - Verify issue exists (not user error)

2. **Read Claude session logs to understand behavior**
   - Session logs stored in `~/.claude/projects/-tmp-claude-test-*/`
   - Use ripgrep to search logs: `rg "pattern" ~/.claude/projects/-tmp-claude-test-*/`
   - Check JSONL files for:
     - User prompts sent to agent
     - Tool calls made by agent
     - Agent's reasoning and decisions
     - Error messages or failures
   - Look for: Did agent read the right files? Follow instructions? Use correct tools?

3. **Form hypothesis about root cause**
   - Verify component follows single source of truth
   - Look for duplication or conflicts
   - **Agent behavior analysis**: Did agent receive correct context? Interpret instructions correctly?

4. **Test hypothesis with controlled experiment**
   - Modify one variable at a time
   - Run test in `/tmp` with `--debug` flag
   - Read session logs to confirm behavior change
   - Iterate until hypothesis confirmed
   - **Pattern**: Change → Test → Read logs → Refine hypothesis

5. **Design minimal fix**
   - Minimal change to address root cause
   - Avoid workarounds
   - Maintain documentation integrity
   - **Fail-fast enforcement**: Add validation that fails immediately on misconfiguration

6. **Create/update integration test**
   - Test must fail with current broken state
   - Test must pass with fix applied
   - Cover regression cases
   - **E2E test**: Agent must actually read and follow instructions (not just file existence)

7. **Validate fix with full test suite**
   - Run all integration tests with `--debug` enabled
   - Verify no new conflicts introduced
   - Confirm documentation consistency
   - Check session logs if tests fail

8. **Log in experiment if significant**
   - Document issue, root cause, fix
   - Note lessons learned from session log analysis
   - Document debugging pattern used
   - Update tests to prevent recurrence

## Debugging Tools

**Session log analysis**:
```bash
# Find test project directories
ls ~/.claude/projects/-tmp-*

# Search for specific prompt
rg "pattern" ~/.claude/projects/-tmp-claude-test-*/

# Check agent tool usage
rg "type.*tool" ~/.claude/projects/-tmp-claude-test-*/
```

**Session transcript generation** (human-readable format):
```bash
# List recent sessions for current project
ls -lt ~/.claude/projects/-home-nic-src-aOps/*.jsonl | head -5

# Generate markdown transcript from JSONL
mkdir -p ~/.cache/aops/transcripts
uv run ~/src/claude-transcript/claude_transcript.py \
  ~/.claude/projects/{project-path}/{session-id}.jsonl \
  -o ~/.cache/aops/transcripts/{session-id}_transcript.md

# Read transcript (much easier than raw JSONL)
cat ~/.cache/aops/transcripts/{session-id}_transcript.md
```

Use transcripts when:
- Raw JSONL search results are hard to interpret
- Need to understand full conversation flow
- Sharing session details for debugging

**Note**: Transcripts don't show hook-injected `<system-reminder>` tags. To verify hook behavior, grep raw JSONL.

**Controlled test environment**:
- Tests run in `/tmp/claude-test-*` (consistent location)
- `--debug` flag automatically enabled (full logging)
- Env vars validated fail-fast (`AOPS`, `ACA_DATA` required)
- Session logs persist for post-mortem analysis

**Hypothesis testing pattern**:
1. State hypothesis about root cause
2. Design test that would confirm/refute hypothesis
3. Run test with `--debug` in `/tmp`
4. Read session logs for evidence
5. Refine hypothesis based on evidence
6. Repeat until root cause identified

## Deep Root Cause Analysis (MANDATORY for "why didn't X work?")

When investigating why something didn't work as expected, **surface explanations are insufficient**. Use these techniques:

### 1. Never Accept Surface Explanations

| Surface answer | Required follow-up |
|----------------|-------------------|
| "It wasn't run" | WHY wasn't it run? Was it invoked but failed? |
| "The file doesn't exist" | WAS it created? Check git history |
| "The skill didn't work" | Find the EXACT error message in transcripts |

### 2. Git Forensics (REQUIRED)

```bash
# What commits touched this file?
git log --oneline --all -- "path/to/file"

# What was the content at a specific commit?
git show <commit>:<path/to/file>

# Full diff history for a file
git log -p --follow -- "path/to/file"

# What else was in a commit?
git show <commit> --stat

# All commits in a time range
git log --oneline --since="YYYY-MM-DD HH:MM"
```

### 3. Production Transcript Analysis

Search transcripts for skill invocations and errors:

```bash
# Find skill invocations
grep -l "Skill.*skillname\|/skillname" data/sessions/claude/*.md

# Find errors in a transcript
grep -B5 -A15 "❌ ERROR\|Traceback\|AttributeError" <transcript>

# See context around skill invocation
grep -B2 -A15 "Skill invoked.*skillname" <transcript>
```

### 4. Verify Claims By Running Code

Don't trust documentation - verify actual state:

```bash
# Check what attributes an object actually has
uv run python -c "
from lib.module import SomeClass
from dataclasses import fields
for f in fields(SomeClass):
    print(f'{f.name}: {f.type}')
"

# Check if file/function exists
uv run python -c "from lib.module import function_name; print('exists')"
```

### 5. Identify Axiom Violations

Common failure patterns map to axiom violations:

| Symptom | Likely violation |
|---------|-----------------|
| Workflow started but didn't complete | AXIOM #8 (Fail-Fast): Agent worked around error instead of halting |
| Wrong data written | AXIOM #7 (Fail-Fast): Silent failure, no validation |
| Skill docs don't match code | H9: Skills contain no dynamic content |
| Agent promised to improve | H11: No promises without instructions |

### Example: Full Investigation

"Why didn't session-insights produce a daily summary?"

1. **Surface**: "It wasn't run" → **Push deeper**
2. **Git forensics**: `git log -- sessions/YYYYMMDD-daily.md` - found commits exist
3. **Transcript search**: `grep "session-insights" transcripts/*.md` - found invocation
4. **Error extraction**: Found `AttributeError: 'SessionInfo' has no 'start_time'`
5. **Verification**: Ran code to confirm `start_time` doesn't exist on `SessionInfo`
6. **Axiom violation**: Agent worked around error (AXIOM #8 violation) instead of halting
7. **Root cause**: Skill docs referenced non-existent attribute + agent didn't halt on error
