---
title: aOps Testing
type: documentation
entity_type: note
tags:
- testing
- hooks
- validation
permalink: aops/docs/tests
---

# aOps Testing

Current testing status and methodology for the aOps framework.

## Current State

**Status**: Comprehensive test suite exists with 22 test files + end-to-end headless testing.

**What exists**:
- ✅ `tests/` directory with pytest infrastructure
- ✅ 22 test files covering hooks, scripts, and integration
- ✅ conftest.py with shared fixtures
- ✅ **End-to-end headless Claude sessions** via `claude_headless` fixture
- ✅ Integration tests that invoke actual Claude Code sessions
- ✅ Hooks run in production via Claude Code lifecycle
- ✅ Debug logging to `~/.claude/debug/`
- ✅ Session log capture from headless runs

**What doesn't exist**:
- CI/CD test pipeline (tests exist but not automated in CI)
- Coverage reporting configuration

## Test Suite Overview

**Location**: `${AOPS}/tests/`

**Test count**: 25+ test files + conftest.py + integration infrastructure

### Hook Tests

**Covered hooks**:

1. **test_hook_start.py** - SessionStart hook
   - Tests load_instructions.py
   - Validates JSON output format
   - Tests missing file handling

2. **test_hook_pretool.py** - PreToolUse hook
   - Tests validate_tool.py
   - Validates permission blocking/allowing
   - Tests exit codes (0=allow, 1=warn, 2=block)

3. **test_hook_stop.py** - Stop hook
   - Tests validate_stop.py
   - Validates uncommitted changes detection
   - Tests exit codes

4. **test_stop_hook_resilience.py** - Stop hook edge cases
   - Tests error handling
   - Tests resilience to failures

5. **test_validate_tool.py** - Tool validation rules
   - Tests rule matching logic
   - Tests file pattern matching

6. **test_session_logging_hook.py** - Session logging
   - Tests log_session_stop.py
   - Validates logging format

### Integration Tests (Headless E2E)

**Infrastructure**: `claude_headless` fixture runs actual Claude Code sessions

7. **test_load_instructions_integration.py**
   - End-to-end SessionStart testing
   - Tests with actual file system

8. **test_context_loading_integration.py**
   - Tests context loading across tiers
   - Integration with chunk system

9. **test_chunks_loading.py**
   - Tests @reference mechanism
   - Validates chunk loading

**Headless E2E tests** (in `tests/integration/`):

10. **test_claude_headless.py**
    - Agent detection (@agent-trainer, @agent-developer)
    - Hook integration (deny blocks, allow permits)
    - Claude Code interpretation of hook output

11. **test_headless_simple.py**
    - Basic headless fixture functionality
    - Working directory verification
    - Simple agent invocation

12. **test_context_loading.py**
    - Context loading in headless sessions

13. **test_dogfooding.py**
    - Framework dogfooding tests

14. **test_hook_output_streams.py**
    - Hook stdout/stderr handling

15. **test_model_performance.py**
    - Model performance comparisons

### Architecture Tests

16. **test_deployment_architecture.py**
    - Tests repository structure
    - Validates paths.toml compliance

17. **test_instruction_tree.py**
    - Tests instruction hierarchy
    - Validates file relationships

18. **test_unified_schema.py**
    - Tests data schema consistency

### Script Tests

19. **test_task_scripts.py**
    - Tests task management scripts
    - Validates task_*.py functionality

20. **test_task_scripts_path_resolution.py**
    - Tests ${AOPS} path resolution
    - Validates environment variable usage

21. **test_task_add_priority.py**
    - Tests task_add.py priority handling

22. **test_task_add_scribe_priority.py**
    - Tests scribe integration with task_add.py

### Other Tests

23. **test_code_review.py**
    - Tests code review functionality

24. **test_command_file_integrity.py**
    - Tests command file validation

25. **test_validation_rules.py**
    - Tests validation rule system

### Test Infrastructure

