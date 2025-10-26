# Real-World Hook Examples from academicOps

Complete, working examples of hooks from the academicOps implementation.

## SessionStart: 3-Tier Instruction Loading

**File:** `bots/hooks/load_instructions.py`

**Purpose:** Load agent instructions from framework, personal, and project tiers

**Full implementation pattern:**
```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file

def get_tier_paths(filename: str) -> dict[str, Path | None]:
    """Get paths to instruction file at all three tiers."""
    paths = {}

    # Framework tier (REQUIRED)
    if bot_path := os.environ.get("ACADEMICOPS_BOT"):
        paths["framework"] = Path(bot_path) / "bots" / "agents" / filename
    else:
        raise ValueError("ACADEMICOPS_BOT environment variable not set")

    # Personal tier (OPTIONAL)
    if personal_path := os.environ.get("ACADEMICOPS_PERSONAL"):
        paths["personal"] = Path(personal_path) / "bots" / "agents" / filename
    else:
        paths["personal"] = None

    # Project tier (OPTIONAL)
    paths["project"] = Path.cwd() / "bots" / "agents" / filename

    return paths

def main():
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        if not sys.stdin.isatty():
            input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Load content from each tier
    paths = get_tier_paths("_CORE.md")
    contents = {}
    for tier, path in paths.items():
        if path and path.exists():
            contents[tier] = path.read_text()

    # Build output with priority order
    sections = []
    if "project" in contents:
        sections.append(f"## PROJECT\\n\\n{contents['project']}")
    if "personal" in contents:
        sections.append(f"## PERSONAL\\n\\n{contents['personal']}")
    if "framework" in contents:
        sections.append(f"## FRAMEWORK\\n\\n{contents['framework']}")

    additional_context = "# Agent Instructions\\n\\n" + "\\n\\n".join(sections)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context
        }
    }

    # Debug log
    output_data = {
        "tiers_loaded": list(contents.keys()),
        "paths": {k: str(v) for k, v in paths.items() if v}
    }
    safe_log_to_debug_file("SessionStart", input_data, output_data)

    # Output JSON
    print(json.dumps(output))
    sys.exit(0)
```

**Configuration:**
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

## PreToolUse: Block Inline Python

**File:** `bots/hooks/validate_tool.py`

**Purpose:** Block `python -c` and require script files

**Validation rule:**
```python
class ValidationRule:
    name: str = "block_inline_python"
    tool_patterns: list[str] = ["Bash"]
    command_patterns: list[str] = ["*python -c*", "*python3 -c*"]
    allowed_agents: set[str] = set()  # No exceptions

    def validate(self, tool_name: str, tool_input: dict, agent: str) -> tuple[bool, str, str]:
        command = tool_input.get("command", "")

        if "python -c" in command or "python3 -c" in command:
            return (
                False,
                "Inline Python (python -c) is blocked. Create a proper script file instead.",
                "block"
            )

        return (True, "", "allow")
```

**Output when blocked:**
```json
{
  "hookSpecificOutput": {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Inline Python (python -c) is blocked. Create a proper script file instead."
  }
}
```

**Configuration:**
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

## PreToolUse: Warn on Markdown Creation

**Purpose:** Discourage unnecessary documentation files

**Validation rule:**
```python
class ValidationRule:
    name: str = "warn_markdown_creation"
    tool_patterns: list[str] = ["Write"]
    file_patterns: list[str] = ["**/*.md"]
    allowed_agents: set[str] = {"trainer"}  # Trainer can create docs

    def validate(self, tool_name: str, tool_input: dict, agent: str) -> tuple[bool, str, str]:
        file_path = tool_input.get("file_path", "")

        # Allow certain paths
        if any(pattern in file_path for pattern in ["papers/", "/tmp/", "bots/agents/"]):
            return (True, "", "allow")

        # Warn but allow
        return (
            True,
            "Creating .md file outside allowed paths. Consider whether documentation is necessary - prefer self-documenting code.",
            "warn"
        )
```

**Output when warning:**
```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow",
    "systemMessage": "Creating .md file outside allowed paths. Consider whether documentation is necessary."
  }
}
```

**Exit code:** `1` (warn - allow with message)

## Stop: Simple Logging Hook

**File:** `bots/hooks/validate_stop.py`

**Purpose:** Log stop events, allow all

**Implementation:**
```python
#!/usr/bin/env python3
import json
import sys
from typing import Any

from hook_debug import safe_log_to_debug_file

def main():
    # Read input
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}

    hook_event = sys.argv[1] if len(sys.argv) > 1 else "Stop"

    # Noop output - allow all stops
    output_data = {}

    # Debug log
    safe_log_to_debug_file(hook_event, input_data, output_data)

    # Output empty JSON (continue)
    print(json.dumps(output_data))
    sys.exit(0)
```

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

## Debug Logging: Noop Hook Pattern

**File:** `bots/hooks/log_posttooluse.py`

**Purpose:** Capture data for hook development without modifying behavior

