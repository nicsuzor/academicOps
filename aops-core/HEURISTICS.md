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

## Indices Before Exploration (P#58)

Prefer curated indices (memory server, zotero, bd) over broad filesystem searches for exploratory queries.

**Corollaries**:
- Grep is for needles, not fishing expeditions
- Semantic search tools exist precisely to answer "find things related to X"
- Broad pattern matching across directories is wasteful and may surface irrelevant or sensitive content
- GLOSSARY.md provides framework terminology — don't search for what's already defined

**Derivation**: This is the key heuristic preventing unnecessary exploration. When you don't know a term, check the glossary. When you need context, it should be pre-loaded. Filesystem exploration is a last resort, not a first instinct.

## Action Over Clarification (P#59)

When user signals "go" and multiple equivalent ready tasks exist, pick one and start. Don't ask for preference.

## Local AGENTS.md Over Central Docs (P#60)

Place agent instructions in the directory where agents will work, not in central docs.

## Internal Records Before External APIs (P#61)

When user asks "do we have a record" or "what do we know about X", search bd and memory FIRST before querying external APIs.

## Tasks Inherit Session Context (P#62)

When creating tasks during a session, apply relevant session context (e.g., `bot-assigned` tag during triage).

## Task Output Includes IDs (P#63)

When displaying tasks to users, always include the task ID. Format: `Title (id: task-id)`.

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

After making bounded changes, commit immediately. NEVER ask "Would you like me to commit?" or any variant.

## Decomposed Tasks Are Complete (P#71)

When you decompose a task into children representing separate follow-up work, complete the parent immediately.

## Decompose Only When Adding Value (P#72)

Create child tasks only when they add information beyond the parent's bullet points. Empty child tasks are premature decomposition.

## Task Sequencing on Insert (P#73)

Every task MUST connect to the hierarchy: `action → task → epic → project → goal`. Disconnected tasks are violations.

## User System Expertise > Agent Hypotheses (P#74)

When user makes specific assertions about their own codebase, trust the assertion and verify with ONE minimal test. Do NOT spawn investigation to "validate" user claims.

**Corollaries**:
- When user/task specifies a methodology, EXECUTE THAT METHODOLOGY
- When user provides failure data and asks for tests, WRITE TESTS FIRST

**Derivation**: Users have ground-truth about their own system. Over-investigation violates P#5 (Do One Thing). Verification ≠ Investigation.

## Tasks Have Single Objectives (P#75)

Each task should have one primary objective. When work spans multiple concerns, create separate tasks with dependency relationships.

## Commands Dispatch, Workflows Execute (P#76)

Command files define invocation syntax and route to workflows. Step-by-step logic lives in `workflows/`.

## CLI-MCP Interface Parity (P#77)

CLI commands and MCP tools exposing the same functionality MUST have identical default behavior.

## Deterministic Computation Stays in Code (P#78)

LLMs are bad at counting and aggregation. Use Python/scripts for deterministic operations; LLMs for judgment, classification, and generation. MCP servers return raw data; agents do all classification/selection.

## Prefer fd Over ls for File Finding (P#79)

Use `fd` for file finding operations instead of `ls | grep/tail` pipelines.

## Fixes Preserve Spec Behavior (P#80)

Bug fixes must not remove functionality required by acceptance criteria.

## Spike Output Goes to Task Graph (P#81)

Spike/learn task output belongs in the task graph (task body, parent epic), not random files.

## Mandatory Reproduction Tests (P#82)

Every framework bug fix MUST be preceded by a failing reproduction test case.

## Make Cross-Project Dependencies Explicit (P#83)

When a task uses infrastructure from another project, create explicit linkage.

## Methodology Belongs to Researcher (P#84)

Methodological choices in research belong to the researcher. When implementation requires methodology not yet specified, HALT and ask.

## Error Recovery Returns to Reference (P#85)

When implementation fails and a reference example exists, re-read the reference before inventing alternatives.

## Background Agent Notifications Are Unreliable (P#86)

