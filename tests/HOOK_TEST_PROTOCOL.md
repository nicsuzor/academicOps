---
title: Hook Testing Protocol
type: test
permalink: hook-test-protocol
description: Manual test protocol for verifying Claude Code hook effectiveness
tags:
  - testing
  - hooks
  - verification
---

# Hook Testing Protocol

Manual test protocol for verifying Claude Code hook effectiveness. Use this protocol to create reproducible evidence of hook behavior.

## Prerequisites

1. Hooks configured in `~/.claude/settings.json`
2. Hook log directory exists: `~/.cache/aops/sessions/`
3. Transcript tool available: `/transcript`

## Currently Configured Hooks

From `[[.claude/settings.json]]`:

| Event | Hook | Purpose |
|-------|------|---------|
| SessionStart | `sessionstart_load_axioms.py` | Load AXIOMS.md + CORE.md at session start |
| PreToolUse | `log_pretooluse.py` | Log tool invocations |
| PostToolUse | `log_posttooluse.py` | Log tool results |
| PostToolUse | `autocommit_state.py` | Auto-commit data/ changes |
| UserPromptSubmit | `log_userpromptsubmit.py` | Log user prompts |
| UserPromptSubmit | `prompt_router.py` | Route prompts to skills |
| SubagentStop | `log_subagentstop.py` | Log subagent completion |

## Test Protocol

### Step 1: Record Session ID

At start of test session, capture session ID:

```bash
# Find current session's hook log (most recent)
ls -lt ~/.cache/aops/sessions/*-hooks.jsonl | head -1
```

### Step 2: Execute Test Cases

Run each test case and note the timestamp.

### Step 3: Generate Transcript

```
/transcript
```

This creates a markdown transcript with hook executions woven in chronologically.

### Step 4: Analyze Hook Log

```bash
# Count hook events by type
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | jq -r '.hook_event' | sort | uniq -c | sort -rn
```

---

## Test Cases

### TC1: SessionStart Hook

**Purpose**: Verify [[AXIOMS.md]] and [[CORE.md]] are loaded at session start.

**Steps**:
1. Start a new Claude Code session
2. Immediately run: `ls -lt ~/.cache/aops/sessions/*-hooks.jsonl | head -1`
3. Check the log for SessionStart event

**Verification**:
```bash
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | head -1 | jq '.hook_event, .hookSpecificOutput.filesLoaded'
```

**Expected**:
- `hook_event` = "SessionStart"
- `filesLoaded` includes AXIOMS.md and CORE.md
- `additionalContext` contains framework principles

**Pass Criteria**:
- [ ] SessionStart is first event in log
- [ ] AXIOMS.md content appears in additionalContext
- [ ] CORE.md content appears in additionalContext
- [ ] Agent demonstrates knowledge of axioms in first response

---

### TC2: UserPromptSubmit Hook (Focus Reminder)

**Purpose**: Verify focus reminder is injected on user prompts.

**Steps**:
1. Send any user message
2. Check hook log for UserPromptSubmit event

**Verification**:
```bash
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | grep '"hook_event":"UserPromptSubmit"' | tail -1 | jq '.hookSpecificOutput.additionalContext'
```

**Expected**:
- Contains "Focus on the user's specific request"
- Contains "Do NOT over-elaborate"

