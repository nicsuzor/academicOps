---
title: Enforcement Mechanisms Guide
type: reference
description: Living document on how to effectively enforce agent behaviors
tags: [framework, enforcement, learning]
---

# Enforcement Mechanisms

**Purpose**: Guide for choosing HOW to enforce a behavior, based on evidence of what works.

## Mechanism Ladder

Agents are intelligent. They don't ignore instructions arbitrarily - they weigh competing priorities. Stronger emphasis and clearer reasons increase compliance. The ladder reflects both *mechanism type* and *persuasive strength*.

| Level | Mechanism | Strength | Use When |
|-------|-----------|----------|----------|
| 1a | Prompt text (mention) | Weakest | Nice-to-have suggestion |
| 1b | Prompt text (explicit rule) | Weak | Stated rule but no emphasis |
| 1c | Prompt text (emphasized + reasoned) | Medium-Weak | Rule with WHY it matters |
| 2a | JIT injection (informational) | Medium-Weak | Agent lacks context to comply |
| 2b | JIT injection (directive) | Medium | Direct instruction with action |
| 2c | JIT injection (emphatic + reasoned) | Medium-Strong | Urgent instruction with clear stakes |
| 3 | Skill abstraction | Strong | Hide complexity, force workflow |
| 4 | Pre-tool-use hooks | Stronger | Block before damage occurs |
| 5 | Post-tool-use validation | Strong | Catch violations, demand correction |
| 6 | Deny rules (settings.json) | Strongest | Hard block, no exceptions |
| 7 | Pre-commit hooks | Absolute | Last line of defense |

### Prompt Strength Guidelines (Levels 1-2)

The same information delivered differently has vastly different compliance rates:

| Approach | Example | Compliance |
|----------|---------|------------|
| Mention | "Consider using TodoWrite" | Low |
| Rule | "Use TodoWrite for multi-step tasks" | Medium-Low |
| Emphasized | "**MANDATORY**: Use TodoWrite" | Medium |
| Reasoned | "Use TodoWrite because [specific benefit to this task]" | Medium-High |
| Emphatic + Reasoned | "**CRITICAL**: TodoWrite required - without it you'll lose track of the 5 steps needed here" | High |

**Key insight**: Agents respond to *salience* and *relevance*. Generic rules compete with task urgency. Task-specific reasons connect enforcement to immediate goals.

## When Each Mechanism Works

### Level 1: Prompt Text (AXIOMS, HEURISTICS)

**Works when**: Agent has all information needed and behavior is about judgment/preference.

**Sub-levels**:

| Level | Style | When to Use |
|-------|-------|-------------|
| 1a | Mention ("consider X") | Optional preference, agent can override |
| 1b | Rule ("always do X") | Expected behavior, no emphasis |
| 1c | Emphatic + Reasoned ("**CRITICAL**: X because Y") | Must-follow, with task-specific stakes |

**Fails when**:
- Agent lacks context to comply (can't execute what it doesn't know)
- Rule competes with stronger patterns (training, task urgency)
- Rule is too abstract to apply
- Emphasis without reason (agent sees urgency but not relevance)

**Evidence**:
- "No mocks" rule exists but ignored → agents default to unit test patterns from training
- "Fail-fast" rule exists but ignored → agents trained to be helpful, work around problems
- Generic "MANDATORY" ignored → competes with immediate task; no task-specific reason given

**Lesson**: Rules alone don't work when they fight strong priors. **Reasoned emphasis** works better than bare rules. Connect enforcement to the specific task's success.

### Level 2: JIT Context Injection

**Works when**: Agent would comply IF it had the information AND recognizes relevance.

**Sub-levels**:

| Level | Style | When to Use |
|-------|-------|-------------|
| 2a | Informational ("here's context: X") | Agent needs facts to make good decision |
| 2b | Directive ("do X before proceeding") | Clear action required, moderate stakes |
| 2c | Emphatic + Reasoned ("**ROUTE FIRST**: X because without it you'll miss Y") | High-stakes action with specific consequences |

**Fails when**:
- Context arrives too late (after decision made)
- Context too verbose (buried in noise)
- Agent doesn't recognize relevance (no connection to current task)
- Directive without reason (agent deprioritizes against task urgency)

**Evidence**:
- "Execute don't explore" problem: agents explore because they lack execution context
- Fix isn't "stop exploring" - fix is inject execution context at the right moment
- Prompt router 2b instruction ("invoke router") ignored → buried in system-reminders, no task-specific reason given
- When injection includes WHY (task-specific benefit), compliance increases

**Lesson**: If agents are searching for information, the fix is often to provide it, not prohibit searching. **Injected directives need task-specific reasons** - "do X" is weaker than "do X because it will help you with Y that you're about to do."

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
| Agent explores when should execute | "Don't explore" rule (1b) | Inject execution context (2a) |
| Agent ignores rule without emphasis | Add more rules (1b) | Add task-specific reason (1c or 2c) |
| Agent skips injected directive | Repeat directive louder | Add WHY - connect to current task (2c) |
| Agent uses mocks despite rule | Add another rule (1b) | Enforcement hook (Level 4) or skill wrapper (Level 3) |
| Agent skips skill invocation | "MANDATORY" without reason (1b) | Pre-tool block (Level 4) OR emphatic + reasoned (2c) |
| Agent claims success without verification | Add AXIOM (1b) | Post-tool verification hook (Level 5) |
| Agent creates backup files | Ask nicely (1a) | Deny rule (Level 6) |

### Escalation Path for Prompt Router

Current state: Level 2b (directive injection) - "invoke router before proceeding"

Proposed escalation: Level 2c (emphatic + reasoned):
```
**ROUTE FIRST** (saves you time): The intent-router will tell you exactly which
skills to invoke and rules to follow for THIS task. Without it, you'll likely
miss required steps and need to redo work. Takes 2 seconds, saves minutes.

Task(subagent_type="intent-router", ...)
```

If 2c fails → escalate to Level 4 (pre-tool hook that blocks first tool until router invoked).

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
