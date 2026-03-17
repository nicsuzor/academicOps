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

## Demo Test Coverage Summary

| Test File                    | What It Proves                                                                                                                                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [[test_reflexive_loop.py]]   | Custodiet fires during normal agent operation. Runs 6 bash commands → custodiet threshold reached → audit file created. Validates the self-reflexive monitoring loop works.                                                                                  |
| [[test_skill_discovery.py]]  | Skills are correctly discovered and loaded. Invokes framework skill → agent demonstrates knowledge of workflow files (e.g., "design", "debug") that can only come from loaded skill content.                                                                 |
| test_hook_sequence.py        | Hooks fire at correct lifecycle events: SessionStart (session completes), UserPromptSubmit (hydrator temp file created), PostToolUse (custodiet audit file created).                                                                                         |
| test_memory_persistence.py   | Remember skill correctly persists knowledge. Validates three-stage flow: Skill tool invoked → mcp__memory__store_memory called → Write tool creates markdown file.                                                                                           |
| test_multi_agent.py          | Subagents spawn correctly and return results. Task tool invoked with subagent_type='critic' → critic executes → main agent processes and reports subagent output.                                                                                            |
| test_compliance_detection.py | Custodiet produces substantive, well-formed audit output. Uses semantic validation (not keyword matching): checks Session Context has ≥3 content lines, AXIOMS has ≥10 numbered items, HEURISTICS has ≥10 H-items, no repeated headers, content ≥1000 chars. |
| test_core_pipeline.py        | Full hydration pipeline works end-to-end: Stage 1 prompt-hydrator invoked → Stage 2 TodoWrite plan created → Stage 3 python-dev skill invoked → Stage 4 code written via Write tool.                                                                         |
| test_quality_gates.py        | Critic agent catches issues and provides feedback. Given a deliberately flawed plan ("run migration on production before testing"), verifies critic identifies concerns (risk, rollback, staging, test).                                                     |

### Framework Feature Coverage Estimate

| Category                       | Coverage | Notes                                                                                                                   |
| ------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| Hooks Lifecycle                | ~85%     | SessionStart, UserPromptSubmit, PostToolUse all verified; Stop/PreCompact not tested                                    |
| Custodiet                      | ~50%     | Threshold firing + audit structure verified; violation detection (drift, missing skills, axiom breaches) not yet tested |
| Skill System                   | ~60%     | Discovery, loading, invocation verified; file references not deeply tested                                              |
| Multi-Agent                    | ~50%     | Critic subagent verified; other subagents (planner, explore, etc.) not covered                                          |
| Memory                         | ~70%     | Store + markdown persistence verified; retrieval/search not tested                                                      |
| Core Pipeline                  | ~80%     | Hydration → workflow → TodoWrite → execution verified                                                                   |
| Quality Gates                  | ~40%     | Critic review verified; other gates (qa, qa-eval) not covered                                                           |
| Principles (Axioms/Heuristics) | ~30%     | Loading verified; violation detection not tested                                                                        |

Overall Estimate: ~55-60% of documented framework capabilities are exercised by these 8 demo tests. Key gaps:

- Violation detection semantics (scope drift, axiom breaches)
- Other subagent types (planner, explore, custodiet variants)
- Stop/PreCompact hooks
- Memory retrieval workflows
- QA/qa-eval quality gates
