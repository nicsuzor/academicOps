---
name: heuristics
title: Heuristics
type: instruction
category: instruction
description: Working hypotheses validated by evidence.
---

# Heuristics

## Don't abdicate your responsibility

Use your discretion. Do not defer judgment calls to the user.

- Auto-assigning judgment tasks to user creates unnecessary noise
- Human attention is the scarcest resource. Tasks should be pulled (claimed) rather than pushed (assigned) unless explicitly requested.

## Project Independence (P#7)

Projects must work independently without cross-dependencies.

## Single-Purpose Files (P#11)

Every file has ONE defined audience and ONE defined purpose.

## Write For The Long Term (P#28)

NEVER create single-use scripts or tests. Inline verification commands (`python -c`, `bash -c`) ARE single-use artifacts — write tests in `tests/`.

## Minimal Instructions (P#44)

Framework instructions should be no more detailed than required. Brevity reduces cognitive load and token cost.

## Imminent Deadline Surfacing (H91)

**Imminent deadlines MUST surface regardless of task status.** A `blocked` or `in_progress` task with a deadline in the current "safe horizon" (default: 7 days) is more important than a `ready` task with no deadline. The `focus_score` calculation must escalate exponentially as the deadline approaches to ensure high-priority surfacing — this escalation enters via the `urgency` term within `focus_score` (see [[multi-parent]] §7 for the canonical composite). Priority labels (P0–P4) are defined canonically in [[PRIORITY.md]].

- **Check**: Does `pkb focus` show tasks due this week that are `blocked`?
- **Check**: Does the `focus_score` increase daily for tasks with a `due` date (via the `urgency` component)?
- **Violation**: Filtering for `status: ready` before computing focus_score, causing deadlines to be hidden.

## Feedback Loops For Uncertainty (P#45)

When the solution is unknown, don't guess — set up a feedback loop. Make minimal intervention, wait for evidence, revise hypothesis.

## Read-Then-Write Memory (P#52)

Before generating insights, search existing knowledge. Memory is read-then-write, never write-only.

**Corollaries**:

- Before analyzing a topic, search PKB for: people mentioned, related goals, prior reflections, and analogous situations.
- Generating new insights without reading existing context risks reinventing or contradicting accumulated knowledge.
- The `/remember` skill's mandatory "search first" step is the model for all knowledge-generating agents.

**Derivation**: Knowledge accumulates across sessions. An agent that writes without reading produces a siloed write-only memory. Checking existing context before synthesis grounds new thinking in what is already known.

## Probabilistic Methods, Deterministic Processes (P#92)

The framework embraces probabilistic methods (LLM agents) while requiring deterministic processes and derivable principles. We don't seek deterministic outcomes — we achieve rigor through deterministic processes that channel probabilistic methods.

## Semantic Link Density (P#54)

Related files MUST link to each other. Orphan files break navigation.

## File Category Classification (P#56)

Every file has exactly one category (spec, ref, docs, script, instruction, template, state).

## Never Bypass Locks Without User Direction (P#57)

Agents must NOT remove or bypass lock files without explicit user authorization. When encountering locks, HALT and ask.

## Enforcement Changes Require enforcement-map.md Update (P#65)

When a PR adds, removes, or modifies an enforcement gate, the enforcement map (`.agents/ENFORCEMENT-MAP.md`; referred to as `specs/enforcement-map.md` in cross-repo specs) MUST be updated in the **same PR** that introduces the gate. The map MUST be current at merge time of the PR that adds the enforcement — it is NOT permissible to defer the map update to a later implementation task or follow-up PR.

This is design-time AND implementation-time discipline collapsed into one: a PR that wires a new gate without updating the map is incomplete, regardless of whether the gate "works." Reviewers (rbg / enforcer) MUST `REQUEST_CHANGES` on any such PR.

## No Commit Hesitation (P#70)

After making bounded changes, commit immediately. NEVER ask "Would you like me to commit?" or any variant.

## Decomposed Tasks Are Complete (P#71)

When you decompose a task into children representing separate follow-up work, complete the parent immediately.

## User System Expertise > Agent Hypotheses (P#74)

When user makes specific assertions about their own codebase, trust the assertion and verify with ONE minimal test. Do NOT spawn investigation to "validate" user claims.

**Corollaries**:

- When user/task specifies a methodology, EXECUTE THAT METHODOLOGY
- When user provides failure data and asks for tests, WRITE TESTS FIRST

**Derivation**: Users have ground-truth about their own system. Over-investigation violates P#5 (Do One Thing). Verification ≠ Investigation.