**Pass Criteria**:
- [ ] UserPromptSubmit event logged
- [ ] Focus reminder in additionalContext
- [ ] Agent behavior matches reminder (doesn't over-elaborate)

---

### TC3: PromptRouter Hook (Skill Detection)

**Purpose**: Verify prompt router detects skills and injects skill requirements.

**Steps**:
1. Send a prompt that should trigger a skill (e.g., "write a python function")
2. Check hook log for PromptRouter event

**Verification**:
```bash
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | grep '"hook_event":"PromptRouter"' | tail -1 | jq '.hookSpecificOutput'
```

**Expected**:
- `skillsMatched` array contains relevant skill names
- `additionalContext` includes "MANDATORY" skill invocation instruction

**Pass Criteria**:
- [ ] PromptRouter event logged
- [ ] Correct skills detected for prompt type
- [ ] Skill invocation instruction in additionalContext

---

### TC4: PostToolUse Autocommit Hook

**Purpose**: Verify auto-commit triggers after data/ modifications.

**Steps**:
1. Use the memory skill to store a note: `Skill(skill="remember")` targeting data/
2. Check hook log for autocommit event
3. Check git log for automatic commit

**Verification**:
```bash
# Check hook log
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | grep 'autocommit\|PostToolUse' | tail -5 | jq '.hook_event, .tool_name'

# Check git log
git -C ~/writing/data log --oneline -5
```

**Expected**:
- PostToolUse event after memory skill invocation
- Git commit with auto-generated message
- Commit includes the data/ file

**Pass Criteria**:
- [ ] PostToolUse logged for state-modifying tool
- [ ] Git commit created automatically
- [ ] Commit message describes the change

---

### TC5: Tool Logging (PreToolUse + PostToolUse)

**Purpose**: Verify all tool invocations are logged.

**Steps**:
1. Execute several tools (Read, Bash, Grep)
2. Check hook log for Pre/PostToolUse events

**Verification**:
```bash
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | jq -r 'select(.hook_event | test("ToolUse")) | "\(.hook_event): \(.tool_name // .tool)"' | tail -20
```

**Expected**:
- PreToolUse event BEFORE each tool execution
- PostToolUse event AFTER each tool execution
- Tool names captured correctly

**Pass Criteria**:
- [ ] PreToolUse logged before tool runs
- [ ] PostToolUse logged after tool completes
- [ ] Tool name captured in log entry

---

### TC6: SubagentStop Hook

**Purpose**: Verify subagent completions are logged.

**Steps**:
1. Invoke a Task subagent (e.g., Explore agent)
2. Wait for completion
3. Check hook log for SubagentStop event

**Verification**:
```bash
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
cat "$SESSION_LOG" | grep '"hook_event":"SubagentStop"' | tail -1 | jq '.'
```

**Expected**:
- `agent_id` present
- `agent_transcript_path` points to valid file

**Pass Criteria**:
- [ ] SubagentStop event logged
- [ ] Agent ID captured
- [ ] Transcript path captured

---

## Running the Full Protocol

### Quick Verification (Current Session)

```bash
# 1. Get current session's hook log
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
echo "Session log: $SESSION_LOG"

# 2. Count events by type
echo "=== Event counts ==="
cat "$SESSION_LOG" | jq -r '.hook_event' | sort | uniq -c | sort -rn

# 3. Verify SessionStart loaded context
echo "=== SessionStart ==="
cat "$SESSION_LOG" | head -1 | jq '.hook_event, (.hookSpecificOutput.filesLoaded // "no files")'

# 4. Check for any errors
echo "=== Exit codes ==="
cat "$SESSION_LOG" | jq -r 'select(.exit_code != 0) | "\(.hook_event): exit \(.exit_code)"' | head -10
```

### Full Evidence Collection

```bash
# 1. Generate transcript for current session
/transcript

# 2. The transcript will be saved to ~/writing/session-{id}-transcript.md
# 3. Review the markdown file - hooks are woven in chronologically

# 4. Save hook analysis
SESSION_LOG=$(ls -t ~/.cache/aops/sessions/*-hooks.jsonl | head -1)
SESSION_ID=$(basename "$SESSION_LOG" | sed 's/-hooks.jsonl//')

# Create evidence file
{
  echo "# Hook Test Evidence: $SESSION_ID"
  echo "Generated: $(date -Iseconds)"
  echo ""
  echo "## Event Summary"
  cat "$SESSION_LOG" | jq -r '.hook_event' | sort | uniq -c | sort -rn
  echo ""
  echo "## SessionStart Check"
  cat "$SESSION_LOG" | head -1 | jq '.'
  echo ""
  echo "## Any Failures"
  cat "$SESSION_LOG" | jq -r 'select(.exit_code != 0)' | head -20
} > ~/writing/hook-test-$SESSION_ID.md

echo "Evidence saved to ~/writing/hook-test-$SESSION_ID.md"
```

---

## Expected Results Summary

| Hook | Expected Behavior | How to Verify |
|------|-------------------|---------------|
| SessionStart | AXIOMS+CORE loaded | Check first log entry |
| UserPromptSubmit | Focus reminder injected | Check additionalContext |
| PromptRouter | Skills detected | Check skillsMatched array |
| PostToolUse (autocommit) | data/ changes committed | Check git log |
| PreToolUse | Tool invocations logged | Check tool_name in log |
| PostToolUse | Tool results logged | Check log after tool |
| SubagentStop | Agent completions logged | Check agent_id in log |

---

## AGENT COMPLIANCE ISSUE (2025-11-28)

**Critical Finding**: Agents IGNORE the "MANDATORY" skill invocation instruction.

### Evidence

1. **Task skill suggestion ignored** (writing repo, 2025-11-28T07:53):
   - User prompt: "add this as a task please"
   - Router output: `MANDATORY: You MUST invoke the 'tasks' skill...`
   - Agent behavior: **Immediately called task_add.py via Bash, DID NOT invoke Skill tool**

2. **Python-dev skill suggestion ignored** (advocate session):
   - User prompt: `/advocate figure out how to assess...`
   - Router output: `MANDATORY: You MUST invoke the 'python-dev' skill...`
   - Agent behavior: **Immediately started reading files, DID NOT invoke skill**

### Quantitative Data (2025-11-28)

| Metric | Value |
|--------|-------|
| Router suggestions | 60 |
| Skill tool invocations (all sessions) | 26 |
| Most common suggestion | `python-dev` (26x) |
| Second | `framework` (8x) |

### Root Causes

1. **Keyword overlap**: "test" triggers `python-dev` even in framework contexts
2. **No enforcement**: "MANDATORY" instruction has no mechanism to force compliance
3. **Context override**: Agents with existing session context bypass skill invocation

### Verification Commands

```bash
# Count router suggestions today
grep '"skillsMatched"' ~/.cache/aops/sessions/2025-11-28-*.jsonl | wc -l

# See skill distribution
grep '"skillsMatched"' ~/.cache/aops/sessions/2025-11-28-*.jsonl | \
  grep -oP '"skillsMatched":\[[^\]]+\]' | sort | uniq -c | sort -rn

# Check if agent invoked Skill tool in a session
grep '"name":"Skill"' ~/.claude/projects/-home-nic-src-aOps/SESSION_ID.jsonl | wc -l
```

### TC7: Agent Skill Compliance

**Purpose**: Verify agent invokes suggested skill after PromptRouter fires.

**Steps**:
1. Start fresh session (no prior context)
2. Send prompt that triggers skill (e.g., "help me write a python function")
3. Check if agent's FIRST tool invocation is Skill

**Verification**:
```bash
# Get session transcript
SESSION_ID=$(ls -t ~/.claude/projects/-home-nic-src-aOps/*.jsonl | head -1)

# Find first tool_use after user prompt
grep '"type":"tool_use"' "$SESSION_ID" | head -1 | jq '.name'
```

**Expected**:
- First tool invocation is `Skill`
- Skill invoked matches `skillsMatched` from router

**Pass Criteria**:
- [ ] Agent's first action is Skill invocation
- [ ] Skill invoked matches router suggestion
- [ ] Skill content is loaded before other tools used

---

## Troubleshooting

### Hook not executing

1. Check settings.json configuration:
   ```bash
   cat ~/.claude/settings.json | jq '.hooks'
   ```

2. Check hook file exists and is executable:
   ```bash
   ls -la $AOPS/hooks/*.py
   ```

3. Check for Python errors:
   ```bash
   PYTHONPATH=$AOPS uv run python $AOPS/hooks/sessionstart_load_axioms.py --test
   ```

### Hook log not created

1. Verify cache directory exists:
   ```bash
   mkdir -p ~/.cache/aops/sessions
   ```

2. Check hook_logger.py can write:
   ```bash
   touch ~/.cache/aops/sessions/test.jsonl && rm ~/.cache/aops/sessions/test.jsonl
   ```

### Autocommit not triggering

1. Check if data/ has uncommitted changes:
   ```bash
   git -C ~/writing/data status
   ```

2. Check autocommit hook output in log:
   ```bash
   cat "$SESSION_LOG" | grep -i autocommit | tail -5 | jq '.'
   ```
