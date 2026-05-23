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

_A17 (Recusal) governs framework-change authoring: the agent that lived through the failure may not author the rule. The same structural property must hold for worker dispatch: the agent that composed the brief should not, in the same invocation, also perform the dispatch. The composing impulse and the dispatching impulse are the same impulse — same agent identity, same in-context reasoning trace — and same-context self-instruction has been observed not to bind ([[aops-e4bf292a]] incident reports 2026-05-16, 2026-05-19)._

The canonical happy path for any non-trivial worker dispatch (polecat or polecat-equivalent execution) is **two agent invocations, mediated by PKB**:

1. **Compose-agent** — author the brief into a PKB task body (intent + AC; the principles in §§1–2 above). Persist. Exit the composing invocation.
2. **Dispatch-agent** — a _separate_ agent invocation reads the brief fresh from PKB and ships the worker. The dispatching actor does not inherit the composer's reasoning trace.

The load-bearing requirement is **agent-identity separation, not temporal separation across ticks or sessions**. A single orchestrator tick MAY chain compose-agent and dispatch-agent so long as they are two independent subagent invocations (fresh subagent contexts), not the same continuing context. Tick / session boundaries are one way to ensure independence — and remain a legitimate fallback for genuinely large compositions where a settling pause adds value — but they are not the load-bearing requirement; agent-identity separation is.

This is a **workflow shape, not a verdict gate.** There is no PASS/REWRITE/HALT check interposed between compose and dispatch; the structural distinctness is delivered by the agent boundary itself. PKB is the persistent intermediary; the freshness of the dispatcher's read is the cure.

**Operational rules**:

- **Surface-by-surface canonical pattern**: see [[../../planner/SKILL#shared-principles]] (planner is the canonical compose-only surface), [[../../supervisor/SKILL#compose-then-dispatch-separation]] (compose-agent and dispatch-agent are two independent subagent invocations, optionally chained within one tick), and the junior coordinator's worker-dispatch rule (write to PKB first; dispatch by task-ID only).
- **No same-agent author-then-dispatch**: if the brief was just authored or substantially refined in the current invocation, that invocation MUST NOT also dispatch. Dispatch is the next agent invocation's responsibility — either a different agent, or the same agent re-invoked in a fresh subagent context.
- **Dispatch by task-ID, not by inlined prose**: when invoking a worker (e.g. `polecat run -t <task-id>`), the worker reads the brief from PKB. Never inline a freshly-composed brief as command arguments or sub-agent prompt text in the same invocation where the brief was composed.
- **Lightweight subagent calls are not worker dispatch**: a short pauli preflight or marsha verify against an existing artifact is not the surface this rule targets. The rule targets sustained worker execution (polecat-equivalent) where the brief is the primary input.
- **If the brief is already a stable PKB artifact** (authored in a prior invocation and unchanged in the current invocation), the current invocation MAY dispatch it. The constraint is on co-occurrence of authoring and dispatching within a single agent's context, not on dispatching pre-existing briefs.
- **Orchestrators must evaluate subagent verdicts, not rubber-stamp them**: the orchestrator that chains compose-agent and dispatch-agent reads each verdict's structural shape (action named, coherent, non-contradictory, no capability fabrication per A7 Edge 2) before acting on it. Independence of the dispatch-agent's _judgment_ is what A17 protects; rubber-stamping its verdict erases that protection. If a verdict is malformed, the orchestrator records the structural reason and halts — it does not improvise.

**Why this works without a gate**: the dispatch-agent reads the brief fresh, with no inheritance of the composer's prescriptive impulse. If the brief is well-shaped (intent + AC), dispatch proceeds; if it is not, the dispatcher's normal attention (the same kind of judgment a human dispatcher applies on read) is sufficient — and the brief is now a visible artifact in PKB rather than transient in-context prose, making it auditable by any subsequent reader. The composer who knows their brief will be read by a fresh actor (not blindly executed by the same impulse that authored it) writes with awareness that the brief must stand on its own.

**Axiom interactions**:

- **A17 (Recusal)**: this rule IS A17 propagated to the dispatch surface — the agent that composed must not own the dispatch. The framework-change variant requires a detached author; the dispatch variant requires a detached dispatcher.
- **A8 (Halt on failure)**: this rule does NOT introduce a gate, a verdict, or a HALT mechanism. There is no "skip dispatch if brief is prescriptive" branch. The dispatching actor either dispatches or routes through the normal A7 Edge 2 escalation if it cannot — it does not invent a new halt condition.
- **A7 Edge 3 (No Shitty NLP)**: the dispatcher's judgment of brief shape, if it forms one at all, is qualitative LLM judgment — never a regex or keyword check. There is no "scan for `/home/` paths" or "grep for 'DO NOT'" rule attached to this workflow.
- **A11 (Full Observability)**: the brief is a visible PKB artifact at the moment of handoff. Any subsequent reader (user, reviewer, audit) can see what was authored and what was dispatched without reading transcripts.

## 4. Decision Surfacing Heuristic (FM-2 Avoidance)

Do not surface pseudo-decisions to the user. Surfacing trivial choices trains the user to rubber-stamp and erodes the signal of genuine asks.

- **DECIDE:** If one option is clearly correct based on framework principles (vision, axioms, heuristics), make the decision and record the rationale. If the decision is an action, execute it now. Do not defer it.
- **DEFER:** If the decision requires runtime evidence or data we don't have yet, note the dependency and evaluate later. Do not surface it to the user now.
- **SURFACE:** Only surface genuine taste, scope, naming, or trade-off decisions where the user's preference is the deciding input.

_Rule of thumb:_ If the question can be answered by reading the documentation, make the call. Only surface if the question can only be answered by the user's unique preference or domain authority.
