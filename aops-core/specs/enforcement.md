---
title: Enforcement Architecture
type: spec
category: spec
status: implemented
permalink: enforcement
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

**Status**: Implemented (core concepts active)

## Enforcement Model

```mermaid
graph TD
    subgraph "Layer 1: Prompts"
        A[AXIOMS.md]
        B[Agent .md]
    end

    subgraph "Layer 2: Intent Router"
        D[Classify Prompt]
        E[Inject Guidance]
    end

    subgraph "Layer 3: Observable"
        F[TodoWrite]
        G[Plan Mode]
    end

    subgraph "Layer 4: Detection"
        H[PostToolUse Hooks]
    end

    subgraph "Layer 5: Review"
        I[advocate]
        J[Critic Agent]
    end

    subgraph "Layer 6: User"
        K[Show Evidence Request]
    end

    A --> D
    D --> E
    E --> F
    F --> H
    H --> I
    I --> K
```

**Purpose**: Architectural philosophy for why enforcement works the way it does. For practical mechanism selection, see [[ENFORCEMENT|docs/ENFORCEMENT.md]]. For current active rules, see [[RULES]].

How the aops framework influences agent behavior. We cannot force compliance - only create encouragement with detection.

## The Hard Truth

**We cannot force agent behavior.** Claude Code has no mechanism to prevent an agent from skipping steps. Any "enforcement" is actually "encouragement with detection."

**But prompt injection IS enforcement.** "Soft" doesn't mean "not real." Prompt-level rules (Level 1 in the enforcement ladder) are the most common enforcement mechanism - 43 rules use this level. When we say a rule is "enforced via FRAMEWORK.md injection at SessionStart," that IS the enforcement. Don't dismiss it as "no enforcement" just because there's no blocking hook.

**The knowing-doing gap**: Agents read AXIOMS, understand them, and still skip steps due to:

- Efficiency pressure (verification takes tokens)
- Confidence from pattern-matching
- No immediate consequence
- Helpful instinct to appear competent

## Layer Defense Model

No single layer is reliable. We combine:

### Layer 1: Prompts (Instruction Surface)

| Location  | Loaded When   | Scope         |
| --------- | ------------- | ------------- |
| AXIOMS.md | Session start | Universal     |
| Agent .md | Agent spawned | Task-specific |

**Limitation**: Agents can read and ignore.

### Layer 2: Prompt Hydration (Soft Gate)

The [[specs/prompt-hydration]] process classifies prompts and suggests workflows.

**What it does**: Injects context, classification, and task-specific guidance
**What it can't do**: Force agent to follow guidance

### Layer 2.5: JIT Compliance Audit

Haiku-based compliance checking at strategic checkpoints. Uses same temp-file pattern as prompt hydration.

#### User Intervention Priority

On every `UserPromptSubmit`, the instruction includes:

> If this prompt is a correction, suggestion, or redirection from the user while you were working on something else: **HALT your current work immediately**.

This addresses the "steamroller" pattern where agents continue planned work instead of responding to user corrections.

#### Periodic Compliance Check

On `PostToolUse` (every ~7 tool calls), spawns custodiet subagent to check:

