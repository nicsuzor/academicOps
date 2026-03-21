# Debugging Tools and Procedures

Detailed tools, patterns, and procedures for diagnosing framework issues.

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

**Hooks logs vs Session files** (important distinction):

| File Type        | Location                                                                 | Contains                                                           |
| ---------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **Session file** | `~/.claude/projects/*/*.jsonl` or `~/.gemini/tmp/*/chats/session-*.json` | Actual conversation: user prompts, agent responses, tool calls     |
| **Hooks log**    | `~/.gemini/tmp/*/chats/*-hooks.jsonl`                                    | Hook events only: SessionStart, BeforeAgent, BeforeTool, AfterTool |

- **Hooks logs** record what hooks fired and their outputs, NOT the conversation
- If you have a hooks log, find the session file via `transcript_path` field in the first entry
- Use `transcript.py` on the **session file**, not the hooks log

```bash
# Extract session file path from hooks log
head -1 /path/to/hooks.jsonl | jq -r '.input.transcript_path'
```

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
