--- 
name: learn
category: instruction
description: Make minimal, graduated framework tweaks with experiment tracking
allowed-tools: Task
permalink: commands/learn
---

# /learn - Graduated Framework Improvement

## Core Principle: Generalisable, not specific

**Don't hyperfocus**:

❌ **WRONG**: User says 'color' should be spelt 'colour' → Create 'AXIOM: HOW TO SPELL COLOR'
✅ **RIGHT**: User says 'color' should be spelt 'colour' → Consider root cause, track in task about 'localization', consider escalation only if necessary, note that large issues likely need SPEC updates.

**Don't overreact**:
❌ **WRONG**: User mentions spelling → Create SPELLING AXIOM + spell-check hook + prominent warning
✅ **RIGHT**: User mentions spelling → Add brief note in relevant location, track in task, escalate only if necessary

**Start small. If we need a heavier intervention, update the Specs.**

## Workflow

### 0. Load Governance Context (MANDATORY)

**Before any framework change, read these files:**

```
Read aops-core/AXIOMS.md
Read aops-core/HEURISTICS.md
Read aops-core/framework/enforcement-map.md
```

You CANNOT proceed without loading this context. Note which principles are relevant.

### 0.5. Create/Update Task FIRST

**Before any fix, document in a task.** This is non-negotiable.

```
mcp__plugin_aops-core_task_manager__create_task(
  title="[Learn] Root cause summary",
  type="task",
  project="aops",
  priority=2,
  body="1. Observation: ...\n2. Root cause category: ...\n3. Proposed fix: ...\n4. Success metric: ..."
)
```

OR if related task exists:
```
mcp__plugin_aops-core_task_manager__update_task(
  id="<id>",
  body="<existing body>\n\nAdding learning observation: ..."
)
```

The task MUST contain:
1. **Observation**: What went wrong (specific, not vague)
2. **Root cause category**: Clarity/Context/Blocking/Detection/Gap
3. **Proposed fix**: What you will change (file path, enforcement level)
4. **Success metric**: How we know the fix worked (measurable)

**You do NOT need user permission** to make the fix if it's documented in the task. The task IS the approval - it creates accountability and traceability.

### 1. Identify Root Cause (Not Proximate Cause)

**We don't control agents** - they're probabilistic. Find the **framework component failure**, not the agent mistake.

See [[specs/enforcement.md]] "Component Responsibilities" for the full model.

| Root Cause Category | Definition                     | Fix Location                  |
| ------------------- | ------------------------------ | ----------------------------- |
| Clarity Failure     | Instruction ambiguous/weak     | framework/AXIOMS, skill text, guardrail |
| Context Failure     | Didn't provide relevant info   | Intent router, hydration      |
| Blocking Failure    | Should have blocked but didn't | PreToolUse hook, deny rule    |
| Detection Failure   | Should have caught but didn't  | PostToolUse hook              |
| Gap                 | No component exists for this   | Create new enforcement        |

