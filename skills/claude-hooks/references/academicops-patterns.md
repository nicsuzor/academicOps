# academicOps Hook Patterns

How academicOps uses Claude Code hooks to enforce framework principles and automate workflows.

## Architecture Context

From `ARCHITECTURE.md`:

**Enforcement Hierarchy** (most → least reliable):

1. **Scripts** - Code that prevents bad behavior
2. **Hooks** - Automated checks at key moments
3. **Configuration** - Permissions and restrictions
4. **Instructions** - Agent directives (agents forget in long conversations)

**Design principle:** If agents consistently disobey instructions, move enforcement UP the hierarchy (towards scripts/hooks), not adding more detailed instructions.

## Installation Pattern

**All academicOps repos use `/bots/` structure:**

```
repo/
├── bots/
│   ├── .academicOps/           # Symlink to $ACADEMICOPS
│   ├── hooks/                  # Repo-local hook scripts (optional)
│   ├── agents/                 # Repo-local agent overrides (optional)
│   └── docs/                   # Project agent instructions
├── .claude/
│   ├── settings.json           # Hook configuration
│   ├── agents -> bots/.academicOps/.claude/skills
│   └── commands -> bots/.academicOps/.claude/commands
```

**Hook configuration location:** `.claude/settings.json` in project root

**Hook scripts location:** `bots/hooks/` in framework (via `.academicOps` symlink)

## Path Resolution Pattern

**Problem:** Hooks need to find scripts regardless of agent's CWD

**Solution:** Use `$CLAUDE_PROJECT_DIR` environment variable

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/load_instructions.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/load_instructions.py || echo '{\"hookSpecificOutput\":{\"additionalContext\":\"# WARNING: Hook script not found\"}}'",
        "timeout": 5000
      }]
    }]
  }
}
```

**Why this works:**

- `$CLAUDE_PROJECT_DIR` = absolute path to repo root
- Works from any subdirectory
- Portable across installations
- Falls back gracefully if script missing

**Alternative (not recommended):** Relative paths resolve from CWD, breaking when agent changes directories

## Active Hooks in academicOps

### SessionStart: Instruction Loading

**Purpose:** Load 3-tier instruction hierarchy into agent context

**Script:** `bots/hooks/load_instructions.py`

**What it does:**

1. Loads `_CORE.md` from framework tier (`$ACADEMICOPS/bots/agents/`)
2. Loads from personal tier if exists (`$ACADEMICOPS_PERSONAL/bots/agents/`)
3. Loads from project tier if exists (`$PWD/bots/agents/`)
4. Combines all into `additionalContext` with priority headers
5. Includes git remote info for context

**Output format:**

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "# Agent Instructions\n\n## REPOSITORY\n\nGit remote origin: ...\n\n## PROJECT: ...\n\n## FRAMEWORK: ..."
  }
}
```

**Configuration:**

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/load_instructions.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/load_instructions.py || echo '{...}'",
        "timeout": 5000
      }]
    }]
  }
}
```

### PreToolUse: Tool Validation

**Purpose:** Enforce tool usage policies before execution

**Script:** `bots/hooks/validate_tool.py`

**Validation rules:**

- Block inline Python (`python -c`) → Require script files
- Block pytest without `uv run` → Enforce environment isolation
- Block python without `uv run` → Enforce package management
- Warn on `.md` file creation → Prevent documentation bloat
- Block `/tmp/` test files → Enforce long-term code
- Agent-specific permissions (trainer can edit `.claude/` files)

**Output formats:**

```json
// Allow
{
  "hookSpecificOutput": {
    "permissionDecision": "allow"
  }
}

// Block with reason
{
  "hookSpecificOutput": {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Inline Python (python -c) is blocked. Create a proper script file instead."
  }
}

// Warn but allow
{
  "hookSpecificOutput": {
    "permissionDecision": "allow",
    "systemMessage": "Creating .md file outside allowed paths. Consider whether this is necessary."
  }
}
```

**Exit codes:**

- `0` = allow
- `1` = warn (allow with message)
- `2` = block

### Stop/SubagentStop: Workflow Logging

**Purpose:** Log agent completion events, validate workflow state

**Script:** `bots/hooks/validate_stop.py`

**What it does:**

1. Receives stop event (main agent or subagent)
2. Logs to debug file for inspection
3. Can enforce completion requirements (future use)
4. Currently allows all stops (returns `{}`)

**Configuration:**

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py Stop || echo '{}'",
        "timeout": 2000
      }]
    }],
    "SubagentStop": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py SubagentStop || echo '{}'",
        "timeout": 2000
      }]
    }]
  }
}
```

### PostToolUse: Debug Logging (Noop)

**Purpose:** Capture post-execution data for hook development

**Script:** `bots/hooks/log_posttooluse.py`

**What it does:**

1. Receives tool execution result
2. Logs input/output to `/tmp/claude_posttooluse_{timestamp}.json`
3. Returns empty output (no behavior modification)

**Output:** `{}` (noop - always continue)

**Usage:** Inspect logs to understand what data is available for future validation

### UserPromptSubmit: Debug Logging (Noop)

**Purpose:** Capture user input for hook development

**Script:** `bots/hooks/log_userpromptsubmit.py`

**What it does:**

1. Receives user prompt before Claude processes
2. Logs to `/tmp/claude_userpromptsubmit_{timestamp}.json`
3. Returns empty output (no behavior modification)

**Output:** `{}` (noop - always continue)

## Debug Logging Pattern

