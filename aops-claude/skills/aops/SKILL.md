---
name: aops
category: instruction
description: "Core academicOps skill — institutional memory, strategic coordination, workflow routing, and framework governance. Merges butler (chief-of-staff) with framework development conventions."
---

# academicOps Core Skill

Coordinate framework operations, maintain institutional memory in the PKB, route workflows, and enforce framework conventions.

## Institutional Memory via PKB

The Personal Knowledge Base (PKB) is the single source of truth.

- On first invocation, load the framework state document: `mcp__plugin_aops-core_pkb__get_document(id="aops-state")`.
- Update this document with visions, decisions, open questions, and roadmaps. Use `mcp__plugin_aops-core_pkb__append` for incremental updates.
- Use `list_tasks` with `project=<project-id>` to find tasks scoped to a single project. Do not infer project membership from IDs.

## Framework Governance

### Instruction Maintenance

If corrected, encountering a process gap, or seeing a `learning`-tagged task:

1. Locate the responsible instruction file (`CORE.md` or `SKILL.md`).
2. Update the file in the same turn.
3. Validate that agents follow the updated instructions.

### Dogfooding & Process Verification

When failures occur, identify and fix the process gap rather than just applying a local patch. Do not declare victory until you verify success with evidence.

### Handover

- Ensure the next strategic step is filed as a PKB task before exiting.
- If a design decision produces implementation work affecting multiple files/projects, run `/planner decompose` first.

### Verification of Assumptions

Verify capability and constraints of framework mechanisms (plugins, model context, environment) against primary codebase files before making claims or routing tasks.

## Strategic Guidance

- Prioritize features serving actual academic workflows.
- Recommend automation in order of maturity: Manual -> Assisted -> Supervised (Default) -> Autonomous. Move to autonomous only after multiple successful supervised runs.

## Workflow Router

Route tasks based on scope:

| Target                                 | Workflow                                                                   |
| :------------------------------------- | :------------------------------------------------------------------------- |
| **Add hook, skill, command, or agent** | [01-design-new-component](workflows/01-design-new-component.md)            |
| **Fix broken framework issues**        | [02-debug-framework-issue](workflows/02-debug-framework-issue.md)          |
| **Test optimizations / experiments**   | [03-experiment-design](workflows/03-experiment-design.md)                  |
| **Check / trim bloat**                 | [04-monitor-prevent-bloat](workflows/04-monitor-prevent-bloat.md)          |
| **Build new features**                 | [05-feature-development](workflows/05-feature-development.md)              |
| **Write/update specifications**        | [06-develop-specification](workflows/06-develop-specification.md)          |
| **Record lessons / learnings**         | [07-learning-log](workflows/07-learning-log.md)                            |
| **Unstick blocked decisions**          | [08-decision-briefing](workflows/08-decision-briefing.md)                  |
| **Diagnose hook/gate failures**        | [09-session-hook-forensics](workflows/09-session-hook-forensics.md)        |
| **Process-level review (dogfooding)**  | [10-reflective-execution](workflows/10-reflective-execution.md)            |
| **Verify session infrastructure**      | [11-self-test](workflows/11-self-test.md)                                  |
| **Verify hook routing**                | [11-self-test §3](workflows/11-self-test.md#3-hook-output-channel-routing) |

## Categorical Conventions

### File Boundaries

- `$AOPS/*`: Modification permitted.
- `$ACA_DATA/*`: Direct file operations forbidden; delegate writes/updates to PKB MCP tools.

### Core Conventions

- **One Spec Per Feature**: Specifications are timeless.
- **Single Source of Truth**: Keep data in exactly one location.
- **Self-Documenting (P#10)**: Embed documentation in code; avoid parallel docs.
- **Always Dogfooding (P#22)**: Use real projects as development guides.
- **Skills are Read-Only (P#23)**: Skills must not store state. State lives in `$ACA_DATA`.
- **Trust Version Control (P#24)**: No backup files (`.bak`, `_new`). Edit files directly, commit, and push.
- **Plan-First Development (P#41)**: Code only after plan approval, except for trivial typos/formatting.
- **Just-in-Time Context (P#43)**: Automatically surface context at decision points.
- **Memory Model (P#46)**: Semantic notes (synthesized) must be understandable without reading sources. Episodic notes are immutable after creation.
- **Agents Execute Workflows (P#47)**: Workflow procedures belong in workflow files, not agent prompts.
- **No Shitty NLP (P#49)**: Use LLM judgment for semantic decisions. Do not write programmatic scripts wrapping LLM APIs; use the agentic platforms directly.

## Task Lifecycle & Execution

Follow the **Plan -> Act -> Validate** cycle:

1. **Plan**: Formulate approach. Invoke critic review (`rbg` or `pauli`) only if uncertainty or blast radius requires it.
2. **Act**: Execute changes.
3. **Validate**: Test locally, commit, push, and release task.

## HALT Protocol

When unable to derive a decision:

1. **STOP**: Halt execution.
2. **STATE**: Record what cannot be determined and why.
3. **ASK**: Prompt the user using `AskUserQuestion`.
4. **DOCUMENT**: Record the resolved rule.

## Rules & Anti-Patterns

### Anti-Pattern: Asking Permission for Safe Actions

Do not ask permission to file tasks, fix bugs, or execute safe operations (e.g., retitling, graph hygiene, canceling superseded tasks). Perform the action and report the outcome. Only ask permission for destructive or externally visible actions.

### Anti-Pattern: Recording Actions Instead of Executing

Perform safe administrative actions (e.g. repointing dependencies, status flips, hygiene) immediately in the same turn instead of documenting them as future TODOs.

### Reporting Norms

Report actions and states in plain English. Avoid using internal taxonomy (`DECIDE-class`, `Externalisation Heuristic`, `P#`) in user-facing output.

- **Wrong**: "DECIDE-class supersession recorded: cancel task-A."
- **Right**: "Cancelled task-A (superseded by task-B)."
- **Wrong**: "Applied DEFER-class treatment to decision."
- **Right**: "Decision deferred pending run data."
