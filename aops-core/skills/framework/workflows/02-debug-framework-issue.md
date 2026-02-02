---
title: Debug Framework Issue
type: automation
category: instruction
permalink: workflow-debug-framework-issue
description: Process for diagnosing and fixing framework component failures and integration issues
---

# Workflow 2: Debug Framework Issue

**When**: Framework component failing, unexpected behavior, integration broken.

**Key principle**: Use **controlled tests in /tmp** to run experiments and validate hypotheses. Read **session transcripts** to understand agent behavior.

**Steps**:

1. **Generate transcript FIRST (MANDATORY)**
   - Raw JSONL wastes 10-70K tokens; transcripts are 90% smaller and human-readable
   - Run: `cd $AOPS && uv run python scripts/transcript.py <session.jsonl>`
   - Works with both Claude (`.jsonl`) and Gemini (`.json`) session files
   - Output shows paths to full and abridged versions
   - **Abridged is usually sufficient** (excludes verbose tool results)

2. **Reproduce the issue with controlled test** (if not already reproduced)
   - Run test with `--debug` flag (fixture does this automatically)
   - Test runs in `/tmp/claude-test-*` directory (controlled environment)
   - Required env vars (`AOPS`, `ACA_DATA`) must be set (fail-fast if missing)
   - Document exact steps to trigger issue
   - Verify issue exists (not user error)

3. **Read the transcript to understand behavior**
   - Look for tool calls, errors, and agent reasoning
   - Check: Did agent read the right files? Follow instructions? Use correct tools?
   - Note: Transcripts don't show hook-injected `<system-reminder>` tags
   - To verify hook behavior, grep raw JSONL: `grep "system-reminder" <session.jsonl>`

4. **Form hypothesis about root cause**
   - Verify component follows single source of truth
   - Look for duplication or conflicts
   - **Agent behavior analysis**: Did agent receive correct context? Interpret instructions correctly?

5. **Test hypothesis with controlled experiment**
   - Modify one variable at a time
   - Run test in `/tmp` with `--debug` flag
   - Generate transcript and read it to confirm behavior change
   - Iterate until hypothesis confirmed
   - **Pattern**: Change → Test → Generate transcript → Refine hypothesis

6. **Design minimal fix**
   - Minimal change to address root cause
   - Avoid workarounds
   - Maintain documentation integrity
   - **Fail-fast enforcement**: Add validation that fails immediately on misconfiguration

7. **Create/update integration test**
   - Test must fail with current broken state
   - Test must pass with fix applied
   - Cover regression cases
   - **E2E test**: Agent must actually read and follow instructions (not just file existence)

8. **Validate fix with full test suite**
   - Run all integration tests with `--debug` enabled
   - Verify no new conflicts introduced
   - Confirm documentation consistency
   - Generate transcripts if tests fail

