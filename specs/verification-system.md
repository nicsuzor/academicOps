---
title: Verification System Architecture
type: spec
status: draft
tier: core
depends_on: [enforcement]
tags: [verification, enforcement, architecture, infrastructure]
---

# Verification System Architecture

**Status**: Design Decision (2026-01-15)
**Priority**: P1 Infrastructure Gap

## Giving Effect

- [[agents/custodiet.md]] - Periodic compliance checking (Layer 2.5)
- [[AXIOMS.md]] - P#26 Verify First principle definition (Layer 1)
- [[HEURISTICS.md]] - H3 Verification heuristic
- [[specs/enforcement.md]] - Enforcement architecture defining evidence types

_Note: This is a design spec. Phase 1 (Independent QA Agent) is implemented as `aops-core:qa`._

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

### Option B: Layer 5 Independent QA Agent

**Mechanism:** Dedicated subagent reviews conclusions with actual-state verification.

**Workflow:**

1. Agent completes work, presents conclusion
2. `/qa` agent invoked (automatically or by user)
3. QA reads actual files/configs to verify claims
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
**Layer 5:** QA agent for conclusions/claims

**Trigger logic:**

```
PostToolUse: If agent says "complete" or "success" without verification tools → inject reminder
Stop hook: Offer qa review when session ends
```

**Pros:**

- Defense in depth (catches different failure modes)
- Escalation path (Layer 4 reminder → Layer 5 verification)
- Cost-effective (only invoke qa when needed)

**Cons:**

- Implementation complexity (two systems to maintain)
- Coordination overhead (when does Layer 4 defer to Layer 5?)

## Decision: Hybrid Approach (Recommended)

**Rationale:**

1. **No single layer is reliable** (P#enforcement-architecture) - defense in depth required
2. **Layer 4 catches obvious violations cheaply** - "success" without evidence gathering
3. **Layer 5 provides ground truth** - qa agent verifies actual state
4. **Gradual enforcement** - reminder before blocking, verification before accepting

### Implementation Phases

#### Phase 1: Layer 5 Independent QA Agent (Foundation)

Build the reliable verification mechanism first.

**Components:**

- `aops-core/agents/qa.md` - Skeptical verification agent (Active)
- Tools: Read, Bash, Grep (can check actual state)
- Model: Opus (needs strong reasoning for verification)
- Invocation: Manual first (`Task(subagent_type="qa")`)

**Workflow:**

```
User: "Verify this conclusion: [agent's claim]"
QA:
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

#### Phase 4: Automatic QA Invocation (Optional)

Automate verification review.

**Hook:** Stop hook offers qa review
**Trigger:** Session ending after qa-proof or verification-required workflow
**Action:** "Run qa verification? [Y/n]"

**Why Phase 4:** Reduces friction. Only pursue if manual invocation proves valuable.

## User Expectations

The Verification System ensures the epistemic integrity of the framework by replacing mechanical checklists with LLM-driven qualitative judgment. Users should expect the following:

### 1. High-Stakes Skepticism (Active)

- **Independent QA**: When a session reaches a "verification required" gate, the `qa` subagent (`aops-core:qa`) will be invoked. This agent provides a skeptical, independent perspective, treating the main agent's claims as hypotheses to be tested against ground truth.
- **Evidence-First Verdicts**: The system will not accept "looks correct" as a verdict. Verification must be grounded in `actual_state` evidence: terminal output, test results, or direct file reads.

### 2. Guarding Original Intent (Active)

- **Anti-Sycophancy**: The QA layer protects against "goalpost shifting." It verifies work against the user's _original_ request verbatim, catching cases where an agent has simplified the task to make it easier to complete.
- **Intent vs. Compliance**: Success is measured by whether the user's need was met, not whether a specific technical procedure was followed.

### 3. Proactive Evidence Gathering (Active)

- **Verify First (P#26)**: Users should expect agents to explore the existing state before proposing changes. Observations (Read/Bash/Grep) must precede assertions.
- **No Silent Failures (P#8)**: If verification tools fail or produce ambiguous output, agents are expected to HALT and report the uncertainty rather than guessing.

### 4. Automated Verification Loop (Aspirational)

- **Layer 4 Nudges**: Users will eventually receive real-time reminders if they attempt to claim "success" or "completion" without having first demonstrated evidence.
- **Continuous Compliance**: Periodic background checks by `custodiet` ensure that the session hasn't drifted away from its original verification goals.

## Success Criteria

**Measurable outcomes:**

1. **Reduction in unverified claims** - Tracked via custodiet detections
2. **User confidence** - Can trust agent conclusions without manual checking
3. **Agent learning** - Agents internalize verification patterns from qa feedback

**Validation:**

- Track verification tool usage before claims (Bash/Read/Grep before "success")
- Measure qa VERIFIED vs QUESTIONABLE rate
- Monitor custodiet P#26 violation detections (should decrease)

## Non-Goals

**Not implementing:**

- Blocking hooks (too many false positives)
- Keyword-based verification detection (fragile, Volkswagen-prone)
- Verification for every statement (only claims requiring evidence)

## Open Questions

1. **QA invocation cost** - Is Opus per verification sustainable? (Measure in Phase 1)
2. **Trigger granularity** - Which conclusions require qa vs self-verification?
3. **False reminder rate** - Will Phase 3 hook create reminder fatigue? (Measure in Phase 3)

## References

- [[enforcement]] - Enforcement architecture layers
- [[AXIOMS.md]] - P#26 Verify First
- [[RULES]] - verification-before-assertion enforcement
- [[critic]] - Existing review agent (plan review, not state verification)

## Revision History

- 2026-01-15: Initial design decision (worker agent aops-8zyt)
