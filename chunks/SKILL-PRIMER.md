---
title: "Skill Execution Context"
type: skill-context
description: "Context primer for Claude Code skills, explaining isolated execution context, framework access via @resources/ symlinks, and differences from main agent environment."
tags:
  - skill
  - execution-context
  - resources
  - framework
relations:
  - "[[chunks/AXIOMS]]"
  - "[[chunks/INFRASTRUCTURE]]"
  - "[[docs/bots/SKILL-DESIGN]]"
---

# Skill Execution Context

**You are running as a Claude Code skill.**

## Key Differences from Main Agent

- **Isolated context**: You don't receive SessionStart hooks
- **No auto-loaded context**: Framework context available via `@resources/` only
- **Single purpose**: Focus on your specific skill function
- **Shared resources**: Access universal principles via `@resources/` symlinks

## Framework Context

Universal principles and infrastructure knowledge available via `@resources/` directory:

- `@resources/AXIOMS.md` - Universal principles (fail-fast, DRY, standard tools, etc.)
- `@resources/INFRASTRUCTURE.md` - Repository structure, paths, environment variables (framework-touching skills only)

These files are symlinked from `$ACADEMICOPS/chunks/` to provide consistent, DRY context across all skills.
