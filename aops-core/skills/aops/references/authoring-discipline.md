# Task-Body Authoring Discipline: Trust the Worker

This document defines the canonical doctrine for authoring task bodies, epic decompositions, and dispatch briefs across the academicOps framework. It applies to all skills and agents that create or decompose work for downstream execution (e.g., `/planner`, `/supervisor`, `/issue-sweep`).

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

## 3. Decision Surfacing Heuristic (FM-2 Avoidance)

Do not surface pseudo-decisions to the user. Surfacing trivial choices trains the user to rubber-stamp and erodes the signal of genuine asks.

- **DECIDE:** If one option is clearly correct based on framework principles (vision, axioms, heuristics), make the decision and record the rationale. If the decision is an action, execute it now. Do not defer it.
- **DEFER:** If the decision requires runtime evidence or data we don't have yet, note the dependency and evaluate later. Do not surface it to the user now.
- **SURFACE:** Only surface genuine taste, scope, naming, or trade-off decisions where the user's preference is the deciding input.

_Rule of thumb:_ If the question can be answered by reading the documentation, make the call. Only surface if the question can only be answered by the user's unique preference or domain authority.