9. **Log in experiment if significant**
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
# List recent Claude sessions
ls -lt ~/.claude/projects/-home-nic-src-academicOps/*.jsonl | head -5

# List recent Gemini sessions
ls -lt ~/.gemini/tmp/*/chats/*.json | head -5

# Generate markdown transcript (works for both Claude and Gemini)
cd $AOPS && uv run python scripts/transcript.py <session-file>

# Output shows paths to full and abridged transcripts
# Abridged is usually sufficient (excludes verbose tool results)
```

**ALWAYS generate transcript first** - raw JSONL/JSON wastes tokens and is hard to read.

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

| Surface answer           | Required follow-up                            |
| ------------------------ | --------------------------------------------- |
| "It wasn't run"          | WHY wasn't it run? Was it invoked but failed? |
| "The file doesn't exist" | WAS it created? Check git history             |
| "The skill didn't work"  | Find the EXACT error message in transcripts   |

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
grep -l "Skill.*skillname\|/skillname" $ACA_DATA/../sessions/claude/*.md

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

| Symptom                              | Likely violation                                                   |
| ------------------------------------ | ------------------------------------------------------------------ |
| Workflow started but didn't complete | AXIOM #8 (Fail-Fast): Agent worked around error instead of halting |
| Wrong data written                   | AXIOM #7 (Fail-Fast): Silent failure, no validation                |
| Skill docs don't match code          | H9: Skills contain no dynamic content                              |
| Agent promised to improve            | H11: No promises without instructions                              |

### Example: Full Investigation

"Why didn't session-insights produce a daily summary?"

1. **Surface**: "It wasn't run" → **Push deeper**
2. **Git forensics**: `git log -- sessions/YYYYMMDD-daily.md` - found commits exist
3. **Transcript search**: `grep "session-insights" transcripts/*.md` - found invocation
4. **Error extraction**: Found `AttributeError: 'SessionInfo' has no 'start_time'`
5. **Verification**: Ran code to confirm `start_time` doesn't exist on `SessionInfo`
6. **Axiom violation**: Agent worked around error (AXIOM #8 violation) instead of halting
7. **Root cause**: Skill docs referenced non-existent attribute + agent didn't halt on error

## Debugging Headless/Subagent Sessions

When a test spawns a headless Claude session (via `claude -p` or Task tool) and it fails or times out, use this workflow to investigate what the subagent actually did.

### 1. Find the Subagent Session File

The test output usually includes the session ID. Search for it:

```bash
# Search by session ID (from test output)
grep -rl "SESSION_ID_HERE" ~/.claude/projects/

# Search by unique prompt content
grep -rl "add_numbers\|unique_prompt_text" ~/.claude/projects/ | head -10

# Find test project sessions (tests run from academicOps)
ls -lt ~/.claude/projects/-home-nic-src-academicOps/*.jsonl | head -10
```

**Tip**: Tests running headless sessions create JSONL in `~/.claude/projects/-home-nic-src-academicOps/` (the project where pytest runs), not in the test temp directory.

### 2. Generate Readable Transcript

Raw JSONL is unreadable. Always convert first:

```bash
# Generate transcript
cd $AOPS && uv run python scripts/transcript.py \
  ~/.claude/projects/-home-nic-src-academicOps/SESSION_ID.jsonl

# Output shows paths to full and abridged versions
# Abridged is usually sufficient (excludes verbose tool results)
```

### 3. Analyze the Transcript

Look for these patterns:

| Pattern             | Location in Transcript                     | What It Reveals                    |
| ------------------- | ------------------------------------------ | ---------------------------------- |
| **Subagent spawns** | `### Subagent: TYPE (description)`         | What subagents were invoked        |
| **Tool errors**     | `**❌ ERROR:**`                            | Failed tool calls with exact error |
| **Turn timing**     | `## User (Turn N (HH:MM, took X seconds))` | Where time was spent               |
| **Hook injections** | `Hook(SessionStart)` at top                | What context was loaded            |
| **TodoWrite items** | `▶ □ ✓` markers                            | Planned vs executed work           |

### 4. Common Failure Patterns

| Symptom                          | Likely Cause                      | Fix                                                     |
| -------------------------------- | --------------------------------- | ------------------------------------------------------- |
| **Timeout with few tool calls**  | Stuck in subagent/hook loop       | Check if hydrator/custodiet spawning recursively        |
| **Timeout with many tool calls** | Over-engineered workflow          | Hydrator prescribed overkill; add "trivial task" bypass |
| **Tool error cascade**           | First error caused confusion      | Fix the first error; later ones are symptoms            |
| **Custodiet CANNOT_ASSESS**      | Audit file has incomplete context | Expected for short sessions; not a real failure         |
| **Write "file not read" error**  | Tried to create new file          | Use Bash heredoc or fix Write tool handling             |

### 5. Example: Demo Test Timeout Investigation

**Problem**: `test_core_pipeline.py` timed out after 180s on a trivial "write add_numbers function" task.

**Investigation**:

```bash
# Find session from test output (session ID: c64de01b-...)
grep -rl "c64de01b" ~/.claude/projects/
# Found: ~/.claude/projects/-home-nic-src-academicOps/c64de01b-....jsonl

# Generate transcript
cd $AOPS && uv run python scripts/transcript.py \
  ~/.claude/projects/-home-nic-src-academicOps/c64de01b-....jsonl
```

**Transcript revealed**:

1. Turn 1 took **2 minutes 34 seconds** (way too long)
2. Hydrator made **3 memory retrieval calls** for a one-liner function
3. Hydrator prescribed full **TDD workflow with 5 todo items**
4. Custodiet spawned but returned `CANNOT_ASSESS` (incomplete context)
5. Write tool failed ("file not read"), Bash heredoc also failed ("file exists")
6. Session timed out before completing

**Root cause**: Framework overhead (hydration + TDD prescription + custodiet) consumed all time on a trivial task.

**Axiom violations identified**:

- Over-hydration: 3 memory queries for "add two numbers"
- TDD overkill: Full test cycle for trivial utility function
- Tool friction: Write tool requires pre-read even for new files
