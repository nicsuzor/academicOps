---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Working hypotheses validated by evidence.
---

# Heuristics

## Probabilistic Methods, Deterministic Processes (P#92)

The framework embraces probabilistic methods (LLM agents) while requiring deterministic processes and derivable principles. We don't seek deterministic outcomes — we achieve rigor through deterministic processes that channel probabilistic methods.

## Skills Contain No Dynamic Content (P#19)

Current state lives in $ACA_DATA, not in skills.

## Semantic Link Density (P#54)

Related files MUST link to each other. Orphan files break navigation.

## File Category Classification (P#56)

Every file has exactly one category (spec, ref, docs, script, instruction, template, state).

## Never Bypass Locks Without User Direction (P#57)

Agents must NOT remove or bypass lock files without explicit user authorization. When encountering locks, HALT and ask.

## Action Over Clarification (P#59)

When user signals "go" and multiple equivalent ready tasks exist, pick one and start. Don't ask for preference.

## Indices Before Exploration (P#58)

Prefer curated indices (memory server, zotero, bd) over broad filesystem searches for exploratory queries. Grep is for needles, not fishing expeditions.

## Local AGENTS.md Over Central Docs (P#60)

Place agent instructions in the directory where agents will work, not in central docs.

## Internal Records Before External APIs (P#61)

When user asks "do we have a record" or "what do we know about X", search bd and memory FIRST before querying external APIs.

## Tasks Inherit Session Context (P#62)

When creating tasks during a session, apply relevant session context (e.g., `bot-assigned` tag during triage, project tag during project work).

## Task Output Includes IDs (P#63)

When displaying tasks to users, always include the task ID. Format: `Title (id: task-id)` or table with ID column.

## Planning Guidance Goes to Daily Note (P#64)

When prioritization agents provide guidance, write output to daily note. Do NOT execute the recommended tasks.

## Enforcement Changes Require enforcement-map.md Update (P#65)

When adding enforcement measures, update enforcement-map.md to document the new rule.

## Just-In-Time Information (P#66)

Never present information not necessary to the task at hand. When hydrator provides specific guidance, follow that guidance rather than investigating from first principles.

## Extract Implies Persist in PKM Context (P#67)

When user asks to "extract information from X", route to remember/persist workflow, not simple-question.

## Background Agent Visibility (P#68)

When spawning background agents, explicitly tell the user: what agents are spawning, that tool output will scroll by, and when the main task is complete.

## Large Data Handoff (P#69)

When data exceeds ~10KB or requires visual inspection, provide the file path and suggested commands instead of displaying inline.

## Trust Version Control (P#70)

When removing or modifying files, delete them outright. Trust git. No `.backup`, `.old`, `.bak` copies.

## No Commit Hesitation (P#24)

After making bounded changes, commit immediately. NEVER ask "Would you like me to commit?" or any variant. Complete the work → commit → report.

## Decomposed Tasks Are Complete (P#71)

When you decompose a task into children representing separate follow-up work, complete the parent immediately. Don't confuse "has children" with "work incomplete."

## Decompose Only When Adding Value (P#72)

Create child tasks only when they add information beyond the parent's bullet points. A child task with an empty body is premature decomposition.

- Validate hypotheses BEFORE decomposing into fix steps.
- Tests passing ≠ acceptance criteria met. Follow the specified methodology.
- Task bodies must be self-contained — never reference `/tmp/` files.

## Task Sequencing on Insert (P#73)

Every task MUST connect to the hierarchy: `action → task → epic → project → goal`. Disconnected tasks are violations.

**Hierarchy**: Goal (months/years, 3-5 total) → Project (weeks/months) → Epic (days/weeks) → Task (hours/days) → Action (minutes, bullet points NOT separate files).

- Before `create_task()`, search for the parent epic
- Set `parent` to link to epic (or create one if none exists)
- Use `depends_on` for explicit sequencing
- Work on one epic at a time when possible

## User System Expertise > Agent Hypotheses (P#74)

When user makes specific assertions about their own system, trust the assertion and verify with ONE minimal test. When user/task specifies a methodology, EXECUTE THAT METHODOLOGY — don't substitute your own. When user provides failure data and asks for tests, WRITE TESTS FIRST.

## Mandatory Reproduction Tests (P#82)

Every framework bug fix MUST be preceded by a failing reproduction test case. Create test → apply fix → verify test passes.

## Tasks Have Single Objectives (P#75)

Each task should have one primary objective. When work spans multiple concerns, create separate tasks with dependency relationships.

## CLI-MCP Interface Parity (P#77)

CLI commands and MCP tools exposing the same functionality MUST have identical default behavior.

## Commands Dispatch, Workflows Execute (P#76)

Command files define invocation syntax and route to workflows. Step-by-step procedural logic lives in `workflows/` directories.

## Prefer fd Over ls for File Finding (P#79)

Use `fd` for file finding instead of `ls | grep/tail` pipelines. Use deterministic sorting (`xargs ls -t | head -1`) when selecting specific files.

## Right Tool for the Work (P#78)