Never block on TaskOutput waiting for notifications. Use polling or fire-and-forget patterns.

## Preserve Pre-Existing Content (P#87)

Content you didn't write in this session is presumptively intentional. Append rather than replace. Never delete without explicit instruction.

**Corollaries**:
- Files must be self-contained. Never write forward-references to conversational output (e.g., "See detailed analysis below") — persist all substantive content in the file itself. Response text is ephemeral; files are state.

## User Intent Discovery Before Implementation (P#88)

Before implementing user-facing features, verify understanding of user intent, not just technical requirements.

## LLM Orchestration Means LLM Execution (P#89)

When user requests content "an LLM will orchestrate/execute", create content for the LLM to read directly — NOT code infrastructure that parses that content.

## Match Planning Abstraction (P#90)

When user is deconstructing/planning, match their level of abstraction. Don't fill in blanks until they signal readiness for specifics.

## Verify Non-Duplication Before Batch Create (P#91)

Before creating tasks from batch input, cross-reference against existing task titles to avoid duplicates.

## Run Python via uv (P#93)

Always use `uv run python` (or `uv run pytest`). Never use `python` or `pip` directly.

## Batch Completion Requires Worker Completion (P#94)

A batch task is not complete until all spawned workers have finished. "Fire-and-forget" means don't BLOCK waiting; it does NOT mean "declare complete after spawning."

## Subagent Verdicts Are Binding (P#95)

When a subagent (critic, custodiet, qa) returns a HALT or REVISE verdict, the main agent MUST stop and address the issue.

**Derivation**: P#9 (Fail-Fast Agents) requires stopping when tools fail. Subagents are tools. Their failure verdicts must be respected.

## QA Tests Are Black-Box (P#96)

When executing QA/acceptance tests, treat the system as a black box. Never investigate implementation to figure out what you're testing.

## Never Edit Generated Files (P#97)

Before editing any file, check if it's auto-generated. If so, find and update the source/procedure that generates it.

## CLI Testing Requires Extended Timeouts (P#98)

When testing CLI tools via Bash, use `timeout: 180000` (3 minutes) minimum.

## Centralized Git Versioning (P#99)

Versioning logic MUST be centralized in a single source of truth.

## Plans Get Critic Review, Not Human Approval (P#100)

After filing a plan or decomposition, the next step is automated critic review. Human approval happens at PR, not at plan filing.

## Prefer Deep Functional Nesting Over Flat Projects (P#101)

Structure tasks hierarchically under functional Epics rather than flat project lists.

## Judgment Tasks Default Unassigned (P#102)

Tasks requiring human judgment default to `assignee: null`. Only mechanical work defaults to `assignee: polecat`.

**Corollaries**:

- Default to `polecat`. A task only needs `assignee: null` when it literally cannot proceed without a human decision RIGHT NOW — not because design decisions exist somewhere in the task.
- Workers decompose tasks and escalate at actual decision forks (via `status: blocked` or AskUserQuestion). Pre-routing to human based on "this involves design choices" is premature.
- Assign to `nic` only when explicitly requested by user (`/q nic: ...`).

## Skills Commit After Brain Writes (P#103)

Skills writing to `~/brain` MUST commit and push with a specific message describing what was written. Use `brain-push.sh` helper:

```bash
brain-push.sh "knowledge: tech/new-fact"
```

**Rationale**: Multiple writers (skills, task manager, /remember, manual edits) write to ~/brain. Meaningful commit messages require the writer to say what they did—a generic sync cannot know intent.

**Implementation**:
- Primary path: Skills call `brain-push.sh "descriptive message"` after writing
- Fallback: `brain-sync.sh` runs every 5 minutes via systemd timer, generating messages from paths
- Conflict handling: Always rebase (no merge commits). On conflict, log to `~/.brain/.sync-failures.log`

**Corollaries**:
- `/remember` skill should commit with `knowledge: <topic>` message
- Task manager updates should commit with `task: <task-id>` message
- `/daily` should commit with `daily: YYYY-MM-DD` message