**Wrong**: "Agent ignored instruction" (proximate cause - we can't fix the agent)
**Right**: "Guardrail instruction too generic for this task type" (root cause - we can fix the guardrail)

### Subagent Failure Root Causes

When a subagent (custodiet, critic, qa, etc.) makes an incorrect decision:

| Symptom | Wrong Fix | Right Fix |
|---------|-----------|-----------|
| Subagent blocks legitimate work | Add exception to subagent instructions | Enrich context the subagent receives |
| Subagent misclassifies intent | Narrow the classification rules | Provide more user intent context |
| Subagent false positive | "Don't do X in case Y" rule | Give subagent information to distinguish X from Y |

**Key insight**: Subagents are haiku-class models with limited context windows. When they make wrong decisions, the root cause is almost always **insufficient context**, not **wrong instructions**. Adding rules/exceptions just papers over the real problem.

**Fix location**: The hook or template that builds the subagent's context (e.g., `custodiet_gate.py:_build_session_context()`, `prompt-hydrator-context.md`).

**CRITICAL**: "No framework change needed" is NEVER a valid conclusion. If an agent made an error, something in the framework failed to provide the right instruction at the right time. Find that component.

**When you're tempted to say "I just failed to follow instructions"**: That's the proximate cause. Ask: WHY did you fail? What instruction was missing, unclear, or not salient enough? That's the root cause. Fix THAT.

### 2. Check for Prior Occurrences

Search tasks for related issues before creating a new one:

```
mcp__plugin_aops-core_task_manager__search_tasks(query="[keywords]")
```

If a related task exists, update it with your observation. Pattern recognition across multiple occurrences informs escalation decisions.

### 3. Choose Intervention Level (Start at Bottom, Escalate with Evidence)

See @docs/ENFORCEMENT.md for mechanism details.

- **Enforcement Ladder** (always start at lowest effective level).
- **Match root cause to intervention**
- **Escalation rule**: Only move up when you have evidence that lower levels failed.

**File placement** (for Prompt-level fixes):

| Fix Type | File | When to Use |
|----------|------|-------------|
| Hard rule, never violate | AXIOMS.md | Principles that apply universally |
| Soft guidance, exceptions exist | HEURISTICS.md | Rules of thumb, "prefer X over Y" |
| Enforcement wiring | framework/enforcement-map.md | Document how rule is enforced |
| Session context | CORE.md | Paths, environment, "what exists" |

### 4. Emit Structured Justification (MANDATORY)

Before editing ANY framework file, output this exact format:

```yaml
## Rule Change Justification

**Scope**: [AXIOMS.md | HEURISTICS.md | framework/enforcement-map.md | hooks/*.py | settings.json]

**Rules Loaded**:
- AXIOMS.md: [P#X, P#Y - or "not relevant"]
- HEURISTICS.md: [H#X, H#Y - or "not relevant"]
- framework/enforcement-map.md: [enforcement entry name - or "not relevant"]

**Prior Art**:
- Search query: "[keywords used in task search]"
- Related tasks: [task IDs found, or "none"]
- Pattern: [existing pattern | novel pattern]

**Intervention**:
- Type: [corollary to P#X | new axiom | new heuristic | enforcement hook | deny rule]
- Level: [1a | 1b | 1c | 1d | 2 | 3a | 3b | 4 | 5 | 6 | 7]
- Change: [exact content, max 3 sentences]

**Generality Check** (STOP if answer is "no"):
- Does this fix address the GENERAL pattern, not just the specific instance?
- If fix contains task-specific keywords (e.g., "test", "commit", "email"), is that specificity actually necessary?

**Minimality**:
- Why not lower level: [explanation]
- Why not narrower scope: [explanation]

**Spec Location**: [specs/enforcement.md | task body | N/A]

**Escalation**: [auto | critic | custodiet | human]
```

**Escalation routing**:
- `auto`: Corollaries only - proceed immediately
- `critic`: New heuristics, Level 4-5 hooks - get critic approval
- `human`: New axioms, deny rules, settings.json - use AskUserQuestion

See [[framework-change]] workflow for full escalation matrix.

### 5. Make the Fix (as an Experiment)

**Fixes are experiments, not permanent solutions.** The task tracks the hypothesis.

Keep changes brief (1-3 sentences for soft interventions). If you need a bigger change, **ABORT** and update/create a Spec instead.

**NEVER create new files.** Edit existing files inline. New files = over-engineering. A 2-line inline note always beats a new context file.

**After making the fix**, update the task with:
- Commit hash or file changed
- Exact change made
- How to verify (what behavior to observe)

```
mcp__plugin_aops-core_task_manager__update_task(
  id="<id>",
  body="<existing>\n\nFix applied: [commit hash]. Changed [file]. Verify by [observable behavior]."
)
```

### 6. Generalize the Pattern (REQUIRED)

After fixing the immediate issue, ask: **What general class of error is this?**

1. **Name the pattern** - e.g., "user data in framework files", "scope creep", "missing validation"
2. **Check existing rules** - Does an axiom/heuristic already cover this? (Search AXIOMS.md, HEURISTICS.md, framework/enforcement-map.md)
3. **If rule exists but wasn't followed** - Strengthen enforcement (add to task notes)
4. **If novel pattern** - Log it in the task body for future tracking

The immediate fix handles THIS instance. The pattern recognition prevents FUTURE instances.

### 7. Create Regression Test (WHEN TESTABLE)

Tests verify the fix works and prevent regressions. **But only when the fix is testable.**

**When to create a test**:
- Fix modifies code (hooks, scripts, libraries) → YES, create test
- Fix modifies hook behavior with deterministic input/output → YES, create test
- Fix modifies prompts/instructions for LLM behavior → NO test possible, skip with justification

**For testable fixes**:
1. **Capture the failure case as a fixture** - Extract the exact input that caused the failure
2. **Write a failing test first** - The test should FAIL with the old behavior
3. **Verify test passes after fix** - Run the test to confirm the intervention works
4. **Use slow tests for live interfaces** - Mark with `@pytest.mark.slow` if testing against live Claude/APIs

**For prompt/instruction fixes (not testable)**:
- Document the expected behavior change in the task
- The fix itself (clearer instructions) IS the intervention
- Do NOT create placeholder tests that pass unconditionally - that's worse than no test

**Test location**: `$AOPS/tests/` - choose appropriate subdirectory:
- `tests/hooks/` - Hook behavior tests
- `tests/integration/` - Cross-component tests
- `tests/` - General framework tests

**Example**: If custodiet was overly restrictive, find the exact input JSON it received and create:
```python
@pytest.mark.slow
def test_custodiet_allows_legitimate_framework_work():
    """Regression: custodiet blocked legitimate framework modification."""
    input_fixture = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "/home/nic/src/academicOps/skills/learn.md", ...},
        # ... exact input that was incorrectly blocked
    }
    result = invoke_custodiet(input_fixture)
    assert result["decision"] != "deny", "Should allow legitimate framework edits"
```

### 8. Update Documentation if Needed

If the fix changes documented behavior, update the relevant docs. Don't create new docs unless necessary.

### 9. Report (Framework Reflection Format)

Output in the standard Framework Reflection format so session-insights can parse it:

```
## Framework Reflection

**Prompts**: [The observation/feedback that triggered /learn]
**Guidance received**: N/A
**Followed**: Yes
**Outcome**: success
**Accomplishments**: [Task created: X], [Fix applied: file:line], [Test added: file]
**Friction points**: [Any difficulties encountered, or "none"]
- The `replace` tool did not seem to work as expected. It reported success, but `git status` showed no changes. I had to resort to `write_file` to get the change to persist.
**Root cause** (if not success): [Category: component that failed]
**Proposed changes**: [Pattern generalized, escalation trigger noted]
**Next step**: [If follow-up needed, must be filed as task]
```

**Field mapping from /learn workflow:**
- Prompts → The user feedback/observation
- Accomplishments → Task + fix + test (the deliverables)
- Root cause → From step 1 (Clarity/Context/Blocking/Detection/Gap)
- Proposed changes → From step 5 (pattern generalization) + escalation triggers

```