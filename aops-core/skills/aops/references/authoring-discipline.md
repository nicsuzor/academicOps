# Task-Body Authoring Discipline: Trust the Worker

This document defines the canonical doctrine for authoring task bodies, epic decompositions, and dispatch briefs across the academicOps framework. It applies to all skills and agents that create or decompose work for downstream execution (e.g., `/planner`, `/supervisor`, junior coordinator, `/issue-sweep`).

## 1. Intent + Acceptance Criteria, Not Prescription

Polecats are **smart agents, not mechanical drones**. When authoring a task body or dispatch brief:

- **State the intent and the Acceptance Criteria (AC).** What is the goal, and how will we know it is done?
- **Do not prescribe the implementation.** Do not propose specific file paths, function names, or directive imperatives ("edit line 42 to say X") unless those details have been empirically verified as correct and necessary.
- **Provide context, not scripts.** Link to the relevant spec or prior work. Do not write a step-by-step checklist of how to approach the code.

_If you find yourself listing "things to look for," "files to edit," or "checks to run," you are anchoring the recipient and reducing their judgment to mechanical execution. Stop._

## 2. No Mid-Stream Approval Theatre

Do not invent phantom approval gates. The framework has a canonical review pipeline (e.g., PRs, `/verify`, `/qa`).

- **Never author "surface for sign-off", "queue for user review", or "review before promoting" prose mid-stream in a task body.**
- When a worker is executing a task or epic, they should complete their work and submit it to the canonical review surface (the PR diff IS the approval surface). Stating "the worker will draft X and surface it for user review before proceeding" substitutes the worker's judgment with fake review theatre, burning polecat-nights waiting for humans.
- **Trust polecat depth, throttle polecat width.** Give each polecat a substantive chunk of work (a complete feature, a full refactor) and trust them to execute it fully instead of micro-decomposing it for them.

## 3. Compose-then-Dispatch Separation (A17 propagated to the dispatch surface)

_A17 (Recusal) propagated to the dispatch surface: the agent that composed a brief should not, in the same invocation, also perform the dispatch. Same agent identity, same in-context reasoning trace — same-context self-instruction has been observed not to bind ([[aops-e4bf292a]] incident reports 2026-05-16, 2026-05-19)._

The canonical pattern is **two agent invocations, mediated by PKB**:

1. **Compose-agent** — author the brief into a PKB task body (intent + AC; the principles in §§1–2 above). Persist.
2. **Dispatch-agent** — a _separate_ agent invocation reads the brief fresh from PKB and ships the worker.

**The load-bearing requirement is agent-identity separation, not temporal separation across ticks or sessions.** A single tick MAY chain compose-agent and dispatch-agent as two independent subagent invocations. Tick-exit-and-defer remains a legitimate fallback but is not required.

**Rules**:

- **No same-agent author-then-dispatch**: if the brief was authored or substantially refined in the current invocation, dispatch is the next agent invocation's job.
- **Dispatch by task-ID**: invoke the worker with `polecat run -t <task-id>`; the worker reads the brief from PKB. Never inline a freshly-composed brief as prompt text in the same invocation where it was composed.
- **Stable brief exception**: if the brief is already a stable PKB artifact (authored in a prior invocation and unchanged), the current invocation MAY dispatch it directly.
- **Evaluate verdicts, not rubber-stamp**: when chaining compose-agent and dispatch-agent, evaluate the dispatch-agent's verdict (action named, coherent, non-contradictory) before acting. A malformed verdict is recorded and the tick exits; do not improvise. See [[../../supervisor/SKILL#verdict-structural-shape-guard-mandatory-before-acting]].

## 4. Decision Surfacing Heuristic (FM-2 Avoidance)

Do not surface pseudo-decisions to the user. Surfacing trivial choices trains the user to rubber-stamp and erodes the signal of genuine asks.

- **DECIDE:** If one option is clearly correct based on framework principles (vision, axioms, heuristics), make the decision and record the rationale. If the decision is an action, execute it now. Do not defer it.
- **DEFER:** If the decision requires runtime evidence or data we don't have yet, note the dependency and evaluate later. Do not surface it to the user now.
- **SURFACE:** Only surface genuine taste, scope, naming, or trade-off decisions where the user's preference is the deciding input.

_Rule of thumb:_ If the question can be answered by reading the documentation, make the call. Only surface if the question can only be answered by the user's unique preference or domain authority.
