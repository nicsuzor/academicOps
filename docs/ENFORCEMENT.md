---
title: Enforcement Mechanisms Guide
type: reference
category: docs
description: Living document on how to effectively enforce agent behaviors
tags: [framework, enforcement, learning]
---

# Enforcement Mechanisms

**Purpose**: Practical guide for choosing HOW to enforce a behavior. For architectural philosophy, see [[enforcement|specs/enforcement.md]]. For current active rules, see [[RULES]].

## Mechanism Ladder

Agents are intelligent. They don't ignore instructions arbitrarily - they weigh competing priorities. Stronger emphasis and clearer reasons increase compliance. The ladder reflects both _mechanism type_ and _persuasive strength_.

| Level | Mechanism                           | Strength      | Use When                                  |
| ----- | ----------------------------------- | ------------- | ----------------------------------------- |
| 1a    | Prompt text (mention)               | Weakest       | Nice-to-have suggestion                   |
| 1b    | Prompt text (explicit rule)         | Weak          | Stated rule but no emphasis               |
| 1c    | Prompt text (emphasized + reasoned) | Medium-Weak   | Rule with WHY it matters                  |
| 2     | **Intent router**                   | Medium-Strong | First intelligent intervention point      |
| 3a    | Tool restriction (soft deny)        | Medium-Strong | Tool available only via specific workflow |
| 3b    | Skill abstraction                   | Strong        | Hide complexity, force workflow           |
| 4     | Pre-tool-use hooks                  | Stronger      | Block before damage occurs                |
| 5     | Post-tool-use validation            | Strong        | Catch violations, demand correction       |
| 6     | Deny rules (settings.json)          | Strongest     | Hard block, no exceptions                 |
| 7     | Pre-commit hooks                    | Absolute      | Last line of defense                      |

### Prompt Strength Guidelines (Level 1)

The same information delivered differently has vastly different compliance rates:

| Approach            | Example                                                                                      | Compliance  |
| ------------------- | -------------------------------------------------------------------------------------------- | ----------- |
| Mention             | "Consider using TodoWrite"                                                                   | Low         |
| Rule                | "Use TodoWrite for multi-step tasks"                                                         | Medium-Low  |
| Emphasized          | "**MANDATORY**: Use TodoWrite"                                                               | Medium      |
| Reasoned            | "Use TodoWrite because [specific benefit to this task]"                                      | Medium-High |
| Emphatic + Reasoned | "**CRITICAL**: TodoWrite required - without it you'll lose track of the 5 steps needed here" | High        |

**Key insight**: Agents respond to _salience_ and _relevance_. Generic rules compete with task urgency. Task-specific reasons connect enforcement to immediate goals.

**Limitation**: Even emphatic + reasoned prompts have limited compliance. Level 2 (intent router) provides intelligent, adaptive enforcement.

## When Each Mechanism Works

### Level 1: Prompt Text (AXIOMS, HEURISTICS)

**Works when**: Agent has all information needed and behavior is about judgment/preference.

**Sub-levels**:

| Level | Style                                             | When to Use                             |
| ----- | ------------------------------------------------- | --------------------------------------- |
| 1a    | Mention ("consider X")                            | Optional preference, agent can override |
| 1b    | Rule ("always do X")                              | Expected behavior, no emphasis          |
| 1c    | Emphatic + Reasoned ("**CRITICAL**: X because Y") | Must-follow, with task-specific stakes  |

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

### Level 2: Intent Router (Intelligent Steering)

**Works when**: Agent needs workflow-aware guidance that adapts to the specific task.

**How it works**: Haiku subagent classifies prompt against known failure patterns and workflows, returns task-specific guidance. Main agent receives filtered output (not full classification logic).

The router IS the Level 2 mechanism. It replaces static JIT injection with intelligent, adaptive intervention:

| Old Approach            | Router Advantage                           |
| ----------------------- | ------------------------------------------ |
| Informational injection | Router knows WHICH information is relevant |
| Directive injection     | Router gives task-specific directives      |
| Emphatic + reasoned     | Router explains WHY for THIS task          |

**Capabilities**:

- Knows common failure patterns from HEURISTICS.md
- Provides workflow-specific skill recommendations
- Adapts guidance to task type (debug, feature dev, question, etc.)
- References H3, H19, H28 etc. to prevent known failures

**Fails when**:

- Router itself gives bad recommendations
- Agent ignores router output (need Level 3+ enforcement)
- Classification misses the task type

**Evidence**:

- 2025-12-26: Router correctly steered agent to framework skill for enforcement updates

**Lesson**: Router is the first _intelligent_ intervention - it understands context, not just patterns. All Level 2 enforcement flows through the router.

### Level 3a: Tool Restriction (Soft Deny)

**Works when**: Tool should be available but only through proper workflow.

**How it works**: Tool not in default tool list. Specific agents/workflows grant access via `allowed_tools` in agent definition or skill context.

**Differs from Level 6 (Deny rules)**:

- Deny rules: Tool NEVER allowed for path/pattern
- Tool restriction: Tool allowed, but only when invoked through correct channel

**Use cases**:

- Write to `tasks/` only via `/tasks` skill (ensures proper frontmatter)
- Database operations only via `/analyst` skill (ensures proper validation)
- Email sending only via explicit user confirmation workflow

**Fails when**:

- Too many restrictions create friction
- Legitimate quick operations become cumbersome
- Agent finds workarounds (different tool for same effect)

**Evidence**:

- (New mechanism - tracking effectiveness)

**Lesson**: Softer than deny rules but enforces "right tool for the job" by making wrong tool unavailable.

### Level 3b: Skill Abstraction

**Works when**: Correct behavior requires multiple steps or hidden complexity.

**Fails when**:

- Agent bypasses skill invocation entirely
- Skill is optional rather than mandatory for the operation

**Evidence**:

- `/remember` skill: abstracts markdown + memory sync → agents can't do it wrong
- Skill bypass: 8+ instances where agents skipped skill despite "MANDATORY" prompt

**Lesson**: Skills work for WHAT to do. They don't ensure agents USE them. Need Level 4+ for that.

### Level 3c: TodoWrite Skill-Chaining

**Works when**: A skill needs another skill's guidance, and suggestions are ignored.

**How it works**: Skill instructs agent to create TodoWrite with explicit `Skill()` calls as steps. Agent executes each step, including the skill invocation.

```
TodoWrite(todos=[
  {content: "Step 1: Prerequisite work", ...},
  {content: "Step 2: Invoke Skill(skill='other-skill')", ...},
  {content: "Step 3: Use loaded guidance", ...}
])
```

**Why it works**:

1. TodoWrite creates trackable, sequential steps
2. Skill invocation is an explicit step (not a suggestion)
3. Agent executes todos in order → must invoke the skill
4. Guidance loads mid-workflow when needed

**Evidence**:

- 2026-01-06: test-skill-chain validated pattern works
- audit skill (v5.0.0) chains to framework and flowchart skills via TodoWrite

**Lesson**: Solves "skills can't invoke skills" without hooks. Makes skill invocation a mandatory workflow step rather than an optional suggestion. See [[framework/SKILL.md]] for pattern details.

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

| Diagnosis                                 | Wrong Solution                  | Right Solution                                   |
| ----------------------------------------- | ------------------------------- | ------------------------------------------------ |
| Agent explores when should execute        | "Don't explore" rule (1b)       | Intent router injects execution context (2)      |
| Agent ignores rule without emphasis       | Add more rules (1b)             | Intent router with task-specific reason (2)      |
| Agent needs workflow-aware guidance       | Generic rules (1b)              | Intent router with failure patterns (2)          |
| Agent uses mocks despite rule             | Add another rule (1b)           | Enforcement hook (Level 4) or skill wrapper (3b) |
| Agent skips skill invocation              | "MANDATORY" without reason (1b) | Intent router (2) OR pre-tool block (Level 4)    |
| Agent uses wrong tool for domain          | Deny rule (overkill)            | Tool restriction via workflow (3a)               |
| Agent claims success without verification | Add AXIOM (1b)                  | Post-tool verification hook (Level 5)            |
| Agent creates backup files                | Ask nicely (1a)                 | Deny rule (Level 6)                              |

