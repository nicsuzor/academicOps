---
name: meta
description: Strategic supervisor for academicOps framework - loads complete context, makes principled decisions, handles work end-to-end with TDD quality gates
permalink: commands/meta
tools:
  - Task
---

**IMMEDIATELY** invoke the `supervisor-meta` subagent with the user's request.

## Purpose: Strategic Framework Management

Hand off framework problems to a supervisor you can trust. The supervisor-meta agent will:

1. **Load complete framework context** before doing anything
   - ACCOMMODATIONS (your work style - binding)
   - CORE (your context and tools)
   - STATE (current framework stage and blockers)
   - AXIOMS (framework principles)
   - VISION (framework goals)
   - ROADMAP (maturity progression)
   - LOG (past learnings)

2. **Make principled decisions** aligned with your vision
   - Trace reasoning to AXIOMS/VISION/ROADMAP
   - Learn from past experiments
   - Respect your work style constraints

3. **Handle work end-to-end** with appropriate delegation
   - Strategic questions: Direct answer with context
   - Implementation work: Full TDD workflow with quality gates
   - Framework changes: Integration tests, validation, commit+push

4. **Have your back** with verified results
   - No claiming success without evidence
   - No corners cut (VERIFY FIRST, NO EXCUSES)
   - Demonstrates working results
   - Documents session progress

## When to Use

**Strategic questions**:
- "What should we work on next?"
- "Is this aligned with our vision?"
- "Where are we on the roadmap?"
- "Why did we decide X?"

**Implementation work**:
- "Add feature X to the framework"
- "Fix bug Y in component Z"
- "Debug this framework issue"
- "Create new automation for W"

**Planning and decisions**:
- "Should we add this component?"
- "How should we approach this problem?"
- "What's the right architecture for X?"

## What You Get

- **Context-aware decisions**: All framework context loaded before acting
- **Principled reasoning**: Decisions traced to AXIOMS/VISION/ROADMAP
- **Quality results**: Tests pass, code validated, changes committed+pushed
- **Institutional memory**: Learns from LOG.md, avoids repeating mistakes
- **Trustworthy output**: Verifies completeness, shows evidence, no excuses

## How It Works

The command invokes the supervisor-meta subagent (Opus model) with your request. The supervisor:
- Loads all context first (MANDATORY)
- For questions: Provides answer with traced reasoning
- For work: Orchestrates full TDD workflow with delegation
- Reports back with verified results and documentation

See agents/supervisor-meta.md for complete capability documentation.
