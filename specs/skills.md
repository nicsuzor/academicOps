---
title: Skills Overview
type: spec
category: spec
status: implemented
permalink: skills-overview
tags:
- spec
- skills
- architecture
---

# Skills Overview

**Status**: Implemented (core skill system active)

## Skill Architecture

```mermaid
graph TD
    A[User/Agent Request] --> B{Skill Invocation}
    B --> C[Load SKILL.md]
    C --> D[Apply Behaviors]
    D --> E[Execute Work]
    E --> F[Return Results]

    subgraph "Skill Components"
        G[SKILL.md - Instructions]
        H[scripts/ - Python]
        I[templates/ - Formats]
        J[workflows/ - Patterns]
    end
```

## Core Skills

| Skill | Purpose | Status |
|-------|---------|--------|
| [[framework-skill]] | Categorical governance | Implemented |
| [[python-dev-skill]] | Fail-fast Python | Implemented |
| [[feature-dev-skill]] | Test-first development | Implemented |
| [[remember-skill]] | Knowledge persistence | Implemented |
| [[supervisor-skill]] | Multi-agent orchestration | Implemented |
| [[tasks-skill]] | Task lifecycle | Implemented |
| [[learning-log-skill]] | Pattern documentation | Implemented |
