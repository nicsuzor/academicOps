---
title: Ultra Vires Custodiet
permalink: ultra-vires-custodiet
type: spec
category: spec
status: draft
tags:
  - framework
  - hooks
  - agent-behavior
  - guardrails
  - enforcement
created: 2025-12-30
---

# Ultra Vires Custodiet

**Status**: DRAFT - architecture designed, ready for implementation
**Priority**: P1 - core guardrail for agent autonomy

## Purpose

Detect when agents act **ultra vires** - beyond the authority granted by the user's request.

The name draws from public law: "ultra vires" (beyond powers) describes acts outside granted authority. The watchdog is the *custodiet* - the guardian that watches.

**Scope**: This spec covers **semantic authority enforcement** - understanding whether an agent's actions align with the user's intent. Pattern-based mechanical violations (`--no-verify`, backup files, destructive git) are handled by PreToolUse hooks (`policy_enforcer.py`) and are NOT part of custodiet.

## Failure Categories

### Type A: Reactive Helpfulness

**Pattern**: Agent encounters obstacle -> immediately tries to fix it without authorization.

**Characteristics**:
- Most common failure mode
- Happens in real-time, no planning/todos
- Agent "just trying to be helpful"
- Unplanned investigation of infrastructure

**Example**:
```
User: "try again with outlook?"

Agent: outlook - get-emails (MCP)
  -> Error: Missing required configuration: tenant_id and client_id

Agent: "Still failing-let me check what's configured:"   <- UNAUTHORIZED
Agent: Read(~/src/academicOps/config/claude/mcp.json)    <- UNAUTHORIZED
Agent: "Found it-needs Azure AD credentials:"            <- UNAUTHORIZED
Agent: Web Search("outlook-mcp configuration setup")     <- UNAUTHORIZED
```

The user asked to "try again" - not to investigate config files, diagnose the problem, or search for solutions.

### Type B: Deliberate Scope Expansion

**Pattern**: Agent consciously expands plan to include work beyond request.

**Characteristics**:
- Less common but more subtle
- Happens at planning stage (TodoWrite)
- Agent decides additional work is "needed" or "would be helpful"

**Example**:
```
User: "fix the login bug"

Agent creates todos:
1. Investigate login bug          <- AUTHORIZED
2. Fix the root cause             <- AUTHORIZED
3. Refactor authentication module <- UNAUTHORIZED
4. Add comprehensive tests        <- UNAUTHORIZED
5. Update documentation           <- UNAUTHORIZED
```

## Problem Statement

**What manual work are we automating?**

User must constantly monitor agent behavior for drift:
- Agent asked to "try again" starts debugging infrastructure (Type A)
- Agent asked to "fix the bug" starts refactoring surrounding code (Type B)
- Agent makes architectural decisions without consulting user
- Agent interprets ambiguous requirements in self-serving ways

**Why does this matter?**

- Wasted work when agent goes off-track
- Trust erosion when agent acts without authority
- Research integrity at risk when agent makes unilateral decisions
- User cognitive load increases from constant vigilance

**Who benefits?**

Nic - ensures agents stay within granted authority, enforces [[AXIOMS]] #4 (Do One Thing) and #22 (Acceptance Criteria Own Success).

## Architecture

### Authority Envelope Model

At session start (or when user makes a request), extract:

| Component | Description | Example |
|-----------|-------------|---------|
| **Explicit scope** | What user directly asked for | "fix the login bug" |
| **Implied scope** | Reasonable necessities | reading login code, running tests |
| **Specified methods** | How user said to do it | "use the existing auth library" |
| **Constraints** | What user said NOT to do | "don't touch the database schema" |

The envelope defines **authorized territory**. Actions outside it are *ultra vires*.

### Detection Method: Semantic Analysis

