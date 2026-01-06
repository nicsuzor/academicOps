---
name: introspect
category: instruction
description: Test framework self-knowledge from session context alone. Reports what agents can answer without reading files.
allowed-tools: AskUserQuestion
version: 1.0.0
permalink: skills-introspect
---

# /introspect - Framework Self-Knowledge Test

Test what you know from session-start context WITHOUT reading additional files.

## Purpose

Per **Axiom #25 (JUST-IN-TIME CONTEXT)**, session start injects core framework knowledge. This skill tests whether that injection is sufficient by asking: "Can I answer this question from current context alone?"

## Usage

```
/introspect                           # Report known context gaps
/introspect <question>                # Test if question is answerable
```

## Execution

### With Question Argument

When invoked with a question (e.g., `/introspect what is task/index.json`):

1. **DO NOT READ ANY FILES** - Answer from current context only
2. **Search your context** for relevant information
3. **Report confidence level**:
   - **HIGH**: Explicitly mentioned in session context (quote the source)
   - **LOW**: Can infer from context but not directly stated
   - **UNKNOWN**: Not in current context

4. **If UNKNOWN**, check the Known Context Gaps table below and report where the information lives

**Response format:**
```
## Introspection: [question]

**Confidence**: [HIGH|LOW|UNKNOWN]

**Answer**: [Your answer OR "Cannot answer from session context"]

**Source**: [If HIGH/LOW: where in context. If UNKNOWN: which file would have this info]
```

### Without Arguments

When invoked as just `/introspect`:

1. Report what knowledge domains ARE covered by session-start context
2. List the Known Context Gaps from this skill
3. Suggest specific questions to test

**Response format:**
```
## Framework Self-Knowledge Report

### What Session Context Provides
- Framework paths (FRAMEWORK.md)
- 29 inviolable axioms (AXIOMS.md)
- 36 empirical heuristics (HEURISTICS.md)
- User context and preferences (CORE.md)

### Known Context Gaps
[Table from below]

### Test Questions
Try: `/introspect what is task/index.json`
```

---

## Session-Start Context Reference

The SessionStart hook (`hooks/sessionstart_load_axioms.py`) injects these files:

| File | Content | Path Variables Expanded |
|------|---------|------------------------|
| FRAMEWORK.md | Paths, environment vars, memory architecture | Yes |
| AXIOMS.md | 29 inviolable principles | No |
| HEURISTICS.md | 36 empirical rules with evidence links | No |
| CORE.md | User profile, tools, workflow requirements | No |

**You CAN answer questions about:**
- Where framework components live (skills, commands, hooks, agents, tests)
- User preferences and accommodations (by reference)
- Memory architecture (semantic vs episodic)
- Core principles and their numbering
- Heuristics and their confidence levels
- Path resolution mechanism

---

## Known Context Gaps

Things the framework uses but does NOT inject at session start:

| Gap | What It Is | Where Info Lives | Severity |
|-----|-----------|-----------------|----------|
| task/index.json | Pre-computed task index for fast queries | `scripts/regenerate_task_index.py` (creator), `skills/tasks/task_loader.py` (consumer) | Medium |
| Skill invocation syntax | How to call specific skills | Individual `skills/*/SKILL.md` files | Low |
| Project-specific state | Current project context | `$ACA_DATA/projects/*/STATE.md` | Low |
| Style guides | Writing conventions | `$ACA_DATA/STYLE.md`, `$ACA_DATA/STYLE-QUICK.md` | Low |
| Accommodations detail | Full ADHD accommodations | `$ACA_DATA/ACCOMMODATIONS.md` | Low |

**When you discover a new gap:**
1. Note it in your response
2. User can add it to this table via PR

---

## Design Rationale

**Why not inject everything?**

Per Axiom #25, not everything belongs in session start:
- **Session start**: Global principles needed for ALL sessions
- **Component CLAUDE.md**: Decisions needed when working on that component
- **Memory server**: Past learnings retrievable on demand
- **Skills**: Detailed workflows loaded when skill is invoked

This skill helps identify when something IS missing vs. when it's correctly deferred.

**Why no file reads allowed?**

The skill tests what agents know WITHOUT additional context. If you could read files, the test would be meaningless. The constraint is the point.
