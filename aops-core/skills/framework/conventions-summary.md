---
name: framework-conventions-summary
title: Framework Conventions Summary
category: ref
description: Condensed framework conventions for JIT injection. Full skill at skills/framework/SKILL.md.
permalink: framework-conventions-summary
---

# Framework Conventions (Summary)

**Full skill**: [[skills/framework/SKILL.md]] - invoke `Skill(skill='framework')` for component patterns, workflows, compliance refactoring.

## Categorical Imperative (MANDATORY)

Every action must be justifiable as a universal rule. No one-off changes.

### Before ANY Change

1. **State the rule**: What generalizable principle justifies this action?
2. **Check rule exists**: Is this in AXIOMS, this skill, or documented elsewhere?
3. **If no rule exists**: Propose the rule. Get user approval. Document it.
4. **Ad-hoc actions are PROHIBITED**: If you can't generalize it, don't do it.

### File Boundaries (ENFORCED)

| Location      | Action                     | Reason                                  |
| ------------- | -------------------------- | --------------------------------------- |
| `$AOPS/*`     | Direct modification OK     | Public framework files                  |
| `$ACA_DATA/*` | **MUST delegate to skill** | User data requires repeatable processes |

## Authoritative Source Chain

| Priority | Document      | Contains              |
| -------- | ------------- | --------------------- |
| 1        | AXIOMS.md     | Inviolable principles |
| 2        | HEURISTICS.md | Validated guidance    |
| 3        | VISION.md     | What we're building   |
| 4        | This skill    | Derived conventions   |
| 5        | INDEX.md      | File tree             |

**Rule**: Every convention must trace to an axiom. If it can't, the convention is invalid.

## HALT Protocol

When you encounter something you cannot derive:

1. **STOP** - Do not guess, do not work around
2. **STATE** - "I cannot determine [X] because [Y]"
3. **ASK** - Use AskUserQuestion for clarification
4. **DOCUMENT** - Once resolved, add the rule

## Core Conventions

### Single Source of Truth

Each piece of information exists in exactly ONE location. Reference, don't repeat.

| Information       | Authoritative Location |
| ----------------- | ---------------------- |
| Principles        | AXIOMS.md              |
| File tree         | INDEX.md               |
| Feature inventory | README.md              |
| Framework vision  | VISION.md              |
| Workflows         | WORKFLOWS.md           |

### Skills are Read-Only

Skills MUST NOT contain dynamic data. All mutable state lives in `$ACA_DATA/`.

### Just-In-Time Context

Information surfaces when relevant. Missing context = framework bug.

### Trust Version Control

- Never create backup files (.bak, _old)
- Edit directly, git tracks changes
- Commit AND push after completing work

### Mandatory Critic Review


```
```

### File Categories

| Category    | Purpose                        |
| ----------- | ------------------------------ |
| spec        | Framework design, architecture |
| ref         | External knowledge             |
| docs        | Implementation guides          |
| script      | Executable code                |
| instruction | Workflow/process for agents    |
| template    | Pattern to fill with content   |
| state       | Auto-generated (don't edit)    |

## Anti-Bloat Rules

- Skill files: 500 lines max
- Documentation chunks: 300 lines max
- Approaching limit = Extract and reference
- No multi-line summaries after references
- No historical context, migration notes
- No meta-instructions

## Skill Delegation

When operating on user data:

1. **Identify category**: What type of work?
2. **Find existing skill**: remember, tasks, analyst, etc.
3. **If skill exists**: Invoke it
4. **If NO skill exists**: Create one first via `Skill(skill='framework')`

Common delegations:

| Domain                   | Delegate To                   |
| ------------------------ | ----------------------------- |
| Python code, pytest      | `python-dev`                  |
| Framework infrastructure | `framework` (full skill)      |
| New feature with tests   | `feature-dev`                 |
| Persist knowledge        | `remember`                    |
| dbt, Streamlit, data     | `analyst`                     |
| Hook development         | `plugin-dev:hook-development` |

## Common Violations

| Violation                         | Principle | Correction                     |
| --------------------------------- | --------- | ------------------------------ |
| Direct user data modification     | Axiom #1  | Delegate to skill              |
| One-off script without skill      | Axiom #1  | Create generalizable skill     |
| Guessing when uncertain           | Axiom #2  | HALT, ask user                 |
| Scope creep beyond request        | Axiom #4  | Do one thing, stop             |
| Silent failure handling           | Axiom #7  | Fail fast, report error        |
| Creating backup files             | H15       | Trust version control          |
| Keyword matching for verification | H37       | Use LLM semantic evaluation    |
| Skipping skill invocation         | H2        | Invoke appropriate skill first |

## Consistency Checks (Before Changes)

| Check            | Question                       | Failure = HALT        |
| ---------------- | ------------------------------ | --------------------- |
| Axiom derivation | Which axiom justifies this?    | Cannot identify axiom |
| INDEX placement  | Does INDEX.md define location? | Location not in INDEX |
| DRY compliance   | Is info stated exactly once?   | Duplicate exists      |
| VISION alignment | Does VISION support this?      | Outside stated scope  |
| Namespace unique | Name conflict with existing?   | Name collision        |

---

**For detailed component patterns (adding skills, hooks, commands), invoke the full skill:**

```
Skill(skill='framework')
```
