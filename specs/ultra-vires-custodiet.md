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
created: 2025-12-30
---

# Ultra Vires Custodiet

**Status**: DRAFT - architecture designed, ready for implementation planning
**Priority**: P1 - core guardrail for agent autonomy

## Purpose

Detect when agents act **ultra vires** - beyond the authority granted by the user's request.

The name draws from public law: "ultra vires" (beyond powers) describes acts outside granted authority. The watchdog is the *custodiet* - the guardian that watches.

## Failure Categories

Ultra vires behavior manifests in two distinct patterns requiring different detection approaches:

### Type A: Reactive Helpfulness (Primary Target)

**Pattern**: Agent encounters obstacle → immediately tries to fix it without authorization.

**Characteristics**:
- Most common failure mode
- Happens in real-time, no planning/todos
- Agent "just trying to be helpful"
- Unplanned investigation of infrastructure

**Example**:
```
User: "try again with outlook?"

Agent: outlook - get-emails (MCP)
  → Error: Missing required configuration: tenant_id and client_id

Agent: "Still failing—let me check what's configured:"   ← UNAUTHORIZED
Agent: Read(~/src/academicOps/config/claude/mcp.json)    ← UNAUTHORIZED
Agent: "Found it—needs Azure AD credentials:"            ← UNAUTHORIZED
Agent: Web Search("outlook-mcp configuration setup")     ← UNAUTHORIZED
```

The user asked to "try again" - not to investigate config files, diagnose the problem, or search for solutions. Each subsequent action is ultra vires.

**Detection**: FAST pattern matching (no LLM needed):
- Tool returns error
- Next action is Read/WebSearch/Grep on infrastructure/config
- Original task was NOT about that infrastructure

