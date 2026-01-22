---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Working hypotheses validated by evidence.
---

# Heuristics

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

**Derivation**: Empty child tasks duplicate information without adding value. They create task sprawl and make the queue harder to navigate. Decomposition should be triggered by need (claiming work, adding detail), not by reflex.

---

## Task Sequencing on Insert (P#73)

**Statement**: When creating tasks, check for an existing project branch and insert with appropriate parent/depends_on. Projects should grow as long branches, not unconnected roots.

**Corollaries**:
- Before `create_task()`, search for related tasks in the same project
- Set `parent` to the most relevant existing task, or `depends_on` if sequential
- Root-level orphans ("thorns") fragment project coherence
- The agent is autonomous on structural improvements - don't ask "should I set parent?"
- Prefer appending at branch ENDS rather than mid-branch insertion
- Attach new work to epics/projects that are themselves at branch ends (away from trunk)
- Priority flows from tree position: tasks closer to trunk are more immediate

**Derivation**: Orphan tasks at the root level create disconnected work items. Sequential branches show progression and enable `/pull` to find contextually related work. Branch-end insertion keeps the tree coherent and makes priority implicit in structure.

---

## User System Expertise > Agent Hypotheses (P#74)

**Statement**: When user makes specific, repeated assertions about their own codebase or system behavior, trust the assertion and verify with ONE minimal test. Do NOT spawn investigation/critic/custodiet to "validate" user claims about their own system.

**Corollaries**:
- User's role: report observations from their environment
- Agent's role: verify with minimal steps, then act or report findings
- Investigate root cause ONLY if user asks "why" or if minimal verification fails
- Do NOT explain investigation reasoning ("I had to rule out X...") - just report the result

**Derivation**: Users have ground-truth about their own system. Over-investigation violates P#5 (Do One Thing) by wasting context on "proving" what the user already knows. Verification ≠ Investigation. One test: reproduce the bug, fix it, stop. P#5's warning applies: "I'll just [investigate a bit more]" is the exact friction the axiom exists to prevent.

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