- Axiom violations (#7 Fail-Fast, #17 Verify First, #22 Acceptance Criteria)
- Heuristic violations (H3 Verification, H4 Explicit Instructions, H19 Questions)
- Plan drift (doing something different from TodoWrite plan)

**Implementation**: `hooks/custodiet_gate.py` tracks tool count in `/tmp/claude-compliance/state.json`, emits audit instruction when threshold reached.

**What it does**: Catches drift and violations mid-execution before user has to intervene
**What it can't do**: Force agent to follow corrections (still relies on agent compliance)

#### Dormant: Random Reminders

**Status**: Disabled (REMINDER_PROBABILITY = 0.0)

The custodiet gate has a dormant random reminder injection mechanism that can inject reminders from `hooks/data/reminders.txt` at 30% probability between threshold checks.

**Rationale for dormancy**: Enforcement should be high-signal, low-noise. Injecting reminders without evidence of agents forgetting instructions adds friction without demonstrated benefit.

**Activation criteria**: Enable when behavioral data shows agents forgetting specific instructions mid-session. The mechanism is preserved in code (set `REMINDER_PROBABILITY = 0.3` in `custodiet_gate.py`) for rapid deployment when evidence justifies it.

### Layer 3: Observable Checkpoints

TodoWrite and Plan Mode create visible artifacts user can review.

**What this enables**: User sees if verification steps exist, creates paper trail
**Limitation**: Agent can skip entirely

### Layer 4: Detection Hooks

PostToolUse hooks can detect patterns:

- Claims without preceding Read/Bash/Grep
- Diagnosis without evidence-gathering tools

**Limitation**: See tool calls, not reasoning.

### Layer 5: Post-Hoc Verification

`/advocate` or critic agent reviews work with skeptical stance.

**Most reliable layer**: Separate invocation, fresh context.
**Limitation**: Reactive, not preventive.

### Layer 6: User Habits

User asking "show me the evidence" is the most effective enforcement.

## Verification: The Top Failure Pattern

**"Can it?" ≠ "Does it?"**

Agents conflate capability with actual state:

| Agent checked           | Should have checked |
| ----------------------- | ------------------- |
| Framework default value | Actual config file  |
| Code capability exists  | Feature is enabled  |
| Tool exists             | Tool is configured  |

**Evidence Types** (require actual_state for conclusions):

- `actual_state` - Config files read, runtime output captured
- `default_only` - Only defaults checked
- `capability_only` - Only documented capabilities
- `none` - No evidence gathered

## Design Principles

1. **Layer defenses** - No single mechanism reliable
2. **Prefer observable over invisible** - TodoWrite/Plan create artifacts
3. **Accept imperfection** - Influence, not force
4. **Measure before changing** - Track compliance first
5. **Least invasive first** - Conventions before gates

## Component Responsibilities

When failures occur, we distinguish:

- **PROXIMATE CAUSE**: Agent made a mistake (non-deterministic, outside our control)
- **ROOT CAUSE**: Framework component failed its responsibility (deterministic, within our control)

> Root Cause = Component did not provide what it promised, OR did not block what it promised, OR did not detect what it promised.

### Root Cause Categories

| Category          | Definition                                             |
| ----------------- | ------------------------------------------------------ |
| Clarity Failure   | Instruction ambiguous or insufficiently emphasized     |
| Context Failure   | Component didn't provide relevant information          |
| Blocking Failure  | Component didn't block what it should have             |
| Detection Failure | Component didn't catch violation it should have        |
| Gap               | No component exists for this case - need to create one |

**Note**: Multiple categories can apply (defense-in-depth failed at multiple layers).

### Responsibilities by Phase

#### Pre-Execution Phase

| Component             | Responsibility                                                | Verification                                          |
| --------------------- | ------------------------------------------------------------- | ----------------------------------------------------- |
| AXIOMS/HEURISTICS     | Rules stated unambiguously with reasoning                     | Each rule has single interpretation + WHY             |
| Intent Router         | Correct classification, relevant context, workflow suggestion | Classification matches human judgment                 |
| Guardrails            | Task-specific emphasis applied                                | Guardrails in output match task type table            |
| Intervention Reminder | User corrections take priority over in-progress work          | Agent halts current work on user intervention         |
| Compliance Auditor    | Detect principle violations mid-execution                     | Check fires at threshold, returns relevant violations |

#### Execution Phase

| Component         | Responsibility                       | Verification                            |
| ----------------- | ------------------------------------ | --------------------------------------- |
| Agent Abstraction | Correct behavior when agent followed | Agent execution produces correct output |
| PreToolUse Hooks  | Block prohibited operations          | Hook fires on known bad input           |
| Tool Restriction  | Wrong tools unavailable              | Tool not in allowed list                |

#### Post-Execution Phase

| Component         | Responsibility                       | Verification                     |
| ----------------- | ------------------------------------ | -------------------------------- |
| PostToolUse Hooks | Detect violations, demand correction | Hook detects violation in output |
| Deny Rules        | Absolute prevention                  | Operation blocked                |
| Pre-Commit Hooks  | Block prohibited commits             | pre-commit run catches violation |

### Root Cause Analysis Protocol

When analyzing a failure:

1. **Was there a rule?** Check AXIOMS/HEURISTICS for applicable rule
2. **Did router suggest correct workflow?** Check hydrator output
3. **Did agent follow workflow?** If yes, was output correct?
4. **Should PreToolUse have blocked?** Check hook rules
5. **Should PostToolUse have detected?** Check detection hooks
6. **Should deny rule have blocked?** Check settings.json
7. **Should pre-commit have caught?** Check .pre-commit-config.yaml

If all components met their responsibilities but failure still occurred: **Gap** - create new enforcement at appropriate level.