- **conftest.py** - pytest configuration and shared fixtures
- **integration/conftest.py** - Headless testing fixtures
- **paths.py** - Path resolution utility (loads from paths.toml)
- **hooks.py** - Hook testing utilities
- **tests/integration/** - E2E integration tests
- **tests/prompts/** - Test prompts for E2E tests
- **tests/results/** - Test results storage

## Path Resolution

### tests/paths.py Utility

**Purpose**: Single source of truth for path resolution in tests, loads from paths.toml

**Usage**:
```python
from tests.paths import get_aops_root, get_aca_root, get_hook_script

# Get framework root
aops_root = get_aops_root()  # Uses $AOPS or auto-detects

# Get personal workspace root
aca_root = get_aca_root()  # Uses $ACA or auto-detects

# Get hook script path
validate_tool = get_hook_script("validate_tool.py")
```

**Functions**:
- `get_aops_root()` - Returns `${AOPS}` (framework repo)
- `get_aca_root()` - Returns `${ACA}` (personal workspace)
- `get_hooks_dir()` - Returns `${AOPS}/hooks`
- `get_skills_dir()` - Returns `${AOPS}/skills`
- `get_scripts_dir()` - Returns `${AOPS}/scripts`
- `get_tests_dir()` - Returns `${AOPS}/tests`
- `get_data_dir()` - Returns `${ACA}/data`
- `get_hook_script(name)` - Returns path to hook script
- `load_paths_config()` - Loads paths.toml as dict


## End-to-End Headless Testing

### claude_headless Fixture

**Location**: `tests/integration/conftest.py`

**Purpose**: Invoke actual Claude Code sessions programmatically with structured output

**Usage**:
```python
def test_something(claude_headless):
    result = claude_headless(
        "What is your current working directory?",
        model="haiku"  # Always use haiku for tests (15x cheaper)
    )

    assert result["success"]
    assert "/home/nic/src/writing" in result["result"]
```

**How it works**:
1. Runs `claude -p <prompt> --output-format json`
2. Captures structured JSON output
3. Returns parsed results with session info

**Parameters**:
- `prompt`: str - The prompt to send to Claude
- `model`: str - Model to use ("haiku", "sonnet", "opus")
- `timeout`: int - Timeout in seconds (default 120)
- `permission_mode`: str - Permission handling ("acceptEdits", "ask", "deny")

**Returns** dict with:
- `success`: bool - Whether session succeeded
- `result`: str - Claude's response text
- `output`: dict - Full JSON output from Claude
- `error`: str - Error messages if any
- `permission_denials`: list - Blocked permissions
- `duration_ms`: int - Session duration

**Example session log**:
```json
{
  "success": true,
  "result": "/home/nic/src/writing",
  "output": {
    "is_error": false,
    "result": "/home/nic/src/writing",
    "duration_ms": 1234,
    "permission_denials": []
  },
  "error": "",
  "permission_denials": [],
  "duration_ms": 1234
}
```

### Testing Guidelines

**From tests/integration/CLAUDE.md**:

**Critical rules**:
- ✅ **ALWAYS use `model="haiku"`** for tests (15x cheaper than Sonnet)
- ✅ Test integration points, NOT business logic
- ✅ Keep tests under 30s timeout
- ✅ Use `claude_headless()` fixture
- ✅ Maximum ~5-7 tests per integration boundary

**What to test**:
- Hook output → Claude Code → tool execution
- Agent type detection → hook receives correct metadata
- Permission decision → Claude response behavior

**What NOT to test**:
- Business logic (unit tests cover this)
- LLM intelligence (test machinery, not reasoning)
- Multiple scenarios of same pattern

### Running Headless Tests

**Run all integration tests**:
```bash
cd ${AOPS}
uv run pytest tests/integration/
```

**Run specific headless test**:
```bash
uv run pytest tests/integration/test_claude_headless.py
uv run pytest tests/integration/test_headless_simple.py
```

**Run with markers**:
```bash
# Only slow (integration) tests
uv run pytest -m slow

# Skip slow tests
uv run pytest -m "not slow"
```

**Note**: Integration tests are marked with:
- `@pytest.mark.slow` - Takes >5s
- `@pytest.mark.timeout(120)` - 2min timeout

### Scripts (Priority: Medium)

**Location**: `${AOPS}/scripts/`

**Current scripts**:
- setup.sh - Installation
- task_*.py - Task management utilities

### Skills (Priority: Low)

Skills are tested through actual use in Claude Code sessions.

## Manual Testing Procedures

### Testing Hooks

**Method**: Trigger lifecycle events and check debug logs

**SessionStart hook (load_instructions.py)**:

1. Start new Claude Code session
2. Check stderr output: Should see "✓ Loaded _CORE.md" or "ℹ No _CORE.md found"
3. Verify environment variables set: `echo $AOPS`
4. Check debug log: `cat ~/.claude/debug/SessionStart_*.json`

**PreToolUse hook (validate_tool.py)**:

1. Execute any tool (e.g., Bash, Read, Write)
2. Check stderr: Should be silent if allowed, or show warning/block message
3. Check debug log: `cat ~/.claude/debug/PreToolUse_*.json`
4. Test blocked action: Try to write to restricted path
5. Verify block message appears

**PostToolUse hook (autocommit_tasks.py)**:

1. Modify a task file via Basic Memory MCP
2. Hook should auto-commit changes
3. Check git log for automated commit
4. Check debug log: `cat ~/.claude/debug/PostToolUse_*.json`

**Stop hook (validate_stop.py)**:

1. End a Claude Code session
2. Hook should check for uncommitted changes
3. Check debug log: `cat ~/.claude/debug/Stop_*.json`

### Testing Scripts

**setup.sh**:

```bash
cd ${AOPS}
./scripts/setup.sh

# Verify symlinks created
ls -la ~/.claude/hooks
ls -la ~/.claude/skills
ls -la ~/.claude/settings.json
```

**task_*.py scripts**:

```bash
# Test task_view.py
uv run --directory ${AOPS} python ${AOPS}/scripts/task_view.py

# Test task_add.py (requires Basic Memory MCP)
uv run --directory ${AOPS} python ${AOPS}/scripts/task_add.py "Test task"

# Test task_index.py
uv run --directory ${AOPS} python ${AOPS}/scripts/task_index.py
```

## Debug Logging

**Location**: `~/.claude/debug/`

**Hook debug files**: `{HookName}_{timestamp}.json`

**Format**:
```json
{
  "hook_name": "SessionStart",
  "timestamp": "2024-11-08T12:00:00",
  "input": { ... },
  "output": { ... }
}
```

**Utility**: `hooks/hook_debug.py` provides `safe_log_to_debug_file()`

**When to check**:
- Hook not firing as expected
- Debugging hook logic
- Verifying hook input/output

## Actual Test Structure

**Current structure**:

```
${AOPS}/tests/
├── conftest.py              # pytest configuration
├── hooks.py                 # Hook testing utilities
├── __init__.py
├── integration/             # Integration test fixtures
├── prompts/                 # Test prompts
├── results/                 # Test results
├── test_hook_start.py
├── test_hook_pretool.py
├── test_hook_stop.py
├── test_stop_hook_resilience.py
├── test_validate_tool.py
├── test_session_logging_hook.py
├── test_load_instructions_integration.py
├── test_context_loading_integration.py
├── test_chunks_loading.py
├── test_deployment_architecture.py
├── test_instruction_tree.py
├── test_unified_schema.py
├── test_task_scripts.py
├── test_task_scripts_path_resolution.py
├── test_task_add_priority.py
├── test_task_add_scribe_priority.py
├── test_code_review.py
├── test_command_file_integrity.py
└── test_validation_rules.py
```

**Test approach**:

1. **Unit tests** - Test hook logic in isolation
   - Mock stdin/stdout
   - Mock file system
   - Test exit codes and output format

2. **Integration tests** - Test hooks with actual Claude Code
   - Tests with real file system
   - Trigger lifecycle events
   - Verify debug logs

3. **Fixture-based tests** - Test with known input/output
   - Load test cases from fixtures/
   - Verify deterministic behavior
   - Use tests/integration/, tests/prompts/, tests/results/

## Test Execution

**Run all tests**:
```bash
cd ${AOPS}
uv run pytest tests/
```

**Run specific test file**:
```bash
uv run pytest tests/test_hook_start.py
uv run pytest tests/test_validate_tool.py
```

**Run tests matching pattern**:
```bash
uv run pytest tests/ -k "hook"
uv run pytest tests/ -k "task"
```

**Run with verbose output**:
```bash
uv run pytest tests/ -v
```

**Run with coverage**:
```bash
uv run pytest --cov=hooks --cov=scripts tests/
```

**Run in CI/CD** (not yet implemented):
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: uv sync
      - run: uv run pytest tests/
```

## Current Testing Reality

**How we currently verify hooks work**:

1. **Production testing** - Hooks run in actual Claude Code sessions
2. **Debug logs** - Check `~/.claude/debug/` when issues occur
3. **Manual triggers** - Execute tools to trigger PreToolUse hook
4. **Session observation** - Watch for expected hook behavior

**When to suspect hook failure**:

- Expected message doesn't appear in stderr
- Tool blocks/allows when it shouldn't
- Debug log shows error or unexpected output
- Environment variables not resolving (`$AOPS` empty)

**Debugging workflow**:

1. Check environment: `echo $AOPS $ACA`
2. Check symlinks: `ls -la ~/.claude/hooks`
3. Check hook file exists: `test -f $AOPS/hooks/validate_tool.py`
4. Check debug logs: `ls -lt ~/.claude/debug/ | head`
5. Check settings.json: `cat ~/.claude/settings.json | grep -A 10 hooks`
6. Run hook manually:
   ```bash
   echo '{}' | uv run --directory $AOPS python $AOPS/hooks/load_instructions.py
   ```

## Next Steps

**To improve test coverage**:

1. ✅ tests/ directory structure exists
2. ✅ pytest infrastructure configured
3. ✅ Unit tests for critical hooks exist
4. ✅ conftest.py with shared fixtures exists
5. ✅ Test execution documented
6. ❌ CI/CD integration (GitHub Actions) - not yet implemented
7. ❌ Coverage reporting - not yet configured
8. ❌ Test documentation - individual tests not fully documented

**Priorities**:
- High: Add CI/CD integration (GitHub Actions)
- High: Configure coverage reporting
- Medium: Document individual test purposes
- Medium: Add tests for newly added scripts
- Low: Expand integration test coverage

## References

- Hook debug utility: `hooks/hook_debug.py`
- Hook configuration: `config/settings.json`
- Hook execution logs: `~/.claude/debug/`
- Repository structure: `paths.toml`