**Intervention**: Immediate, blocking:
> "⚠️ You are about to investigate infrastructure that wasn't part of your task. The user asked you to 'try again with outlook' - not to debug configuration. Report the error and ask what the user wants to do."

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
1. Investigate login bug          ← AUTHORIZED
2. Fix the root cause             ← AUTHORIZED
3. Refactor authentication module ← UNAUTHORIZED
4. Add comprehensive tests        ← UNAUTHORIZED
5. Update documentation           ← UNAUTHORIZED
```

**Detection**: Semantic analysis via background subagent (compare todos to original request)

**Intervention**: Blocking before TodoWrite completes:
> "⚠️ Your plan includes work beyond the original request. Items 3-5 weren't requested. Revise your plan to only include authorized work, or ask the user if they want to expand scope."

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

## Relationship to Existing Components

| Component | Purpose | Relationship |
|-----------|---------|--------------|
| [[agent-behavior-watchdog]] | Catches mechanical violations (`--no-verify`, backup files) | Complementary - different concern |
| [[hypervisor]] | Creates authority envelope through planning | Upstream - defines what's authorized |
| [[/qa]] | Verifies "does it work" | Orthogonal - verifies outcomes not authority |
| [[specs/prompt-hydration]] | Enriches prompts with context | Upstream - surfaces relevant skills |

## Design

### Authority Envelope Model

At session start (or when user makes a request), extract:

| Component | Description | Example |
|-----------|-------------|---------|
| **Explicit scope** | What user directly asked for | "fix the login bug" |
| **Implied scope** | Reasonable necessities | reading login code, running tests |
| **Specified methods** | How user said to do it | "use the existing auth library" |
| **Constraints** | What user said NOT to do | "don't touch the database schema" |

The envelope defines **authorized territory**. Actions outside it are *ultra vires*.

### Detection Signals

| Signal | Indicates | Detection Method |
|--------|-----------|------------------|
| Todo growth | Scope expansion | Compare current todos to initial |
| New file creation | Work outside original scope | Check if files relate to request |
| "Also" / "additionally" | Scope creep language | Pattern match in agent output |
| Architectural changes | Method substitution | Detect changes to core patterns |
| Missing verification | Arbitrary confidence | Agent claims success without evidence |

### Enforcement Levels

Per existing framework graduated enforcement:

| Level | Action | When |
|-------|--------|------|
| 1. Log | Record observation | Minor drift, first occurrence |
| 2. Warn | Inject warning to agent | Clear drift from scope |
| 3. Checkpoint | Block until user confirms | Significant scope change |
| 4. Block | Halt execution | Obvious ultra vires action |

**Default**: Level 2 (Warn) - loud and forceful intervention on drift.

## Invocation Pathways

**Constraint**: Per [[HEURISTICS#H31]], hooks must never call LLM directly. Must spawn background subagent.

**Runtime estimate**: Spawning subagent + transcript analysis ≈ 10-40 seconds (haiku: ~10s, sonnet: ~30s).

### Empirical Data (from hook log analysis 2025-12-30)

Analysis of a 1.5-hour active session with subagent orchestration:

| Hook Event | Frequency | Data Available |
|------------|-----------|----------------|
| **PreToolUse** | ~122/session | `tool_name`, `tool_input`, `transcript_path` |
| **PreToolUse:TodoWrite** | ~10/session | Full todo list in `tool_input.todos` |
| **Stop** | ~10/session | `transcript_path` (full session) |
| **SubagentStop** | ~12/session (~8/hour) | `agent_transcript_path`, `agent_id` |
| **SessionStart** | 1/session | Initial context injection point |

**Key finding**: PreToolUse:TodoWrite provides the exact todo list being written, enabling direct comparison with original scope. SubagentStop provides full subagent transcript path for auditing delegated work.

### Options Analysis

| Pathway | Trigger | Blocking? | Frequency | Data Quality | Catches Drift... |
|---------|---------|-----------|-----------|--------------|------------------|
| **A. PreToolUse:TodoWrite** | Agent updates todos | Yes | ~10/session | Excellent - full todo list | At planning stage |
| **B. Stop** | Agent completes response | Optional | ~10/session | Good - transcript path | After action |
| **C. SubagentStop** | Subagent completes | Background | ~8/hour | Excellent - subagent transcript | In delegated work |
| **D. Periodic** | Every N tool calls | Background | Tunable | Requires state tracking | Over trajectory |
| **E. Semantic trigger** | Scope-expansion phrases | Background | Variable | Pattern-only (no LLM in hook) | At expansion moments |

### Recommended Architecture

Two-tier system matching the failure categories:

#### Tier 1: Type A Detection (background, triggered by errors)

| Hook | Trigger | Mode | Detection | Purpose |
|------|---------|------|-----------|---------|
| **PostToolUse** | Tool returns error | Background | Spawn subagent | Watch for reactive helpfulness |

**Trigger condition**: When a tool returns an error, spawn a background subagent to monitor subsequent actions.

**What the subagent watches for**:
- Agent reading config/infrastructure files
- Agent searching for "how to fix/configure X"
- Agent investigating infrastructure unrelated to original task
- Any action that goes beyond "report error, ask user"

**Why background is acceptable**:
- Intervention comes 10-30 seconds after the unauthorized action starts
- That's fast enough - user will see the warning before agent gets far
- Avoids complex pattern matching in hooks
- Same semantic analysis approach as Type B

**Frequency control**:
- Only trigger on tool errors (not every tool call)
- Errors are relatively rare - acceptable spawn rate
- Subagent is short-lived (quick check, then done)

#### Tier 2: Type B Detection (semantic, async)

| Hook | Trigger | Mode | Detection | Purpose |
|------|---------|------|-----------|---------|
| **PreToolUse:TodoWrite** | Todo list changes | **Blocking** | Spawn subagent | Catch scope expansion |
| **SubagentStop** | Subagent completes | Background | Spawn subagent | Audit delegated work |
| **Stop** | Agent response (sampled) | Background | Spawn subagent | Safety net |

**Semantic analysis** (requires LLM via background subagent):
- Compare todo items to original user request
- Identify items that weren't requested or implied
- Check subagent transcripts against delegated authority

**Why blocking for TodoWrite**: Catch scope expansion BEFORE work begins. Low frequency (~10/session) makes latency acceptable.

**Why background for others**: Higher frequency, post-hoc audit is sufficient.

### Architecture Summary

| Failure Type | Detection | Speed | Hook | Mode |
|--------------|-----------|-------|------|------|
| **Type A: Reactive helpfulness** | Semantic analysis | ~10-30s | PostToolUse (on error) | Background |
| **Type B: Scope expansion** | Semantic analysis | ~10-30s | PreToolUse:TodoWrite | Blocking |
| **Subagent audit** | Semantic analysis | ~10-30s | SubagentStop | Background |

**Unified approach**: All tiers use semantic analysis via background subagents. Differentiated by trigger conditions and frequency, not detection method.

## Design Decisions

1. **Todo growth detection**: **Semantic analysis only**. The custodiet must be smart - no mechanical count thresholds or keyword matching. The background subagent compares new todos semantically against the original user request to detect scope drift.

2. **State persistence**: The PreToolUse:TodoWrite hook provides `transcript_path` - the session transcript JSON log. The background subagent reads this to understand original request context. No separate state file needed.

## Open Questions

1. **Authority expansion**: When user legitimately expands scope, how is envelope updated? (Defer until it becomes a problem)
2. **Subagent authority delegation**: Does subagent inherit full authority envelope or narrower delegated scope?

## Implementation Phases

### Phase 1: MVP - Type A Detection (Primary Target)
- [ ] PostToolUse hook that triggers on tool errors
- [ ] Background subagent spawn on error detection
- [ ] Subagent reads transcript to understand original task
- [ ] Subagent monitors for unauthorized investigation actions
- [ ] Warning injection when reactive helpfulness detected

**Deliverable**: Catches the most common ultra vires behavior (reactive helpfulness) within ~10-30 seconds.

### Phase 2: Type B Detection
- [ ] PreToolUse:TodoWrite hook integration
- [ ] Background subagent spawn for semantic analysis
- [ ] Authority envelope extraction from user request
- [ ] Todo-to-request comparison logic
- [ ] Blocking intervention before TodoWrite completes

### Phase 3: Audit & Polish
- [ ] SubagentStop audit for delegated work
- [ ] Graduated enforcement levels (log/warn/checkpoint/block)
- [ ] Dashboard visibility into drift events
- [ ] User configuration for strictness
- [ ] Integration with existing behavior watchdog

## Acceptance Criteria

### Phase 1 (Type A)
1. When a tool fails and agent attempts to investigate infrastructure, intervention warns promptly (~10-30s)
2. Agent receives clear message explaining why the action is unauthorized
3. Agent is directed to report the error and ask user for direction
4. Warning arrives before agent can do significant unauthorized work

### Phase 2 (Type B)
5. When agent adds todos beyond original scope, user is warned before work proceeds
6. Semantic comparison catches non-obvious scope expansion (not just keyword matching)
7. False positive rate is low enough that warnings are actionable

### Phase 3 (Audit)
8. When subagent completes, its work is audited against delegated authority
9. Drift events are logged for pattern analysis
10. User can see what authority envelope was extracted from their request

## References

- [[AXIOMS]] #4 (Do One Thing)
- [[AXIOMS]] #22 (Acceptance Criteria Own Success)
- [[HEURISTICS#H31]] (No LLM Calls in Hooks)
- [[agent-behavior-watchdog]] (complementary mechanical violations spec)
