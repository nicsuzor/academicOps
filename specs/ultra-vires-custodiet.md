---
title: Ultra Vires Custodiet
type: spec
status: migrated
tier: core
depends_on: [enforcement]
tags: [framework, agent-behavior, guardrails, enforcement, auto-mode]
---

# Ultra Vires Custodiet

**Status**: Migrated to Claude Code auto mode classifier
**Current**: Automated axiom enforcement via CC `autoMode.soft_deny` rules; custodiet agent retained for manual invocation
**Archived**: In-process custodiet gate (gate engine, templates, compliance report action)

## Giving Effect

- [[aops-core/config/automode-rules.json]] - Canonical aops-specific auto mode rules (soft_deny, allow, environment)
- [[scripts/setup-automode.sh]] - Merges aops rules with CC defaults into user settings
- [[agents/custodiet.md]] - Haiku agent for manual full-narrative compliance review
- CC auto mode classifier (Sonnet 4.6 two-stage pipeline) - evaluates every tool call

## Purpose

Detect when agents act **ultra vires** - beyond the authority granted by the user's request.

The name draws from public law: "ultra vires" (beyond powers) describes acts outside granted authority. The watchdog is the _custodiet_ - the guardian that watches.

**Scope**: This spec covers **semantic authority enforcement** - understanding whether an agent's actions align with the user's intent. Pattern-based mechanical violations (`--no-verify`, backup files, destructive git) are handled by mechanical hooks and are NOT part of custodiet.

**Scope compliance is necessary but not sufficient.** An action within the user's requested scope can still be ultra vires if the execution method breaches framework axioms. An agent that mechanically maps input to output without applying judgment — when judgment was warranted — violates P#78 the same way regex for semantic decisions violates P#49. Custodiet checks both scope AND method compliance.

## Operation

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
Agent: Read(~/src/academicOps/aops-tools/config/claude/mcp.json)    <- UNAUTHORIZED
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

See [[specs/gate-agent-architecture]] for the unified gate system design. Custodiet is a **post-action gate** that enforces compliance after tool execution.

### Session State Integration

Custodiet reads and updates the unified session state file (`/tmp/claude-session/state-{hash}.json`):

| Operation  | Fields                                                                 |
| ---------- | ---------------------------------------------------------------------- |
| **Reads**  | `declared_workflow`, `active_skill`, `intent_envelope` (from hydrator) |
| **Writes** | `last_compliance_ts`, `tool_calls_since_compliance` (reset on check)   |

The `intent_envelope` from hydration provides the authority baseline for drift detection.

### Authority Envelope Model

At session start (or when user makes a request), extract:

| Component             | Description                  | Example                           |
| --------------------- | ---------------------------- | --------------------------------- |
| **Explicit scope**    | What user directly asked for | "fix the login bug"               |
| **Implied scope**     | Reasonable necessities       | reading login code, running tests |
| **Specified methods** | How user said to do it       | "use the existing auth library"   |
| **Constraints**       | What user said NOT to do     | "don't touch the database schema" |

The envelope defines **authorized territory**. Actions outside it are _ultra vires_.

### Detection Method: Semantic Analysis

