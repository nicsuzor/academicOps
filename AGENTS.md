---
title: Framework Agent Instructions
type: instruction
category: instruction
permalink: root-claude-instructions
description: Entry point for academicOps framework. Loads CORE.md and project context.
---

@CORE.md

# academicOps Agent Rules

You are working with the academicOps framework. These rules apply to all framework-aware agents.

## Core Behaviors

- **HALT on underspecified tasks**: Verify What, Where, Why before starting. If unclear, use AskUserQuestion.
- **Fail fast**: If something doesn't work, ESCALATE. No workarounds.
- **Agent instructions are expensive**: Every line should tell agent WHAT TO DO. No meta-commentary.

## Task Tracking

Use the **tasks MCP server** for all work tracking. Agent owns task structure - set parents, dependencies, reorder as needed without asking.

## Session Completion

**Work is NOT complete until `git push` succeeds.**

1. File tasks for unfinished work
2. Run quality gates (if code changed)
3. Push: `git pull --rebase && git push`
4. Output Framework Reflection

## Framework Reflection (MANDATORY)

At session end, output this EXACT format (extracted by transcript.py):

```
## Framework Reflection

**Prompts**: [User prompts from this session]
**Guidance received**: [Hydrator/custodiet advice, or "N/A"]
**Followed**: [Yes/No/Partial]
**Outcome**: [success/partial/failure]
**Accomplishments**: [What was done]
**Friction points**: [What was hard, or "none"]
**Root cause** (if not success): [Component that failed]
**Proposed changes**: [Improvements, or "none"]
**Next step**: [Follow-up - file as task if actionable]
**Workflow improvements**: [Process improvements, or "none"]
**JIT context needed**: [Info that would have helped]
**Context distractions**: [Files/sections to remove or shrink]
**User tone**: [Float -1.0 to 1.0]
```

**DO NOT STOP without outputting this reflection.**
