---
name: taxonomy
title: Taxonomy — Canonical Definitions
type: reference
category: framework
description: Single source of truth for all framework concepts and their relationships
permalink: taxonomy
tags: [framework, taxonomy, canonical, reference]
---

# Taxonomy: Canonical Definitions

This document is the **single authoritative source** for all framework concepts. Every other document in the framework MUST use these terms consistently. When in doubt, this document wins.

## The Hierarchy

```
GOAL (multi-month/year desired outcome)
  └─ PROJECT (coherent body of work toward a goal)
      └─ EPIC (PR-sized unit of verifiable work)
          └─ TASK (discrete deliverable within an epic)
              └─ ACTION (single-session step within a task)
```

Every node has exactly one parent. Goals are roots. Tasks never float free — they always belong to an epic.

## The Orchestration Layer

```
WORKFLOW (composable step arrangement for achieving an epic)
  └─ STEP (one unit of work within a workflow)
      └─ SKILL (instructions for an agent on HOW to execute a step)
```

Workflows define WHAT to do and in WHAT order. Skills define HOW to do a single step. These are separate concerns.

---

## Concept Definitions

### Goal

A desired future state, typically multi-month or multi-year in scope. Goals are directional — they describe where you want to be, not exactly how to get there. A goal may be vague and is expected to evolve.

**Examples**: "Transform academicOps into autonomous academic research engine", "World-class academic profile"

**Children**: Projects

**Anti-pattern**: A goal with tasks directly underneath. If you can do it in a session, it's not a goal.

### Project

A coherent body of work that advances a goal. A project has a defined scope, clear boundaries, and produces tangible outputs. Projects are ongoing — they can run for weeks or months.

**Examples**: "AcademicOps", "Reliability Study", "TJA"

**Children**: Epics (and sub-projects, rarely)

**Anti-pattern**: A project with 30 direct task children. Projects need epics to provide intermediate structure and verifiable milestones.

### Epic

The **basic unit of verifiable work**. An epic is PR-sized: a coherent set of changes that can be reviewed, tested, and merged together. An epic is complete when all of its workflow steps pass — planning, execution, and verification.

An epic includes:

1. **Planning tasks**: Methodology, acceptance criteria, approach design
2. **Execution tasks**: The actual work
3. **Verification tasks**: Testing, QA, cross-referencing, review

In the Bazaar model, different agents may handle different tasks within an epic. The quality guarantee comes from the workflow structure — if every required step is verifiably complete, the epic is good. A failure at any step fails the entire epic until fixed or abandoned.

**Typical scope**: 5–20 hours across multiple sessions. Multiple distinct deliverables. Results in one PR or one reviewable unit.

**Children**: Tasks, bugs, features

**Anti-pattern**: An epic that is really a project (months of work, dozens of tasks). If it needs more than ~12 child tasks, decompose into sub-epics or reclassify as a project.

**Anti-pattern**: An epic with no verification tasks. Every epic must include at least one QA/review step to be considered verifiable.

### Task

A discrete deliverable within an epic. A task can be completed in a single focused session (1–4 hours) and produces a specific, identifiable output.

**Examples**: "Write acceptance criteria for dashboard", "Implement sort function", "Run regression tests"

**Parent**: Always an epic

**Children**: Actions (optional, for multi-step tasks)

**Anti-pattern**: An orphan task with no epic parent. Find or create the epic first.

**Anti-pattern**: A task that takes multiple sessions. That's an epic, not a task.

### Action

A single work step within a task, completable in under 30 minutes. Actions are optional — not every task needs to be decomposed into actions.

**Examples**: "Add import statement", "Run test suite", "Update config file"

### Bug, Feature

Specialised task types that follow the same rules as tasks but carry semantic meaning about what kind of work they represent.

### Learn

Observational tracking — not actionable work, but a record of something discovered or noted. Learns can be attached at any level.

---

## Orchestration Concepts

### Workflow

A **brief, composable arrangement of steps** that describes how to achieve an epic. A workflow answers "WHAT do we do and in WHAT order?" — not "HOW do we do each step."

Workflows are the Bazaar's quality guarantee. By defining required steps (including verification), workflows ensure that work is good enough regardless of which agent performs it. You don't need to micromanage agents if the workflow structure mandates planning before execution and verification after.

**Structure**: A workflow is a sequence of steps, each of which may invoke a base workflow pattern and require a specific skill. Workflows compose base patterns (task-tracking, tdd, verification, commit, handover, etc.) into coherent processes.

