---
title: academicOps Framework
type: guide
category: framework
permalink: claude-framework-guide
---

# academicOps Framework Guide

This directory contains the academicOps framework for managing complex workflows through an LLM-driven system with structured enforcement, task management, and governance.

## Quick Navigation

- [[README.md]] - Framework overview and core loop
- [[AXIOMS.md]] - Core principles
- [[HEURISTICS.md]] - Rules of thumb
- [[SKILLS.md]] - Available skills and commands
- [[INDEX.md]] - Complete file index

## Key Components

- **aops-core/**: Framework core (hooks, enforcement, skills)
- **aops-tools/**: Developer tools and utilities
- **config/**: Configuration files (Claude, Gemini, environment)
- **data/**: Project data (tasks, contexts, session history)
- **specs/**: Framework specifications and architecture

## For Framework Users

See [[SKILLS.md]] to learn what you can do. Start with:
- `/pull` - Get a task from the queue
- `/log` - Log observations
- `/learn` - Make framework improvements

## For Framework Developers

See [[aops-core/skills/framework/SKILL.md]] to understand framework development workflows.