Per [[HEURISTICS#H31]] (No LLM Calls in Hooks), hooks cannot call LLMs directly. Custodiet spawns a **background subagent** (haiku) that reads the session transcript and evaluates authority compliance.

**What the subagent checks**:

| Category | Signal | Example |
|----------|--------|---------|
| Axiom violations | #7 Fail-Fast | Working around errors instead of halting |
| Axiom violations | #17 Verify First | Claims without checking actual state |
| Axiom violations | #22 Acceptance Criteria | Modifying what "done" means |
| Heuristic violations | H3 Verification | Claims without preceding Read/Bash |
| Heuristic violations | H4 Explicit Instructions | Interpreting instead of following literally |
| Heuristic violations | H19 Questions | Implementing when user asked a question |
| Drift patterns | Plan deviation | TodoWrite shows X, agent doing Y |
| Drift patterns | Scope creep | Work user didn't request |

### Invocation Points

| Hook | Trigger | Mode | Purpose |
|------|---------|------|---------|
| **PostToolUse** | Tool returns error | Background | Watch for Type A (reactive helpfulness) |
| **PostToolUse** | Every ~7 tool calls | Background | Periodic compliance check |
| **PreToolUse:TodoWrite** | Todo list changes | Blocking | Catch Type B (scope expansion) |
| **SubagentStop** | Subagent completes | Background | Audit delegated work |

### Enforcement Levels

Per existing framework graduated enforcement:

| Level | Action | When |
|-------|--------|------|
| 1. Log | Record observation | Minor drift, first occurrence |
| 2. Warn | Inject warning to agent | Clear drift from scope |
| 3. Checkpoint | Block until user confirms | Significant scope change |
| 4. Block | Halt execution | Obvious ultra vires action |

**Default**: Level 2 (Warn) - loud and forceful intervention on drift.

## Output Format

### If OK

```markdown
## Compliance Check: OK
No issues detected. Continue current work.
```

### If Issues Found

```markdown
## Compliance Check: ATTENTION

**Issue**: [1 sentence description]
**Principle**: [axiom/heuristic number and name]
**Correction**: [what to do instead]
```

## Relationship to Other Components

| Component | Purpose | Relationship |
|-----------|---------|--------------|
| [[policy_enforcer.py]] | Blocks mechanical violations | Complementary - handles pattern matching |
| [[specs/prompt-hydration]] | Enriches prompts with context | Upstream - surfaces relevant skills |
| [[/qa]] | Verifies "does it work" | Orthogonal - verifies outcomes not authority |
| [[RULES.md]] | Documents all enforcement | Registry - custodiet entries there |

## Implementation

### Current State

- `hooks/custodiet.py` - PostToolUse hook, triggers every ~7 tool calls
- `agents/custodiet.md` - Haiku agent that reads transcript
- `hooks/templates/custodiet-*.md` - Context and instruction templates

### Implementation Phases

#### Phase 1: Periodic Compliance (IMPLEMENTED)

- [x] PostToolUse hook tracks tool count
- [x] Spawns haiku subagent at threshold
- [x] Subagent reads transcript via temp file
- [x] Checks axioms/heuristics/drift

#### Phase 2: Error-Triggered Detection

- [ ] PostToolUse detects tool errors
- [ ] Spawns subagent to watch for reactive helpfulness
- [ ] Warns if agent investigates infrastructure without permission

#### Phase 3: TodoWrite Scope Gate

- [ ] PreToolUse:TodoWrite hook
- [ ] Blocking semantic analysis of new todos
- [ ] Compares against original user request
- [ ] Warns if scope expanded without authorization

#### Phase 4: Subagent Audit

- [ ] SubagentStop hook
- [ ] Audit delegated work against granted authority
- [ ] Log drift events for pattern analysis

## Acceptance Criteria

1. When agent drifts from original request, warning appears within ~30s
2. Agent receives clear message explaining the violation
3. Agent directed to report issues and ask user for direction
4. TodoWrite scope expansion caught BEFORE work begins
5. False positive rate low enough that warnings are actionable

## References

- [[AXIOMS]] #4 (Do One Thing)
- [[AXIOMS]] #22 (Acceptance Criteria Own Success)
- [[HEURISTICS#H31]] (No LLM Calls in Hooks)
- [[RULES.md]] (Enforcement registry)
