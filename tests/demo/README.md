# Demo Tests

Demo tests provide **transparent evidence** for human validation of agent capabilities.

## Requirements

All demo tests MUST satisfy:

1. **Location**: `tests/demo/` directory (enforced by pre-commit hook)
2. **Marker**: `@pytest.mark.demo` decorator on test class/function
3. **Fixture**: Use `claude_headless_tracked` for session tracking
4. **Failure**: Call `pytest.fail()` when criteria not met - never just print "FAIL"

## Running Demo Tests

```bash
# Run all demo tests with visible output
uv run pytest tests/demo/ -v -s -n 0 -m demo

# Run specific demo test
uv run pytest tests/demo/test_reflexive_loop.py -v -s -n 0 -m demo
```

The `-n 0` flag disables parallelization so output is visible in sequence.

## H37 Enforcement

Per [[HEURISTICS.md]] H37: Demo tests must use LLM semantic evaluation, never keyword matching.

**The fixture enforces this**:

- `claude_headless_tracked` wraps sessions with `fail_on_error=True`
- Session failures automatically fail the test
- No need to manually check `result['success']` - fixture handles it

**The test logic must enforce this**:

- Evaluate criteria semantically (not substring matching)
- Call `pytest.fail()` when criteria aren't met
- Print full evidence for human review (H37a)

## Volkswagen Anti-Patterns

A "Volkswagen test" passes when functionality fails - named after the emissions scandal.

### Anti-Pattern 1: Print-Only Failure

```python
# WRONG - prints failure but test passes
if not criteria_met:
    print("FAIL: criteria not met")

# CORRECT - actually fails the test
if not criteria_met:
    pytest.fail("Criteria not met: ...")
```

### Anti-Pattern 2: Keyword Matching

```python
# WRONG - keyword matching can false-positive
assert "success" in response.lower()

# CORRECT - semantic evaluation
# Let the test logic evaluate whether the response MEANS success
```

### Anti-Pattern 3: Truncated Evidence or Hidden Internals

```python
# WRONG - truncates evidence humans need
print(response[:100])

# WRONG - shows final output but hides internal working
print(response)

# CORRECT - expose the feature's internal machinery (H37a)
print("\n=== FEATURE INTERNALS ===")
print(f"Step 1 - Loaded context: {context}")
print(f"Step 2 - Applied transform: {intermediate_state}")
print(f"Step 3 - Generated response: {response}")
print(f"Internal state after processing: {processor.state}")
```

**Why this matters**: Demo tests must make visible the ENTIRE INTERNAL WORKING of the feature - how it processes data step-by-step, what decisions it makes, what internal state changes occur. Printing just the final response (even untruncated) doesn't demonstrate how the feature works.

### Anti-Pattern 4: Ignoring Session Failure

```python
# WRONG - continues despite session failure
result = claude_headless(prompt)
# ... proceeds to check other things ...

# CORRECT - fixture handles this automatically
# claude_headless_tracked fails test on session error
```

## Template

```python
@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.integration
class TestMyDemo:
    """Demo test for [capability]."""

    def test_demo_capability(self, claude_headless_tracked) -> None:
        """Demo: [what this proves]."""

        prompt = "..."
        result, session_id, tool_calls = claude_headless_tracked(
            prompt, timeout_seconds=300, model="haiku"
        )

        # Session failures auto-fail via fixture
        # Now evaluate criteria

        criteria = [
            ("Description", condition),
            # ...
        ]

        all_passed = all(passed for _, passed in criteria)

        # Print evidence for human review
        print("\n--- EVALUATION ---")
        for name, passed in criteria:
            print(f"[{'PASS' if passed else 'FAIL'}] {name}")

        # MUST fail test if criteria not met
        if not all_passed:
            failed = [name for name, passed in criteria if not passed]
            pytest.fail(f"Criteria not met: {', '.join(failed)}")
```

## Related

- [[HEURISTICS.md]] H37: LLM Semantic Evaluation
- Epic ns-5n7: Test Infrastructure & H37 Enforcement
- Epic ns-6fq: Self-Reflexive Loop Architecture
