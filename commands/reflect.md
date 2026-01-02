---
name: reflect
description: Agent self-audit of process compliance against skill specifications and framework workflow
allowed-tools: Read,Grep,Glob
permalink: commands/reflect
---

# /reflect - Process Compliance Self-Audit

**Purpose**: Compare what you actually did against what you should have done per skill specs and [[execution-flow-spec]].

## When to Use

User invokes `/reflect` when they suspect you bypassed proper workflow:
- Invoked a skill but didn't use its prescribed data sources
- Took shortcuts instead of following skill instructions
- Made ad-hoc decisions that should have followed framework patterns

## Workflow

### 1. Identify Skills Invoked This Session

Check your recent actions for `Skill(skill="...")` invocations.

### 2. For Each Skill, Compare Actions to Spec

Read the skill's SKILL.md and check:

| Spec Says | I Actually Did | Compliant? |
|-----------|----------------|------------|
| [prescribed data source] | [what I used] | Y/N |
| [prescribed tool/method] | [what I called] | Y/N |
| [prescribed output format] | [what I produced] | Y/N |

### 3. Report Deviations

For each non-compliance:

```
DEVIATION: [skill name]
- Expected: [what spec prescribed]
- Actual: [what I did instead]
- Impact: [what was missed or done wrong]
```

### 4. Propose Correction

If the deviation matters:
- What should I redo?
- What output needs to be regenerated using proper sources?

### 5. Persist Observations

After completing the audit, invoke `/log` to record deviations:

```
Skill(skill="log", args="[deviation summary from Phase 3]")
```

This ensures process violations are tracked as GitHub Issues (label: `learning`) and can trigger heuristic synthesis when patterns emerge.

## Example

```
/reflect
```

**Agent response**:
```
AUDIT: dashboard skill invocation

| Spec Says | I Actually Did | Compliant? |
|-----------|----------------|------------|
| Use SessionProcessor for session data | Ran my own Python parsing | NO |
| Use parse_daily_log() for daily notes | Did not call this | NO |
| Display via Streamlit panels | Launched Streamlit but generated narrative manually | PARTIAL |

DEVIATION: dashboard
- Expected: Use lib.session_reader.SessionProcessor for session data
- Actual: Wrote ad-hoc Python to parse JSONL files directly
- Impact: Bypassed tested infrastructure, duplicated logic, may have missed data

CORRECTION: Should re-run using dashboard's actual data sources and let
the Streamlit panels display the synthesized view.
```

## Scope

`/reflect` is for **process compliance**, not outcome quality. For outcome verification, use [[/qa]].

| Command | Question Answered |
|---------|-------------------|
| `/reflect` | Did I follow the rules? |
| `/qa` | Does the output meet acceptance criteria? |
| `/log` | What observation should we record? |