**Shared utility:** `bots/hooks/hook_debug.py`

All hooks use `safe_log_to_debug_file()` for consistent logging:

```python
from hook_debug import safe_log_to_debug_file


def main():
    input_data = json.load(sys.stdin)

    # ... hook logic ...

    output_data = {"result": "..."}

    # Log before returning
    safe_log_to_debug_file("PreToolUse", input_data, output_data)

    print(json.dumps(output_data))
```

**Log location:** `/tmp/claude_{hook_event}_{timestamp}.json`

**Log format:**

```json
{
  "hook_event": "PreToolUse",
  "timestamp": "2025-10-22T23:13:51.603727+00:00",
  "input": {/* full stdin */},
  "output": {/* full stdout */}
}
```

**Benefits:**

- Non-invasive (never crashes hooks)
- Timestamped for correlation
- Full input/output capture
- Helps design future hooks

## Fail-Fast Hook Pattern

**From `references/FAIL-FAST.md`:**

**Agents don't defend against missing hooks:**

```json
// ❌ Wrong - defensive
"command": "if [ -f script.py ]; then python script.py; else echo 'missing'; fi"

// ✅ Correct - fail-fast
"command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/script.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/script.py || echo '{\"error\":\"script not found\"}'"
```

**Why:**

- If hook script missing, something is wrong with installation
- Error message directs user to fix infrastructure
- No silent failures masking problems
- Trainer agent fixes root cause, not hook logic

## Permission Integration

**Hooks work WITH permission system:**

`.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run python:*)"
    ],
    "deny": [
      "Write(**/*.md)",
      "Write(**/*.env*)"
    ]
  },
  "hooks": {
    "PreToolUse": [/* validation hooks */]
  }
}
```

**Execution order:**

1. Claude creates tool parameters
2. Permission system checks deny/allow rules
3. PreToolUse hooks execute (if permission granted)
4. Tool executes (if hook allows)

**Hooks can:**

- Add context-aware validation beyond simple patterns
- Provide detailed error messages
- Enforce project-specific rules
- Log usage patterns

## Testing Pattern

**Integration test validates hooks from subdirectories:**

From `tests/integration/test_claude_headless.py`:

```python
def test_hook_allow_permits_execution(claude_headless):
    # Test hooks work from subdirectory (validates $CLAUDE_PROJECT_DIR)
    result = claude_headless(
        "First cd to tests/ subdirectory, then use the Read tool...", model="haiku"
    )

    assert result["success"]
    assert not result["permission_denials"]
```

**What this validates:**

- Hooks resolve paths correctly from any CWD
- `$CLAUDE_PROJECT_DIR` works as expected
- No silent failures when agent changes directories

## Common Mistakes & Solutions

### Mistake: Relative paths

```json
// ❌ Breaks when agent in subdirectory
"command": "uv run python bots/hooks/script.py"
```

**Solution:** Use `$CLAUDE_PROJECT_DIR`

```json
// ✅ Works from anywhere
"command": "uv run python $CLAUDE_PROJECT_DIR/bots/hooks/script.py"
```

### Mistake: No fallback

```json
// ❌ Cryptic error if script missing
"command": "uv run python $CLAUDE_PROJECT_DIR/bots/hooks/script.py"
```

**Solution:** Test and provide informative fallback

```json
// ✅ Clear error message
"command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/script.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/script.py || echo '{\"error\":\"Hook script not found - check installation\"}'"
```

### Mistake: Blocking without reason

```json
// ❌ Claude doesn't know why
{
  "hookSpecificOutput": {
    "permissionDecision": "deny"
  }
}
```

**Solution:** Always provide reason

```json
// ✅ Claude understands and can adapt
{
  "hookSpecificOutput": {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Inline Python blocked. Use 'uv run python script.py' instead."
  }
}
```

### Mistake: Long-running hooks

```json
// ❌ Timeout after 60s
"command": "complex-operation-that-takes-2-minutes"
```

**Solution:** Increase timeout or make async

```json
// ✅ Extended timeout
{
  "type": "command",
  "command": "...",
  "timeout": 180
}
```

## When to Create New Hooks

**Consider a hook when:**

1. Agents consistently violate a rule despite instructions
2. Validation requires runtime context (tool name, file path, etc.)
3. Behavior must be guaranteed (not probabilistic)
4. Need to inject dynamic context at session start

**Don't create a hook when:**

1. Permission patterns suffice (use `permissions.deny`)
2. Agent can follow simple instructions reliably
3. Validation is static (use pre-commit hooks instead)
4. Performance sensitive (hooks add latency)

**Process:**

1. Try instructions first
2. If agents forget → Try permission rules
3. If too complex for patterns → Consider hook
4. Prototype with debug logging first
5. Test thoroughly from various CWDs
6. Document in ARCHITECTURE.md

## Hook Development Workflow

1. **Enable debug logging:** Add `safe_log_to_debug_file()` to capture data
2. **Test from subdirectories:** Verify `$CLAUDE_PROJECT_DIR` works
3. **Provide clear errors:** Help agents understand why blocked
4. **Fall back gracefully:** Don't crash if dependencies missing
5. **Update tests:** Add integration test for new hook behavior
6. **Document:** Update ARCHITECTURE.md with new hook

## References

- `ARCHITECTURE.md` - Overall system design
- `docs/hooks_guide.md` - Complete hooks reference
- `bots/hooks/` - Hook script implementations
- `.claude/settings.json` - Hook configuration
- `/tmp/claude_*` - Debug logs for inspection
