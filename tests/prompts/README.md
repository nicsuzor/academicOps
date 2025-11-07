# Agent Context Awareness Testing

**Purpose**: Systematic evaluation of how well agents understand their context when starting in the parent repo.

**Related Issues**:

- #64 - Agent project context system
- #66 - Documentation consolidation
- #67 - Evidence-based documentation (Plan B)

## Quick Start

### 1. Run Tests

From parent repo (`/home/nic/src/writing/`):

```bash
# Run single test with Claude Code
claude -p "Where should I document project-specific auto-extraction patterns?" > bot/tests/results/test1_claude_$(date +%Y%m%d).txt

# Run single test with Gemini CLI
gemini -p "Where should I document project-specific auto-extraction patterns?" > bot/tests/results/test1_gemini_$(date +%Y%m%d).txt
```

### 2. Evaluate Results

In a new session:

```bash
# Start evaluation session
claude -p "Evaluate test results in bot/tests/results/test1_*.txt against CONTEXT-AWARENESS-TESTS.md"
```

The evaluator agent will:

1. Read the test specification from `CONTEXT-AWARENESS-TESTS.md`
2. Read the test output files
3. Compare against success criteria
4. Generate result file in `bot/tests/results/context_awareness_YYYY-MM-DD.md`

### 3. Review & Act

- Review result file
- Address any FAIL results by updating docs/INSTRUCTIONS.md or agent instructions
- Track improvements via GitHub issues

## File Organization

```
bot/tests/
├── prompts/
│   ├── README.md                          # This file
│   ├── CONTEXT-AWARENESS-TESTS.md         # Test specifications
│   └── [future test suites]
└── results/
    ├── test*_claude_YYYYMMDD.txt         # Raw test outputs
    ├── test*_gemini_YYYYMMDD.txt         # Raw test outputs
    └── context_awareness_YYYY-MM-DD.md   # Evaluation reports
```

## Test Philosophy

### What We're Testing

**NOT** testing code execution or task completion. We're testing:

1. **Context Loading**: Does agent read docs/INSTRUCTIONS.md?
2. **Policy Awareness**: Does agent know critical rules?
3. **Architecture Understanding**: Does agent know where things go?
4. **Boundary Awareness**: Does agent understand public vs private?

### Why Headless Mode (`-p`)

Using `-p` flag ensures:

- No interactive clarifications
- Agent must answer from loaded context only
- Simulates real autonomous operation
- Comparable results across runs

### Self-Contained Evaluation

The test specification (`CONTEXT-AWARENESS-TESTS.md`) contains:

- Complete success/failure criteria
- Rationale for each test
- Evaluation rubric
- Result file template

This allows **any** agent (or human) to evaluate results without additional context.

## Test Maintenance

### When to Update Tests

1. **After docs/INSTRUCTIONS.md changes**: Add test for new critical policies
2. **After agent failures**: Create test that would have caught the failure
3. **After trainer interventions**: Add test to prevent recurrence
4. **Quarterly review**: Verify tests still match current documentation

### How to Add New Tests

1. Open `CONTEXT-AWARENESS-TESTS.md`
2. Add new test following existing format:
   ```markdown
   ### Test N: [Name] ([PRIORITY])

   **Question**: "[Single, clear question]"

   **Success Criteria**:

   - ✅ PASS: [specific observable behavior]
   - ❌ FAIL: [specific anti-pattern]

   **Rationale**: [Why this test matters]
   ```
3. Update "Evaluation Rubric" score ranges if adding/removing tests
4. Document in test version history

### Tracking Changes

Use `bot/docs/CHANGES.md` (when created per #67 Plan A) to track:

- Test additions/modifications
- Hypothesis about what behavior will change
- Results after implementation

Example:

```markdown
## 2025-10-05: Initial Context Awareness Tests (#67)

**Hypothesis**: Agents don't consistently load docs/INSTRUCTIONS.md on startup.

**Test**: Created 8-question context awareness test suite

**Expected**: ≤50% PASS rate before fixes, ≥90% PASS after documentation improvements

**Validation Date**: 2025-11-05
```

## Integration with Plan B (Future)

These manual tests form the foundation for automated testing (Issue #67 Plan B):

### Current (Manual)

1. Human runs `claude -p "question" > output.txt`
2. Human/Agent evaluates against criteria
3. Human logs results

### Future (Automated via Plan B)

1. Script runs `claude -p "question" > output.txt`
2. Assertion framework evaluates against criteria
3. CI/CD logs results and fails on regression

### Migration Path

When implementing Plan B:

1. Convert test questions → Python test functions
2. Convert success criteria → `assert` statements
3. Convert evaluation rubric → test suite scoring
4. Keep `CONTEXT-AWARENESS-TESTS.md` as canonical specification
5. Auto-generate test code from specification

Example:

```python
# bot/tests/agent_behavior/test_context_awareness.py

def test_documentation_location():
    """Test 1 from CONTEXT-AWARENESS-TESTS.md"""
    response = ask_agent("Where should I document project-specific auto-extraction patterns?")

    # Success criteria from spec
    assert "docs/INSTRUCTIONS.md" in response or "parent repo docs" in response
    assert "bot/docs/" not in response  # Failure criteria
```

## Best Practices

### Running Tests

1. **Consistent environment**: Always run from `/home/nic/src/writing/`
2. **Fresh sessions**: Use `-p` flag for stateless tests
3. **Dated outputs**: Include date in output filenames for tracking over time
4. **Batch runs**: Can run all 8 tests in sequence, but use separate output files

### Evaluation

1. **Objective criteria**: Follow success/fail criteria exactly as written
2. **Document edge cases**: If result is ambiguous, note in evaluation
3. **Context for failures**: Include relevant context (was docs changed recently?)
4. **Action items**: Every FAIL should generate a GitHub issue or action item

### Results Management

1. **Keep raw outputs**: Never delete test output files (they're evidence)
2. **Timestamped evaluations**: One result file per test run with date
3. **Trend analysis**: Compare results over time (are we improving?)
4. **Link to changes**: Reference specific docs updates or agent modifications

## Troubleshooting

### "Agent didn't load context"

**Symptoms**: Agent asks for clarification or gives generic answer

**Check**:

1. Is CLAUDE.md in repo root pointing to correct instructions?
2. Does docs/INSTRUCTIONS.md exist and have expected content?
3. Try running `claude -p "What documentation should you read first?"` to debug

### "Results don't match expectations"

**Could mean**:

1. Documentation unclear (fix docs)
2. Test criteria too strict (update test)
3. Agent genuinely failing (escalate to trainer)

**Action**: Review with fresh eyes, consult test rationale

### "Getting different results on reruns"

**Expected**: Some variation in phrasing is normal

**Concerning**: If PASS/FAIL status changes between runs

**Action**:

1. Check if docs changed between runs
2. Note non-determinism in evaluation
3. Consider making success criteria more specific

## Ownership

**Maintained by**: Agent Trainer (bot/agents/trainer.md)

**Review frequency**:

- After each major docs/INSTRUCTIONS.md change
- Monthly during trainer reflection sessions
- Quarterly comprehensive review

**Questions/Issues**: Create issue in nicsuzor/academicOps with `prompts` label
