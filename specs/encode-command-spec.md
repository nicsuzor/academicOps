---
title: Encode Command Specification
type: spec
category: spec
status: implemented
permalink: specs/encode-command
tags: [framework, commands, pattern-capture]
---

# /encode Command Specification

## Purpose

Enable iterative capture of work patterns as reusable framework artifacts (workflows, skills, commands).

## Design Justification

### Problem Statement

Users frequently perform tasks that could become reusable patterns, but:
1. Pattern extraction happens rarely (friction to create artifacts)
2. Single-pass extraction misses nuances (patterns need refinement)
3. Created artifacts over-fit to the immediate task (not generalizable)

### Solution

A command that:
- **Tracks work in real-time** via TodoWrite (evidence gathering)
- **Extracts patterns iteratively** (multiple passes to refine)
- **Creates actual artifacts** (not drafts) with embedded generalization warnings
- **Documents justifications** in specs (this file pattern)

## Evidence

### Source Observations

1. **2026-01-01 session**: User asked "teach me how to work with you if I want to undertake a task but also encode the process as a workflow and/or skill"
   - Revealed need for explicit "do AND encode" pattern
   - Identified two modes: start (track) vs. after (extract)

2. **Existing command patterns analyzed**:
   - `/do` - Execution with full pipeline, checkpoint tracking
   - `/q` - Capture for later, delegates to tasks skill
   - `/add` - Quick capture, semantic search for duplicates

3. **User refinements during design**:
   - "don't specify" → agent infers scenario from context
   - "don't directly create - start with drafts" → later revised to "just make the edits"
   - "generalization warning" → avoid over-fitting to immediate task

### Design Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Two-mode detection (start/extract) | Matches natural workflow - either beginning work or reviewing it | Explicit flags (`/encode --start`, `/encode --extract`) - rejected as unnecessary |
| TodoWrite as evidence | Already tracks steps; reuse rather than new mechanism | Custom trace file - rejected as duplicate infrastructure |
| Edit actual workflows, not drafts | User feedback: "make the edits to the workflow" | Draft staging area - rejected as extra indirection |
| Generalization warning embedded | Agents tend to over-fit; explicit reminder helps | Training/prompting alone - insufficient |
| Spec per artifact | Meta-info lives separately from the artifact itself | Inline comments - too verbose, mixed concerns |

## Generalization Scope

This command should handle:

1. **Task-to-workflow**: Single task → repeatable workflow
2. **Session-to-skill**: Complex session → skill with context + delegation
3. **Pattern-to-command**: Common entry point → slash command
4. **Refinement**: Existing workflow → improved version

### Not Currently Scoped

- Cross-session pattern detection (would need session corpus analysis)
- Automatic similarity matching to existing workflows (semantic search of workflow library)
- Version control of workflow evolution (relies on git)

## Acceptance Criteria

1. `/encode [task]` tracks each step in TodoWrite
2. `/encode` (no args) reviews recent work and creates/updates workflow
3. Created workflows include inputs/outputs specification
4. Spec file created for each new workflow with evidence section
5. Generalization warning appears in command instructions

## Open Questions

1. **How to detect "recent work"?** Currently relies on session context and TodoWrite. Could extend to session file parsing.

2. **When to create skill vs workflow vs command?** Current heuristic:
   - Steps only → workflow
   - Context + delegation → skill
   - User entry point needed → command

   May need refinement based on usage.

3. **How to avoid duplicate workflows?** Semantic search of existing workflows could help. Not implemented yet.

## Related

- [[commands/encode.md]] - Command definition
- [[skills/framework/workflows/01-design-new-component.md]] - Pattern for creating components
- [[HEURISTICS#H2]] - Skill-First Action Principle (encode patterns for reuse)
