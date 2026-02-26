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

Prefer curated indices (PKB, zotero, bd) over broad filesystem searches for exploratory queries.

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

**Corollaries**:

- Task hierarchy is defined by graph relationships (`parent`, `depends_on`), not filesystem paths. Directory layout is an implementation detail of task storage.

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

## Spike Output Goes to Task Graph or GitHub (P#81)

Spike/learn output belongs in the task graph (task body, parent epic) or GitHub issues, not random files.

## Mandatory Reproduction Tests for Fixes (P#82)

Every framework bug fix MUST be preceded by a failing reproduction test case. This applies when implementing a fix, not necessarily during the initial async capture (/learn).

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

## Verify Non-Duplication Before Create (P#91)

Before creating ANY task, search existing tasks (`search_tasks`) for similar titles. This applies to single creates, not just batch operations.

## Run Python via uv (P#93)

Always use `uv run python` (or `uv run pytest`). Never use `python` or `pip` directly.

## Batch Completion Requires Worker Completion (P#94)

A batch task is not complete until all spawned workers have finished. "Fire-and-forget" means don't BLOCK waiting; it does NOT mean "declare complete after spawning."

## Subagent Verdicts Are Binding (P#95)

When a subagent (custodiet, qa) returns a HALT or REVISE verdict, the main agent MUST stop and address the issue.

**Corollaries**:

- When custodiet blocks work as out-of-scope, capture the blocked improvement as a new task before reverting. Useful work should be deferred, not lost.

**Derivation**: P#9 (Fail-Fast Agents) requires stopping when tools fail. Subagents are tools. Their failure verdicts must be respected.

## QA Tests Are Black-Box (P#96)

When executing QA/acceptance tests, treat the system as a black box. Never investigate implementation to figure out what you're testing.

## Never Edit Generated Files (P#97)

Before editing any file, check if it's auto-generated. If so, find and update the source/procedure that generates it.

## CLI Testing Requires Extended Timeouts (P#98)

When testing CLI tools via Bash, use `timeout: 180000` (3 minutes) minimum.

## Centralized Git Versioning (P#99)

Versioning logic MUST be centralized in a single source of truth.

## Prefer Deep Functional Nesting Over Flat Projects (P#101)

Structure tasks hierarchically under functional Epics rather than flat project lists.

**The Star Pattern is a code smell.** When a project has more than 5 direct children, it almost certainly needs intermediate epics. A project with 10 direct children is a flat list, not a hierarchy.

**How to fix a flat project:**
1. Group related tasks by purpose (not by type or timing)
2. Create epics that describe the milestone or workstream each group serves
3. Re-parent the tasks under the appropriate epic
4. Each epic should answer: "What outcome does this group of tasks achieve?"

**Decision heuristic:** When creating a task under a project, ask: "Is there already an epic this belongs to? Should there be?" If the task is one of several related implementation steps, the answer is almost always yes.

**Corollaries**:
- Infrastructure tasks (refactors, migrations, pipeline changes) MUST be parented under an epic that explains WHY the infrastructure work is needed. "GCS → DuckDB refactor" is never a valid direct child of a research project — it needs an epic like "Local reproducible analysis pipeline" that explains the strategic purpose.
- Leaf tasks (single-session work items) should almost never be direct children of a project. They belong under epics.

## Tasks Require Purpose Context (P#106)

Every task MUST be justifiable in terms of its parent's goals. If you can't articulate why a task exists in the context of its parent, it is either misplaced, missing an intermediate epic, or an orphan.

**The WHY test:** Before creating a task, state: "We need [task] so that [parent goal] because [reason]." If you can't complete this sentence, the task needs restructuring.

**Derivation**: Extends P#73 (Task Sequencing on Insert) from structural connection to semantic connection. A task can be connected to the graph yet still be incoherent if its purpose relative to its parent is unclear.

## Match Type to Scale (P#107)

Before creating a task, check its actual scope against the type hierarchy:

- Multiple sessions + multiple deliverables → **epic**
- One session, one deliverable → **task**
- Under 30 minutes → **action**

The most common error is creating a `type: task` for work that is actually epic-scale. "Incorporate longitudinal findings into paper" is not a task — it contains data collection, analysis, writing, and revision. It's an epic.

**Derivation**: Operationalises the type hierarchy in TASK_FORMAT_GUIDE.md. Agents systematically underestimate scope and create shallow structures. This heuristic forces a scale check before type assignment.

## Judgment Tasks Default Unassigned (P#102)

Tasks requiring human judgment default to `assignee: null`. Only mechanical work defaults to `assignee: polecat`.

**Corollaries**:

- Default to `polecat`. A task only needs `assignee: null` when it literally cannot proceed without a human decision RIGHT NOW — not because design decisions exist somewhere in the task.
- Workers decompose tasks and escalate at actual decision forks (via `status: blocked` or AskUserQuestion). Pre-routing to human based on "this involves design choices" is premature.
- Assign to `nic` only when explicitly requested by user (`/q nic: ...`).

## Skills Commit After Brain Writes (P#103)

