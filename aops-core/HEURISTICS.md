---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Working hypotheses validated by evidence.
---

# Heuristics

## Probabilistic Methods, Deterministic Processes (P#92)

**Statement**: The framework embraces probabilistic methods (LLM agents) while requiring deterministic processes and derivable principles. Experimentation is encouraged within clear safeguards.

**Corollaries**:
- LLMs are inherently probabilistic - we don't seek deterministic *outcomes*
- Processes (workflows, enforcement, derivation chains) must be deterministic and reproducible
- Principles must be derivable from axioms - no ad-hoc rules
- Feedback loops (P#45) enable controlled experimentation
- Fail-fast (P#8, P#9) provides safeguards against runaway experiments

**Derivation**: Attempting deterministic outcomes from probabilistic agents is futile. The framework achieves rigor through deterministic *processes* that channel probabilistic methods productively.

---

## Skills Contain No Dynamic Content (P#19)

**Statement**: Current state lives in $ACA_DATA, not in skills.

**Derivation**: Skills are shared framework infrastructure. Dynamic content in skills creates merge conflicts and state corruption.

---

## Semantic Link Density (P#54)

**Statement**: Related files MUST link to each other. Orphan files break navigation.

**Derivation**: Links create navigable knowledge graphs. Orphans are undiscoverable.

---

## File Category Classification (P#56)

**Statement**: Every file has exactly one category (spec, ref, docs, script, instruction, template, state).

**Derivation**: Mixed-category files are hard to maintain. Clear classification enables appropriate handling.

---

## Never Bypass Locks Without User Direction (P#57)

**Statement**: Agents must NOT remove or bypass lock files (sync locks, file locks, process locks) without explicit user authorization.

**Derivation**: Locks exist to prevent data corruption from concurrent operations. Removing a lock without understanding whether another process is active risks corrupting git state, SQLite databases, or file systems. Multi-agent concurrency is not currently architected. When encountering locks, agents must HALT and ask the user rather than attempting workarounds.

---

## Action Over Clarification (P#59)

**Statement**: When user signals "go" and multiple equivalent ready tasks exist, pick one and start. Don't ask for preference.

**Derivation**: Asking "which one?" when tasks are fungible wastes a round-trip. If the user cared about order, they'd specify. Bias toward motion.

---

## Indices Before Exploration (P#58)

**Statement**: Prefer curated indices (memory server, zotero, bd) over broad filesystem searches for exploratory queries.

**Derivation**: Grep is for needles, not fishing expeditions. Semantic search tools exist precisely to answer "find things related to X" - broad pattern matching across directories is wasteful and may surface irrelevant or sensitive content.

---

## Local AGENTS.md Over Central Docs (P#60)

**Statement**: Place agent instructions in the directory where agents will work, not in central docs.

**Derivation**: `lib/AGENTS.md` is discovered when an agent enters `lib/`. A `docs/SUBMODULES.md` linked from root requires agents to know the link exists. Discoverability beats indirection.

---

## Internal Records Before External APIs (P#61)

**Statement**: When user asks "do we have a record" or "what do we know about X", search bd and memory FIRST before querying external APIs.
**Derivation**: "Do we have" implies checking our knowledge stores, not fetching new data. Internal-first respects the question's scope and avoids unnecessary API calls.

---

## Tasks Inherit Session Context (P#62)

**Statement**: When creating tasks during a session, apply relevant session context (e.g., `bot-assigned` tag during triage, project tag during project work).

**Derivation**: Tasks created mid-session often share properties with the session's focus. A bug found during bot-triage is likely bot-fixable. Carrying context forward reduces manual re-tagging.

---

## Task Output Includes IDs (P#63)

**Statement**: When displaying tasks to users (lists, trees, summaries), always include the task ID.

**Derivation**: Task IDs are required for all task operations (update, complete, get). Omitting IDs forces users to look up what they just saw. Format: `Title (id: task-id)` or table with ID column.

---

## Planning Guidance Goes to Daily Note (P#64)

**Statement**: When effectual-planner or similar prioritization agents provide guidance, write output to daily note. Do NOT execute the recommended tasks.

**Derivation**: User asking "help me prioritize" wants GUIDANCE FOR THEMSELVES, not automated execution. The agent's job is to surface the plan, not act on it. User controls execution timing. Write marching orders to daily note via /daily skill, then STOP.

---

## Enforcement Changes Require enforcement-map.md Update (P#65)

**Statement**: When adding enforcement measures (AXIOMS, HEURISTICS, CORE.md context, hooks), update enforcement-map.md to document the new rule.

**Derivation**: enforcement-map.md is the enforcement index - it tracks what's shown to agents, when, and why. Undocumented enforcement creates invisible constraints. All information-forcing measures must be auditable.

---

## Just-In-Time Information (P#66)

**Statement**: Never present information that is not necessary to the task at hand.

**Corollaries**:
- When hydrator provides specific guidance (e.g., "look for tests", "verify interactively"), follow that guidance rather than investigating from first principles. The hydrator has already done the context analysis.

**Derivation**: Cognitive load degrades performance. Context should be loaded on-demand when relevant, not front-loaded speculatively. This enables focused work and supports the hydrator's JIT context loading pattern.

---

## Extract Implies Persist in PKM Context (P#67)

**Statement**: When user asks to "extract information from X", route to remember/persist workflow, not simple-question.

**Derivation**: "Extract" is ambiguous - it can mean "tell me" or "file away." In a PKM system with remember capability, extract + named entities (projects, people, bugs) + document source implies knowledge should be STORED, not just displayed. Simple-question is only appropriate when the user clearly wants information returned to them without persistence.

---

## Background Agent Visibility (P#68)

**Statement**: When spawning background agents, explicitly tell the user: what agents are spawning, that tool output will scroll by, and when the main task is complete.

**Derivation**: Background agent tool calls appear in the Claude Code interface alongside main agent output. Users cannot distinguish "agent still working" from "background tasks running while main agent is done." Without explicit signaling, users wait unnecessarily or interrupt completed work. Say: "I'm spawning N background agents to [task]. You'll see their tool calls scroll by. The main task is complete - check back later or wait for notifications."

---

## Large Data Handoff (P#69)

**Statement**: When data exceeds ~10KB or requires visual inspection for user sign-off, provide the file path and suggested commands (jq, IDE) instead of attempting to display inline.

**Derivation**: Large JSON, logs, or structured data are better inspected with user tooling (jq, IDE, grep). Attempting workarounds (chunked reads, head/tail) wastes cycles. Recognize handoff scenarios on first attempt: user says "show me the full X" + data is large = provide path and commands.

---

## Trust Version Control (P#70)

**Statement**: When removing or modifying files, delete them outright rather than creating backup copies. Trust git.

**Derivation**: Git history preserves all prior versions. Creating `.backup`, `.old`, or `.bak` copies adds noise and implies distrust in the recovery mechanism already in place. If content is recoverable via `git checkout` or `git show`, the backup is redundant. Delete cleanly.

---

## No Commit Hesitation (P#24)

**Statement**: After making bounded changes, commit immediately. Never ask permission to commit in any form.

**Corollaries**:
- NEVER output: "Would you like me to commit?", "Ready to commit?", "Should I push?", or any variant
- Complete the work → commit → report what you did. No pause for permission.

**Derivation**: Asking "should I commit?", "want me to commit?", "ready to push?", or any variant wastes a round-trip and signals uncertainty. Bounded, low-risk changes (single-file edits, config tweaks, rollbacks) should be committed as part of the action. User controls via git - they can revert if needed.

---

## Decomposed Tasks Are Complete (P#71)

**Statement**: When you decompose a task into children representing separate follow-up work, complete the parent immediately. Children can be siblings (next work), not blockers.

**Derivation**: Parent completion guard blocks completing parents with *incomplete subtasks of the same work*. But decomposition for learn/design/spike tasks creates *follow-up* work - the parent task IS done once decomposition is complete. Don't confuse "has children" with "work incomplete."

---

## Decompose Only When Adding Value (P#72)

**Statement**: Create child tasks only when they add information beyond the parent's bullet points - acceptance criteria, dependencies, distinct ownership, or execution context. Until then, keep items as bullets in the parent body.

**Corollaries**:
- A child task with an empty body (just title) is a sign of premature decomposition
- Decompose when work is claimed OR when subtasks need independent tracking
- Numbered lists in parent body are sufficient for planning; tasks are for execution
- For debugging tasks, validate the hypothesis (e.g., "working version exists at commit X") BEFORE decomposing into fix steps. An unvalidated hypothesis leads to wasted subtasks.
- **Tests passing ≠ acceptance criteria met**. When a task specifies a methodology (e.g., "use git bisect"), follow the methodology. A passing test found by a different path doesn't satisfy "identify the breaking commit."
- **Task bodies must be self-contained**. Tasks are long-lived; `/tmp/` is ephemeral. Never reference temporary files in task bodies - include all required details inline or persist data to `$ACA_DATA/` first.

**Derivation**: Empty child tasks duplicate information without adding value. They create task sprawl and make the queue harder to navigate. Decomposition should be triggered by need (claiming work, adding detail), not by reflex.

---

## Task Sequencing on Insert (P#73)

**Statement**: The creating agent is responsible for inserting tasks onto the work graph. Every task MUST connect to the hierarchy: `action → task → epic → project → goal`. Disconnected tasks are violations.

**Hierarchy definitions**:
- **Goal**: Strategic life outcome (months/years). You have 3-5 goals total - "World-Class Academic Profile", "Get Paid", "Be Happy". If you're creating more than 5, you're misusing this type.
- **Project**: Bounded initiative with deliverables (weeks/months) - "Reliability Paper", "v1.1 Framework Release". Projects live under goals.
- **Epic**: Group of tasks toward a milestone (days/weeks) - "Implement batch processing". Epics live under projects.
- **Task**: Discrete piece of work (hours/days) - "Fix hydrator bug". Tasks are files with IDs.
- **Action**: Single atomic step (minutes) - "Run tests". Actions are bullet points in task bodies, NOT separate files.

**Sequencing principle**: Work on one epic at a time when possible. Epics are the unit of focus - completing an epic before starting another reduces context-switching and makes progress visible.

**Corollaries**:
- Before `create_task()`, search for the parent epic in the project
- Set `parent` to link to epic (or create one if none exists)
- Use `depends_on` for explicit sequencing between tasks within an epic
- Root-level orphans ("thorns") are invisible to prioritization and sequencing
- The agent is autonomous on structural decisions - don't ask "should I set parent?"
- If no suitable epic exists, create one that links to the project
- Priority flows from tree position: tasks closer to trunk are more immediate

**Derivation**: Orphan tasks fragment project coherence and become invisible to prioritization. The task graph visualization reveals structural gaps - 15 disconnected components instead of 3-5 indicates missing links. Agents must maintain graph integrity on every insert.

---

## User System Expertise > Agent Hypotheses (P#74)

**Statement**: When user makes specific, repeated assertions about their own codebase or system behavior, trust the assertion and verify with ONE minimal test. Do NOT spawn investigation/critic/custodiet to "validate" user claims about their own system.

**Corollaries**:
- User's role: report observations from their environment
- Agent's role: verify with minimal steps, then act or report findings
- Investigate root cause ONLY if user asks "why" or if minimal verification fails
- Do NOT explain investigation reasoning ("I had to rule out X...") - just report the result
- **When user/task specifies a methodology, EXECUTE THAT METHODOLOGY.** Do not substitute your own approach. "User says git bisect" → do git bisect. "User says X worked yesterday" → it's a regression, find when it broke.
- **When user provides failure data and asks for tests, WRITE TESTS FIRST.** Capture the observed behavior as test fixtures immediately. Do not investigate root cause before producing the requested artifact.

**Derivation**: Users have ground-truth about their own system. Over-investigation violates P#5 (Do One Thing) by wasting context on "proving" what the user already knows. Verification ≠ Investigation. One test: reproduce the bug, fix it, stop. P#5's warning applies: "I'll just [investigate a bit more]" is the exact friction the axiom exists to prevent.

---

## Mandatory Reproduction Tests (P#82)

**Statement**: Every framework bug fix MUST be preceded by a failing reproduction test case.

**Derivation**: Fixing bugs without a failing test leads to "success theater" where the agent claims a fix that might not address the root cause or might regress. A failing test provides objective proof of the bug and objective proof of the fix.

**Protocol**: 
1. Identify the failing input/state.
2. Create a test in `tests/` that fails with that input.
3. Apply the fix.
4. Verify the test passes.

---

## Tasks Have Single Objectives (P#75)

**Statement**: Each task should have one primary objective. When work spans multiple concerns (execute work + improve framework, verify fix + document pattern), create separate tasks with dependency relationships.

**Corollaries**:
- Executing work is separate from reflecting on/improving the framework that guided it
- Verification work is separate from documenting patterns learned
- If task description contains "AND THEN" or combines action + meta-work, decompose
- Use depends_on to create accountability chain: primary work completes first, then reflection/improvement

**Example**:
- Task A: "Verify Unicode fix resolves Gemini error" (primary work)
- Task B: "[Learn] Task structure - separate verification from framework improvement" (meta-work, depends_on: A)

**Derivation**: Mixed-objective tasks obscure completion criteria and make it unclear whether the task is done. Single-objective tasks with explicit dependencies create clear accountability and enable proper sequencing of work vs. meta-work.

---

## CLI-MCP Interface Parity (P#77)

**Statement**: CLI commands and MCP tools exposing the same functionality MUST have identical default behavior. Users should get the same result whether using CLI or MCP.

**Corollaries**:
- Same function, same defaults: If MCP `list_tasks` defaults to `limit=10`, CLI `task list` must too
- CLI may offer convenience flags (`--all`) but defaults must match MCP
- When adding features to one interface, update the other

**Derivation**: Divergent interfaces cause user confusion and enable agent lies. "The CLI shows all tasks" vs "MCP shows one task" creates false claims about system behavior. Single source of truth requires interface parity.

---

## Commands Dispatch, Workflows Execute (P#76)

**Statement**: Command files define invocation syntax and route to workflows. Step-by-step procedural logic lives in `workflows/` directories.

**Boundary definition**:
- Commands: Argument parsing, validation, error presentation, dispatch to agent or workflow reference
- Workflows: Sequential steps, state transitions, retries, agent orchestration, branching logic

**Corollaries**:
- Commands reference workflows via `See [[workflow-name]]` or spawn agents that execute workflows
- Workflows are reusable across different entry points (commands, skills, agents)
- When a command exceeds ~30 lines, check if procedural logic should move to a workflow

**Derivation**: Commands are UI (invocation interface). Workflows are business logic (procedure). Mixing them creates non-reusable, non-configurable procedures tightly coupled to one entry point. P#47 (Agents Execute Workflows) establishes that workflows are the unit of reusable procedure.

---

## Prefer fd Over ls for File Finding (P#79)

**Statement**: Use `fd` for file finding operations instead of `ls | grep/tail` pipelines. Use specific patterns to avoid false positives.

**Examples**:
- Find recent hook logs: `fd -l --newer 1h "hook.*jsonl"` (not `ls *.jsonl | tail`)
- Find files by type: `fd -e py` (not `ls *.py`)
- Find with time filter: `fd --changed-within 1d` (not `find -mtime`)

**Corollaries**:
- Before creating a file in a new location, use `fd` to discover if related files already exist elsewhere
- Example: Before creating `data/osb/osb.md`, run `fd "osb\|oversight" $ACA_DATA` to find existing locations

**Derivation**: fd is faster, has built-in time filtering, and respects .gitignore. Generic `ls *.jsonl` matches unintended files (transcripts vs hooks). Specific patterns prevent deceptive results.

---

## Deterministic Computation Stays in Code (P#78)

**Statement**: LLMs are bad at counting, aggregation, and numerical computation. Use Python/scripts for deterministic operations; LLMs for judgment, classification, and generation.

**Examples**:
- Token counting → transcript_parser.py UsageStats (not LLM)
- File counts, line counts → glob/wc (not LLM)
- Data aggregation → pandas/SQL (not LLM)
- Pattern matching on logs → Python (not LLM)

**Corollaries (MCP Tool Design)**:
- Server returns **raw data** (counts, metrics, lists); agent does **all classification/selection**
- NO word-matching, fuzzy search, or NLP in MCP servers - agent uses LLM for similarity
- Thresholds as **parameters** (agent decides), not hardcoded constants
- If a tool name contains "candidates", "similar", or "suggest" → wrong boundary, redesign

**Derivation**: LLMs hallucinate numbers and fail at counting. Deterministic operations have exact solutions that code computes reliably. Session logs and hook logs already exist - process them with Python, not inference.

---

## Fixes Preserve Spec Behavior (P#80)

**Statement**: Bug fixes must not remove functionality required by acceptance criteria. When a proposed fix would remove spec-required behavior, either ask user for clarification or find a fix that preserves the behavior.

**Corollaries**:
- Before proposing a fix, check the spec's acceptance criteria
- "Node selection shows task details" in spec → fix cannot remove click interaction
- If the only fix removes required functionality → ask user about acceptable tradeoffs

**Derivation**: Specs define required behavior. A "fix" that removes required functionality is a design change requiring user approval, not a bug fix. P#31 (Acceptance Criteria Own Success) establishes that only user-defined criteria determine completion.

---

## Match Planning Abstraction (P#90)

**Statement**: When user is deconstructing/planning, match their level of abstraction. Don't fill in blanks until they signal readiness for specifics.

**Signals of planning phase**:
- "Let's figure out...", "What are we building...", "First steps first..."
- Questions being explored, decisions not yet made
- User providing partial answers with room for more discussion

**Signals of execution phase**:
- "Let's do it", "Go ahead", specific values provided
- User answering all questions, decisions finalized

**Corollaries**:
- If user says "we need to decide X, Y, Z" - help explore, don't propose X=foo, Y=bar
- If user answers 2 of 3 questions, ask about the 3rd - don't assume
- Premature specifics break the user's planning flow
- **Vital question first**: During planning, identify the vital question (usually "what does success look like?") before listing implementation details. Success criteria unlock everything else; notebook contents don't.

**Derivation**: P#5 (Do One Thing) applies to abstraction level too. When user is planning, the task is planning - not executing. Jumping to implementation details violates the requested scope.

---

## Spike Output Goes to Task Graph (P#81)

**Statement**: Spike/learn task output belongs in the task graph, not random files. Write findings to: (1) task body, (2) parent epic "Findings from Spikes" section, (3) decomposed subtasks for actionable items.

**Corollaries**:
- NEVER create standalone markdown files for spike output
- If task doesn't specify output location, output goes to task body
- Actionable findings become subtasks with depends_on relationships
- Parent epic inherits summary for sibling task context

**Derivation**: Random output files are orphaned from the task graph. Task body is the canonical location for work products. Decomposition ensures findings become executable work.

---

## Make Cross-Project Dependencies Explicit (P#83)

**Statement**: When a task uses infrastructure from another project as its implementation vehicle, create explicit linkage: (1) document in task body, (2) add soft_depends_on to infrastructure project task if exists, (3) create sibling task for infrastructure improvements discovered.

**Corollaries**:
- Using buttermilk pipeline for OSB work → document "also testing buttermilk batch" in task body
- Discovering buttermilk bug during OSB work → create buttermilk task, link via soft_depends_on
- "Incidental improvements" = separate tracked tasks, not hidden scope creep

**Derivation**: P#22 (Dogfooding) encourages using real work to test infrastructure. But dual-purpose work has dual objectives (P#75 violation) unless both are tracked. Explicit cross-project links make infrastructure improvements visible and prevent the secondary work from being lost.

---

## Methodology Belongs to Researcher (P#84)

**Statement**: Methodological choices in research (how to classify, measure, or evaluate) belong to the researcher. When implementation requires methodology not yet specified, HALT and ask - do not invent approaches.

**Signs you're making a methodological choice**:
- "I'll detect X by checking for Y" (classification method)
- "I'll measure success by Z" (evaluation criteria)
- "I'll use pattern matching to identify..." (measurement approach)

**Corollaries**:
- Text matching for LLM output classification → methodological choice, needs researcher approval
- Defining evaluation rubrics → methodological choice, needs researcher approval
- Choosing statistical tests → methodological choice, needs researcher approval
- LLM generation parameters (temperature, max_tokens, top_p) → methodological choice, needs researcher approval
- Building infrastructure to RUN an evaluation → agent work, proceed

**Derivation**: Research methodology requires disciplinary expertise and ethical oversight that agents cannot provide. P#48 (Human Tasks) establishes that decisions requiring human judgment route back to users. Methodology is inherently such a decision. P#8 (Fail-Fast) requires halting on uncertainty rather than inventing fallbacks - this applies to methodological uncertainty too.

---

## User Intent Discovery Before Implementation (P#88)

**Statement**: Before implementing user-facing features, verify understanding of user intent, not just technical requirements. Ask "what question will this answer for the user?" before building.

**Signs you're skipping intent discovery**:
- Building from spec without asking "who uses this and what pain point does it solve?"
- Acceptance criteria describe code behavior ("displays X") without user outcome ("user can determine Y")
- Feature passes technical review but user says "this isn't useful"

**Practice**:
- Document user workflow in epic body: who uses this, what pain points, what success looks like
- Include user-centric litmus tests: "Can user answer [specific question]?" not just "Does code run?"
- When unclear about user value, ASK rather than assume and build
- Validation checks user value, not just technical correctness
- Before completion, QA must verify deliverables against ORIGINAL user prompt, not derived acceptance criteria

**Evidence**: Session 2026-02-03 - agent built "499 agents working" dashboard feature showing `unknown: No specific task` for every entry. Feature passed planning and technical review but provided zero value to user. The spec described WHAT to display without WHY users need it.

**Evidence 2**: Same session - QA acceptance test passed "Session Display 5/5" by checking element presence ("WHERE YOU LEFT OFF exists") without examining content. Actual content showed "now unknown ok" - completely useless. QA used Playwright to verify UI element existence, not whether the content answered user questions.

**QA Verification Corollary**: For user-facing features, automated tests (element presence, string matching) are INSUFFICIENT. QA must examine ACTUAL CONTENT and ask: "Would a real user find this helpful?" Content showing "unknown", placeholder text, or meaningless data is a FAILURE regardless of whether UI elements exist. Output screenshots/samples and make explicit user-value judgments.

**Epic Verification Corollary**: User-facing features MUST belong to an epic with a qualitative verification step. The epic acceptance criteria must include "run the actual interface and verify it addresses the original user need." Individual subtasks may pass technical QA, but epic completion requires qualitative user-value assessment.

**Handover Epic Context Corollary**: When completing a task that has a parent epic, handover MUST report: (1) remaining work on the epic, (2) whether epic is now ready for qualitative verification. This ensures visibility into feature completion state, not just subtask completion.

**Monitoring Task Corollary**: For tasks involving monitoring or observation ("assess", "observe", "watch", "evaluate how X is going"), acceptance criteria must include OUTCOME verification, not just INITIATION verification. Starting a process ≠ evaluating its results. Criteria must include: observed completions, measured performance, or evaluated quality—not just "process started successfully."

**Derivation**: P#31 (Acceptance Criteria Own Success) and P#74 (User System Expertise) establish user as authority on success. This heuristic operationalizes: verify understanding of user intent BEFORE building, not just validate technical correctness after.

---

## Error Recovery Returns to Reference (P#85)

**Statement**: When implementation fails and a reference example exists, re-read the reference before inventing alternatives.

**Corollaries**:
- Error → problem-solving mode is the wrong instinct when following an example
- Error → "what does the reference actually do?" is the right first question
- If reference uses X and you tried Y, fix is to use X, not to simplify to Z

**Derivation**: P#3 says "adapt the example directly, don't re-implement." This applies equally during error recovery. Errors don't license divergence from the reference - they signal that you haven't matched it closely enough.

---

## Preserve Pre-Existing Content (P#87)

**Statement**: Content you didn't write in this session is presumptively intentional. Append new content rather than replacing. Never delete existing content without explicit instruction. Never "correct" content you assume is wrong.

**Corollaries**:
- "Looks wrong" is not justification for deletion
- When instructed to update a section, preserve unrelated sections intact
- If content genuinely appears erroneous, flag it for user review rather than fixing

**Derivation**: You cannot know who wrote content. Multi-agent collaboration, past-self context, and deliberate user choices all look identical. Unilateral "cleanup" destroys information the agent cannot reconstruct. Git recovery exists but imposes friction and context loss.

---

## Background Agent Notifications Are Unreliable (P#86)

**Statement**: Claude Code background task completion notifications may not arrive or may be delayed. Never block on TaskOutput waiting for notifications. Use polling or fire-and-forget patterns.

**Empirical Evidence (2026-01-22 hypervisor test)**:
- 4/5 (80%) notification delivery observed with 5 parallel workers
- Delivered notifications were delayed 2-5 minutes
- `TaskOutput(block=true)` can deadlock when notifications fail to arrive
- Output files are cleaned up after completion, making post-hoc analysis difficult

**Workaround Patterns**:
- **Fire-and-forget**: Spawn workers, continue other work, don't wait for completion
- **MCP status polling**: Check task status directly via `get_task` MCP calls
- **Never use** `TaskOutput(block=true)` with background agents

**Example (polling pattern)**:
```python
# Instead of blocking:
# TaskOutput(task_id=id, block=true)  # DEADLOCK RISK

# Poll MCP task status or just continue other work
# Workers will update task status when done
mcp__plugin_aops-tools_task_manager__get_task(id="...")
# Check if status == "done"
```

**Derivation**: Empirical observation from hypervisor testing (see specs/worker-hypervisor.md "Empirical Findings"). P#8 (Fail-Fast) says we should fail on unreliable dependencies - notification-blocking supervision patterns fail silently via deadlock instead.

---

## LLM Orchestration Means LLM Execution (P#89)

**Statement**: When user requests content "an LLM will orchestrate/execute", create content for the LLM to read and act on directly - NOT code infrastructure that parses that content.

**Signs you're violating this**:
- Creating Python runners for "LLM-orchestrated tests"
- Building parsing/execution infrastructure for "agent-readable" documents
- Inserting automation layer between LLM and the content it was meant to read

**Corollaries**:
- "LLM will read and act" → markdown with clear instructions for LLM
- "Code/automation will read and act" → structured data + parsing code
- When ambiguous about execution model, ask

**Derivation**: Category error prevention. "LLM orchestration" describes WHO executes (the LLM), not HOW to build tooling around it. P#78's "code for deterministic computation" reinforces: semantic interpretation is LLM work.

---

## Verify Non-Duplication Before Batch Create (P#91)

**Statement**: Before creating tasks from batch input (email triage, backlog import, etc.), cross-reference against existing task titles and entry_ids to avoid duplicates.

**Corollaries**:
- Query existing tasks BEFORE processing inbox items
- Compare email entry_ids and subject lines against existing task bodies
- Apply workflow classification rules (Task/FYI/Skip) - not every item needs a task
- For email triage specifically: check sent mail for existing replies first

**Derivation**: Corollary of P#26 (Verify First) and P#58 (Indices Before Exploration). Batch operations without deduplication create noise and duplicate work. The task index is the authoritative source - query it first.

---

## Run Python via uv (P#93)

**Statement**: Always use `uv run python` (or `uv run pytest`) to execute Python code. Never use `python`, `python3`, or `pip` directly.

**Derivation**: `uv` manages the virtual environment and dependencies. System python lacks the project context. `uv run` guarantees the correct environment is active without manual activation steps.

---

## Batch Completion Requires Worker Completion (P#94)

**Statement**: A batch task is not complete until all spawned workers have finished. "Fire-and-forget" means don't BLOCK waiting; it does NOT mean "declare complete after spawning."

**Corollaries**:
- Spawning workers is the START of batch work, not completion
- Before completing a batch task, poll worker status via MCP `get_task` calls
- If session must end with workers still running: set task status to `waiting`, not `done`
- Handover with active workers requires `outcome: partial` and explicit "delegated work in progress" note
- Workers updating task status to `done` is the signal for batch completion, not spawn confirmation

**Signs you're violating this**:
- Completing batch task immediately after spawning workers
- Using "fire-and-forget" as justification for marking work complete
- Handover claiming completion while background agents still running

**Example (correct pattern)**:
```python
# Spawn workers (don't block)
for task in batch:
    Task(subagent_type="worker", prompt=task, run_in_background=True)

# Continue other work while workers run...

# Before completing batch task, check worker status
for worker_task_id in spawned_ids:
    status = mcp__task_manager__get_task(id=worker_task_id)
    if status["task"]["status"] != "done":
        # Workers still running - cannot complete batch
        mcp__task_manager__update_task(id=batch_task_id, status="waiting")
        return  # Don't mark complete

# All workers done - NOW complete the batch task
mcp__task_manager__complete_task(id=batch_task_id)
```

**Derivation**: P#86 (Background Notifications Unreliable) correctly recommends not blocking on notifications. But "don't block" was over-applied to mean "declare done immediately." The correct interpretation: continue other work while monitoring, but verify completion before declaring the batch task done. Premature completion violates P#31 (Acceptance Criteria Own Success) - the batch task's success criteria is "all work processed," not "all work delegated."

---

## Subagent Verdicts Are Binding (P#95)

**Statement**: When a subagent (critic, custodiet, qa) returns a HALT or REVISE verdict, the main agent MUST stop and address the issue. Proceeding after a blocking verdict is a protocol violation.

**Corollaries**:
- "HALT" from critic → don't proceed with plan, fix the blocking issue first
- "HALT" from custodiet → don't proceed with action, address the violation
- "REVISE" from qa → fix identified issues before claiming complete
- Agent cannot substitute its own judgment for a failed subagent review
- If subagent fails to execute (file not found, tool error), that is also a HALT condition

**Derivation**: P#9 (Fail-Fast Agents) requires stopping when tools fail. Subagents are tools. Their failure verdicts must be respected - the agent cannot self-certify when external review is mandated.

