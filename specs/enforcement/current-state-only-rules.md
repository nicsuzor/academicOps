---
title: Current State Only Rules
status: ready
type: spec
tags: [rules, enforcement, project-local, current-state]
---

# Current State Only Rules

This specification establishes three standing project-local rules for all agents operating in the repository. It mandates that repository files represent current operational state only, eliminating backwards-compatibility retention and in-file historical accounts.

## User stories

### US-1 Current state across repository files

As a repository maintainer, I want instructions and code to reflect current operational state without backwards-compatibility layers or historical narratives, so that agent context and human review are not occupied by obsolete paths.

- **AC-1.1** Given a deprecated file, module, or helper, when refactoring occurs, then the deprecated file is deleted rather than retained as a backwards-compatibility shim.
- **AC-1.2** Given an agent, skill, workflow, configuration, or code file, when authored or modified, then the file contains only content necessary for current execution, with all historical narrative and changelogs deferred to git.
- **AC-1.3** Given a specification document, when recording architectural choices, then the specification may carry at most one brief bullet point naming a rejected alternative and the reason for rejection.

## Design

### 1. Placement and Carriers

In accordance with the enforcement pyramid, these rules are introduced as Level 2 instructions (`instructions`, `imperative`).

The rules are carried in two project-local locations:

1. **Primary Carrier (`.agents/rules/current-state-only.md`):**
   A dedicated project-local rule file with `trigger: always_on`. This file is loaded by the rule evaluation hook (`plugins/rbg/hooks/rules.py`), compliance review lenses (`plugins/rbg/agents/rbg.md`), and automated review agents.

2. **Secondary Carrier (`.agents/CORE.md`):**
   A binding constraint entry under `## Binding constraints` in `.agents/CORE.md`. Because `.agents/CORE.md` is loaded at session start across both supported client harnesses (`CLAUDE.md` and `AGENTS.md`), this ensures universal runtime visibility for executing agents.

### 2. Enforcement-Map Status

- **Current Status:** Absent. Inspection of `specs/ENFORCEMENT-MAP.md` confirms that no rows currently exist governing backwards compatibility, deletion of deprecated files, or current-state-only instruction/code conventions.
- **Planned Mapping:** During Stage 2 (Build), `specs/ENFORCEMENT-MAP.md` will be updated under `## Agent instructions` with a dedicated row:
  `| [Project Rule: Current State Only](../.agents/rules/current-state-only.md) -- Deprecated files deleted; no history in instructions or code; specs may carry one concise rejected-choice bullet. | instructions | imperative | .agents/rules/current-state-only.md:1-20 |`

### 3. Proposed Rule Wording

The proposed wording for `.agents/rules/current-state-only.md` states the three rules and the spec exception, and nothing beyond them:

```markdown
---
trigger: always_on
description: Deprecated files are deleted; instructions and code state current state only with no history; specs may contain one brief rejected-choice bullet.
---

## Current state only

Maintain current state only across the repository. Do not preserve backwards compatibility or maintain history in instructions or code.

- **No backwards compatibility:** Deprecated files are deleted, not kept around.
- **No history in instructions or code:** Git holds history; instruction, skill, agent, configuration, and code files state current state only.
- **Spec exception:** A specification may carry one very brief bullet naming a rejected choice and the reason it was rejected.
```

### 4. Supporting Binding Constraint in CORE.md

The corresponding binding constraint in `.agents/CORE.md`:

`- **Current state only.** Deprecated files are deleted, not kept around. Git holds history; instructions, skills, agent definitions, and code state current state only. As a sole exception, a spec may carry one very brief bullet naming a rejected choice and the reason it was rejected.`
