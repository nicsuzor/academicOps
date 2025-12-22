---
title: Enforcement Mechanisms Guide
type: reference
description: Living document on how to effectively enforce agent behaviors
tags: [framework, enforcement, learning]
---

# Enforcement Mechanisms

**Purpose**: Guide for choosing HOW to enforce a behavior, based on evidence of what works.

## Mechanism Ladder

| Level | Mechanism | Strength | Use When |
|-------|-----------|----------|----------|
| 1 | Prompt text (rules, heuristics) | Weakest | Behavior is occasional preference |
| 2 | JIT context injection (hooks) | Medium | Agent needs information to comply |
| 3 | Skill abstraction | Strong | Hide complexity, force workflow |
| 4 | Pre-tool-use hooks | Stronger | Block before damage occurs |
| 5 | Post-tool-use validation | Strong | Catch violations, demand correction |
| 6 | Deny rules (settings.json) | Strongest | Hard block, no exceptions |
| 7 | Pre-commit hooks | Absolute | Last line of defense |

## When Each Mechanism Works

### Level 1: Prompt Text (AXIOMS, HEURISTICS)

**Works when**: Agent has all information needed and behavior is about judgment/preference.

**Fails when**:
- Agent lacks context to comply (can't execute what it doesn't know)
- Rule competes with stronger patterns (training, other instructions)
- Rule is too abstract to apply

**Evidence**:
- "No mocks" rule exists but ignored → agents default to unit test patterns from training
- "Fail-fast" rule exists but ignored → agents trained to be helpful, work around problems

**Lesson**: Rules alone don't work when they fight strong priors. Need enforcement.

### Level 2: JIT Context Injection

**Works when**: Agent would comply IF it had the information.

**Fails when**:
- Context arrives too late (after decision made)
- Context too verbose (buried in noise)
- Agent doesn't recognize relevance

**Evidence**:
- "Execute don't explore" problem: agents explore because they lack execution context
- Fix isn't "stop exploring" - fix is inject execution context at the right moment

**Lesson**: If agents are searching for information, the fix is often to provide it, not prohibit searching.

### Level 3: Skill Abstraction

**Works when**: Correct behavior requires multiple steps or hidden complexity.

**Fails when**:
- Agent bypasses skill invocation entirely
- Skill is optional rather than mandatory for the operation

**Evidence**:
- `/remember` skill: abstracts markdown + memory sync → agents can't do it wrong
- Skill bypass: 8+ instances where agents skipped skill despite "MANDATORY" prompt

**Lesson**: Skills work for WHAT to do. They don't ensure agents USE them. Need Level 4+ for that.

### Level 4: Pre-Tool-Use Hooks

**Works when**: You can detect intent before action and block/modify.

**Fails when**:
- Detection is imperfect (can't tell if this Edit is problematic)
- Hook adds latency users won't tolerate

**Evidence**:
- Pre-edit auto-read: can reliably detect "file not read" → auto-read before Edit
- Skill enforcement: can detect "editing sensitive path without skill token" → block

**Lesson**: Best for mechanical preconditions (file read, path checks, format validation).

### Level 5: Post-Tool-Use Validation

**Works when**: Can verify outcome and demand correction.

**Fails when**:
- Damage already done (destructive operations)
- Correction loop is expensive

**Evidence**:
- Autocommit hook: validates commit format after git commit
- ROADMAP enforcement: prompt "did you update?" after framework changes

**Lesson**: Good for verification and nudges, not prevention.

### Level 6: Deny Rules

**Works when**: Behavior should NEVER occur, no exceptions.

**Fails when**:
- Legitimate uses exist (false positives block real work)
- Pattern matching is imprecise

**Evidence**:
- `*_backup*`, `*.bak` deny rules: prevents backup file creation absolutely
- Works because there's never a legitimate reason to create these

**Lesson**: Reserve for truly inviolable rules. Over-use creates friction.

### Level 7: Pre-Commit Hooks

**Works when**: Must catch before code enters repository.

**Fails when**:
- Developers bypass with `--no-verify`
- Check is slow (developers disable)

**Evidence**:
- Ruff/mypy: catches lint/type errors reliably
- File size limits: prevents oversized files entering repo

**Lesson**: Last line of defense, not primary enforcement.

## Diagnosis → Solution Mapping

| Diagnosis | Wrong Solution | Right Solution |
|-----------|----------------|----------------|
| Agent explores when should execute | "Don't explore" rule | Inject execution context (Level 2) |
| Agent uses mocks despite rule | Add another rule | Enforcement hook (Level 4) or skill wrapper (Level 3) |
| Agent skips skill invocation | Stronger wording in prompt | Pre-tool block for sensitive paths (Level 4) |
| Agent claims success without verification | Add AXIOM | Post-tool verification hook (Level 5) |
| Agent creates backup files | Ask nicely | Deny rule (Level 6) |

## Open Questions

- How to enforce skill invocation without blocking legitimate direct operations?
- How to detect "claiming success without verification" mechanically?
- What's the right balance of hook latency vs enforcement strength?

## Evidence Log

Track observations here to inform mechanism choices:

| Date | Observation | Mechanism Tried | Worked? |
|------|-------------|-----------------|---------|
| 2025-12-22 | 8+ skill bypass instances | Prompt text ("MANDATORY") | No |
| 2025-12-22 | "No mocks" ignored | AXIOM rule | No |
| 2025-12-22 | File not read before edit | (none) | N/A - needs Level 4 |
| 2025-12-21 | Backup file creation | Deny rule | Yes |
| 2025-12-20 | Autocommit format | Post-tool hook | Yes |

---

## Revision Protocol

When adding enforcement for a behavior:

1. **Diagnose**: Why is the behavior occurring? (lack of info? conflicting priors? no enforcement?)
2. **Choose level**: Start at lowest effective level
3. **Implement**: Add mechanism
4. **Observe**: Log evidence of success/failure
5. **Escalate**: If ineffective, move up the ladder
