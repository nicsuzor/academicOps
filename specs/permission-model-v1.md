---
title: Task-Gated Permission Model v1.0
type: spec
category: specs
description: Architectural spec for enforcing task binding before destructive operations
tags: [permissions, enforcement, security]
status: draft
created: 2026-01-21
---

# Task-Gated Permission Model v1.0

## User Story

As a **framework user**, I want destructive operations (Write, Edit, git commit) blocked unless there's an active task binding, so that all work is tracked and agents cannot modify files without task accountability.

## Problem Statement

Currently, main agents have unrestricted access to file modification tools (Write, Edit, etc.). This creates observability and control problems:

1. **No work tracking**: Agents can modify files without any task in the system
2. **No scope enforcement**: Nothing prevents agents from editing files unrelated to their assigned work
3. **Permission sprawl**: Main agent has all permissions, making auditing impossible

The `/q` command exists as a workaround - users manually invoke it to create tasks. But this is opt-in, not enforced.

## Solution: Task-Gated Permissions

**Principle**: Destructive operations require an active task binding. No task = no edits.

### Enforcement Points

```
User Prompt
    │
    ▼
┌──────────────────┐
│  Hydration Gate  │  ─── Blocks until hydrator invoked
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Prompt Hydrator │  ─── Guides: "claim existing task or create new"
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Task Binding    │  ─── PostToolUse: sets current_task on create/claim
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Task Required    │  ─── PreToolUse: blocks Write/Edit if no current_task
│     Gate         │
└──────────────────┘
```

## Destructive Operations (Explicit Definition)

Tools that require task binding:

### Always Require Task

| Tool | Reason |
|------|--------|
| `Write` | Creates/overwrites files |
| `Edit` | Modifies existing files |
| `NotebookEdit` | Modifies Jupyter notebooks |

### Conditional (Bash Commands)

| Command Pattern | Requires Task | Reason |
|----------------|---------------|--------|
| `rm`, `rm -rf` | Yes | Deletes files |
| `mv`, `cp` | Yes | Moves/copies files |
| `mkdir`, `touch` | Yes | Creates filesystem entries |
| `chmod`, `chown` | Yes | Modifies permissions |
| `git commit`, `git push` | Yes | Commits/pushes changes |
| `npm install`, `pip install` | Yes | Modifies dependencies |
| `sed -i`, `awk -i` | Yes | In-place file edits |
| `cat`, `head`, `tail` | No | Read-only |
| `ls`, `find`, `grep` | No | Read-only |
| `git status`, `git diff`, `git log` | No | Read-only |
| `npm list`, `pip list` | No | Read-only |

### Never Require Task

| Tool | Reason |
|------|--------|
| `Read` | Read-only |
| `Glob` | Read-only |
| `Grep` | Read-only |
| `Task` | Spawning subagents (not destructive) |
| `WebFetch` | Read-only external |
| `WebSearch` | Read-only external |
| MCP read tools | Read-only |

## Bypass Conditions

### 1. User Bypass Prefix (`.`)

User prefix `.` signals "bypass all gates" for emergency/trivial fixes:

```
. fix this typo
```

This sets `gates_bypassed=true` in session state, which all gates respect.

### 2. Subagent Sessions

Subagents (detected via `CLAUDE_AGENT_TYPE` env var) bypass the gate because:
- They inherit the parent session's task context
- The parent is responsible for task binding
- Blocking subagents would break legitimate workflows

### 3. Task Operations

The tools that establish task binding are always allowed:
- `mcp__plugin_aops-core_task_manager__create_task`
- `mcp__plugin_aops-core_task_manager__update_task`

These are how agents CLAIM tasks - blocking them would be circular.

## Implementation

### PreToolUse Hook: `task_required_gate.py`

```python
def should_require_task(tool_name: str, tool_input: dict) -> bool:
    """Determine if this tool call requires task binding."""

    # File modification tools always require task
    if tool_name in ("Write", "Edit", "NotebookEdit"):
        return True

    # Bash commands: check for modification patterns
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        return is_destructive_bash(command)

    return False

def main():
    # ... parse input ...

    # Bypass: subagent sessions
    if os.environ.get("CLAUDE_AGENT_TYPE"):
        return allow()

    # Bypass: user prefix '.'
    if is_gates_bypassed(session_id):
        return allow()

    # Check if task required
    if not should_require_task(tool_name, tool_input):
        return allow()

    # Check for task binding
    current_task = get_current_task(session_id)
    if current_task:
        return allow()

    # No task - block
    print(BLOCK_MESSAGE, file=sys.stderr)
    sys.exit(2)
```

