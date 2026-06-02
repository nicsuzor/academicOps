---
id: ultra-vires-enforcer
title: Ultra Vires Enforcer
type: spec
status: ready
tier: core
depends_on: [enforcement]
tags: [framework, agent-behavior, guardrails, enforcement, enforcer]
---

# Ultra Vires Enforcer

> **Spec, not state.** This file is the **design rationale** for the enforcer agent + PreToolUse gate (why ultra vires matters, failure categories, invocation points, output format). For the **operative runtime catalogue** of the enforcer gate (configuration paths, verification commands, debug procedures, custodiet→enforcer rename mapping) see [`specs/GATES.md#enforcer-gate`](../../specs/GATES.md#enforcer-gate). For the operative cost-ladder catalogue, see `specs/ENFORCEMENT-MAP.md`.

**Status**: Active — unified gate system implemented.
**Scope**: Narrow. This spec covers the specific internal mechanism at pipeline layer L4 / L7 of `specs/enforcement.md` — the `enforcer` agent (Haiku) and its PreToolUse gate. It is not the whole pyramid, and it is not a statement about enforcement in general. For the design statement, see `specs/enforcement.md`.

**Rename note**: This mechanism was previously called `custodiet`. The rename to `enforcer` is in progress (see §8 operator impact in `specs/enforcement.md`). Until files are updated, on-disk locations referenced below may still use the `custodiet` name — the mapping is one-for-one.

## Giving effect

- `aops-core/lib/gates/definitions.py` — gate definition (`enforcer` gate)
- `aops-core/hooks/gate_config.py` — threshold, mode, sibling env vars
- `aops-core/agents/enforcer.md` — Haiku agent that reads transcript and evaluates authority compliance
- `aops-core/agents/enforcer-reviewer.md` — async PR compliance review (formerly `custodiet-reviewer.md`)
- `aops-core/hooks/templates/enforcer-*.md` — context / instruction / countdown templates

## Purpose

Detect when agents act **ultra vires** — beyond the authority granted by the user's request.

The term is borrowed from public law: _ultra vires_ ("beyond powers") describes acts outside granted authority. The gate is the mechanical watcher; the agent (`enforcer`) is the reviewer.

**Scope — semantic, not mechanical.** This mechanism covers authority and method compliance: does the agent's activity match what the user asked for, and is the method compliant with framework axioms? **Mechanical violations** (`--no-verify`, destructive git, writes to forbidden paths) are handled by `policy_enforcer.py` at L5 and are explicitly NOT part of this mechanism.

**Scope compliance is necessary but not sufficient.** An action within scope can still be ultra vires if the execution method breaches axioms. An agent that mechanically maps input to output when judgment was warranted violates P#78 the same way regex for semantic decisions violates P#49. The enforcer checks both scope AND method.

## Failure categories

### Type A — reactive helpfulness

Agent encounters obstacle → immediately investigates or fixes without authorization.

Characteristics:

- Most common failure mode
- Happens in real-time, no planning or todos
- Agent "just trying to be helpful"
- Unplanned investigation of infrastructure

Example:

```
User: "try again with outlook?"
Agent: outlook — get-emails (MCP)
  → Error: Missing required configuration: tenant_id and client_id
Agent: "Still failing — let me check what's configured:"   ← UNAUTHORIZED
Agent: Read(config file)                                   ← UNAUTHORIZED
Agent: WebSearch("outlook-mcp configuration")              ← UNAUTHORIZED
```

### Type B — deliberate scope expansion

Agent consciously expands plan to include work beyond request (usually at TodoWrite / planning stage).

Example:

```
User: "fix the login bug"
Agent todos:
  1. Investigate login bug         ← AUTHORIZED
  2. Fix the root cause            ← AUTHORIZED
  3. Refactor auth module          ← UNAUTHORIZED
  4. Add comprehensive tests       ← UNAUTHORIZED
  5. Update documentation          ← UNAUTHORIZED
```

## Problem statement

**What manual work does this automate?** Without this mechanism, the user must continually monitor agent behaviour for drift. Wasted work and trust erosion compound: agent asked to "try again" starts debugging infrastructure; agent asked to "fix the bug" refactors the surrounding code; agent makes architectural decisions without consulting user; agent interprets ambiguous requirements in self-serving ways.

**Enforcement target.** Axiom P#4 (Do One Thing) and P#22 (Acceptance Criteria Own Success).

## User expectations

- **Visibility** — current gate status in the session icon strip (`◇` for overdue, `◇ N` for countdown).
- **Predictability** — compliance check triggers automatically at the configured threshold (default 50 write operations).
- **Non-interruption** — gate remains OPEN and non-blocking until the threshold, so focused work proceeds without constant interjection.
- **Actionable feedback** — on violation, a diagnostic message naming the specific axiom or heuristic and a correction.
- **Proportionate enforcement** — level (warn vs block) is configurable via `ENFORCER_GATE_MODE` env var; default is warn.
- **PR alignment** — the same principles are applied asynchronously to PRs by `enforcer-reviewer`, so local and remote use one rubric.

## Architecture

See `specs/gate-agent-architecture.md` for the unified gate system design. The enforcer is a **post-action gate** that enforces compliance after tool execution.

### Session state integration

The enforcer reads and updates the unified session state file (`/tmp/claude-session/state-{hash}.json`):

| Operation  | Fields                                                                 |
| ---------- | ---------------------------------------------------------------------- |
| **Reads**  | `declared_workflow`, `active_skill`, `intent_envelope` (from hydrator) |
| **Writes** | `last_compliance_ts`, `tool_calls_since_compliance` (reset on check)   |

The `intent_envelope` from hydration provides the authority baseline for drift detection.

### Authority envelope model

At session start (or per request), extract:

| Component             | Description                  | Example                           |
| --------------------- | ---------------------------- | --------------------------------- |
| **Explicit scope**    | What user directly asked for | "fix the login bug"               |
| **Implied scope**     | Reasonable necessities       | reading login code, running tests |
| **Specified methods** | How user said to do it       | "use the existing auth library"   |
| **Constraints**       | What user said NOT to do     | "don't touch the database schema" |

The envelope defines **authorised territory**. Actions outside it are _ultra vires_.

### Detection method — semantic analysis

Per H31 (no LLM calls in hooks), the hook cannot call an LLM directly. The enforcer spawns a **background Haiku subagent** that reads the session transcript and evaluates authority compliance.

What the subagent checks:

| Category            | Signal                   | Example                                     |
| ------------------- | ------------------------ | ------------------------------------------- |
| Axiom violation     | P#7 Fail-Fast            | Working around errors instead of halting    |
| Axiom violation     | P#17 Verify First        | Claims without checking actual state        |
| Axiom violation     | P#22 Acceptance Criteria | Modifying what "done" means                 |
| Heuristic violation | H3 Verification          | Claims without preceding Read/Bash          |
| Heuristic violation | H4 Explicit Instructions | Interpreting instead of following literally |
| Heuristic violation | H19 Questions            | Implementing when user asked a question     |
| Drift               | Plan deviation           | TodoWrite shows X, agent doing Y            |
| Drift               | Scope creep              | Work user didn't request                    |
| Method              | P#78 Right Tool          | Mechanical transform, judgment warranted    |
| Method              | P#49 No Shitty NLP       | Regex / keywords for semantic decisions     |

### Invocation points

| Hook                     | Trigger             | Mode       | Purpose                                           |
| ------------------------ | ------------------- | ---------- | ------------------------------------------------- |
| **PostToolUse**          | Tool returns error  | Background | Watch for Type A (reactive helpfulness) — planned |
| **PostToolUse**          | Every ~50 write ops | Background | Periodic compliance check — active                |
| **PreToolUse:TodoWrite** | Todo list changes   | Blocking   | Catch Type B (scope expansion) — planned          |
| **SubagentStop**         | Subagent completes  | Background | Audit delegated work — planned                    |

### Enforcement levels

| Level         | Action                    | When                          |
| ------------- | ------------------------- | ----------------------------- |
| 1. Log        | Record observation        | Minor drift, first occurrence |
| 2. Warn       | Inject warning to agent   | Clear drift from scope        |
| 3. Checkpoint | Block until user confirms | Significant scope change      |
| 4. Block      | Halt execution            | Obvious ultra vires action    |

**Default**: Level 2 (warn) — loud and forceful intervention without work stoppage.

## Relationship to the pyramid

Placing this mechanism in the pyramid (`specs/enforcement.md` §4):

- **Pipeline layer**: L4 (soft gate) for the gate itself; L7 (agent review) for the Haiku subagent it spawns.
- **Pyramid tier**: middle. It fires only at threshold or trigger, is non-blocking by default, and warns rather than halts.
- **Escalation**: the mechanism escalates to tip only when `ENFORCER_GATE_MODE=block` is set or the subagent detects an obvious ultra vires action (level 4).

Why middle, not base? A base-tier mechanism runs every action — the enforcer runs at a threshold and spawns a subagent, which is expensive. Why not tip? Because the default behaviour is warn, not block; users can operate past it.

## Output format

### OK

```markdown
## Compliance check: OK
```

### WARN

```markdown
## Compliance check: WARN

**Issue**: [one-sentence description]
**Principle**: [axiom/heuristic number and name]
**Evidence**: [short quote or reference]
**Correction**: [what to do instead]
```

### BLOCK

Use BLOCK only when the violation is clear and the correction is non-negotiable.

```markdown
## Compliance check: BLOCK

**Issue**: [one-sentence description]
**Principle**: [axiom/heuristic number and name]
**Evidence**: [short quote or reference]
**Required action**: [what MUST happen before continuing]
```

## Implementation evolution

- **Original**: `custodiet_gate.py` (archived) — standalone hook, pre-unified gate system.
- **Transitional**: `overdue_enforcement.py` (archived) — interim consolidation.
- **Current**: unified `enforcer` gate in `aops-core/lib/gates/definitions.py`.

Moving the logic into the unified gate architecture gave lifecycle management, icons in the icon strip, and JIT gate opening for compliance agents.

### Implementation phases

**Phase 1: periodic compliance (IMPLEMENTED)**

- [x] Unified `enforcer` gate tracks tool count
- [x] Spawns Haiku subagent at threshold
- [x] Subagent reads transcript via temp file
- [x] Checks axioms / heuristics / drift
- [x] Uses `deny` (block) or `warn` mode via `ENFORCER_GATE_MODE` env var
- [x] Visual feedback in icon strip (`◇`)

**Phase 2: error-triggered detection (PLANNED)**

- [ ] PostToolUse detects tool errors
- [ ] Spawns subagent to watch for reactive helpfulness (Type A)
- [ ] Warns if agent investigates infrastructure without permission

**Phase 3: TodoWrite scope gate (PLANNED)**

- [ ] PreToolUse:TodoWrite hook
- [ ] Blocking semantic analysis of new todos
- [ ] Compares against original user request
- [ ] Warns if scope expanded without authorisation

**Phase 4: subagent audit (PLANNED)**

- [ ] SubagentStop hook
- [ ] Audits delegated work against granted authority
- [ ] Logs drift events for pattern analysis

## Known gaps

- **Threshold is hard-coded** (50). No per-task adjustment; a long, complex task gets the same budget as a trivial one.
- **Subagent bypass** — subagents inherit the parent gate state; a subagent spawned just before the threshold may avoid a check entirely.
- **PostToolUse absence** — no audit of what a Read actually consumed, so "unnecessary read" drift is not caught.
- **Gate directs to subagent name** — historically the instruction pointed to `aops-core:custodiet`; this mechanism's rename to `enforcer` is the fix. Until templates are updated, the directive may reference a non-existent subagent name.

## Acceptance criteria

1. When the agent drifts from the original request, the warning trips.
2. The agent receives a clear message naming the violation.
3. The agent is directed to report issues and ask the user for direction.
4. TodoWrite scope expansion is caught BEFORE work begins (Phase 3).
5. False-positive rate is low enough that warnings are actionable.

## Relationship to Claude Code auto mode (2026-03)

Claude Code's [auto mode classifier](https://www.anthropic.com/engineering/claude-code-auto-mode) is a Sonnet 4.6 agent that reads the proposed tool call **alongside the conversation transcript and the rules expressed as prose**, then decides whether to allow, surface a permission prompt, or block. It is not a regex matcher and it is not limited to a single tool call's local arguments — explicit user intent in prior turns can override default rules, and stated boundaries in the conversation ("don't push", "wait until I review") become block signals the classifier observes.

In framework terms: the classifier is **rbg-class judgment running at the per-action gate** — fast, transcript-aware, prose-reasoning. Treat it as a peer reviewer, not a pattern matcher.

| Aspect       | CC auto mode classifier                                               | Enforcer subagent                                          |
| ------------ | --------------------------------------------------------------------- | ---------------------------------------------------------- |
| Trigger      | Every tool call (pre-execution)                                       | Threshold (~50 writes) or explicit invocation              |
| Context      | Proposed action + conversation transcript + prose rules               | Full session transcript + axioms / heuristics              |
| Verdict      | Allow / permission-prompt / block — surfaced to user before execution | OK / WARN / BLOCK injected back into the agent's context   |
| Latency cost | Negligible (already in the path)                                      | Subagent spawn — non-trivial, hence threshold-gated        |
| Platform     | Claude Code only                                                      | Claude Code + Gemini                                       |
| Memory       | Stateless across calls — re-reads transcript each time                | Writes `last_compliance_ts`, runs trend across the session |

**Why both still exist.** They overlap in capability — both can judge prose, both see the transcript. They differ in **where they sit in the loop**:

- The classifier is a **gate at the action**: cheap, surfaces to the user before the action runs, and is bound to CC's permission UI. Good fit for actions where pre-execution intervention beats post-hoc warning.
- The enforcer is a **review at the threshold**: deliberately invoked, writes a verdict back into the agent's working context, and runs across CC and Gemini. Good fit for the "is this whole session still on track?" review where catching drift in the agent's next move matters more than blocking the current tool call.

**Practical implications for rule design.**

1. Write `autoMode.soft_deny` (and `allow`) rules as **prose stating the principle and the reasoning**, not as rule-ID lookups or keyword patterns. The classifier reads them as natural language and applies judgment; a rule that just names "P#5" is wasted ink.
2. Do not exclude rules from auto mode on the grounds that they are "session-level" or "judgment-heavy". The classifier has the transcript and is judgment-capable. Exclude only when the rule is genuinely better caught downstream (e.g. integration tests catch what a pre-execution gate cannot observe).
3. State limits and exceptions in prose so the classifier can apply them. ("Allow `--force` when validating; block `--force` when bypassing tests" — written as prose, the classifier handles the disjunction. Written as a keyword match, it cannot.)
4. Enforcer remains valuable for verdicts the framework itself needs to **read and act on** (writing to the session-state file, feeding `/learn`, surfacing in the icon strip). The classifier's verdict goes to the user, not to the agent's tool stack.

See `aops-core/.claude-plugin/plugin.json` (`autoMode` key) for the rule set and `aops-core/lib/automode.py` for installation (invoked via `scripts/install.py`). The rules are written as prose stating the axiom (by slug), the reasoning, and the kinds of action that count as a violation, with explicit carve-outs where they apply.

## References

- `.agents/rules/AXIOMS.md` — P#4 (Do One Thing), P#22 (Acceptance Criteria Own Success), P#7 (Fail-Fast), P#17 (Verify First), P#49 (No Shitty NLP), P#78 (Right Tool)
- `.agents/rules/HEURISTICS.md` — H31 (No LLM Calls in Hooks)
- `specs/enforcement.md` — design statement
- `specs/ENFORCEMENT-MAP.md` — operative state catalogue (SSoT; redirect stub remains at `specs/enforcement/enforcement-map.md`)
- `specs/enforcement-mechanisms.md` — per-mechanism catalogue
- [CC Auto Mode engineering post](https://www.anthropic.com/engineering/claude-code-auto-mode)
