---
title: E2E Test Harness Reference
type: reference
permalink: ref-e2e-test-harness
description: Guide to the framework's end-to-end testing infrastructure for validating agent behavior
---

# E2E Test Harness Reference

Guide to the framework's end-to-end testing infrastructure for validating agent behavior.

## Current State

- **227 total tests**: 170 unit, 31 fast integration, 26 slow E2E
- **100% passing** as of 2025-11-22
- Harness fully functional for behavioral validation

## What E2E Tests Can Do

### 1. Headless Claude Execution (`claude_headless` fixture)

Location: `tests/integration/conftest.py`

```python
result = claude_headless(
    prompt="What is 2+2?",
    model="haiku",              # Optional, defaults to haiku
    timeout_seconds=120,        # Optional
    permission_mode="plan",     # Optional
    cwd=some_path,              # Optional
)
# Returns: {success, output, result, error}
```

### 2. Session Start Validation
- Verify content loads into agent context (not via Read tool)
- Test from multiple directories
- Verify agent knows user info from ACCOMMODATIONS.md

### 3. Behavioral Tests
- Agent has info without using Read tool
- Skill invocation produces expected output
- Scripts discoverable via symlinks

### 4. Bmem Skill Tests
- Creates valid Obsidian files
- Writes to $ACA_DATA
- Handles YAML escaping

## What E2E Tests Cannot Do (Gaps)

1. **Hook behavior** - No tests for PreToolUse/PostToolUse execution
2. **MCP server integration** - No tests for bmem MCP tool calls
3. **Multi-turn conversations** - All tests are single-prompt
4. **Error recovery** - No tests for agent behavior when tools fail
5. **Prompt Intent Router** - New spec, no tests yet

## Infrastructure Location

```
tests/
├── conftest.py                    # Unit fixtures
├── paths.py                       # Path utilities
└── integration/
    ├── conftest.py                # E2E fixtures (claude_headless)
    ├── test_headless_fixture.py   # Fixture validation (7 tests)
    ├── test_session_start_content.py
    ├── test_file_loading_e2e.py
    ├── test_bmem_*.py             # Bmem tests
    ├── test_skill_script_discovery.py
    ├── test_subagent_skill_invocation.py
    └── test_task_viz.py
```

## Running Tests

```bash
# Fast unit tests (default)
uv run pytest tests/

# Fast integration tests
uv run pytest tests/ -m "integration and not slow"

# All E2E tests (slow, executes Claude)
uv run pytest tests/integration/ -m "slow"

# Everything
uv run pytest tests/ -m "integration"
```

## Writing New E2E Tests

```python
@pytest.mark.slow
@pytest.mark.integration
def test_agent_behavior(claude_headless) -> None:
    """Test agent knows expected information."""
    result = claude_headless(
        prompt="What principle says we should fail fast?",
        timeout_seconds=60,
    )

    assert result["success"], f"Execution failed: {result.get('error')}"
    # Check response contains expected content
```

## Related

- `tests/README.md` - Full test documentation
- [[hooks_guide]] - Hook system reference
- [[testing-with-live-data]] - Testing methodology
- [[script-design-guide]] - Script and utility design
