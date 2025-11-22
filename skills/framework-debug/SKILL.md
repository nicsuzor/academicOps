# Framework Debugging Skill

**Purpose**: Efficiently investigate recent Claude Code session logs to diagnose framework issues (hook failures, agent errors, unexpected behavior).

**When to use**:
- Hook execution failed with unclear error
- Agent behaved unexpectedly (bypassed instructions, wrong tool usage)
- Framework component didn't load or execute as expected
- User asks "what happened in this session?" or "why did X fail?"

---

## Quick Start: Find Recent Errors

```bash
# Set repo path (run once per session)
repo=$(pwd | sed 's/\//-/g')
```

**Step 1: Scan all log sources**

```bash
# 1a. Debug logs - general errors, MCP failures
grep -Hn '\[ERROR\]' ~/.claude/debug/*.txt 2>/dev/null | grep -v 'Server stderr.*INFO' | tail -30

# 1b. Agent logs - tool execution failures (the actual useful errors)
grep -Hn '"is_error":true' ~/.claude/projects/${repo}/agent-*.jsonl 2>/dev/null | tail -30
```

**Step 2: Format errors for review**

```bash
# Using the extensible filter script (add new patterns to scripts/errors.jq as discovered)
cat ~/.claude/projects/${repo}/agent-*.jsonl 2>/dev/null | \
  jq -r -f ~/.claude/skills/framework-debug/scripts/errors.jq 2>/dev/null | tail -30
```

**Step 3: Investigate specific error**

```bash
# Full context from agent log (replace AGENT_ID and pattern)
jq -c 'select(.toolUseResult | test("PATTERN"))' ~/.claude/projects/${repo}/agent-AGENT_ID.jsonl

# Surrounding lines from debug log (replace SESSION_ID)
grep -B3 -A3 'PATTERN' ~/.claude/debug/SESSION_ID*.txt
```

---

## Log Locations (Priority Order)

**1. `~/.claude/debug/*.txt`** - CHECK FIRST
- Human-readable debug logs
- Tagged with `[ERROR]`, `[DEBUG]`, `[INFO]`
- Best for: Quick error discovery, MCP failures, tool errors

**2. `~/.claude/projects/[repo-path]/`** - Detailed investigation
- `[session-id].jsonl` - Main session messages
- `agent-*.jsonl` - Agent subprocess logs (tool results, errors)
- Best for: Understanding what agent did, tool call sequences, error context

**3. `/tmp/claude-sessions/*-hooks.jsonl`** - Hook-specific debugging
- Hook execution records (which hooks fired, inputs, results)
- Best for: Hook configuration issues, permission problems
- Only check this if debugging hooks specifically

---

## Common Workflows

### "Find recent tool failures"

```bash
# Step 1: Quick scan of debug logs
grep -h "\[ERROR\]" ~/.claude/debug/*.txt | tail -30

# Step 2: If need more context, check agent logs
pwd_encoded=$(pwd | sed 's/\//-/g')
grep -l "is_error" ~/.claude/projects/${pwd_encoded}/agent-*.jsonl 2>/dev/null

# Step 3: Extract actual errors from agent logs
grep "is_error.*true" ~/.claude/projects/${pwd_encoded}/agent-*.jsonl | head -20
```

### "What errors happened in the last hour?"

```bash
# Debug logs (easiest)
find ~/.claude/debug/ -name "*.txt" -mmin -60 -exec grep -l "\[ERROR\]" {} \;

# Then extract errors from those files
find ~/.claude/debug/ -name "*.txt" -mmin -60 -exec grep -h "\[ERROR\]" {} \; | tail -50
```

### "Debug a specific MCP tool failure"

```bash
# Find MCP errors
grep "MCP server.*Error" ~/.claude/debug/*.txt | tail -20

# Get full context around the error
grep -B5 -A5 "Error calling tool" ~/.claude/debug/*.txt | tail -50
```

---

## Deep Investigation (When Quick Start Isn't Enough)

### Find Session/Agent Logs

```bash
# Encode current repo path
pwd_encoded=$(pwd | sed 's/\//-/g')

# List recent session logs
ls -lt ~/.claude/projects/${pwd_encoded}/*.jsonl 2>/dev/null | grep -v "agent-" | head -3

# List agent logs
ls -lt ~/.claude/projects/${pwd_encoded}/agent-*.jsonl 2>/dev/null | head -5
```

### Extract Errors from JSONL

```bash
# Tool errors in agent logs (look for is_error field)
grep '"is_error":true' ~/.claude/projects/${pwd_encoded}/agent-*.jsonl

# With jq for structured output
cat ~/.claude/projects/${pwd_encoded}/agent-*.jsonl | jq -c 'select(.toolUseResult | contains("Error"))' 2>/dev/null
```

---

## Hook-Specific Debugging

### Pattern: "Hook execution failed"

Hook debugging uses `/tmp/claude-sessions/` logs (not debug/*.txt).

```bash
# Find recent hook log
hook_log=$(ls -t /tmp/claude-sessions/*-hooks.jsonl 2>/dev/null | head -1)

# Check if hooks are firing
jq -r '.hook_event_name' "$hook_log" | sort | uniq -c

# Check for null hook_results (hook configured but didn't execute)
jq -c 'select(.hook_results == null)' "$hook_log" | head -10
```

**Key diagnostic**: Event fires but `hook_results: null` = permission issue or config problem.

### Pattern: "Agent bypassed instructions"

```bash
# Find agent invocations
grep "agentStart\|agentEnd" ~/.claude/projects/${pwd_encoded}/agent-*.jsonl

# Check what prompt agent received
grep -A20 '"role":"user"' ~/.claude/projects/${pwd_encoded}/agent-*.jsonl | head -50
```

**Common causes**: Unclear skill instructions, missing context, error-triggered workaround.

---

## Notes

- For large logs (>10MB), use grep/tail to filter before reading with Read tool
- Log format may change with Claude Code updates
- Report what you analyzed: "Checked debug/*.txt and agent-*.jsonl, found X errors"
