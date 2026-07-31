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

- **Container isolation** — polecat workers run inside Docker (`Dockerfile`, [`lib/polecat/cli.py`](../../lib/polecat/cli.py)), with no ambient host credentials, a read-only staging mount, and a scoped workspace volume. This is prevention by construction: a worker cannot exfiltrate host secrets or touch files outside its mount because the container doesn't have them, not because a rule told it not to.
- **`polecat.yaml`** (loaded from `$AOPS_POLECAT_CONFIG` or `$AOPS_SESSIONS/polecat.yaml`, overridable per-machine via `<polecat_home>/local.yaml`) is the operator config for session configuration: cache root, container image, project-path map. No built-in fallback: a missing required value (`polecat_home`, `docker.image`) is a hard fail, not a silent default.
- **Delivery guard** — a container that exits zero has not thereby delivered. Before `polecat run` reports success it checks the workspace has no uncommitted changes and no unpushed commits ([`lib/polecat/cli.py`](../../lib/polecat/cli.py), `_verify_workspace_delivery`), and for a seeded `agy -t <task>` dispatch that the agent's own transcript references the task id (`_seed_confirmed`) — a dropped seed leaves a clean workspace, so the delivery check alone would read it as a pass. Either failing exits non-zero naming the task.
- **Reopen on caught delivery loss** — detection and repair are separate duties with separate owners, and the guard above is only the detection half. A worker that wrote a terminal status to the graph and delivered nothing leaves that status behind; nothing downstream can tell it apart from real completion, and neither filing a fix subtask nor re-dispatching undoes it. The repair is owned by the dispatcher, which reopens the task through pauli on any non-zero container exit for a terminal-status unit ([`dispatch`](../../plugins/ida/skills/dispatch/SKILL.md) §6). It sits here rather than in the launcher because writing to the knowledge base belongs to its sole writer, and a launcher carrying its own client for another plugin's tool namespace is a second copy of that plugin's job.
- **Agent-definition model pins** — an agent whose model matters pins it in its own frontmatter: james `opus` ([`plugins/ida/agents/james.md`](../../plugins/ida/agents/james.md)), pauli and rbg `sonnet` ([`plugins/pkb/agents/pauli.md`](../../plugins/pkb/agents/pauli.md), [`plugins/rbg/agents/rbg.md`](../../plugins/rbg/agents/rbg.md)). The pin is the enforcement point, not the call site: a dispatcher passes no `model` override to a pinned agent, because a dispatch-time parameter replaces the pin rather than reinforcing it. Naming a model at dispatch applies only to workers with no pinned definition. This is prevention by construction against `model: inherit`, which resolves to the root session's model rather than the immediate caller's — the layered topology (ida → james → workers) breaks that inheritance chain only because james carries his own pin.

### 2. Dual-layer rule enforcement channel

Every plugin hook shares one runtime, `lib/hooks/`, injected into each plugin at
build time (`ARCHITECTURE.md`, Hooks). Two rule layers run in-session. The first
advises and can do nothing else; the second withholds a stop:

- **Layer 1 (Turn-by-Turn Local Model COPE):** **`rbg`**, `PreToolUse` ([`plugins/rbg/hooks/handlers.py`](../../plugins/rbg/hooks/handlers.py), `evaluate`) — loads the three-layer rule set (`rules.py`) and asks a fast, lightweight local Reflexes LLM evaluator model ([`evaluator.py`](../../plugins/rbg/hooks/evaluator.py)) whether each tool call complies with active rules. Runs in parallel across rules inside one deadline to advise the agent on every tool call. **Advisory and overridable, permanently**: it returns injected context, never a disposition, and no confidence score promotes it to one. On agy the same plugin states the live rule roster at `PreInvocation` (`inject_ruleset`) instead, because agy maps no tool event for the evaluator to judge.
- **Layer 2 (Session Stop RBG Check):** **`rbg`**, `Stop` and `SubagentStop` ([`plugins/rbg/hooks/handlers.py`](../../plugins/rbg/hooks/handlers.py), `rule_check`) — returns `decision: "block"` once per stop-chain, directing the agent that is stopping to run an explicit RBG rule check (`axioms/` + project-local + user rules) and present checkable evidence before handing over. What it withholds is the stop, not a tool call: the turn continues, and the agent uses it to run the check. The block is legal because the question is whether the check happened at all — a fact about the session — rather than a model's reading of a rule, which is why Layer 1 may never carry one.

  The hook obliges the check and never performs it. Nothing hook-side reads the transcript or grades what the agent did with the turn it was given; a mechanical verdict on the substance of an agent's work is the thing the governing principle above forbids.

  **The gate is unscoped, in one way that matters for cost.** `Stop` fires each time the session's own agent finishes a response, a turn boundary rather than a session boundary, so an interactive session meets the gate once per turn. On a face turn it composes with `ida`'s `strip_the_reply` quiet gate, which is registered on the same `Stop` event: two separate plugin processes, both blocks, each once per chain — `_merge`'s precedence is scoped to one plugin's own handler list (`ARCHITECTURE.md`, Hooks) and does not adjudicate between them, so the client fires and honours both.

  The mechanics it rests on — which events honour a block, and the once-per-chain guard that keeps a stop hook from re-firing against its own continuation — belong to the shared runtime and are stated in `ARCHITECTURE.md`, Hooks. What matters here is that neither is this gate's to opt out of.

  Two things the gate does not fire on, both so that its one block per chain is spent on the handback: a stop the client has marked as a continuation, and a stop taken while `background_tasks` are still running, when nothing is being handed back yet.

  **Which stop gate goes live is a standing question, and this one being live does not close it.** Two other gates are specified against the same event and neither is built: `pkb`'s task-release gate (`ARCHITECTURE.md`, Hooks) and the retired `aops` evidence gate (`present_checkable_evidence`). The mechanism is shared, so building a second is cheap — the constraint is that every gate on this event costs the blocked agent a turn, and they compose by addition, not by precedence. Adding one is a decision about that budget, not about the runtime.