### Escalation Path

**Level 2 (Intent Router)** is the first intelligent intervention. It handles ALL of:

- **Context insertion** - provides information agent needs
- **Directives** - tells agent what to do for THIS task
- **Skill/tool suggestions** - recommends which skills to invoke
- **Workflow guidance** - steers to Plan Mode, TodoWrite, etc.
- **Subagent delegation** - recommends Task() for appropriate work

**If router guidance ignored** → escalate to Level 3+ (tool restriction, pre-tool hooks)

### Workflow Development Pattern

**Commands → Router pipeline**:

1. **Prototype with /commands**: Create a `/command` to test a workflow (e.g., `/qa`, `/ttd`)
2. **Iterate**: Refine the workflow based on real usage
3. **Graduate to router**: When workflow is proven, add it to the intent router for automatic/general application

This allows testing strict workflows (e.g., supervisor-only mode, mandatory subagent delegation) before making them default behavior. Commands are explicit user invocation; router is automatic steering.

## Claude Code Native Permission Model

Understanding what's achievable natively vs requiring custom enforcement.

### What settings.json Can Do

| Capability               | Supported | Notes                                     |
| ------------------------ | --------- | ----------------------------------------- |
| Path-based allow/deny    | ✅        | `Write(data/tasks/**)`                    |
| Tool-based allow/deny    | ✅        | `Bash(rm:*)`                              |
| Agent-scoped permissions | ❌        | Rules are global                          |
| Skill-scoped permissions | ❌        | Skills don't create permission boundaries |

### Permission Precedence

```
Deny (highest) → Ask → Allow (lowest)
```

**Implication**: Can't "deny for main agent, allow for subagent" - deny wins globally.

### Subagent `tools:` Field

Agent frontmatter can restrict tools:

```yaml
tools: [Read, Grep]  # Only these tools available
```

**Key limitation**: This only **restricts** - it can't **grant** permissions beyond settings.json. A subagent with `tools: [Write]` follows the same allow/deny rules as everyone else.

### What's NOT Achievable Natively

| Goal                                      | Why Not                              | Alternative                |
| ----------------------------------------- | ------------------------------------ | -------------------------- |
| "Only /tasks skill can write to tasks/"   | Skills don't create permission scope | PreToolUse hook (Level 4)  |
| "Subagent gets more permission than main" | Deny rules are global                | Not possible without hooks |
| "Different paths for different agents"    | Allow/deny is global                 | Hook-based gating          |

### Achievable Patterns

1. **Restricted subagents** - Subagent has fewer tools than main agent
2. **Path-based protection** - All agents follow same path rules
3. **Hook-gated access** - PreToolUse hook checks context before allowing

**Lesson**: For agent/skill-scoped permissions, must use Level 4 (PreToolUse hooks) with context detection (transcript parsing or state tracking).

## Open Questions

- ~~How to enforce skill invocation without blocking legitimate direct operations?~~ → **Solved**: Level 3c (TodoWrite Skill-Chaining)
- How to detect "claiming success without verification" mechanically?
- What's the right balance of hook latency vs enforcement strength?

## Revision Protocol

When adding enforcement for a behavior:

1. **Diagnose**: Why is the behavior occurring? (lack of info? conflicting priors? no enforcement?)
2. **Choose level**: Start at lowest effective level
3. **Implement**: Add mechanism
4. **Observe**: Log evidence of success/failure
5. **Escalate**: If ineffective, move up the ladder