**Examples**: `feature-dev` (plan → test → implement → verify → commit), `decompose` (understand → identify stages → draft tasks → verify coverage)

**Anti-pattern**: A workflow that contains detailed HOW-TO instructions. That's a skill, not a workflow.

**Anti-pattern**: A workflow embedded inside a skill file. Workflows are orchestration; skills are execution. A skill never contains a workflow (see Principle #0 in workflow-system-spec).

### Step

One unit within a workflow. A step has a clear purpose, an expected output, and may specify which skill an agent needs to execute it.

**Examples**: "Write acceptance criteria" (step in a feature-dev workflow, uses QA skill), "Run regression tests" (step in verification workflow, uses testing skill)

### Skill

Instructions to an individual agent about **HOW to achieve a workflow step**. A skill is domain expertise packaged as a document: what tools to use, what quality criteria to meet, what patterns to follow, what anti-patterns to avoid.

Skills are fungible — any agent with the right skill can execute the step. This is what enables the Bazaar model: you don't need a specific agent, just one that can follow the skill's instructions.

**Structure**: A skill document contains the domain expertise needed for one type of work. It should NOT contain routing logic, decision trees for selecting between different workflows, or multi-mode operational patterns.

**Examples**: `python-dev` (how to write production-quality Python), `qa` (how to verify work meets criteria), `pdf` (how to create formatted PDFs)

**Anti-pattern**: A skill with 6 different "modes" that are each a separate workflow. Extract the modes as separate workflows; keep the skill focused on one type of expertise.

**Anti-pattern**: A skill with an embedded workflow router ("If you need to do X, use workflow A; if Y, use workflow B"). That routing belongs in WORKFLOWS.md, not in a skill file.

---

## Key Principles

### 1. Every task belongs to an epic

No orphan tasks. If a task exists, there must be an epic that gives it purpose and context. If you can't identify the epic, create one — even a lightweight one — before creating the task.

### 2. Epics are PR-sized and verifiable

An epic is not an arbitrary container. It's sized for review: small enough to understand in one sitting, large enough to be a meaningful unit of progress. It includes its own verification steps.

### 3. Workflows orchestrate; skills execute

Workflows define WHAT steps to take and in WHAT order. Skills define HOW to execute a step. A workflow may reference multiple skills. A skill NEVER contains a workflow. This separation is what makes the Bazaar model work — workflows guarantee quality through structure, skills provide the expertise for each step.

### 4. The hierarchy provides context

Each level of the hierarchy answers "why?" in terms of its parent. A task's purpose is explained by its epic. An epic's purpose is explained by its project. A project's purpose is explained by its goal. If you can't trace this chain, something is misplaced.

### 5. Failure propagates up within an epic

In the Bazaar model, a failure at any workflow step (a failed test, a rejected review, an inadequate plan) fails the entire epic. This is by design — it's how we achieve quality without micromanaging agents. The epic isn't done until all required steps verifiably pass.

---

## Relationships Between Concepts

```
HIERARCHY                          ORCHESTRATION
─────────                          ─────────────
Goal                               Workflow
 └─ Project                         ├─ Step 1 → Skill A
     └─ Epic ◄──── achieved by ────►├─ Step 2 → Skill B
         ├─ Task                    ├─ Step 3 → Skill A
         ├─ Task                    └─ Step 4 → Skill C
         └─ Task
```

An epic is achieved by executing a workflow. The workflow's steps correspond to (but are not identical to) the epic's child tasks. The workflow defines the required sequence; the tasks are the concrete work items created to fulfill each step.

---

## Quick Reference: "Is this a...?"

| Question                                                | Answer       |
| ------------------------------------------------------- | ------------ |
| Multi-month desired outcome?                            | **Goal**     |
| Coherent body of work toward a goal?                    | **Project**  |
| PR-sized unit with planning + execution + verification? | **Epic**     |
| Single-session deliverable within an epic?              | **Task**     |
| Sub-30-minute step within a task?                       | **Action**   |
| Sequence of steps describing WHAT to do?                | **Workflow** |
| Instructions for HOW to do one step?                    | **Skill**    |

---

## Document Authority

This document supersedes any conflicting definitions in other framework files. If another document defines these terms differently, that document should be updated to reference this one.

**Referenced by**: TASK_FORMAT_GUIDE.md, WORKFLOWS.md, SKILLS.md, all SKILL.md files, workflow-system-spec.md
