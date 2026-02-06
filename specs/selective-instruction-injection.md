---
title: Selective Instruction Injection
type: spec
category: spec
status: draft
permalink: selective-instruction-injection
tags: [enforcement, hydration, optimization]
---

# Selective Instruction Injection

## Giving Effect

- [[hooks/user_prompt_submit.py]] - Hook that loads context (current: full file loading)
- [[agents/prompt-hydrator.md]] - Hydrator that selects relevant principles
- [[hooks/templates/prompt-hydrator-context.md]] - Template with `{heuristics}` variable
- [[AXIOMS.md]] - Source of universal principles
- [[HEURISTICS.md]] - Source of practical patterns (~254 lines, target for selective injection)

*Note: This spec proposes optimization of existing injection - not yet implemented.*

Replace full-file instruction loading with per-task selective injection via prompt hydration.

## Problem Statement

**Current state**: The UserPromptSubmit hook loads the ENTIRE `HEURISTICS.md` file (~254 lines, ~6KB) into the hydrator temp file. Every prompt pays this token cost regardless of relevance.

**Evidence**: `user_prompt_submit.py` line 148-168 (`load_heuristics()`) reads the full file. The `{heuristics}` variable in `prompt-hydrator-context.md` template (line 47) injects it entirely.

**Waste quantified**:
- HEURISTICS.md: ~254 lines, ~6KB, ~1500 tokens
- Per-prompt cost: 1500 tokens × N prompts/session
- Most principles irrelevant to any given task

## Design

### Principle: Hydrator as Filter

The hydrator (haiku) receives full AXIOMS/HEURISTICS files and selects which principles are relevant to the current task. The main agent receives ONLY the selected principles in the hydrator output - never the full files.

**Key insight**: Haiku tokens are cheap. Main agent (sonnet/opus) tokens are expensive. Let haiku do the filtering.

### Architecture

```
UserPromptSubmit hook
       ↓
Load full AXIOMS.md + HEURISTICS.md into temp file
       ↓
Hydrator (haiku) reads full files, selects relevant principles
       ↓
Hydrator outputs: "### Applicable Principles" with ONLY relevant ones
       ↓
Main agent receives hydrator output (filtered principles only)
```

**Token economics**:
- Hydrator sees ~3000 tokens (full AXIOMS + HEURISTICS)
- Main agent sees ~100-200 tokens (3-5 relevant principles)
- Haiku cost: ~$0.0003 per prompt
- Savings: Main agent doesn't pay for 2800 irrelevant tokens

### Hydrator Output Format

The hydrator outputs relevant principles with brief justification:

```markdown
### Applicable Principles

From AXIOMS:
- **P#5 (Do One Thing)**: This is a bounded task - complete it, then stop

From HEURISTICS:
- **P#74 (User System Expertise)**: User reported the bug, trust their observation
- **P#26 (Verify First)**: Run the fix, don't assume it works
```

This becomes the **default enforcement mechanism for instructions**. Rather than injecting full files at session start, principles surface JIT via hydration.

## Implementation

### Phase 1: Add AXIOMS.md Loading

Currently only HEURISTICS.md is loaded. Add AXIOMS.md so hydrator can select from both:

1. **Edit `user_prompt_submit.py`**: Add `load_axioms()` function mirroring `load_heuristics()`
2. **Edit `prompt-hydrator-context.md`**: Add `{axioms}` section before `{heuristics}`

### Phase 2: Update Hydrator Instructions

Ensure hydrator outputs selected principles clearly:

1. **Edit `agents/prompt-hydrator.md`**: Emphasize that "Applicable Principles" section is the enforcement mechanism
2. Add instruction: "Select 3-7 relevant principles. Include P#ID, name, and brief justification for why it applies to this task."

### Phase 3: Update enforcement-map.md (Documentation)

1. Update "What Constitutes Prompt-Level Enforcement" section
2. Document that selective injection via hydrator is the default enforcement mechanism
3. Clarify: main agents receive filtered principles, not full files

## Acceptance Criteria

1. Hydrator receives full AXIOMS.md + HEURISTICS.md
2. Hydrator outputs "Applicable Principles" section with 3-7 relevant principles
3. Main agent receives ONLY the selected principles (never full files)
4. Token savings realized for main agent (~2800 tokens saved)

## Backwards Compatibility

None needed. The hydrator output format already includes "Applicable Principles" - we're just clarifying its role as the enforcement mechanism.

## Risk Assessment

**Risk**: Hydrator might miss critical principles.

**Mitigation**:
- Universal axioms (P#5 Do One Thing, P#3 Don't Make Shit Up) should always be included for ambiguous tasks
- Framework-change tasks should always include P#65 (enforcement-map update)
- Debug tasks should always include P#26 (Verify First)

**Risk**: Hydrator output becomes inconsistent.

**Mitigation**:
- Add explicit instruction in hydrator agent definition
- QA can check if relevant principles were included

## Files to Modify

| File | Change |
|------|--------|
| `hooks/user_prompt_submit.py` | Add `load_axioms()` function |
| `hooks/templates/prompt-hydrator-context.md` | Add `{axioms}` section |
| `agents/prompt-hydrator.md` | Clarify principle selection instructions |
| `indices/enforcement-map.md` | Document selective injection as enforcement mechanism |