Agents exist to apply judgment. Using deterministic techniques for work requiring reasoning is negligence. Conversely, deterministic operations (counting, aggregation, lossless conversion) belong in existing tools, not LLM reasoning.

**Judgment warranted**: structural decisions, ambiguity, lossy transformation, trade-offs.
**Mechanical appropriate**: pure functions with no branching on semantic content.

**MCP Tool Design**: Server returns raw data; agent does all classification/selection. NO word-matching or NLP in MCP servers. Thresholds as parameters, not hardcoded.

## Fixes Preserve Spec Behavior (P#80)

Bug fixes must not remove functionality required by acceptance criteria. If the only fix removes required functionality, ask user about tradeoffs.

## Match Planning Abstraction (P#90)

When user is planning, match their level of abstraction. Don't fill in blanks until they signal readiness. Identify the vital question first (usually "what does success look like?").

## Spike Output Goes to Task Graph (P#81)

Spike/learn task output belongs in the task graph (task body, parent epic, decomposed subtasks), not random files.

## Make Cross-Project Dependencies Explicit (P#83)

When a task uses infrastructure from another project, create explicit linkage. "Incidental improvements" = separate tracked tasks, not hidden scope creep.

## Methodology Belongs to Researcher (P#84)

Methodological choices in research belong to the researcher. When implementation requires methodology not yet specified, HALT and ask. Signs: "I'll detect X by checking for Y", "I'll measure success by Z", choosing statistical tests, LLM generation parameters.

## User Intent Discovery Before Implementation (P#88)

Before implementing user-facing features, verify understanding of user intent. Ask "what question will this answer for the user?" For QA: examine ACTUAL CONTENT and ask "Would a real user find this helpful?" — element presence is insufficient.

## Error Recovery Returns to Reference (P#85)

When implementation fails and a reference example exists, re-read the reference before inventing alternatives.

## Preserve Pre-Existing Content (P#87)

Content you didn't write in this session is presumptively intentional. Append rather than replacing. Never delete existing content without explicit instruction.

## Background Agent Notifications Are Unreliable (P#86)

Never block on TaskOutput waiting for notifications. Use polling or fire-and-forget patterns. `TaskOutput(block=true)` can deadlock.

## LLM Orchestration Means LLM Execution (P#89)

When user requests content "an LLM will orchestrate/execute", create content for the LLM to read — NOT code infrastructure that parses that content.

## Verify Non-Duplication Before Batch Create (P#91)

Before creating tasks from batch input, cross-reference against existing task titles and entry_ids to avoid duplicates.

## Run Python via uv (P#93)

Always use `uv run python` (or `uv run pytest`). Never use `python`, `python3`, or `pip` directly.

## Never Edit Generated Files (P#97)

Before editing any file, check if it's auto-generated. If so, find and update the source/procedure that generates it.

## Batch Completion Requires Worker Completion (P#94)

A batch task is not complete until all spawned workers have finished. "Fire-and-forget" means don't BLOCK waiting; it does NOT mean "declare complete after spawning." Before completing a batch task, poll worker status.

## Subagent Verdicts Are Binding (P#95)

When a subagent (critic, custodiet, qa) returns a HALT or REVISE verdict, the main agent MUST stop and address the issue. Agent cannot substitute its own judgment for a failed subagent review.

## QA Tests Are Black-Box (P#96)

When executing QA/acceptance tests, treat the system as a black box. If you don't know how to execute the test procedure, FAIL the test and halt. Never investigate implementation to figure out what you're testing.

## CLI Testing Requires Extended Timeouts (P#98)

When testing CLI tools via Bash, use `timeout: 180000` (3 minutes) minimum. Default timeout is insufficient for conversational CLI tools.

## Centralized Git Versioning (P#99)

Versioning logic MUST be centralized in a single source of truth. Prefer `git tag --merged HEAD --sort=-v:refname` over `git describe`. Use explicit pattern matching to ignore noise tags.

## Plans Get Critic Review, Not Human Approval (P#100)

After filing a plan/decomposition, the next step is automated critic review. Do NOT ask user "should I proceed?" Human approval happens at PR, not at plan filing.

## Prefer Deep Functional Nesting Over Flat Projects (P#101)

Structure tasks hierarchically under functional Epics rather than flat project lists. Root project should have minimal direct children.

## Judgment Tasks Default Unassigned (P#102)

Tasks requiring human judgment default to `assignee: null`. Only mechanical/automatable work defaults to `assignee: polecat`. Assigning to `nic` requires explicit user instruction.

## QA Must Produce Independent Evidence (P#103)

QA must generate NEW evidence, not re-read the agent's own work. For bug fixes: trace the failure path independently. For features: exercise from user's perspective, not inspect code.

## Cross-Repo References Use Absolute Paths (P#104)

When task bodies reference files outside the current project, use absolute paths. Relative paths fail when sessions run from a different working directory.

## Validate Architecture Before Decomposing (P#105)

Before decomposing a task into >3 subtasks, present the architectural approach to the user and get confirmation. Use "what you gain / what you lose" format for tradeoffs.