### Session State Extension

Add `gates_bypassed` flag to session state (set by UserPromptSubmit on `.` prefix):

```python
def set_gates_bypassed(session_id: str, bypassed: bool = True) -> None:
    """Set gates bypass flag for emergency/trivial operations."""
    state = get_or_create_session_state(session_id)
    state["state"]["gates_bypassed"] = bypassed
    save_session_state(session_id, state)

def is_gates_bypassed(session_id: str) -> bool:
    """Check if gates are bypassed for this session."""
    state = load_session_state(session_id)
    if state is None:
        return False
    return state.get("state", {}).get("gates_bypassed", False)
```

### Hydrator Update

The prompt-hydrator must include task routing in its output:

```markdown
### Task Routing

**Before any edits**, you must have an active task:

1. **Search existing tasks**: `mcp__plugin_aops-core_task_manager__search_tasks(query="keyword")`
2. **Claim existing**: `mcp__plugin_aops-core_task_manager__update_task(id="...", status="active")`
3. **Or create new**: `mcp__plugin_aops-core_task_manager__create_task(...)`

The task_required_gate will BLOCK Write/Edit until a task is bound to this session.
```

## /q Command Removal

With task binding enforced by the gate, `/q` becomes redundant:

| /q Functionality | New Location |
|-----------------|--------------|
| Hydrate prompt | Standard hydrator (already invoked) |
| Check for duplicates | Hydrator guidance includes search step |
| Place in hierarchy | Hydrator guidance includes parent finding |
| Create task(s) | Main agent follows hydrator guidance |

The `/q` command file can be removed. Its functionality is absorbed by the default hydration workflow.

## Error Messages

### Block Message (No Task)

```
⛔ TASK REQUIRED: No active task bound to this session.

Before modifying files, you must claim or create a task:

1. Search for existing task: `mcp__plugin_aops-core_task_manager__search_tasks(query="...")`
2. Claim it: `mcp__plugin_aops-core_task_manager__update_task(id="...", status="active")`
   Or create new: `mcp__plugin_aops-core_task_manager__create_task(...)`

This ensures all work is tracked. For emergency/trivial fixes, user can prefix prompt with `.`
```

## Migration Path

1. **Phase 1** (this spec): Implement in WARN mode (log but don't block)
2. **Phase 2**: Enable BLOCK mode after validation
3. **Phase 3**: Remove `/q` command once gate is proven

## Security Considerations

- Gate is FAIL-CLOSED: on error, block (safety over convenience)
- Bash command detection uses allowlist of safe commands, not blocklist
- Session state is per-session - no cross-session leakage

## Testing

### Must Pass

1. `Write` without task → BLOCKED
2. `Write` with task → ALLOWED
3. `Read` without task → ALLOWED (read-only)
4. `.` prefix → ALLOWED (bypass)
5. Subagent session → ALLOWED (bypass)
6. `Bash(ls)` without task → ALLOWED (read-only)
7. `Bash(rm file)` without task → BLOCKED (destructive)

## Acceptance Criteria

### Success Criteria
- `Write`/`Edit` without active task → BLOCKED with clear error message
- `Write`/`Edit` with active task → ALLOWED
- Read-only tools (Read, Glob, Grep) → ALLOWED without task
- User bypass prefix `.` → ALLOWED (gates bypassed)
- Subagent sessions → ALLOWED (inherit parent context)
- Task create/update tools → ALLOWED (establishes binding)

### Failure Modes
- Gate blocks legitimate subagent work → false positive, breaks workflows
- Destructive Bash commands not detected → bypass via command line
- Gates bypassed becomes default → no tracking benefit
- Session state not found → block all operations (fail-closed)

## Open Questions

- Should `git commit` without task be allowed for autocommit hooks?
- Should there be a "task timeout" after which binding expires?
- How to handle long-running sessions where task is completed mid-session?
