# Framework Debugging Skill

**Purpose**: Efficiently investigate recent Claude Code session logs to diagnose framework issues (hook failures, agent errors, unexpected behavior).

**When to use**:
- Hook execution failed with unclear error
- Agent behaved unexpectedly (bypassed instructions, wrong tool usage)
- Framework component didn't load or execute as expected
- User asks "what happened in this session?" or "why did X fail?"

**Investigation approach**: This skill provides **structured investigation methodology** for agents to use existing tools (Read, Grep, Bash) to efficiently extract debugging information from session logs.

---

## Quick Start

**User request**: "What went wrong in the last session?" or "Debug the current session"

**Agent workflow**:
1. Identify session ID and log locations using commands below
2. Extract error messages and tool failures
3. Build chronological timeline of events
4. Synthesize narrative explanation for user

---

## Session Log Architecture

Claude Code maintains logs in multiple locations:

```
~/.claude/
├── debug/               # Human-readable debug logs (session-id.txt)
├── projects/            # JSONL session logs per repository
│   └── [repo-path]/     # e.g., -home-nic-src-academicOps/
│       ├── [session-id].jsonl      # Main session messages
│       └── agent-[id].jsonl        # Agent subprocess logs

/tmp/claude-sessions/
└── YYYY-MM-DD-[id]-hooks.jsonl     # Hook execution logs (CRITICAL for debugging hooks)
```

**Key insights**:
- Repository path is encoded with dashes replacing slashes: `/home/nic/src/academicOps` → `-home-nic-src-academicOps`
- **TWO DIFFERENT DEBUGGING PATHWAYS** - use the right one for your problem:
  1. **`~/.claude/projects/`** - Session behavior (agent actions, tool calls, user messages)
  2. **`/tmp/claude-sessions/`** - Hook execution (which hooks fired, with what inputs, hook results)

### When to Use Each Pathway

**Use `~/.claude/projects/` when debugging**:
- Agent behavior (did agent follow instructions?)
- Tool usage (what files were read/written?)
- Session flow (user messages → agent responses)
- Errors in tool execution
- Agent subprocess behavior

**Use `/tmp/claude-sessions/` when debugging**:
- Hook execution (did hooks actually run?)
- Hook inputs (what data did hooks receive?)
- Hook results (did hook commands execute or return null?)
- Permission-related hook failures
- Hook timing and sequencing

**Common pattern**: Start with `/tmp/claude-sessions/` to verify hooks executed, then use `~/.claude/projects/` to understand what the agent did.

---

## Investigation Steps

### Step 1: Identify Current Session

**Find most recent session log for current repository**:

```bash
# Get current working directory encoded as repository path
pwd_encoded=$(pwd | sed 's/\//-/g')

# Find most recent session log
ls -lt ~/.claude/projects/${pwd_encoded}/*.jsonl 2>/dev/null | grep -v "agent-" | head -3
```

**Output**: Most recent session logs with timestamps. Pick the newest one.

**If logs not found**: Repository might not have hyphen encoding, or session hasn't been logged yet. Try:

```bash
# List all project directories
ls -lt ~/.claude/projects/ | head -10

# Manually identify matching directory
```

### Step 2: Locate Agent Logs

**Find agent logs for session**:

```bash
# List all agent logs in repository
ls -lt ~/.claude/projects/${pwd_encoded}/agent-*.jsonl

# Or find logs by timestamp (within session time range)
find ~/.claude/projects/${pwd_encoded}/ -name "agent-*.jsonl" -newermt "2025-11-18 10:00"
```

### Step 3: Extract Error Messages

