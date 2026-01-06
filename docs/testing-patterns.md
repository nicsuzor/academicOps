---
title: Test Design Patterns
type: docs
category: docs
description: Patterns for testing LLM behavior without keyword matching
permalink: testing-patterns
tags: [testing, H37, patterns]
---

# Test Design Patterns

How to write tests that verify actual behavior, not surface patterns. Per H37: never use keyword/substring matching for verification.

## The Problem: Volkswagen Tests

A "Volkswagen test" passes on wrong behavior by checking surface patterns instead of actual outcomes:

```python
# WRONG: Keyword matching - passes if ANY of these strings appear
assert any(ind in output for ind in ["success", "completed", "done"])

# WRONG: Weak length check - passes on ANY non-empty output
assert len(output) > 0
```

These tests provide false confidence. They can pass when the system is broken.

## Pattern 1: Verify Tool Invocations via Session Tracking

When testing that an agent invokes specific tools, use `claude_headless_tracked` to parse actual tool calls from the session JSONL:

```python
@pytest.mark.integration
def test_hydrator_task_is_spawned(claude_headless_tracked):
    """Verify prompt-hydrator Task is actually spawned."""
    result, session_id, tool_calls = claude_headless_tracked(
        "Help me refactor the policy_enforcer hook",
        timeout_seconds=180
    )

    assert result["success"]

    # Find ACTUAL tool invocations - not keywords in output
    hydrator_calls = [
        call for call in tool_calls
        if call["name"] == "Task"
        and call.get("input", {}).get("subagent_type") == "prompt-hydrator"
    ]

    assert len(hydrator_calls) > 0, (
        f"prompt-hydrator Task should be spawned. "
        f"Found {len(tool_calls)} tool calls: {[c['name'] for c in tool_calls]}"
    )
```

**Why this works**: We're checking the session JSONL for actual `tool_use` blocks, not searching output text for keywords.

## Pattern 2: Demo Tests for Human Validation

For behavior that requires semantic judgment, create demo tests that show full output:

```python
@pytest.mark.demo
class TestHydratorDemo:
    """Run with: pytest -k demo -v -s -n 0"""

    def test_demo_full_output(self, claude_headless):
        result = claude_headless("Real framework prompt here")

        # Print FULL output - no truncation (H37a)
        print("\n" + "=" * 80)
        print("FULL OUTPUT FOR HUMAN VALIDATION")
        print("=" * 80)
        print(result.get("output", ""))  # No [:3000] truncation!
        print("=" * 80)

        # Structural checks only - semantic validation is human's job
        assert result["success"]
```

**Why this works**: Human reviews full output and makes semantic judgment. The test creates an observable artifact.

## Pattern 3: Real Framework Prompts (H37b)

Use actual prompts from real framework work, not contrived examples:

```python
# WRONG: Contrived example proves nothing about real behavior
prompt = "What is the meaning of life?"

# RIGHT: Real framework task
prompt = (
    "Help me refactor the policy_enforcer hook to add support for "
    "blocking dangerous npm commands"
)
```

**Why this works**: Testing fake scenarios doesn't verify real behavior. Use prompts from actual framework workflows.

## Pattern 4: Structural Verification

When you need automated checks, verify structure not content:

```python
def test_hydrator_temp_file_structure(self):
    """Verify temp file has required sections."""
    content = temp_file.read_text()

    # Check structure exists - human validates content via demo test
    assert "## User Prompt" in content, "Missing User Prompt section"
    assert "## Your Task" in content, "Missing Your Task section"
    assert "## Return Format" in content, "Missing Return Format section"
```

**Why this works**: We verify the file has the right structure. Content correctness is validated by humans via demo tests.

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Better Approach |
|--------------|----------------|-----------------|
| `any(x in text for x in list)` | Matches surface patterns | Parse structured data (tool_calls) |
| `assert len(output) > 0` | Passes on any output | Verify specific structure/invocations |
| `print(x[:3000])` | Truncates evidence | Show full output in demo tests |
| `"What is 2+2?"` prompts | Proves nothing about framework | Use real framework prompts |

## Fixture Reference

### `claude_headless`

Basic headless execution, returns parsed result:

```python
result = claude_headless("prompt", model="haiku", timeout_seconds=120)
# result = {"success": bool, "output": str, "result": dict}
```

### `claude_headless_tracked`

Headless execution with session tracking:

```python
result, session_id, tool_calls = claude_headless_tracked("prompt")
# tool_calls = [{"name": "Task", "input": {...}}, ...]
```

### `skill_was_invoked`

Check if a skill was invoked:

```python
assert skill_was_invoked(tool_calls, "framework")
```

## When to Use Each Pattern

| Testing For | Pattern |
|-------------|---------|
| Tool was invoked | Session tracking (Pattern 1) |
| Output is semantically correct | Demo test (Pattern 2) |
| File has correct structure | Structural verification (Pattern 4) |
| End-to-end workflow | Real prompts (Pattern 3) + Demo test |