**Implementation:**
```python
#!/usr/bin/env python3
import json
import sys
from typing import Any

from hook_debug import safe_log_to_debug_file

def main():
    # Read input
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        pass

    # Noop output
    output_data: dict[str, Any] = {}

    # Debug log hook execution
    safe_log_to_debug_file("PostToolUse", input_data, output_data)

    # Output empty JSON (no behavior modification)
    print(json.dumps(output_data))
    sys.exit(0)
```

**Inspecting logs:**
```bash
# View recent PostToolUse events
ls -lt /tmp/claude_posttooluse_*.json | head -5

# Read specific log
cat /tmp/claude_posttooluse_20251022_231351.json
```

**Log contents:**
```json
{
  "hook_event": "PostToolUse",
  "timestamp": "2025-10-22T23:13:51.603727+00:00",
  "input": {
    "tool_name": "Bash",
    "tool_input": {
      "command": "ls -la",
      "description": "List files"
    },
    "tool_response": {
      "success": true,
      "output": "total 48\\ndrwxr-xr-x..."
    }
  },
  "output": {}
}
```

## Shared Debug Utility

**File:** `bots/hooks/hook_debug.py`

**Purpose:** Centralized safe logging for all hooks

**Implementation:**
```python
#!/usr/bin/env python3
import datetime
import json
from pathlib import Path
from typing import Any

def safe_log_to_debug_file(
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
) -> None:
    """
    Safely log hook invocation to timestamped debug file.
    Never crashes - failures silently ignored.
    """
    try:
        log_dir = Path("/tmp")
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S_%f")
        log_file = log_dir / f"claude_{hook_event.lower()}_{timestamp}.json"

        debug_data = {
            "hook_event": hook_event,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "input": input_data,
            "output": output_data,
        }

        with log_file.open("w") as f:
            json.dump(debug_data, f, indent=2)
            f.write("\\n")
    except Exception:
        # Silently ignore logging failures - never crash a hook
        pass
```

**Usage in any hook:**
```python
from hook_debug import safe_log_to_debug_file

def main():
    input_data = json.load(sys.stdin)

    # ... hook logic ...

    output_data = {"result": "success"}

    safe_log_to_debug_file("MyHook", input_data, output_data)

    print(json.dumps(output_data))
```

## Complete settings.json Example

**File:** `.claude/settings.json` in academicOps

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run python:*)",
      "mcp__gh__create_issue"
    ],
    "deny": [
      "Write(**/*.env*)",
      "Read(**/*.cache/**)",
      "Write(./**/.venv/**)"
    ]
  },
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/load_instructions.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/load_instructions.py || echo '{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"# WARNING: Hook script not found\"}}'",
        "timeout": 5000
      }]
    }],
    "PreToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/validate_tool.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/validate_tool.py || echo '{\"continue\":true,\"systemMessage\":\"WARNING: Hook script not found\"}'",
        "timeout": 3000
      }]
    }],
    "SubagentStop": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py SubagentStop || echo '{\"continue\":true,\"systemMessage\":\"WARNING: Hook script not found\"}'",
        "timeout": 2000
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/validate_stop.py Stop || echo '{\"continue\":true,\"systemMessage\":\"WARNING: Hook script not found\"}'",
        "timeout": 2000
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/log_posttooluse.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/log_posttooluse.py || echo '{}'",
        "timeout": 2000
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "test -f $CLAUDE_PROJECT_DIR/bots/hooks/log_userpromptsubmit.py && uv run python $CLAUDE_PROJECT_DIR/bots/hooks/log_userpromptsubmit.py || echo '{}'",
        "timeout": 2000
      }]
    }]
  }
}
```

## Testing Hooks

**Integration test pattern:**
```python
def test_hook_allow_permits_execution(claude_headless):
    # Test hooks work from subdirectory
    result = claude_headless(
        "First cd to tests/ subdirectory, then use the Read tool to read ../README.md",
        model="haiku"
    )

    assert result["success"], "Hook should work from subdirectory"
    assert not result["permission_denials"]
```

**What this validates:**
- `$CLAUDE_PROJECT_DIR` resolves correctly
- Hooks execute from any CWD
- No silent path resolution failures

## Debugging Hooks

**Run Claude with debug flag:**
```bash
claude --debug
```

**Check logs:**
```bash
# List recent logs by hook type
ls -lt /tmp/claude_sessionstart_*.json | head -3
ls -lt /tmp/claude_pretooluse_*.json | head -3
ls -lt /tmp/claude_stop_*.json | head -3

# View specific log
jq . /tmp/claude_pretooluse_20251022_231351.json
```

**Common issues:**

**Hook not executing:**
- Check settings.json syntax (valid JSON?)
- Verify script path with `$CLAUDE_PROJECT_DIR`
- Check script is executable: `chmod +x bots/hooks/script.py`
- Look for Python import errors in stderr

**Wrong output format:**
- Validate JSON structure matches schema
- Check exit codes (0=allow, 1=warn, 2=block)
- Ensure `permissionDecision` field present for PreToolUse

**Timeout:**
- Increase timeout in hook config
- Profile slow operations
- Consider async execution for long tasks

**Path resolution:**
- Always use `$CLAUDE_PROJECT_DIR`
- Test from subdirectories: `cd tests/ && claude`
- Never use relative paths without environment variable
