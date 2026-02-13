---
name: qa
category: instruction
description: Independent end-to-end verification before completion
allowed-tools: Task,Read,Glob,Grep
version: 1.0.0
permalink: skills-qa
---

# /qa Command Skill

Invoke the QA verification agent to verify work is complete before task completion.

## Purpose

Provides rigorous, cynical verification that work **actually achieves** what the user needs - not just that tests pass or agents claim success.

## Usage

```
/qa
```

Or with context:

```
Skill(skill="qa", args="Verify the authentication feature is complete")
```

## Execution

**This skill wraps the QA agent.** When invoked, immediately delegate to the QA agent:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Verify the work is complete.

**Original request**: [hydrated prompt from session context]

**Acceptance criteria**:
[Extract from task or session state]

**Work completed**:
[Files changed, todos marked complete]

Check all three dimensions (Output Quality, Process Compliance, Semantic Correctness) and produce verdict.
")
```

## When to Use

- Before marking a task as complete
- When the stop hook requires QA verification
- To verify complex implementations match acceptance criteria

## Output

The QA agent produces a verification report with:

- **Verdict**: VERIFIED or ISSUES
- **Verification Summary**: Pass/fail for each dimension
- **Issues Found**: If any, with severity and fix recommendations

## Integration

- **Stop hook**: May require QA verification before session end
- **Task completion**: QA should verify before `complete_task()`
- **Gate tracking**: `post_qa_trigger()` detects QA invocation
