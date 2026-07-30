---
id: enforcement-318d578e
title: Enforcement Architecture
type: spec
status: ready
tier: core
depends_on: []
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

## Governing principle — agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**. Hooks, server contracts, and config are **delivery channels** — they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict — did this follow the rules, is this actually good, was this worth doing — is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

The only **mechanical** enforcement in the framework is **structural prevention**: credential and workspace isolation (Docker containers for polecat workers, repo-scoped access, no ambient credentials inside a container). Prevention by construction — never reactive detection, never content-sniffing ("no shitty NLP" — no regex-for-meaning, no destructive-verb pattern matching), never a deterministic pass/fail on the substance of an agent's work.

This is a deliberate, ratified narrowing from an earlier model that ran a ~40-mechanism in-session gate pyramid (turn-based compliance counters, blocking Stop gates with per-gate mode config, a dedicated `GateConfig` engine). That engine has been retired in full; see [Retired](#retired) below. Enforcement's centre of gravity is now the **task-graph boundary** (claim → execute → release, see [task-contract.md](task-contract.md)) and the **agent judgment** applied at review time (see [workflow.md](workflow.md)), not a stack of harness-level gates.

## Personalities are not skills

An **agent personality** (charter — Ida, pauli, rbg, marsha, james, …) defines conduct, judgment register, disposition, and responsibilities: who the agent is and what standard it holds. An **agent skill** defines a procedure or capability: how a job gets done. These are different artifacts and are never conflated.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for exactly two reasons: **earmarking** (the skill genuinely depends on that personality's judgment register — e.g. `/verify` owned by marsha's broken-until-proven disposition) or **permission control** (tool grants deliberately restricted to force a workflow — e.g. a review role gated to keep authoring and verification separate).
- The three review lenses in [workflow.md](workflow.md) — pauli / rbg / marsha — name **judgment registers a review must apply**, not exclusive executors: which agent carries a lens is a dispatch decision, provided reviewer ≠ executor holds.

## What actually enforces things today

**Enforcement is risk-reduction**: compliance is not guaranteed. Mechanical hard blocks are often NOT the best option. We have four groups of levers:

1. **Norms** — the agent's internalised alignment with intent (prompt directives, system rules, explicit instructions).
2. **Cost** — the token/time/friction cost of complying versus the incentive to bypass.
3. **Defaults** — whether the compliant path is mechanically the path of least resistance (e.g. automated execution) rather than something the agent must remember to invoke.
4. **Likelihood** — the probability a violation is detected, multiplied by its consequence (Rule + Delict × Likelihood) — this is the one lever pyramid severity directly moves.

Before escalating severity, check whether the actual failure is a cost or defaults problem — the "Escalate up" rule below already requires confirming the lighter tiers were exhausted first, and a cost/defaults fix is usually cheaper than a severity bump. _Worked example:_ repeated stale-state PKB assertions across sessions are not a norms or severity failure — agents are told to check the PKB and the rule is known and enforced. The fix is lowering the cost (better search ergonomics, trimmed response payloads) and improving the default (inject PKB search results directly into context via the `UserPromptSubmit` hook, rather than merely exhorting agents to search).

### 1. Structural prevention (the only mechanical layer)

- **Container isolation** — polecat workers run inside Docker (`Dockerfile`, [`plugins/aops/polecat/cli.py`](../../plugins/aops/polecat/cli.py)), with no ambient host credentials, a read-only staging mount, and a scoped workspace volume. This is prevention by construction: a worker cannot exfiltrate host secrets or touch files outside its mount because the container doesn't have them, not because a rule told it not to.
- **`polecat.yaml`** (loaded from `$AOPS_POLECAT_CONFIG` or `$AOPS_SESSIONS/polecat.yaml`, overridable per-machine via `<polecat_home>/local.yaml`) is the operator config for session configuration: cache root, container image, project-path map. No built-in fallback: a missing required value (`polecat_home`, `docker.image`) is a hard fail, not a silent default.

### 2. Dual-layer rule enforcement channel

Every plugin hook shares one runtime, `lib/hooks/`, injected into each plugin at
build time (`ARCHITECTURE.md`, Hooks). The framework enforces rules via two complementary layers:

- **Layer 1 (Turn-by-Turn Local Model COPE):** **`rbg`**, `PreToolUse` ([`plugins/rbg/hooks/handlers.py`](../../plugins/rbg/hooks/handlers.py), `evaluate`) — loads the three-layer rule set (`rules.py`) and asks a fast, lightweight local Reflexes LLM evaluator model ([`evaluator.py`](../../plugins/rbg/hooks/evaluator.py)) whether each tool call complies with active rules. Runs in parallel across rules inside one deadline to advise the agent on every tool call. **Advisory and overridable, permanently**: it returns injected context, never a disposition, and no confidence score promotes it to one. On agy the same plugin states the live rule roster at `PreInvocation` (`inject_ruleset`) instead, because agy maps no tool event for the evaluator to judge.
- **Layer 2 (Session Stop RBG Check):** **`rbg`**, `Stop` and `SubagentStop` ([`plugins/rbg/hooks/handlers.py`](../../plugins/rbg/hooks/handlers.py), `rule_check`) — returns `decision: "block"` once per stop-chain, directing the agent that is stopping to run an explicit RBG rule check (`axioms/` + project-local + user rules) and present checkable evidence before handing over. What it withholds is the stop, not a tool call: the turn continues, and the agent uses it to run the check. The block is legal because the question is whether the check happened at all — a fact about the session — rather than a model's reading of a rule, which is why Layer 1 may never carry one.

  The hook obliges the check and never performs it. Nothing hook-side reads the transcript or grades what the agent did with the turn it was given; a mechanical verdict on the substance of an agent's work is the thing the governing principle above forbids.

  **The gate is unscoped, in two ways that matter for cost.** These are turn boundaries, not session boundaries: `Stop` fires each time the session's own agent finishes a response, so an interactive session meets the gate once per turn. And the payload carries no per-agent identity, so a face's `Stop` and a worker's `SubagentStop` reach the same handler with the same text — the gate cannot currently be aimed at workers alone. On a face turn it therefore composes with `ida`'s `honesty_floor`, which fires on the same event: two hooks, one advisory and one block, each once per chain.

  **Once per chain, guarded structurally.** A block gives the session another turn, which stops again and re-fires the hook; the client marks that re-entry with `stop_hook_active`. [`lib/hooks/dispatch.py`](../../lib/hooks/dispatch.py) drops every handler on a marked `Stop`/`SubagentStop` before any of them load, so the obligation is stated once, the continuation stop is silent, and the session ends. It lives in the shared runtime rather than in a handler so no future stop hook has to remember it.

  **Blocking is Claude-only, structurally.** `dispatch.py` honours `block` only on the events in `BLOCKABLE_EVENTS`; returned anywhere else it degrades to an advisory and reports the misuse on stderr, because no other Claude event has a `decision` field to honour and a handler must not mistake a no-op for enforcement. agy has no blockable mapped event at all, so `rule_check` reaches it as an `injectSteps` advisory.
- **Honesty floor (face-scoped):** **`ida`**, `Stop` ([`plugins/ida/hooks/handlers.py`](../../plugins/ida/hooks/handlers.py), `honesty_floor`) — requires every load-bearing claim in the answer to carry its evidence (observed vs reported) and its stated confidence, and forbids writing an inference as an observation. Advisory, once per stop-chain (`stop_hook_active`), silent while background work runs. Counterpart to `rule_against_hearsay` on `PostToolUse` in the same file: that governs what ida may accept from a worker, this governs what ida may then assert to the user. Scoped to the face by its event — `Stop` fires only on the session's own turn boundary, and `SubagentStop` is deliberately not wired — because the hook payload carries no per-agent discriminator.
- **`pkb`**, `UserPromptSubmit` ([`plugins/pkb/hooks/handlers.py`](../../plugins/pkb/hooks/handlers.py)) — grounds every user prompt in PKB history before action.
- **`ts`**, `SessionStart` ([`plugins/ts/hooks/tailscale-up.sh`](../../plugins/ts/hooks/tailscale-up.sh)) — Tailscale bring-up for remote sessions.

Every agent-visible string a hook emits comes from a markdown file next to it
(`hooks/messages/*.md`), editable without touching code. **No hook in this layer
produces a verdict**, and none of them checks whether the agent actually did what
was asked — that is the executing agent's own judgment call, backstopped by the
review lenses below, not by the hook. One of them can withhold a stop, which is
the Layer 2 gate above: it obliges a check to be run, and is silent on what the
check then finds.

**Hook injection budget scales inversely with firing frequency.** `PreToolUse`,
`PostToolUse`, and `UserPromptSubmit` fire on every tool call or turn, so what
they inject stays to a line or two — a message the agent learns to skip past is
worse than no message. `Stop` and `SubagentStop` fire once per chain, so the text
there can afford to be a full instruction.

**A delivery channel that has stopped delivering does not currently say so.**
These are reminders people come to rely on, and every way they can fail — a
handler that raised, an evaluator that did not answer, a rule file that could not
be read — is reported on stderr alone, which the client captures into the
transcript and renders to nobody. There is no rate limiting and no route onto the
hook's own response; the structured degradation reporting that once occupied that
role has been removed and not replaced. So a hook that has silently stopped
working is legible in the log and nowhere else, including to the person who is
the only one able to fix it. This is a known gap in the channel, not a property
of it.

What does still hold is that **degradation is distinguished from legitimate
absence** by the handlers themselves: `rbg` with no evaluator configured,
`$ACA_DATA` unset, and a project with no local rules directory are all valid
states, and each is a clean no-op rather than a fault. And a fault is never a
gate — reporting one cannot change any hook's disposition, and the tool call
proceeds either way.

### 3. Claude Code's native auto-mode classifier

A model-based (not deterministic) tool-call classifier built into the harness, configured with prose rules in [`plugins/aops/polecat/defaults/claude-settings.json`](../../plugins/aops/polecat/defaults/claude-settings.json). Full design statement, admission criteria, and cost model: [auto-mode-classifier.md](auto-mode-classifier.md). Because it is an LLM judgment call over a stripped transcript rather than a deterministic pattern match, it sits inside the "agents all the way down" principle rather than beside it — it is the one place a per-action judgment call happens before the agent's own review loop closes.

### 4. Task-graph boundary — the primary enforcement point

`claim_task` in, `release_task` out. A completion claim must carry independent-verification evidence or a stated failure reason — this is where the framework actually holds agents accountable, because it binds to the claim act rather than to session mechanics. Full contract: [task-contract.md](task-contract.md); the universal claim-evidence shape every boundary reads: [evidence-contract.md](evidence-contract.md).

**The claim is written twice, deliberately.** The dispatch surface records one at launch; the worker claims the task from inside its own session, which is what moves the status. Two writes, because the launch record is the only thing that makes a worker which died before ever claiming legible as an unanswered dispatch rather than as work nobody picked up. Full invariant: [task-contract.md](task-contract.md).

**A boundary that agents sometimes never cross back through needs a sweep behind it.** No session is obliged to return, so nothing re-examines a claim once it is made: claims outlive dead sessions, merges land unwatched, and completed work sits uncertified. The reconcile skill ([`plugins/pkb/skills/reconcile/SKILL.md`](../../plugins/pkb/skills/reconcile/SKILL.md)) is that sweep — it reads the graph against the evidence trail and writes back what is actually true. It runs on engagement after an absence (commissioned by ida as a delegation, since touching the knowledge base is not hers to do), inside the consolidation cycle, and on demand. Behavioural spec: [reconcile.md](../workflows/reconcile.md).

A container emits no completion signal, so evidence reaches this boundary only because something carries it. The durable carrier is the task record the worker writes before exiting; the dispatch surface ([`plugins/aops/skills/dispatch/SKILL.md`](../../plugins/aops/skills/dispatch/SKILL.md)) supplies the second by running every container inside a plain background subagent — the courier — whose final message returns the worker's result as a harness notification. The courier is delivery, not supervision and not a gate: the worker's method stays entirely its own, and the claim-evidence contract above remains the thing that holds it accountable.

### 5. Task-boundary review — three pauli-specified lenses

- **pauli** (pre-hoc) — the premise standard: the idea is sound, elegant, and strongly aligned with the project's strategic aims when evaluated in the full context. Where composed in, it is emitted early and blocking, so the rest of the epic depends on it clearing. The former standalone dispatch-time "premise gate" (a two-judge hard-refuse ceremony run at `/pull`/`/dispatch`) is retired; decomposition carries this judgment instead, and dispatch surfaces trust the planner's decomposition rather than re-judging it.
- **rbg** — rules were followed: boundary review of the task contract and handback only (inputs/outputs), never the transcript.
- **marsha** (post-hoc) — the task does what it was supposed to and does it _well_: delivered artifact vs. the original aim and acceptance criteria, bar is excellent, not passing.

Each blocks epic acceptance where the composed process obliges it.

**Which of these a given piece of work runs is composed, not hardcoded.** The `decompose` skill ([`plugins/pkb/skills/decompose/SKILL.md`](../../plugins/pkb/skills/decompose/SKILL.md)) loads the review process from the workflow-template namespace — shipped library, the user's own layer, and the PKB's `wf-*` templates, one namespace resolved later-wins-by-name — and turns each obligation it names into a real blocking node. The three lenses above are the standard those templates express; a fixed set carried in the skill's own text would be a process the user could never override.

Composition can yield an **empty** set, and that is the dangerous branch: work would pass decomposition carrying no review obligation and read as correctly planned. So a composed process obliging no review at all is itself a library gap `decompose` names and halts on — the same pathway as an obligation no layer defines.

**Human sign-off at a one-way door is not composed.** It is the [`one-way-door`](../../lib/axioms/one-way-door.md) axiom, binding the agent at the moment it crosses rather than the planner who drew the DAG. An obligation a template layer could drop, or name-shadow with a layer of its own, was never a floor; an axiom sits outside that namespace by construction.

`decompose` plans only: it emits those nodes and their `depends_on` wiring into the graph; it never dispatches or runs them itself. Review depth (per-chunk subtasks vs. one consolidated pass at the final PR) is the planner's call at decomposition time, based on the work's risk and blast radius. Full shape: [workflow.md](workflow.md).

**Certification at completion executes those nodes.** When a unit's return contract lands, the dispatch surface commissions the review the graph already carries — through the [`strategic-review`](../../plugins/aops/skills/strategic-review/SKILL.md) and [`verify`](../../plugins/aops/skills/verify/SKILL.md) skills — and records the verdict on the task record, which [evidence-contract.md](evidence-contract.md) makes the message bus every handback crosses. One path, never a second review standing beside the nodes decomposition already emitted; and no judgment of the dispatcher's own, since relaying a worker's "confirmed" is what the gate exists to prevent.

**Certification therefore has a precondition: the certifying context must be able to spawn.** Commissioning a review means deploying reviewers, so a context holding no subagent surface cannot satisfy this gate at all — it must hand the unit to one that can, and refuse to self-certify in the meantime. A gate routed to a context that cannot execute it produces no verdict and no failure, which is the one outcome this boundary must not have. Contract: [`dispatch`](../../plugins/aops/skills/dispatch/SKILL.md) §4.

The acceptance that follows certification belongs to the face, judged against user intent — the two-signature rule in [workflow.md](workflow.md).

### 6. Workflow components for assembly

A set of composable workflow templates — prose, not code — that live in the PKB task/knowledge graph under `wf-*` IDs (`wf-outbound-review`, `wf-verification`, `wf-handover`, `wf-constraint-check`, `wf-qa`, `wf-human-approval`). Each names its own stakes, door-type (one-way/two-way), and category. Workflows assemble these at generation/decomposition time rather than every task inventing its own review ceremony.

### 7. Sign-off — the workflow-level instantiation

The git PR pipeline (`.github/workflows/`: `rbg-review.yml`, `agent-qa.yml`, `agent-enforcer.yml`, `agent-mechanic.yml`, `agent-pre-admission-responder.yml`, `issue-sweep.yml`, plus mechanical `lint.yml`/`pytest.yml`/`typecheck.yml`) is the concrete instantiation of workflow-level sign-off for anything that ships as a PR. Design statement: [sign-off.md](sign-off.md).

## Evidence loop — how the framework learns

Two flows, deliberately separated (witness vs. judge), so the volume and direction of framework change is governed by cross-incident pattern, not by the salience of the most recent failure:

1. **Diagnose and route** (`/learn`) — an agent that hits friction traces it back to the structural cause immediately and unilaterally, fixing what the session under review itself broke and nothing that governs future sessions. It then routes the lesson to the one destination its scope claims: the task record, a project rule via `add-rule`, the PKB via `remember`, or — reachable only from inside this repository's own source tree — framework source or a filed issue. The two framework destinations still propose no fix; they record the gap, one friction to one record. Writing a standing rule needs the user to have asked for one: recurrence the pass notices itself is cited as evidence, never acted on, which is what keeps this side of the loop a witness. `add-rule` ships with `rbg`, so the project-rule destination is live in every consuming project, not only here.
2. **Improve the framework** (`/issue-sweep` / the `triage` skill's sweep mode) — a detached pass over the accumulated issue queue, on a cadence the user sets, classifies each issue and only proposes a mechanism add/escalation where ≥3 recurrences (or explicit user direction) justify it. The user gates every disposition.

A single incident that is a **bug** (broken skill routing, a wrong path, an incomplete instruction) gets fixed immediately from one report. A single incident that is an **escalation proposal** (a new gate, a new axiom, a heavier mechanism) gets logged and waits for the pattern.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism, not on keeping behaviour in prose.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail. Given the choice, extend the prose an agent reads and judges against, not the code that pre-judges for it.
3. **Measure before changing.** The evidence loop above is the authority for adding or escalating a mechanism. Authorial intuition is not evidence.
4. **Show, don't tell.** Where compliance is claimed, require information that demonstrates it — the evidence contract, not reassurance.
5. **Never guess.** With no evidence either way, current placement holds.

## Retired

The framework's prior in-session hook/gate engine — a dedicated `GateConfig` framework, a ~1600-line hook router, per-gate mode-key plumbing, a turn-based `rbg` PreToolUse compliance counter, standalone critic/QA-exit gates, a two-judge dispatch-time premise gate, and the separate `ENFORCEMENT-MAP.md` / `GATES.md` / `pyramid.md` register documents that catalogued it — has been deleted in full, not versioned or kept as a fallback. The concerns it addressed either moved to the task-graph boundary and review lenses above, moved to structural prevention, or are judged unnecessary given the module-boundary thesis. Git history is the record of what existed and why it was removed; this spec describes what exists now, not an archive of what came before.

## Sibling documents

- [task-contract.md](task-contract.md) — the work-unit contract (`claim_task` → `release_task`).
- [workflow.md](workflow.md) — the five-step workflow shape (contract → execution → boundary-check → QA-around → sign-off) and the review-depth call.
- [sign-off.md](sign-off.md) — the workflow-level review, instantiated today as the git PR pipeline.
- [evidence-contract.md](evidence-contract.md) — the single universal claim-evidence shape every boundary above reads.
- [auto-mode-classifier.md](auto-mode-classifier.md) — design statement for Claude Code's native per-action classifier.
- **PKB Workflow Templates** (`wf-*` nodes in the PKB) — the prose workflow template component library for assembled workflows.
- [agent-authority.md](../agents/agent-authority.md) — the frontmatter schema and deny-by-default tool/skill/subagent permissions this spec's L3/L4 layers apply; documents a current harness defect that forces four core agents (pauli, james, marsha, rbg) to omit their `tools` allowlist rather than lose MCP access, and the resulting gap in RBG's ground truth for those four until upstream fixes it.