## Prefer Loud Failures Over Silent Skips (P#121)

Tests should NOT use `pytest.skip` to mask configuration errors, missing dependencies, or environment-specific setup issues. Silence masks technical debt.

**Patterns**:

- **❌ BAD**: `if not path.exists(): pytest.skip()`
- **✅ GOOD**: `assert path.exists(), f"Required directory {path} not found. Check setup."`

**Derivation**: Surfacing environment issues immediately allows for faster remediation and prevents tests from providing a false sense of security. See [[python-dev-testing]].

## Preserve Pre-Existing Content (P#87)

Content you didn't write in this session is presumptively intentional. Append rather than replace. Never delete without explicit instruction.

**Corollaries**:

- Files must be self-contained. Never write forward-references to conversational output (e.g., "See detailed analysis below") — persist all substantive content in the file itself. Response text is ephemeral; files are state.

## Run Python via uv (P#93)

Always use `uv run python` (or `uv run pytest`). Never use `python` or `pip` directly.

## Batch Completion Requires Worker Completion (P#94)

A batch task is not complete until all spawned workers have finished. "Fire-and-forget" means don't BLOCK waiting; it does NOT mean "declare complete after spawning."

## QA Tests Are Black-Box (P#96)

When executing QA/acceptance tests, treat the system as a black box. Never investigate implementation to figure out what you're testing.

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

## Delegate Agency to Capable Agents (P#116)

LLM agents are more capable than our instructions assume. Current training data systematically underestimates LLM capabilities, which creates a pervasive bias in instruction design toward excessive granularity and mechanical enforcement. This bias is understandable and wrong.

Instructions should delegate responsibility for HOW a task is fulfilled. Specify the goal, the constraints, and the quality criteria — then trust the agent to find a good path. Granular step-by-step procedures should be reserved for cases where a specific sequence is genuinely required (e.g., API call ordering, safety-critical operations), not used as a general approach to ensuring quality.

**Corollaries**:

- When writing or reviewing skill instructions, ask: "Am I specifying this step because the sequence matters, or because I don't trust the agent?" If the latter, remove it
- Prefer a clear statement of acceptance criteria over a detailed procedure
- When an agent produces good output via an unexpected method, that is success — not a compliance violation
- Agentic-first design applies here too (see P#49 corollary in [[agents/framework-ops.md]])

**Derivation**: Extends P#104 from single decisions to entire workflows.

<a id="P117"></a>

## Surface Observations, Not Interpretations (P#117)

When an agent observes unexpected behavior — a tool firing unexpectedly, a file missing, a hook blocking a call — the agent must surface the raw observation to the user before acting on an interpretation of it. Observations are facts. Interpretations are design choices. Only one of these belongs to the agent.

**The failure pattern**: "The hook fired on TaskCreate → these are read tools, not file-modifying tools → the hook is misconfigured." Step 1 is an observation. Steps 2 and 3 are an interpretation that encodes an unexamined design assumption as doctrine.

**The correct pattern**: "The hook fired on TaskCreate. This is unexpected. Is this intended behaviour or a misconfiguration?" Surface it. Don't interpret it.

**Corollaries**:

- "The hook fired unexpectedly" (observation) ≠ "The hook is misconfigured" (interpretation requiring design judgment)
- "This test failed" (observation) ≠ "The test is wrong" (interpretation)
- "This constraint blocks my plan" (observation) ≠ "This constraint is wrong" (interpretation)
- Before encoding an unexpected observation as a task, fix, or guideline: ask "does this rest on a design assumption I haven't examined?"
- P#104 (Explain, Don't Ask) applies to clearly superior implementation choices — it does not authorise interpreting system behavior as flawed without evidence

**Why this gap matters**: P#104 and P#116 together push agents toward action and away from unnecessary clarification. This creates pressure to classify ambiguous observations as bugs rather than design questions. P#117 is the counterweight: act on clear choices, but surface ambiguous system observations before encoding interpretations as fact.

**Derivation**: Emerged from a session process failure (2026-03-17).

<a id="P122"></a>

## Orchestrator Is a Dispositor (P#122)

The general CLI agent (main Claude Code session) is a **dispositor** when it runs in the **brain repo** (`$ACA_DATA`) — it understands intent, creates tasks, and delegates execution to polecat workers. It does not execute feature work itself. The full boundary definition lives in the brain PKB (project: aops, topic: orchestrator-boundary).

**Scope**: this boundary applies only when `cwd` is inside `$ACA_DATA`. When the agent is launched directly inside a project source repo (academicOps, mem, explorations, etc.), it IS the worker for that repo — the orchestrator reminder and the `orchestrator_boundary` gate are suppressed, and the agent should execute directly.

**Orchestrator may do** (read-only / planning / dispatch):

- Read files for context
- Create/update/query tasks via PKB
- Decompose epics into subtasks
- Run `/pull`, `/daily`, `/planner`, `/dump`, `/q` and other meta-skills
- Dispatch tasks via the `polecat` CLI
- Edit framework files (`aops-core/`, `aops-tools/`, `.agents/`, `docs/`, `tests/`, `scripts/`, `templates/`, `polecat/`) — framework maintenance is orchestrator scope. Authoritative allowlist: `FRAMEWORK_PATH_PREFIXES` in `aops-core/lib/orchestrator_boundary.py`.

**Orchestrator must not do** (worker scope — queue instead):

- Edit or Write project source files (i.e. files outside the framework allowlist)
- Make feature commits or push feature branches
- Run tests as part of task execution — the worker verifies its own work

**Exceptions** (hot-path direct execution):

- User explicitly requests direct execution ("just fix this one line", "do it here")
- Hotfix / one-liner where queuing overhead exceeds work
- The agent cannot unilaterally classify "too small to queue" — that judgment belongs to the user

**Why**: Bypassing polecat makes worker failure modes invisible, creates accountability gaps (no PKB task record), and undermines the evidence loop that tells us whether polecat is working. A bug-free CLI session doing the work itself hides a bug in the worker pipeline.

**How to apply**: When a prompt reads as a work request (implementation, refactor, new feature), prefer `create_task(...)` + dispatch over directly invoking Edit/Write on project source. The Level 4 detection hook (PostToolUse, warn-only) surfaces when project source is written outside a worker session so drift is caught without blocking legitimate framework work.

**Derivation**: Extends P#47 (Agents Execute Workflows) and P#116 (Delegate Agency to Capable Agents). Just as workflows belong in workflow files, feature execution belongs in worker sessions. The orchestrator's agency is strategic coordination, not keystrokes.

<a id="P119"></a>

## Bound Subagent Scope Before Dispatch (P#119)

Before spawning an Explore subagent or any research-oriented subagent, the main agent MUST state a bounded investigation plan: what specific questions need answering (3-5 bullet points max). Subagents without a scoped mandate default to exhaustive exploration, wasting tokens on information that is summarized but never used.

**The failure pattern**: User asks for a simple creative or implementation task → agent converts it into a research project → spawns Explore subagent with open-ended prompt → subagent reads 8+ files across multiple directories → most findings are not directly used in the output.

**The correct pattern**:

1. State what you need to learn (3-5 specific questions)
2. Check whether the answer is already available (prompt context, indices, glossary — per P#58)
3. Only spawn a subagent for questions that remain unanswered, with the specific questions as its mandate
4. If the task is creative/writing (not investigation), ask the user clarifying questions instead of researching

**Corollaries**:

- An Explore subagent's prompt MUST include the specific questions it should answer, not open-ended instructions like "understand the codebase structure"
- If the user's prompt already contains the information needed (error messages, file paths, function names), do NOT spawn a subagent to re-discover that information
- When the answer is evident from context, act directly — exploration is not a prerequisite for action

**Derivation**: Extends P#58 (Indices Before Exploration) from search strategy to subagent dispatch. P#58 says prefer indices over filesystem searches; P#119 says prefer direct action over subagent research when context is sufficient. Addresses systematic over-exploration documented in #356.

<a id="P123"></a>

## Age Is Not a Staleness Signal (P#123)

Age is not a staleness signal. Never cancel based on age alone. Only cancel when work becomes irrelevant. Garden passes surface candidates for human review — they do not recommend cancellation.

**Derivation**: Age correlates weakly with relevance. A task untouched for 180 days may be a stalled priority, a deferred dependency, or genuinely dead — distinguishing requires reading the work, not counting days. Auto-cancellation by age destroys signal; surfacing for review preserves it.

<a id="P124"></a>

## Dispatch Specialist-Owned Tasks (P#124)

When operating as supervisor (top-level interactive session) and a claimed task has an `assignee` matching a specialist sub-agent namespace (`aops-core:<name>`, `aops-cowork:<name>`, or the bare name `polecat`), the main agent MUST dispatch via the Agent tool with `subagent_type` set to the bare name — NOT execute inline with Read/Grep/Bash. See `/pull` Step 1.7 for the short-circuit. Inline execution by the supervisor erases the specialist's audit trail and bypasses the agent's specialised prompt.
