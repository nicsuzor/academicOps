---
name: claude-hooks
description: This skill should be used when working with Claude Code hooks - creating,
  configuring, debugging, or understanding hook input/output schemas. Provides complete
  technical reference for all hook types, academicOps patterns, and real-world examples.
permalink: aops/skills/claude-hooks/skill
---

# Claude Code Hooks

## Overview

Claude Code hooks are shell commands that execute at specific lifecycle events (SessionStart, PreToolUse, PostToolUse, Stop, etc.). They enable deterministic automation, validation, and context injection by running scripts that receive JSON input via stdin and return structured JSON output via stdout.

This skill provides comprehensive knowledge of:

- Hook event types and their input/output schemas
- academicOps hook patterns and enforcement hierarchy
- Path resolution using `$CLAUDE_PROJECT_DIR`
- Real-world implementations with complete code examples
- Debugging techniques and common issues

## When to Use This Skill

Use this skill when:

- Creating a new hook for validation or automation
- Understanding what data is available in hook input
- Debugging hooks that aren't executing correctly
- Learning academicOps hook architecture patterns
- Configuring hooks in `.claude/settings.json`
- Deciding whether to use hooks vs permissions vs instructions

**Example triggers:**

- "How do I create a PreToolUse hook to validate tool usage?"
- "What input data does the SessionStart hook receive?"
- "Why isn't my hook executing from subdirectories?"
- "Show me examples of real hooks from academicOps"
- "How does academicOps use hooks for enforcement?"

## Hook Fundamentals

### Hook Lifecycle Events

Claude Code supports 9 hook events:

1. **SessionStart** - Session begins or resumes
2. **PreToolUse** - Before tool execution (can block)
3. **PostToolUse** - After tool execution
4. **UserPromptSubmit** - Before processing user input
5. **Stop** - Main agent finishes response
6. **SubagentStop** - Subagent (Task tool) finishes
7. **SessionEnd** - Session terminates
8. **PreCompact** - Before context compaction
9. **Notification** - Permission requests or idle notifications

### Basic Configuration Pattern

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "EventName": [{
      "hooks": [{
        "type": "command",
        "command": "script-to-execute",
        "timeout": 60
      }]
    }]
  }
}
```

### Input/Output Contract

**All hooks receive JSON via stdin:**

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "hook_event_name": "EventName"
  // ... event-specific fields
}
```

**Hooks respond via stdout (JSON) and exit codes:**

- Exit `0` = Success/allow
- Exit `1` = Warning (allow with message)
- Exit `2` = Block/error

**Common output fields:**

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "explanation",
    "additionalContext": "context for Claude"
  }
}
```

## Core Workflow: Creating a Hook

### Step 1: Choose Hook Type

Match your use case to the appropriate hook event:

**Inject context at session start** → SessionStart

- Example: Load instruction files, set environment

**Validate tool usage before execution** → PreToolUse

- Example: Block dangerous commands, enforce patterns

**Process tool results** → PostToolUse

- Example: Auto-format code, run tests, update state

**Validate prompt input** → UserPromptSubmit

- Example: Block sensitive queries, inject safety context

**Enforce completion requirements** → Stop/SubagentStop

- Example: Ensure tests pass, validate workflow state

### Step 2: Understand Input Schema

**Read the complete schema** in `references/hook-schemas.md` for your chosen hook type.

Key patterns to note:

- **SessionStart**: No matcher, receives `source` field
- **PreToolUse**: Receives `tool_name` and `tool_input`
- **PostToolUse**: Receives `tool_response` with execution results
- **Stop**: Receives `stop_hook_active` to prevent recursion

### Step 3: Design Hook Logic

**Follow academicOps enforcement hierarchy** (from `references/academicops-patterns.md`):

1. **Scripts** - Most reliable
2. **Hooks** - Automated checks ← YOU ARE HERE
3. **Configuration** - Permission patterns
4. **Instructions** - Least reliable

**When to use hooks:**

- Agents consistently violate instructions
- Validation requires runtime context
- Need guaranteed (non-probabilistic) behavior
- Must inject dynamic context

**When NOT to use hooks:**

- Simple pattern matching → Use `permissions.deny` instead
- Agents follow instructions reliably → Keep as instructions
- Static validation → Use pre-commit hooks
- Performance sensitive → Hooks add latency

### Step 4: Implement Hook Script

**Use academicOps patterns:**

```python
#!/usr/bin/env python3
import json
import sys
from typing import Any

# Import shared debug utility
from hook_debug import safe_log_to_debug_file

