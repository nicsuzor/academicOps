---
name: output-targets
category: ref
description: Target structure for generated documentation files (README.md, INDEX.md)
---

# Audit Output Targets

Reference for target structure of generated documentation files.

## README.md Structure Target

Brief overview (~100-150 lines):

```markdown
# academicOps Framework

Academic support framework for Claude Code. Minimal, fight bloat.

## Quick Start

[paths, principles links]

## How Enforcement Works

[Mermaid flowchart showing 7-level mechanism ladder]

The framework influences agent behavior through layered defenses:

| Level | Mechanism                            | When          | What It Does                            |
| ----- | ------------------------------------ | ------------- | --------------------------------------- |
| 1a-c  | Prompt text                          | Session start | Mention → Rule → Emphatic+Reasoned      |
| 2     | Intent router                        | Before task   | Intelligent steering, skill suggestions |
| 3a-b  | Tool restriction / Skill abstraction | Tool use      | Force correct workflow                  |
| 4     | Pre-tool hooks                       | Before action | Block before damage                     |
| 5     | Post-tool validation                 | After action  | Catch violations                        |
| 6     | Deny rules                           | Tool use      | Hard block, no exceptions               |
| 7     | Pre-commit                           | Git commit    | Last line of defense                    |

See [[docs/ENFORCEMENT.md]] for practical guide, [[specs/enforcement.md]] for architecture.

## Commands

[table: command | purpose]

## Skills

[table: skill | purpose]

## Hooks

[table: hook | trigger | purpose]

## Agents

[table: agent | purpose]
```

**Enforcement flowchart requirement**: README.md MUST include a simplified Mermaid diagram derived from [[docs/ENFORCEMENT.md]] (the practical 7-level mechanism ladder). The diagram should show the enforcement levels (1a-7) in a way that helps new users understand when each mechanism operates. Note: `specs/enforcement.md` is architectural philosophy; `docs/ENFORCEMENT.md` is the practical guide.

## INDEX.md Structure Target

Complete file-to-function mapping:

```markdown
# Framework Index

## File Tree

$AOPS/
├── AXIOMS.md # Inviolable principles
├── [complete annotated tree...]

## Cross-References

### Command → Skill

### Skill → Skill

### Agent → Skill
```
