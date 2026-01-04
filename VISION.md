---
title: Automation Framework Vision
type: note
permalink: aops-vision
tags:
  - framework
  - vision
  - planning
---

# academicOps Vision

**Last updated**: 2025-12-30

## What This Is

An academic support framework for Claude Code. It provides:

1. **Consistent agent behavior** - Principles ([[AXIOMS]]) loaded every session
2. **Specialized workflows** - [[data/projects/aops/specs/skills]] for research, writing, task management
3. **Quality enforcement** - [[hooks]] that inject context and verify compliance
4. **Knowledge persistence** - Memory server + [[remember]] skill for institutional memory

**Scope**: Supports academic work across ALL repositories.

## What It Does

### Currently Working

| Capability                 | Implementation           | How Invoked          |
| -------------------------- | ------------------------ | -------------------- |
| Research data analysis     | [[analyst]] skill        | Skill tool           |
| Citation management        | [[zotmcp]] + Zotero      | MCP tools            |
| Task capture from email    | [[tasks]] skill + [[email\|/email]] | Slash command        |
| Task visualization         | [[excalidraw]] skill     | [[task-viz\|/task-viz]]          |
| Writing style enforcement  | [[STYLE]] guides         | Agents follow guides |
| Knowledge capture          | [[remember]] skill       | Skill tool           |
| Session transcripts        | [[transcript]] skill     | /transcript          |
| Markdown to PDF generation | [[pdf]] skill            | Skill tool           |

### Enforcement Mechanisms

| What's Enforced | How |
|-----------------|-----|
| Principles loaded | [[sessionstart_load_axioms.py\|sessionstart_load_axioms]] hook |
| Skill suggestions | Prompt Enricher (planned) via UserPromptSubmit hook |
| Framework delegation | `FRAMEWORK SKILL CHECKED` token |
| Memory format compliance | [[pre-commit]] hooks |
| File boundaries | [[framework]] skill file boundary rules |

## Knowledge Architecture

### Repository Model

| Repo | Purpose | Sharing |
|------|---------|---------|
| `$AOPS/` | Framework machinery | Public (no personal data) |
| `$ACA_DATA/` | Personal knowledge | Never shared |
| Project repos | Code + docs | Collaborators only |

### Information Flow

```
Capture → memory server (semantic search) → JIT injection via hooks → Agent action
```

- **Session start**: [[AXIOMS]], [[FRAMEWORK]] paths, user context loaded
- **Every prompt**: Prompt Enricher (planned) suggests relevant skills
- **On demand**: Memory server search for related knowledge

## Success Criteria

1. **Zero-friction capture** - Ideas flow from any input (voice, email, notes) to organized context
2. **Consistent quality** - Writing matches style guide, citations formatted correctly
3. **Nothing lost** - Tasks tracked, knowledge searchable, context surfaces when needed
4. **Fail-fast** - Problems caught immediately, no silent failures
5. **Minimal maintenance** - Framework doesn't require constant babysitting

## Constraints

### Must Work Within

- Solo academic schedule (fragmented time, context switching)
- ADHD accommodations (zero-friction, clear boundaries)
- Cross-device workflow (multiple computers)
- Private data (secure and confidential)
- Academic standards (publication-quality required)

### Must Not Require

- Extensive configuration
- Manual maintenance
- Perfect inputs
- Full-time developer support

## Non-Goals

- ❌ Autonomous research decisions
- ❌ Replacing expert judgment
- ❌ Speed over quality
- ❌ Generic/formulaic output

## Design Philosophy

1. **Fail-fast** - No defaults, no silent failures, demand explicit configuration
2. **Modular** - Each component works independently, composes into workflows
3. **Minimal** - Fight bloat aggressively, one golden path
4. **Dogfooding** - Use real research projects as test cases

## Self-Curating Framework

The framework should become increasingly self-aware and self-improving:

1. **Agent-ready instructions** - Core docs ([[AXIOMS]], [[HEURISTICS]]) contain only actionable rules, no explanations or evidence
2. **Evidence-informed changes** - Framework changes are motivated by consolidated diagnostic data, not ad-hoc observations
3. **Closed-loop learning** - Observations → [[LOG]] → Diagnostics → [[experiments]] → Changes → Validation
4. **Framework introspection** - The [[framework]] skill understands the whole system and enforces consistency before accepting additions
5. **Bounded growth** - Logs don't grow forever; they consolidate into actionable diagnostics then archive
6. **Session-end reflection** - At session end, automatically analyze behavior patterns and suggest heuristic updates. User approves with one click, no manual observation writing. Zero friction for framework improvement.