def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}), file=sys.stderr)
        sys.exit(2)

    # Extract relevant fields
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})

    # Validation logic
    if should_block(tool_name, tool_input):
        output = {
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "Explanation for Claude"
            }
        }
        exit_code = 2
    else:
        output = {
            "hookSpecificOutput": {
                "permissionDecision": "allow"
            }
        }
        exit_code = 0

    # Debug log (safe, never crashes)
    safe_log_to_debug_file("PreToolUse", input_data, output)

    # Output JSON to stdout
    print(json.dumps(output))
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
```

**Key patterns:**

- Always import and use `safe_log_to_debug_file()` for debugging
- Provide clear `permissionDecisionReason` when blocking
- Handle JSON parse errors gracefully
- Exit with appropriate code (0/1/2)

### Step 5: Configure in settings.json

**Use `$CLAUDE_PROJECT_DIR` for path resolution:**

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/validate_tool.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/validate_tool.py || echo '{\"hookSpecificOutput\":{\"permissionDecision\":\"allow\"}}'",
        "timeout": 3000
      }]
    }]
  }
}
```

**Pattern breakdown:**

1. `test -f $CLAUDE_PROJECT_DIR/bots/hooks/script.py` - Check script exists
2. `&& uv run python $CLAUDE_PROJECT_DIR/bots/hooks/script.py` - Execute if found
3. `|| echo '{...}'` - Fallback if script missing (don't crash session)

**Why `$CLAUDE_PROJECT_DIR`:**

- Resolves to absolute path of project root
- Works from any subdirectory (agent can `cd` anywhere)
- Portable across installations
- Recommended by Claude Code documentation

### Step 6: Test from Subdirectories

**Critical:** Hooks must work regardless of agent's CWD.

**Test manually:**

```bash
cd tests/  # Change to subdirectory
claude     # Launch Claude Code

# Try operations that trigger your hook
# Check that hook executes without path errors
```

**Add integration test:**

```python
def test_my_hook_from_subdirectory(claude_headless):
    result = claude_headless(
        "First cd to tests/, then [trigger hook operation]",
        model="haiku"
    )

    assert result["success"]
    # Add specific assertions for your hook behavior
```

### Step 7: Debug and Iterate

**Enable debug logging:**

```bash
claude --debug
```

**Inspect hook logs:**

```bash
# List recent logs for your hook type
ls -lt /tmp/claude_pretooluse_*.json | head -5

# View specific log
cat /tmp/claude_pretooluse_20251022_231351.json | jq .
```

**Log contents show:**

- Complete input data Claude sent to hook
- Complete output data hook returned
- Timestamp for correlation
- Any errors or unexpected data

**Common issues:**

- **Hook not executing:** Check settings.json syntax, script path, permissions
- **Path errors:** Use `$CLAUDE_PROJECT_DIR`, test from subdirectories
- **Timeout:** Increase timeout value, optimize slow operations
- **Wrong output:** Validate JSON matches schema for your hook type

## academicOps Hook Architecture

### Installation Structure

All academicOps repos use consistent structure:

```
repo/
├── bots/
│   ├── .academicOps/           # Symlink to framework
│   └── hooks/                  # Hook scripts here
├── .claude/
│   └── settings.json           # Hook configuration here
```

**Hook scripts location:** `bots/hooks/` (via `.academicOps` symlink) **Hook configuration:** `.claude/settings.json`

### Active Hooks in academicOps

**SessionStart (`load_instructions.py`):**

- Loads 3-tier instruction hierarchy (framework → personal → project)
- Injects combined instructions as `additionalContext`
- Example in `references/examples.md`

**PreToolUse (`validate_tool.py`):**

- Blocks inline Python (`python -c`)
- Enforces `uv run python` for isolation
- Warns on `.md` file creation
- Blocks `/tmp/` test files
- Example in `references/examples.md`

**Stop/SubagentStop (`validate_stop.py`):**

- Logs completion events
- Can enforce workflow requirements
- Currently allows all (debug logging only)

**PostToolUse (`log_posttooluse.py`):**

- Noop hook for development
- Captures tool execution data
- Logs to `/tmp/` for inspection

**UserPromptSubmit (`log_userpromptsubmit.py`):**

- Noop hook for development
- Captures user input data
- Logs to `/tmp/` for inspection

### Enforcement Hierarchy

From ARCHITECTURE.md, academicOps uses layered enforcement:

1. **Scripts** (most reliable) - Deterministic automation
2. **Hooks** (automated) - Runtime validation ← This skill
3. **Configuration** (pattern-based) - Permission rules
4. **Instructions** (probabilistic) - Agent directives

**Design principle:** If agents consistently disobey instructions, move enforcement UP (towards scripts/hooks), not adding more instructions.

### Debug Logging Pattern

**All hooks use shared utility** (`bots/hooks/hook_debug.py`):

```python
from hook_debug import safe_log_to_debug_file

def main():
    input_data = json.load(sys.stdin)

    # ... hook logic ...

    output_data = {"result": "..."}

    # Safe logging (never crashes)
    safe_log_to_debug_file("MyHook", input_data, output_data)

    print(json.dumps(output_data))
```

**Benefits:**

- Consistent logging across all hooks
- Timestamped files in `/tmp/`
- Full input/output capture
- Helps design future hooks
- Never crashes (silently ignores failures)

## Reference Documentation

### Complete Technical Schemas

**File:** `references/hook-schemas.md`

Contains complete input/output schemas for all 9 hook types:

- SessionStart, PreToolUse, PostToolUse
- Stop, SubagentStop
- UserPromptSubmit, SessionEnd
- PreCompact, Notification

**When to reference:**

- Designing a new hook
- Understanding what data is available
- Validating output format
- Debugging schema mismatches

### academicOps Patterns

**File:** `references/academicops-patterns.md`

Contains academicOps-specific knowledge:

- Enforcement hierarchy
- Installation structure
- Path resolution patterns
- Active hook implementations
- Testing patterns
- Common mistakes and solutions

**When to reference:**

- Working in academicOps repos
- Understanding existing hooks
- Following established patterns
- Avoiding common pitfalls

### Real-World Examples

**File:** `references/examples.md`

Contains complete, working implementations:

- SessionStart 3-tier loading
- PreToolUse validation rules
- Stop logging hooks
- Noop debug hooks
- Shared utilities
- Complete settings.json

**When to reference:**

- Starting a new hook (copy pattern)
- Seeing complete implementations
- Understanding integration
- Learning by example

## Common Patterns and Recipes

### Pattern: Block with Helpful Error

```python
if violates_rule(tool_input):
    return {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": "Rule violated. Try this instead: <alternative>"
        }
    }
```

**Why:** Claude can adapt behavior when given clear guidance.

### Pattern: Warn but Allow

```python
if questionable_pattern(tool_input):
    print("WARNING: This might cause issues", file=sys.stderr)
    sys.exit(1)  # Warn (1) but don't block (2)
```

**Why:** Guide agents without blocking legitimate use cases.

### Pattern: Inject Dynamic Context

```python
# SessionStart or UserPromptSubmit
context = generate_dynamic_context()

return {
    "hookSpecificOutput": {
        "additionalContext": context
    }
}
```

**Why:** Provide runtime-specific information agents can't know ahead of time.

### Pattern: Noop with Logging

```python
# Any hook type
safe_log_to_debug_file(hook_event, input_data, {})

print(json.dumps({}))  # No behavior modification
sys.exit(0)
```

**Why:** Capture data for future hook development without affecting behavior.

### Pattern: Graceful Degradation

```json
{
  "command": "test -f $CLAUDE_PROJECT_DIR/script.py && uv run python $CLAUDE_PROJECT_DIR/script.py || echo '{\"hookSpecificOutput\":{\"permissionDecision\":\"allow\"}}'"
}
```

**Why:** Session continues even if hook script missing (infrastructure issues shouldn't crash sessions).

## Troubleshooting Guide

### Hook Not Executing

**Symptoms:** No debug logs, hook seems ignored

**Checks:**

1. Validate `.claude/settings.json` syntax (valid JSON?)
2. Verify hook script exists at expected path
3. Check script is executable: `chmod +x bots/hooks/script.py`
4. Run `claude --debug` to see execution attempts
5. Look for Python import errors in stderr

**Fix:** Correct path, syntax, or permissions issue

### Path Resolution Fails

**Symptoms:** "File not found" from subdirectories

**Checks:**

1. Does command use `$CLAUDE_PROJECT_DIR`?
2. Test from subdirectory: `cd tests/ && claude`
3. Check debug logs for actual path resolution

**Fix:** Always use `$CLAUDE_PROJECT_DIR/bots/hooks/script.py` pattern

### Hook Times Out

**Symptoms:** Hook execution interrupted after 60s (or configured timeout)

**Checks:**

1. Profile hook execution time
2. Check for slow network requests
3. Look for blocking I/O operations

**Fix:** Increase timeout or optimize performance

### Wrong Output Format

**Symptoms:** Hook returns but behavior incorrect

**Checks:**

1. Validate JSON output matches schema
2. Check exit code (0/1/2)
3. Inspect debug logs for actual output
4. Verify field names (e.g., `permissionDecision` not `decision`)

**Fix:** Correct output format for hook type

### Hook Blocks Unintentionally

**Symptoms:** Valid operations being blocked

**Checks:**

1. Review validation logic
2. Check for overly broad patterns
3. Inspect debug logs for input data
4. Verify exit codes

**Fix:** Refine validation rules, add exceptions

## Best Practices

### DO:

- ✅ Use `$CLAUDE_PROJECT_DIR` for all script paths
- ✅ Test hooks from subdirectories
- ✅ Provide clear `permissionDecisionReason` when blocking
- ✅ Use `safe_log_to_debug_file()` for debugging
- ✅ Handle JSON parse errors gracefully
- ✅ Include fallback for missing scripts
- ✅ Document hook purpose in comments

### DON'T:

- ❌ Use relative paths without `$CLAUDE_PROJECT_DIR`
- ❌ Block without explanation
- ❌ Crash on invalid input
- ❌ Create long-running hooks (>5s)
- ❌ Forget to test from subdirectories
- ❌ Mix hook logic with application code
- ❌ Skip debug logging

## See Also

- `ARCHITECTURE.md` - Overall academicOps design
- `docs/hooks_guide.md` - Comprehensive hooks reference
- `bots/hooks/` - Hook script implementations
- `.claude/settings.json` - Hook configuration
- `/tmp/claude_*` - Debug logs for inspection