- **Quiet gate (face-scoped):** **`ida`**, `Stop` ([`plugins/ida/hooks/handlers.py`](../../plugins/ida/hooks/handlers.py), `strip_the_reply`) — returns `decision: "block"` once per stop-chain, directing ida to strip its own reply to the person down to load-bearing content before it stops. Not a check on what was already said — the hook has no transcript to read, only the fact that a stop is about to happen. Silent on the continuation stop. Scoped to the face by its event: `Stop` fires only on the session's own turn boundary, and `SubagentStop` is deliberately not wired, because that event fires on the _stopping subagent's_ own context — wiring it there would direct a worker or james to strip a reply it never sends to the person. (The superseded `gate-wiring-v07` branch shipped this bug; it is fixed as of the `rbg-dual-channel-v07` supersede.)
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
worse than no message. `Stop` and `SubagentStop` fire at a turn boundary and are
guarded to once per stop-chain, so the text there can afford to be a full
instruction.

**Degradation reaches the agent, and reaches the person only sometimes.** A
handler that raises is caught in `_run_handler`, printed to stderr, and returned
as an advisory, so its reason lands in the agent's context on the same response
the hook would have carried — and a raising handler on a stop therefore fails
open, its block degrading to text. Everything a handler reports for itself, by
contrast, goes to stderr and no further: an evaluator that did not answer, a rule
file that could not be read. Those the client captures into the transcript and
renders to nobody, with no rate limiting and no route onto the response. So a
check that has quietly stopped checking is legible to the log, sometimes to the
agent, and not to the person who is the only one able to fix it. That asymmetry
is a known gap in the channel, not a property of it.

**Degradation is distinguished from legitimate absence** by the handlers
themselves: `rbg` with no evaluator configured, `$ACA_DATA` unset, and a project
with no local rules directory are all valid states, and each is a clean no-op
rather than a fault. And a fault is never a gate — reporting one cannot promote
any hook's disposition, and the tool call proceeds either way.

### 3. Claude Code's native auto-mode classifier

A model-based (not deterministic) tool-call classifier built into the harness, configured with prose rules in [`lib/polecat/defaults/claude-settings.json`](../../lib/polecat/defaults/claude-settings.json). Full design statement, admission criteria, and cost model: [auto-mode-classifier.md](auto-mode-classifier.md). Because it is an LLM judgment call over a stripped transcript rather than a deterministic pattern match, it sits inside the "agents all the way down" principle rather than beside it — it is the one place a per-action judgment call happens before the agent's own review loop closes.

### 4. Task-graph boundary — the primary enforcement point

`claim_task` in, `release_task` out. A completion claim must carry independent-verification evidence or a stated failure reason — this is where the framework actually holds agents accountable, because it binds to the claim act rather than to session mechanics. Full contract: [task-contract.md](task-contract.md); the universal claim-evidence shape every boundary reads: [evidence-contract.md](evidence-contract.md).

**The claim is written twice, deliberately.** The dispatch surface records one at launch; the worker claims the task from inside its own session, which is what moves the status. Two writes, because the launch record is the only thing that makes a worker which died before ever claiming legible as an unanswered dispatch rather than as work nobody picked up. Full invariant: [task-contract.md](task-contract.md).

