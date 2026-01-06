---
name: compliance-auditor-context
title: Compliance Auditor Context Template
category: template
description: Template written to temp file by PostToolUse hook for compliance-auditor subagent.
---

# Compliance Auditor Context Template

This template is written to a temp file by the PostToolUse hook (every ~7 tool calls).
The compliance-auditor subagent reads this file to check session compliance.

Variables:
- `{session_context}` - Recent prompts, active skill, TodoWrite state
- `{tool_name}` - Most recent tool that was used

---
# Compliance Audit Request

Review this session's recent activity and check for principle violations or drift.

## Recent Tool
Last tool used: {tool_name}
{session_context}

## Your Task

Compare recent session activity against framework principles:

1. **Check axiom compliance** - Any violations of AXIOMS.md?
   - #7 Fail-Fast: Is agent working around errors instead of reporting?
   - #15 Verify First: Is agent making claims without verification?
   - #17 VERIFY FIRST: Has agent checked actual state before asserting?
   - #22 Acceptance Criteria: Is agent modifying/weakening success criteria?

2. **Check heuristic compliance** - Any violations of HEURISTICS.md?
   - H3 Verification Before Assertion: Claims supported by evidence?
   - H4 Explicit Instructions Override: Following user instructions literally?
   - H19 Questions Require Answers: Answering questions or jumping to action?

3. **Check for drift** - Is agent staying on task?
   - Following the plan from TodoWrite?
   - Not scope-creeping into unasked work?

## Return Format

If everything looks good:
```
## Compliance Check: OK
No issues detected. Continue current work.
```

If issues detected:
```
## Compliance Check: ATTENTION

**Issue**: [brief description]
**Principle violated**: [axiom/heuristic reference]
**Correction**: [what agent should do differently]
```
