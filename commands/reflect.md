---
name: reflect
category: instruction
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

### 3. Report Deviations with Root Cause Analysis

For each non-compliance, trace to **framework component responsibility** (not just agent behavior):

```
DEVIATION: [skill name]
- Expected: [what spec prescribed]
- Actual: [what I did instead]
- Proximate Cause: [what agent did wrong]
- Root Cause: [which framework component failed which responsibility]
- Root Cause Category: Clarity | Context | Blocking | Detection | Gap
- Responsible Component: [e.g., Intent Router, Guardrail, Skill instruction]
```

See [[specs/enforcement.md]] "Component Responsibilities" for the full model.

### 4. Propose Correction

**Two levels of correction**:

1. **Immediate**: What output needs to be regenerated?
2. **Framework**: What component needs strengthening to prevent recurrence?

| Root Cause Category | Framework Fix |
|---------------------|---------------|
| Clarity Failure | Strengthen instruction text in skill/guardrail |
| Context Failure | Improve router classification or context injection |
| Blocking Failure | Add/fix PreToolUse hook or deny rule |
| Detection Failure | Add/fix PostToolUse hook |
| Gap | Create new enforcement mechanism |

### 5. Persist Observations

After completing the audit, invoke `/log` to record deviations:

```
Skill(skill="log", args="[root cause category]: [responsible component] - [deviation summary]")
```

This ensures framework component failures are tracked as GitHub Issues (label: `learning`) and can trigger heuristic synthesis when patterns emerge.

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
- Proximate Cause: Agent chose ad-hoc implementation over prescribed workflow
- Root Cause: Skill instruction didn't emphasize WHY SessionProcessor matters
- Root Cause Category: Clarity Failure
- Responsible Component: dashboard skill SKILL.md

CORRECTION:
1. Immediate: Re-run using dashboard's actual data sources
2. Framework: Strengthen dashboard skill to explain SessionProcessor benefits
```

## Scope

`/reflect` is for **manual process compliance**, not outcome quality. For outcome verification, use [[/qa]].

| Command | Question Answered |
|---------|-------------------|
| `/reflect` | Did I follow the rules? (manual self-audit) |
| `/session-insights current` | What patterns occurred? (automated mining + heuristic updates) |
| `/qa` | Does the output meet acceptance criteria? |
| `/log` | What observation should we record? |

## Automated Reflection

For automated session mining with heuristic update suggestions, use:

```
Skill(skill="session-insights", args="current")
```

This runs automatically at session end via Stop hook. It:
1. Mines session transcript for patterns
2. Maps findings to heuristics (H2, H3, etc.)
3. Presents approve/dismiss options
4. Updates HEURISTICS.md on approval
