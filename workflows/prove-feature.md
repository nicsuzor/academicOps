---
id: prove-feature
category: quality-assurance
---

# Prove Feature Workflow

## Overview

Prove a framework feature works correctly by establishing baseline state, executing the operation, and verifying structural changes. Unlike general QA (which checks "does the code work?"), this workflow validates "does the feature integrate correctly with the existing system?"

## When to Use

- Validating new framework capabilities before release
- Testing that operations produce expected data structures
- Verifying components connect properly (not orphaned/disconnected)
- Any feature where "correct" means "properly integrated" not just "runs without error"

## Steps

### 1. Establish Baseline

Before running the feature, capture the existing state relevant to what will change:

**Identify what to capture:**
- What data structure will the feature modify?
- What relationships should exist after execution?
- What IDs/references need to be preserved?

**Capture methods by domain:**

| Domain | Baseline Query |
|--------|----------------|
| Tasks | `search_tasks()`, `get_task_tree()` |
| Memory | `retrieve_memory()`, `list_memories()` |
| Files | `Glob()`, `Read()` to capture current state |
| MCP tools | Query current state via tool |
| Hooks | Check current trigger behavior |

**Output**: Clear statement of "before state" with specific values.

### 2. Execute Feature

Run the feature being tested **as a user would**:

- Use normal invocation (skill, command, direct tool call)
- Do not modify the feature behavior for testing
- Capture any output/return values

### 3. Verify Structural Changes

Check that the feature produced correct integration:

**Verification queries by domain:**

| Domain | Verification |
|--------|--------------|
| Tasks | Tree structure, parent/child, dependencies |
| Memory | Content stored, tags applied, retrievable |
| Files | Created/modified, correct location, valid format |
| MCP tools | Response structure, side effects |
| Hooks | Triggered at right time, correct context |

**Key questions:**
- Did the operation connect to existing data (not orphan)?
- Are bidirectional relationships updated (parent knows child, child knows parent)?
- Are computed fields correct (depth, leaf, blocks)?

### 4. Report Evidence

Present verification as structured evidence:

```markdown
## QA Test Result: ✅ PASS / ❌ FAIL

### [Feature Name] Verification

| Field | Expected | Actual | Correct? |
|-------|----------|--------|----------|
| [key1] | [value] | [value] | ✅/❌ |
| [key2] | [value] | [value] | ✅/❌ |

### Evidence
- **Before**: [baseline state]
- **After**: [new state]
- **Change**: [what the feature did]
```

## Decision Tree

```
Is this a "does it run without error?" question?
  └─ YES → Use [[qa-demo]] instead

Is this a "does it integrate correctly?" question?
  └─ YES → Use this workflow
           ↓
      1. Identify what data the feature affects
      2. Query baseline state (before)
      3. Execute feature normally
      4. Query result state (after)
      5. Compare expected vs actual
      6. Report evidence table
```

## Edge Cases to Consider

This workflow validates the happy path. Document which edge cases are NOT covered:

- **Missing dependencies** - What if referenced items don't exist?
- **Ambiguous targets** - Multiple valid matches for a reference?
- **Cycles/conflicts** - Does the feature prevent invalid states?
- **Concurrent access** - Race conditions?
- **Format evolution** - What if schemas change?

List these as "future validation needed" in your report.

## Examples

### Example 1: Task Chaining

**Baseline**: Search for parent task, note its children array
**Execute**: `/q` command referencing parent work
**Verify**: `get_task_tree()` shows new task as child
**Evidence**: parent field, depth, bidirectional link

### Example 2: Memory Storage

**Baseline**: `retrieve_memory("topic")` returns N results
**Execute**: `Skill(skill="remember")` with new knowledge
**Verify**: `retrieve_memory("topic")` returns N+1, new entry present
**Evidence**: content hash, tags, retrievability

### Example 3: Hook Trigger

**Baseline**: Document expected trigger conditions
**Execute**: Perform action that should trigger hook
**Verify**: Hook output present in context/response
**Evidence**: Hook fired, correct context injected

### Example 4: MCP Tool Response

**Baseline**: Document expected response schema
**Execute**: Call tool with test input
**Verify**: Response matches schema, side effects occurred
**Evidence**: Response fields, state changes

## See Also

- [[qa-demo]] - General QA verification (functionality check)
- [[dogfooding]] - Framework self-improvement during work
- [[tdd-cycle]] - Test-driven development for code changes