Skills writing to `$ACA_DATA` MUST commit and push with a specific message describing what was written. Use `brain-push.sh` helper:

```bash
brain-push.sh "knowledge: tech/new-fact"
```

**Rationale**: Multiple writers (skills, task manager, /remember, manual edits) write to `$ACA_DATA`. Meaningful commit messages require the writer to say what they did—a generic sync cannot know intent.

**Implementation**:
- Primary path: Skills call `brain-push.sh "descriptive message"` after writing
- Fallback: `brain-sync.sh` runs every 5 minutes via systemd timer, generating messages from paths
- Conflict handling: Always rebase (no merge commits). On conflict, log to `${ACA_DATA}/.sync-failures.log`

**Corollaries**:
- `/remember` skill should commit with `knowledge: <topic>` message
- Task manager updates should commit with `task: <task-id>` message
- `/daily` should commit with `daily: YYYY-MM-DD` message

## Explain, Don't Ask (P#104)

When your own analysis identifies a clearly superior option among alternatives, execute the choice and explain your reasoning. Do not present options and ask the human to pick when the decision is derivable from constraints, conventions, or engineering trade-offs.

Pattern: "I'm going with X because [reasoning]. Alternatives considered: Y (rejected: [reason]), Z (rejected: [reason])."

This applies when:
- One option is strictly dominated (your analysis already says it's "fiddly" or "preserves a bad model")
- The choice follows from established project conventions
- Engineering constraints clearly favor one approach

This does NOT apply when:
- The decision involves taste, values, or genuine ambiguity
- Multiple options are genuinely equivalent with different trade-offs the user might weight differently
- The decision has irreversible consequences beyond the immediate task
- An axiom might be at risk

**Derivation**: Extends P#59 (Action Over Clarification) from task selection to implementation decisions. P#102 corollary establishes that pre-routing to human based on "this involves design choices" is premature. P#78 establishes that classification is LLM work. If an agent can classify one option as superior, asking the human is wasted attention.

## Defer User Engagement Until Work Is Done (P#108)

When the agent needs to engage the user on definitions, clarifications, or open questions, it MUST NOT do so until it has handled all other actionable work first. Premature engagement loses context.

**Pattern**: Create a follow-up task for the user interaction. Then decide whether to execute it immediately (if nothing else remains) or defer it.

**Why**: Context is precious. If the agent stops to ask "what did you mean by X?" before extracting decisions, creating tasks, and recording knowledge, the user's response will push the original work out of working memory. Handle everything you CAN handle first, then engage.

**Derivation**: Extends P#59 (Action Over Clarification). P#59 says pick a task and start; P#108 says finish all extractable work before engaging on ambiguity.

## Completion Loops Close Parent Goals (P#109)

When decomposing work into subtasks, ALWAYS create a verify-parent task that depends on all subtasks. This task returns to the original problem and confirms it's fully solved or triggers another iteration.

**Pattern**: After creating subtasks, create: `"Verify: [parent goal] fully resolved"` with `depends_on: [all-subtask-ids]` and `assignee: null`.

**Why**: Subtasks completing does not mean the parent's goal was met. Without a completion loop, work is marked done prematurely and the original problem silently persists.

**Relationship to P#71**: P#71 says complete the parent when decomposing. The verify task is not the parent — it's a NEW sibling task that checks the original goal after all implementation is done.

**Derivation**: Addresses the systemic failure mode where agents complete subtasks but nobody checks the parent epic. This is the key mechanism for reliable multi-session task execution.

## Standard Tooling Over Framework Gates (P#105)

When proposing enforcement for repo-level rules (file structure, naming, content format), prefer standard git tooling (pre-commit hooks, CI checks) over framework-internal mechanisms (PreToolUse gates, custom hooks). Framework gates control agent behavior in real-time; repo structure rules belong in git.

**Derivation**: Extends P#5 (Do One Thing) to enforcement design. The enforcement-map.md already shows the pattern: `data-markdown-only`, `check-orphan-files`, `check-skill-line-count` are all pre-commit hooks. New rules of the same kind should follow the same pattern, not escalate to a more complex enforcement layer.

## Authoritative Specs Supersede Pre-Formed Plans (P#110)

When you form a plan and then encounter authoritative documentation (specs, workflow files, CLAUDE.md, framework instructions), you MUST revise the plan to align with the documentation. Specs are not input to summarize — they override your prior hypotheses.

**The failure mode**: Agent forms plan → reads spec → presents spec accurately → repeats original plan unchanged. This is anchoring: the spec was treated as a reporting task, not a plan revision input.

**Required behavior**:

- After reading authoritative documentation, explicitly ask: "Does my plan contradict this spec?"
- If it does, revise the plan before responding
- "Spec says X, my recommendation is Y (which contradicts X)" = violation

**Derivation**: Plans formed before reading relevant documentation are hypotheses based on incomplete information. Authoritative documentation represents documented system design and decisions. Anchoring on a pre-spec hypothesis after encountering authoritative documentation is confirmation bias. The spec always wins.
