# Task-Body Authoring Discipline: Trust the Worker

This document defines the canonical doctrine for authoring task bodies, epic decompositions, and dispatch briefs across the academicOps framework. It applies to all skills and agents that create or decompose work for downstream execution (e.g., `/planner`, `/supervisor`, junior coordinator, `/issue-sweep`).

## 1. Intent + Acceptance Criteria, Not Prescription

Polecats are **smart agents, not mechanical drones**. When authoring a task body or dispatch brief:

- **State the intent and the Acceptance Criteria (AC).** What is the goal, and how will we know it is done?
- **Do not prescribe the implementation.** Do not propose specific file paths, function names, or directive imperatives ("edit line 42 to say X") unless those details have been empirically verified as correct and necessary.
- **Provide context, not scripts.** Link to the relevant spec or prior work. Do not write a step-by-step checklist of how to approach the code.

_If you find yourself listing "things to look for," "files to edit," or "checks to run," you are anchoring the recipient and reducing their judgment to mechanical execution. Stop._

**Frame the outcome to verify, not the edit to make.** The AC should name the observable behaviour change the worker must produce and confirm, not the code change you imagine produces it:

- **Lead with the observable outcome** — "after your fix, X should look/behave like Y" — not "change the exponent in `foo.ts` from 0.7 to 2.5."
- **Name the verification, not just the goal.** Require a concrete before/after check the worker runs against the real surface (measure it, screenshot it, diff the two states), so "done" means _observed-changed_, not _edited_.
- **If you must name a file, mark it unverified.** Even when you believe you know the code path, write "verify this is actually the code path that runs before editing it" as an explicit check. Over-specifying an implementation anchors the worker on your mental model, which may be wrong.

Failure this prevents: a brief said "change the exponent in `focusEmphasis.ts` from 0.7 to 2.5"; the worker did exactly that, but the treemap read hardcoded constants in a _different_ file — the edit had zero effect, and the prescription masked the real code path. An outcome-framed brief ("high-focus nodes should be visibly more emphasised; screenshot before/after to confirm") would have surfaced the wrong-file problem on the first verification.

## 2. No Mid-Stream Approval Theatre

Do not invent phantom approval gates. The framework has a canonical review pipeline (e.g., PRs, `/verify`, `/qa`).

- **Never author "surface for sign-off", "queue for user review", or "review before promoting" prose mid-stream in a task body.**
- When a worker is executing a task or epic, they should complete their work and submit it to the canonical review surface (the PR diff IS the approval surface). Stating "the worker will draft X and surface it for user review before proceeding" substitutes the worker's judgment with fake review theatre, burning polecat-nights waiting for humans.
- **Trust polecat depth, throttle polecat width.** Give each polecat a substantive chunk of work (a complete feature, a full refactor) and trust them to execute it fully instead of micro-decomposing it for them.

## 3. Compose-then-Dispatch Separation (`recusal` propagated to the dispatch surface)

_`recusal` propagated to the dispatch surface: the agent that composed a brief should not, in the same invocation, also perform the dispatch. Same agent identity, same in-context reasoning trace — same-context self-instruction has been observed not to bind ([[aops-e4bf292a]] incident reports 2026-05-16, 2026-05-19)._

The canonical pattern is **two agent invocations, mediated by PKB**:

1. **Compose-agent** — author the brief into a PKB task body (intent + AC; the principles in §§1–2 above). Persist.
2. **Dispatch-agent** — a _separate_ agent invocation reads the brief fresh from PKB and ships the worker.

**The load-bearing requirement is agent-identity separation, not temporal separation across ticks or sessions.** A single tick MAY chain compose-agent and dispatch-agent as two independent subagent invocations. Tick-exit-and-defer remains a legitimate fallback but is not required.

**Rules**:

- **No same-agent author-then-dispatch**: if the brief was authored or substantially refined in the current invocation, dispatch is the next agent invocation's job.
- **Dispatch by task-ID**: invoke the worker with `polecat run -t <task-id>`; the worker reads the brief from PKB. Never inline a freshly-composed brief as prompt text in the same invocation where it was composed. This method assumes the worker has PKB access.
- **Worker-Type ↔ Required-Capability Dispatch Guard**: Before dispatching, verify whether the target worker type carries the required capabilities to fulfill the brief. Specifically:
  - **PKB-dependent briefs** (tasks requiring `get_task`, `get_document`, or other `mcp__plugin_aops-core_pkb__*` tools) must only be briefed by task-ID to worker types that carry the PKB MCP tools (e.g., `junior` / `aops-core:jr`, `james`, `pauli`, `rbg`, `marsha`, and local/remote `polecat` containers).
  - **Non-PKB Worker Types** (e.g., `general-purpose` subagents, `Jules`, and `GHA` runners) do not carry PKB MCP tools. When dispatching to these worker types, the brief content **must** be passed inline (in the prompt argument or piped via `pkb task <task-id> | jules new`) rather than by PKB-ID. Never instruct a non-PKB worker to "read your brief fresh from PKB" or run `get_task`.
  - **Pre-dispatch Verification**: A reader or dispatching agent must determine, prior to dispatching, whether the chosen worker type carries the capabilities required by the brief format.
- **Stable brief exception**: if the brief is already a stable PKB artifact (authored in a prior invocation and unchanged), the current invocation MAY dispatch it directly.
- **Evaluate verdicts, not rubber-stamp**: when chaining compose-agent and dispatch-agent, evaluate the dispatch-agent's verdict (action named, coherent, non-contradictory) before acting. A malformed verdict is recorded and the tick exits; do not improvise. See [[../../supervisor/SKILL#verdict-structural-shape-guard-mandatory-before-acting]].

### Investigation boundary (Pauli's identity-layer projection of `recusal`)

Pauli frames + dispatches; Pauli does NOT perform investigation. Investigation means: reading source files to audit an implementation, running Bash to gather evidence, synthesising technical findings inline as part of a planning invocation. These inflate Pauli's context and bury findings in an ephemeral invocation rather than a durable PKB node.

**Context-loading is not investigation.** Querying the PKB, reading .agents/CORE.md, and reading spec documents are always allowed — they ground the framing without substituting for the worker's execution.

When asked to plan work that requires investigation, Pauli:

1. Names the investigation question.
2. Names the data sources the worker should consult.
3. Writes the brief into PKB (intent + AC, per §§1–2).
4. Exits. The worker reads the brief fresh and investigates.

The brief must contain: the investigation question + the data sources. It must NOT contain Pauli's own interim findings.

**WRONG — planner investigates inline:**

> User: "Plan work to fix why the gate is blocking valid tool calls."
> Pauli: [reads `gate_config.py`, runs tests, synthesises findings, reports conclusion in the planning invocation]

**CORRECT — planner frames + dispatches:**

> User: "Plan work to fix why the gate is blocking valid tool calls."
> Pauli: Creates task: "Investigate gate tool-blocking issue. Read `gate_config.py` §tool-categories and `tests/hooks/test_gate_verdict_logic.py`. Determine why tool X is categorised as blocked. Report: the current category, the expected category, and the specific config line to change." → Exits. Worker reads brief fresh and investigates.

## 4. Decision Surfacing Heuristic (FM-2 Avoidance)

Do not surface pseudo-decisions to the user. Surfacing trivial choices trains the user to rubber-stamp and erodes the signal of genuine asks.

- **DECIDE:** If one option is clearly correct based on framework principles (vision, axioms, heuristics), make the decision and record the rationale. If the decision is an action, execute it now. Do not defer it.
- **DEFER:** If the decision requires runtime evidence or data we don't have yet, note the dependency and evaluate later. Do not surface it to the user now.
- **SURFACE:** Only surface genuine taste, scope, naming, or trade-off decisions where the user's preference is the deciding input.

_Rule of thumb:_ If the question can be answered by reading the documentation, make the call. Only surface if the question can only be answered by the user's unique preference or domain authority.

## 5. Verification Honesty in Completion Summaries

When a worker reports what it did, the summary must keep two things apart: what it **observed this session**, and what it **inferred**. State the command (or tool call) that produced an observed result; an inferred conclusion is fine but must read as inferred, not be dressed up in observed language. Phrasing a guess as a fact ("tests pass", "the build is green") when you did not run the thing this session is the failure this principle exists to prevent — it launders an assumption into the record a reviewer trusts. This is prose, not a template: no required manifest section, no `OBSERVED`/`ASSERTED` tags, no mandatory `cmd:`/`out:` fields — just the discipline of not claiming as seen what you only assumed.
