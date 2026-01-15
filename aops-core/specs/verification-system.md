---
title: Verification System Architecture
type: spec
category: spec
status: decided
permalink: verification-system
tags: [verification, enforcement, architecture, infrastructure]
---

# Verification System Architecture

**Status**: Design Decision (2026-01-15)
**Priority**: P1 Infrastructure Gap

## Problem Statement

Agents frequently violate **P#26 (Verify First)** by claiming success without verification. This is the **top failure pattern** in the framework:

**Common violations:**
- "Should work" / "probably works" without checking
- Claiming configuration is X without reading files
- Assuming feature is enabled without verification
- Conflating capability ("can it") with actual state ("does it")

**Current enforcement:** Weak. Layer 1 (AXIOMS.md) + Layer 2.5 (custodiet periodic checks) are insufficient.

## Evidence Categories

From enforcement.md, agents need to distinguish:

| Type              | Definition                                | Valid? |
| ----------------- | ----------------------------------------- | ------ |
| `actual_state`    | Config files read, runtime output checked | ✅     |
| `default_only`    | Only framework defaults checked           | ❌     |
| `capability_only` | Only documented capabilities checked      | ❌     |
| `none`            | No evidence gathered                      | ❌     |

## Design Options Considered

### Option A: Layer 4 Detection Hook (PostToolUse)

**Mechanism:** Hook detects claims without preceding verification tools.

**Detection logic:**
```python
if claim_pattern(agent_output) and not recent_verification_tools():
    return "BLOCK: Must verify before claiming"
```

**Pros:**
- Preventive (catches violations before user sees them)
- Mechanical (no LLM cost per check)
- Fast (pattern matching)

**Cons:**
- Imperfect detection (can't parse natural language claims reliably)
- Can't distinguish "I will verify" from "I verified"
- False positives (blocks legitimate conclusions)
- False negatives (misses subtle claims)
- Adds latency to every tool use

**Enforcement strength:** Medium-Strong (Level 4 on enforcement ladder)

### Option B: Layer 5 Advocate Agent

**Mechanism:** Dedicated subagent reviews conclusions with actual-state verification.

**Workflow:**
1. Agent completes work, presents conclusion
2. `/advocate` agent invoked (automatically or by user)
3. Advocate reads actual files/configs to verify claims
4. Returns VERIFIED / QUESTIONABLE / FALSE with evidence

**Pros:**
- Most reliable (separate invocation, fresh context, skeptical stance)
- Can verify actual state (has Read/Bash/Grep tools)
- No false positives (only activates when reviewing conclusions)
- Educates agents (shows what verification looks like)

**Cons:**
- Reactive (damage may already be done)
- Cost (Opus subagent per review)
- Latency (user must wait for review)
- Requires trigger mechanism (when to invoke?)

**Enforcement strength:** Strong (Level 5 on enforcement ladder)

### Option C: Hybrid Approach

**Layer 4:** Lightweight detection for obvious violations (no verification tools used)
**Layer 5:** Advocate agent for conclusions/claims

**Trigger logic:**
```
PostToolUse: If agent says "complete" or "success" without verification tools → inject reminder
Stop hook: Offer advocate review when session ends
```

**Pros:**
- Defense in depth (catches different failure modes)
- Escalation path (Layer 4 reminder → Layer 5 verification)
- Cost-effective (only invoke advocate when needed)

**Cons:**
- Implementation complexity (two systems to maintain)
- Coordination overhead (when does Layer 4 defer to Layer 5?)

## Decision: Hybrid Approach (Recommended)

**Rationale:**

1. **No single layer is reliable** (P#enforcement-architecture) - defense in depth required
2. **Layer 4 catches obvious violations cheaply** - "success" without evidence gathering
3. **Layer 5 provides ground truth** - advocate agent verifies actual state
4. **Gradual enforcement** - reminder before blocking, verification before accepting

### Implementation Phases

#### Phase 1: Layer 5 Advocate Agent (Foundation)

Build the reliable verification mechanism first.

**Components:**
- `aops-core/agents/advocate.md` - Skeptical verification agent
- Tools: Read, Bash, Grep (can check actual state)
- Model: Opus (needs strong reasoning for verification)
- Invocation: Manual first (`Task(subagent_type="advocate")`)

**Workflow:**
```
User: "Verify this conclusion: [agent's claim]"
Advocate:
  1. Identify claims requiring verification
  2. Gather evidence (Read configs, Bash commands, Grep patterns)
  3. Compare claim vs actual state
  4. Return verdict with evidence
```

**Why Phase 1:** Provides the ground truth mechanism. Can be used immediately even without automation.

#### Phase 2: TodoWrite Integration (Observable Checkpoint)

Make verification a trackable step.

**Mechanism:**
- Prompt hydrator suggests verification todo for qa-proof workflows
- TodoWrite includes: `{content: "Verify [claim] by checking [file/output]", ...}`
- Creates paper trail of intended verification

**Why Phase 2:** Layer 3 (Observable) creates artifacts user can review. Low-cost, high-visibility.

#### Phase 3: Layer 4 Detection Hook (Automated Reminder)

Detect missing verification and inject reminder.

**Hook:** `hooks/verification_reminder.py` on PostToolUse
**Trigger:** Agent output contains claim keywords ("complete", "success", "configured") without recent verification tools
**Action:** Inject reminder: "**REMINDER**: P#26 Verify First - check actual state before claiming"

**Why Phase 3:** Preventive nudge. Doesn't block (avoids false positives) but raises salience.

#### Phase 4: Automatic Advocate Invocation (Optional)

Automate verification review.

**Hook:** Stop hook offers advocate review
**Trigger:** Session ending after qa-proof or verification-required workflow
**Action:** "Run advocate verification? [Y/n]"

**Why Phase 4:** Reduces friction. Only pursue if manual invocation proves valuable.

## Success Criteria

**Measurable outcomes:**
1. **Reduction in unverified claims** - Tracked via custodiet detections
2. **User confidence** - Can trust agent conclusions without manual checking
3. **Agent learning** - Agents internalize verification patterns from advocate feedback

**Validation:**
- Track verification tool usage before claims (Bash/Read/Grep before "success")
- Measure advocate VERIFIED vs QUESTIONABLE rate
- Monitor custodiet P#26 violation detections (should decrease)

## Non-Goals

**Not implementing:**
- Blocking hooks (too many false positives)
- Keyword-based verification detection (fragile, Volkswagen-prone)
- Verification for every statement (only claims requiring evidence)

## Open Questions

1. **Advocate invocation cost** - Is Opus per verification sustainable? (Measure in Phase 1)
2. **Trigger granularity** - Which conclusions require advocate vs self-verification?
3. **False reminder rate** - Will Phase 3 hook create reminder fatigue? (Measure in Phase 3)

## References

- [[enforcement]] - Enforcement architecture layers
- [[AXIOMS.md]] - P#26 Verify First
- [[RULES]] - verification-before-assertion enforcement
- [[critic]] - Existing review agent (plan review, not state verification)

## Revision History

- 2026-01-15: Initial design decision (worker agent aops-8zyt)