**Efficient error extraction** (don't read entire logs):

```bash
# Extract lines containing "error" or "Error" or "ERROR"
grep -i "error" ~/.claude/projects/${pwd_encoded}/[session-id].jsonl

# Extract tool failures
grep "\"type\":\"tool\"" ~/.claude/projects/${pwd_encoded}/[session-id].jsonl | grep -i "error\|fail"

# Extract from agent logs
grep -i "error" ~/.claude/projects/${pwd_encoded}/agent-*.jsonl
```

**Using jq** for structured extraction (if available):

```bash
# Extract all error-type messages with timestamps
cat ~/.claude/projects/${pwd_encoded}/[session-id].jsonl | jq -r 'select(.type=="error") | "\(.timestamp): \(.message)"'

# Extract tool calls with errors
cat ~/.claude/projects/${pwd_encoded}/[session-id].jsonl | jq -r 'select(.type=="tool" and (.message | contains("Error"))) | "\(.timestamp): \(.message)"'
```

### Step 4: Build Chronological Timeline

**Merge and sort messages from main session + agent logs**:

```bash
# Read specific line ranges if files are large
# Use Read tool with offset/limit parameters for efficiency

# For small-medium logs, read full content and sort by timestamp field
```

**Agent approach**:
1. Use Read tool to load log contents (may need chunking for large files)
2. Parse JSONL (each line is valid JSON)
3. Filter to relevant message types: "error", "tool", "user", "assistant"
4. Sort by timestamp field
5. Present as chronological narrative

### Step 5: Extract Recent Messages Only

**Filter to last N minutes or last N messages**:

```bash
# Get timestamp from 1 hour ago
one_hour_ago=$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S')

# Extract messages since then
cat ~/.claude/projects/${pwd_encoded}/[session-id].jsonl | jq -r --arg since "$one_hour_ago" 'select(.timestamp >= $since)'

# Or just get last 50 lines
tail -50 ~/.claude/projects/${pwd_encoded}/[session-id].jsonl
```

---

## Common Investigation Patterns

### Pattern: "Hook execution failed"

**CRITICAL**: Hook debugging MUST use `/tmp/claude-sessions/` logs - these show actual hook execution, not just that hooks are configured.

**Investigation workflow**:

1. **Find today's hook log**:
   ```bash
   ls -lt /tmp/claude-sessions/*.jsonl | head -3
   ```

2. **Check if hooks are firing at all**:
   ```bash
   # Find most recent hook log
   hook_log=$(ls -t /tmp/claude-sessions/*-hooks.jsonl | head -1)

   # Check what hooks are executing
   jq -r '.hook_event_name' "$hook_log" | sort | uniq -c
   ```

   **Expected output**: Shows counts of SessionStart, PreToolUse, PostToolUse, etc.
   **If empty**: Hooks aren't configured or settings.json is wrong

3. **Check specific hook execution for a tool**:
   ```bash
   # Example: Check PostToolUse hooks for Write operations
   jq -c 'select(.tool_name == "Write" and .hook_event == "PostToolUse") | {time: .logged_at, file: .tool_input.file_path, hooks: .hook_results}' "$hook_log" | head -10
   ```

   **Key field**: `hook_results` - if `null`, hook commands didn't execute even though event fired

4. **Diagnose why hooks didn't execute**:
   ```bash
   # Check if permission denied operations prevent hook execution
   jq -c 'select(.permission_mode == "bypassPermissions" and .hook_results == null)' "$hook_log"
   ```

   **Common finding**: Operations with `bypassPermissions` may not trigger hook commands

5. **Check for hook command errors**:
   ```bash
   # Look for hook execution failures
   grep -i "error" "$hook_log" | jq -c 'select(.hook_event)'
   ```

**Common failures**:
- **Hooks configured but `hook_results` is `null`**: Permission deny rules may block hook execution entirely
- **Hook script not found**: Path issue in settings.json
- **Python dependencies missing**: Hook command fails silently
- **Hook script syntax error**: Check stderr in hook_results
- **Permission denied**: Hook script not executable

**Key diagnostic pattern**:
- Event fires (PreToolUse/PostToolUse logged) ✓
- BUT `hook_results: null` ✗
- = Hook commands didn't execute (permission issue or configuration problem)

### Pattern: "Agent bypassed instructions"

**Investigation**:
1. Find session and agent logs
2. Extract agent invocation:
   ```bash
   grep "agentStart" ~/.claude/projects/${pwd_encoded}/agent-*.jsonl
   ```
3. Check prompt provided to agent (look for "prompt" or "task" fields)
4. Compare agent actions to expected behavior
5. Look for tool use that violated instructions

**Common causes**:
- Skill instructions unclear or contradictory
- Agent didn't receive expected context
- Agent encountered error and improvised workaround

### Pattern: "Skill didn't load"

**Investigation**:
1. Check session start messages for skill loading
2. Search for skill name in logs
3. Verify skill exists: `ls -la ~/.claude/skills/[skill-name]/SKILL.md`
4. Check for syntax errors in skill markdown

### Pattern: "What happened in last session?"

**Investigation**:
1. Get most recent completed session (not current session)
2. Extract summary timeline: user messages + assistant responses + errors
3. Highlight any failures or unexpected behavior
4. Present chronological narrative

---

## Error Handling

**Fail-fast cases** (HALT immediately):
- `~/.claude/` directory doesn't exist (Claude Code not properly installed)
- Session ID explicitly provided but log file completely unreadable (permissions issue)

**Graceful degradation** (best effort):
- Some log files missing → Report which files unavailable, continue with available logs
- Malformed JSONL lines → Skip bad lines, count them, continue with valid lines
- Empty logs → Report "no messages found in timeframe"
- Timestamp parsing failures → Group messages without timestamps separately

**Always report coverage**: "Analyzed X/Y lines, Z lines malformed" or "Logs found: main session ✓, agent logs ✗"

---

## File Size Considerations

**Large log files** (>10MB):
- Don't use Read tool to load entire file (expensive, high token usage)
- Use Bash tools for filtering first:
  - `grep` to extract relevant lines
  - `tail`/`head` to get recent portion
  - `wc -l` to check size before reading

**Efficient approach**:
1. Check file size: `ls -lh [log-file]`
2. If >10MB, use grep/tail to filter before reading
3. If <10MB, safe to read with Read tool

**Example**:
```bash
# Check size
ls -lh ~/.claude/projects/${pwd_encoded}/[session-id].jsonl

# If large, filter first
grep -i "error" [large-log].jsonl > /tmp/filtered-errors.jsonl

# Then read filtered results
```

---

## Output Format

**Present findings as chronological narrative**:

```
Session Investigation: [session-id]
Repository: [repo-path]
Time range: [start] to [end]

=== Timeline ===
10:00:00 - User: "create new feature"
10:00:05 - Assistant: "I'll invoke the framework skill"
10:00:10 - [AGENT START] framework skill
10:00:15 - [ERROR] Agent: "Hook validation failed: missing required field"
10:00:20 - [AGENT END] framework skill (failed)
10:00:25 - Assistant: "Encountered error during execution"

=== Summary ===
- Hook validation error occurred at 10:00:15
- Agent subprocess terminated with failure
- Root cause: [analysis from error message]

=== Coverage ===
- Main session log: ✓ (250 lines analyzed)
- Agent logs: ✓ (3 agents found, 45 total lines)
- Malformed lines: 2 (skipped)
```

---

## Limitations

**Known constraints**:
- Log format specific to current Claude Code version (may change in updates)
- Cannot recover deleted or rotated logs
- Timestamp correlation assumes system clock accuracy
- Large logs (>100MB) may be slow to process

**Future improvements**:
- Pattern recognition for common error types
- Automatic diagnosis suggestions
- Cross-session comparison
- Integration with framework experiments/LOG.md

---

## Examples

### Example 1: Hook Failure Investigation

User: "My session start hook failed, what happened?"

Agent workflow:
```bash
# 1. Find current session
pwd_encoded=$(pwd | sed 's/\//-/g')
recent_session=$(ls -t ~/.claude/projects/${pwd_encoded}/*.jsonl | grep -v agent | head -1)

# 2. Extract hook-related errors
grep -i "hook" "$recent_session" | grep -i "error"

# Output might show:
# {"type":"error","message":"Hook execution failed: SessionStart:startup command failed with code 1",...}

# 3. Get more context around that timestamp
# Use Read tool to load surrounding messages

# 4. Present findings to user
```

### Example 2: Agent Behavior Investigation

User: "The agent didn't follow the framework skill instructions, can you check what happened?"

Agent workflow:
```bash
# 1. Find session and agent logs
pwd_encoded=$(pwd | sed 's/\//-/g')
session_log=$(ls -t ~/.claude/projects/${pwd_encoded}/*.jsonl | grep -v agent | head -1)
agent_logs=$(ls -t ~/.claude/projects/${pwd_encoded}/agent-*.jsonl)

# 2. Extract agent invocations
for log in $agent_logs; do
  echo "=== Agent: $log ==="
  grep "agentStart\|agentEnd" "$log"
done

# 3. Look for framework skill mentions
grep -i "framework" "$session_log" "$agent_logs"

# 4. Build timeline of what agent actually did vs expected behavior
```

---

## Integration with Framework

**Related workflows**:
- [[workflows/02-debug-framework-issue.md]] - Framework debugging process
- [[experiments/LOG.md]] - Log patterns to learning database

**Invocation triggers** (add to CORE.md):
- "Debug the current session" → Invoke framework-debug skill
- "What went wrong?" → Invoke framework-debug skill
- "Investigate hook failure" → Invoke framework-debug skill

**Success metrics**:
- Investigation time < 5 minutes (vs 10-30 minutes manual)
- Extracts relevant errors in >90% of cases
- Chronological timeline helps user understand "what happened"