Per [[HEURISTICS#H31]] (No LLM Calls in Hooks), hooks cannot call LLMs directly. Custodiet spawns a **background subagent** (haiku) that reads the session transcript and evaluates authority compliance.

**What the subagent checks**:

| Category             | Signal                   | Example                                     |
| -------------------- | ------------------------ | ------------------------------------------- |
| Axiom violations     | #7 Fail-Fast             | Working around errors instead of halting    |
| Axiom violations     | #17 Verify First         | Claims without checking actual state        |
| Axiom violations     | #22 Acceptance Criteria  | Modifying what "done" means                 |
| Heuristic violations | H3 Verification          | Claims without preceding Read/Bash          |
| Heuristic violations | H4 Explicit Instructions | Interpreting instead of following literally |
| Heuristic violations | H19 Questions            | Implementing when user asked a question     |
| Drift patterns       | Plan deviation           | TodoWrite shows X, agent doing Y            |
| Drift patterns       | Scope creep              | Work user didn't request                    |
| Method compliance    | P#78 Right Tool          | Mechanical transform, judgment warranted    |
| Method compliance    | P#49 No Shitty NLP       | Regex/keywords, semantics needed            |

### Invocation Points

| Hook                     | Trigger             | Mode       | Purpose                                 |
| ------------------------ | ------------------- | ---------- | --------------------------------------- |
| **PostToolUse**          | Tool returns error  | Background | Watch for Type A (reactive helpfulness) |
| **PostToolUse**          | Every ~7 tool calls | Background | Periodic compliance check               |
| **PreToolUse:TodoWrite** | Todo list changes   | Blocking   | Catch Type B (scope expansion)          |
| **SubagentStop**         | Subagent completes  | Background | Audit delegated work                    |

### Enforcement Levels

Per existing framework graduated enforcement:

| Level         | Action                    | When                          |
| ------------- | ------------------------- | ----------------------------- |
| 1. Log        | Record observation        | Minor drift, first occurrence |
| 2. Warn       | Inject warning to agent   | Clear drift from scope        |
| 3. Checkpoint | Block until user confirms | Significant scope change      |
| 4. Block      | Halt execution            | Obvious ultra vires action    |

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

## Implementation

### Current State

- `hooks/overdue_enforcement.py` - PostToolUse hook, triggers every N tool calls
- `hooks/data/reminders.txt` - Soft-tissue file with editable reminder lines
- `agents/custodiet.md` - Haiku agent that reads transcript
- `hooks/templates/custodiet-context.j2` - Jinja2 context template (conditional axiom/heuristic injection)
- `hooks/templates/custodiet-instruction.md` - Short instruction template

### Implementation Evolution

**Original**: `custodiet_gate.py` (archived)
**Current**: `overdue_enforcement.py`

The hook was renamed to better reflect its purpose: enforcing overdue compliance checks rather than acting as a "gate". The core functionality remains identical—periodic spawning of the custodiet agent to check for axiom/heuristic violations and plan drift.

**What changed**: File name and semantic clarity
**What didn't change**: Logic, thresholds, output formats, agent integration

### Hook Output Formats

**Critical**: PostToolUse hooks have two output modes with different behavior:

| Format                                                 | Behavior                             | Use Case             |
| ------------------------------------------------------ | ------------------------------------ | -------------------- |
| `{"decision": "block", "reason": "..."}`               | **Active** - forces agent to address | Full custodiet check |
| `{"hookSpecificOutput": {"additionalContext": "..."}}` | **Passive** - agent may ignore       | Light reminders      |

The custodiet hook uses `decision: "block"` at threshold to ensure the agent spawns the compliance subagent.

### Random Reminder Injection

Between threshold checks, the hook randomly injects soft reminders:

| Parameter              | Value          | Location                   |
| ---------------------- | -------------- | -------------------------- |
| `TOOL_CALL_THRESHOLD`  | 7              | `overdue_enforcement.py`   |
| `REMINDER_PROBABILITY` | 0.0 (disabled) | `overdue_enforcement.py`   |
| Reminder lines         | Editable       | `hooks/data/reminders.txt` |

**Behavior**:

- Tool calls 1 to (N-1): Random reminder with 30% probability (passive)
- Tool call N (threshold): Full custodiet check (blocking)

Edit `hooks/data/reminders.txt` to add/modify reminders. One per line, `#` for comments.

### Implementation Phases

#### Phase 1: Periodic Compliance (IMPLEMENTED)

- [x] PostToolUse hook tracks tool count
- [x] Spawns haiku subagent at threshold
- [x] Subagent reads transcript via temp file
- [x] Checks axioms/heuristics/drift
- [x] Uses `decision: "block"` output format
- [x] Random reminder injection between checks

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

1. When agent drifts from original request, warning trips
2. Agent receives clear message explaining the violation
3. Agent directed to report issues and ask user for direction
4. TodoWrite scope expansion caught BEFORE work begins
5. False positive rate low enough that warnings are actionable

## Migration to CC Auto Mode (2026-03)

The in-process custodiet gate was replaced by Claude Code's auto mode classifier. See [engineering blog post](https://www.anthropic.com/engineering/claude-code-auto-mode).

### Why

| Aspect            | Custodiet gate               | CC auto mode                           |
| ----------------- | ---------------------------- | -------------------------------------- |
| Classifier        | Haiku subagent every ~50 ops | Sonnet 4.6, every tool call, two-stage |
| Latency           | ~2-5s (subagent spawn)       | <1s (prompt-cached)                    |
| Prompt injection  | Not defended                 | Input probe + output classifier        |
| Subagent coverage | Main session only            | Recursive (subagent delegation too)    |
| Maintenance       | ~1500 LOC Python             | JSON settings file                     |

### What Was Removed

- Custodiet `GateConfig` from `lib/gates/definitions.py`
- `CUSTODIET_GATE_MODE`, `CUSTODIET_TOOL_CALL_THRESHOLD` from `gate_config.py`
- Custodiet entries from `COMPLIANCE_SUBAGENT_TYPES` and `SPAWN_TOOLS`
- 7 custodiet template files (`hooks/templates/custodiet-*.md`)
- `prepare_compliance_report` custom action
- Custodiet countdown/status display in router

### What Was Kept

- Custodiet agent (`agents/custodiet.md`) — available for manual invocation
- QA and handover gates — session lifecycle enforcement (auto mode has no equivalent)
- Policy enforcer — mechanical pattern blocking (belt-and-suspenders)
- Gate engine, types, registry — still used by QA/handover

### Enforcement Downgrades

Some enforcement that relied on full-narrative review downgraded to Prompt level:

- Plan deviation detection (custodiet compared TodoWrite to actual actions)
- Verification-before-assertion (custodiet checked for Read/Bash before claims)
- Session-level scope creep (custodiet tracked drift across multiple actions)

The auto mode classifier evaluates each action independently with user messages + tool commands only (assistant text stripped). This is a deliberate design choice — prevents the agent from "talking the classifier into" bad decisions.

### Gemini-CLI Polecat Gap

**Decision (2026-03):** CC auto mode is Claude Code-only. Gemini polecat workers have no equivalent per-action semantic classifier.

Remaining enforcement for Gemini sessions:

| Layer | Mechanism | Applies to Gemini? |
|-------|-----------|-------------------|
| Mechanical | policy_enforcer.py (pattern blocking) | Yes |
| Mechanical | Handover and QA gates | Yes |
| Prompt | AXIOMS.md, HEURISTICS.md via SessionStart | Yes |
| Semantic | CC auto mode soft_deny classifier | **No** |

**Rationale for accepting the gap:** Polecat workers execute narrow, well-defined tasks with explicit acceptance criteria. The risk profile is lower than open-ended sessions. The custodiet agent remains available for manual invocation if needed (`agents/custodiet.md`).

**Remediation path:** If Gemini CLI ships an equivalent pre-action classifier, apply the same `automode-rules.json` rule set. Until then, the gap is documented and accepted.

## References

- [[AXIOMS]] #4 (Do One Thing)
- [[AXIOMS]] #22 (Acceptance Criteria Own Success)
- [[enforcement-map.md]] (Enforcement registry)
- [CC Auto Mode engineering post](https://www.anthropic.com/engineering/claude-code-auto-mode)
- [CC Auto Mode docs](https://code.claude.com/docs/en/permissions#configure-the-auto-mode-classifier)