**A boundary that agents sometimes never cross back through needs a sweep behind it.** No session is obliged to return, so nothing re-examines a claim once it is made: claims outlive dead sessions, merges land unwatched, and completed work sits uncertified. A `reconcile` skill was built to be that sweep — reading the graph against the evidence trail and writing back what is actually true, on engagement after an absence (commissioned by ida as a delegation, since touching the knowledge base is not hers to do), inside the consolidation cycle, and on demand. That skill is retired to `plugins.disabled/skills.disabled/reconcile/SKILL.md` and excluded from the build, so this sweep currently has no shipped procedure behind it. Behavioural spec: [reconcile.md](../workflows/reconcile.md).

A container emits no completion signal, so evidence reaches this boundary only because something carries it. The durable carrier is the task record the worker writes before exiting; the dispatch surface ([`plugins/ida/skills/dispatch/SKILL.md`](../../plugins/ida/skills/dispatch/SKILL.md)) supplies the second by running every container inside a plain background subagent — the courier — whose final message returns the worker's result as a harness notification. The courier is delivery, not supervision and not a gate: the worker's method stays entirely its own, and the claim-evidence contract above remains the thing that holds it accountable.

### 5. Task-boundary review — three pauli-specified lenses

- **pauli** (pre-hoc) — the premise standard: the idea is sound, elegant, and strongly aligned with the project's strategic aims when evaluated in the full context. Where composed in, it is emitted early and blocking, so the rest of the epic depends on it clearing. The former standalone dispatch-time "premise gate" (a two-judge hard-refuse ceremony run at `/pull`/`/dispatch`) is retired; decomposition carries this judgment instead, and dispatch surfaces trust the planner's decomposition rather than re-judging it.
- **rbg** — rules were followed: boundary review of the task contract and handback only (inputs/outputs), never the transcript.
- **marsha** (post-hoc) — the task does what it was supposed to and does it _well_: delivered artifact vs. the original aim and acceptance criteria, bar is excellent, not passing.

Each blocks epic acceptance where the composed process obliges it.

**Which of these a given piece of work runs is composed, not hardcoded — by design.** The `decompose` skill, retired to `plugins.disabled/skills.disabled/decompose/SKILL.md` and excluded from the build, was built to load the review process from the workflow-template namespace — shipped library, the user's own layer, and the PKB's `wf-*` templates, one namespace resolved later-wins-by-name — and turn each obligation it names into a real blocking node. The three lenses above are the standard those templates express; a fixed set carried in the skill's own text would be a process the user could never override. The rest of this section describes that design as `decompose` specified it; with the skill unshipped, nothing currently executes it.

Composition can yield an **empty** set, and that is the dangerous branch: work would pass decomposition carrying no review obligation and read as correctly planned. So a composed process obliging no review at all is itself a library gap `decompose` names and halts on — the same pathway as an obligation no layer defines.

**Human sign-off at a one-way door is not composed.** It is the [`one-way-door`](../../lib/axioms/one-way-door.md) axiom, binding the agent at the moment it crosses rather than the planner who drew the DAG. An obligation a template layer could drop, or name-shadow with a layer of its own, was never a floor; an axiom sits outside that namespace by construction.

`decompose` plans only: it emits those nodes and their `depends_on` wiring into the graph; it never dispatches or runs them itself. Review depth (per-chunk subtasks vs. one consolidated pass at the final PR) is the planner's call at decomposition time, based on the work's risk and blast radius. Full shape: [workflow.md](workflow.md).

**Certification at completion executes those nodes.** When a unit's return contract lands, the dispatch surface commissions the review the graph already carries — through the [`strategic-review`](../../plugins/ida/skills/strategic-review/SKILL.md) skill and `verify` (`plugins.disabled/aops/skills/verify/SKILL.md`, marsha's skill — not built, since `aops` lives in `plugins.disabled/` and the build excludes it) — and records the verdict on the task record, which [evidence-contract.md](evidence-contract.md) makes the message bus every handback crosses. One path, never a second review standing beside the nodes decomposition already emitted; and no judgment of the dispatcher's own, since relaying a worker's "confirmed" is what the gate exists to prevent.

**Certification therefore has a precondition: the certifying context must be able to spawn.** Commissioning a review means deploying reviewers, so a context holding no subagent surface cannot satisfy this gate at all — it must hand the unit to one that can, and refuse to self-certify in the meantime. A gate routed to a context that cannot execute it produces no verdict and no failure, which is the one outcome this boundary must not have. Contract: [`dispatch`](../../plugins/ida/skills/dispatch/SKILL.md) §4.

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
