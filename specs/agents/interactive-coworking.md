---
id: interactive-coworking
title: Interactive Co-Working — the polecat↔interactive axis, thin Ida sibling, hook-router separation
type: spec
status: approved
tier: core
depends_on: [polecat-system, agent-definition-content, agent-authority]
tags: [spec, agents, interactive-mode, hooks, ida, junior, agent-doctrine]
created: 2026-06-26
---

# Interactive Co-Working — the polecat↔interactive axis, thin Ida sibling, hook-router separation

**Status**: Approved (Nic, 2026-06-26). Design-dialogue origin and provenance record: [[mem-438429c5]] (consolidates decisions [[mem-47da1659]], [[mem-d241b0c2]], [[mem-f164fc68]] and the supervision-architecture note [[note-36c15a69]]; mechanism note [[mem-e7b976da]]). This spec file is the SSoT going forward; the note remains the dated provenance trail. Reconciled through two strategic-review rounds (rbg + pauli + marsha → james) plus a direct design dialogue with Nic.

> **Doctrine revision (Nic, 2026-06-26, supersedes the shared-skill design below).** Agents are **not subclassable**. The original design extracted the co-working disposition + quality floor into a single `interactive-coordinator` skill that both Junior and Ida referenced, with Ida written as Junior's "thin sibling" — that is subclassing, and it makes the agents non-portable and forces a leaky conditional (framework-coupled floor items kept "conditional" in a skill a stranger repo would load). New rule: **disposition lives in the agent definition; each head agent is fully self-contained and carries its own disposition inline** (duplicated prose across Junior and Ida is the accepted cost of self-containment). The `interactive-coordinator` skill is **deleted**. Reusable _procedures_ (dispatch mechanics, supervision, task lifecycle) stay where they already are — `/supervisor`, `/dispatch`, `/task-lifecycle` — and agents invoke them; that is not subclassing. Universal safety stays in the session-start SSoT only because it must reach agent-less surfaces (polecats), not for DRY. Sections below that describe the shared `interactive-coordinator` skill are retained for provenance but are superseded by this note.

## User Story

**As** a person co-working live, step-by-step, in a single local repo with the framework's head agent (Junior in the framework, Ida in a research repo),
**I want** the agent to hold between steps, answer questions it can answer itself, and not be interrupted by hard Stop-gate nags on legitimately-held turns,
**So that** interactive sessions feel like a capable collaborator rather than "the framework getting dumber" — while every agent, interactive or autonomous, keeps the same quality floor and the same non-negotiable safety invariants.

> **Coherence check**: This serves the core mission by making the _consistent quality_ axiom hold in both registers the framework actually runs in (interactive and autonomous) instead of only the autonomous one — and by removing the single highest-friction interruption (the handover/honesty Stop-gate firing on held interactive turns, #1978).

## Acceptance Criteria

**CRITICAL**: These criteria are USER-OWNED and define what "done" means. Agents CANNOT modify, weaken, or reinterpret them.

### Success Criteria (ALL must hold)

1. [ ] In an interactive (non-polecat) session, the agent **holds between steps** — the user drives the sequence — and does not front-run a plan or chase "land the plane".
2. [ ] In an interactive session, the agent **does not deflect a self-answerable question to the user** (the #1974/#1975 failure); it answers from its own means (read a file, confirm a fact) or delegates substantive work for context hygiene.
3. [ ] The **autonomous drive-to-completion** behaviour fires **only on the polecat surface**, not on every Junior session.
4. [ ] The **quality floor** (did what was asked / saved + committed / checked assumptions / gave references + confidence / did not stop short) is carried **in full by each agent's own definition** — Junior and Ida are each self-contained. Duplicated prose is the accepted cost; agents are not subclassed off a shared disposition block. _(Revised 2026-06-26 — was "sourced from one shared skill".)_
5. [ ] **Safety Invariants + PKB-HALT** are injected once from the **session-start SSoT** and reach **every** surface including polecats; no per-agent copy remains in `junior.md` or `ida.md`.
6. [ ] On the interactive path the handover gate is **soft block-once-then-release** (deliver once via the non-blocking agent-visible Stop channel, then open the gate); on the polecat path it is **hard block-until-resolved**.
7. [ ] The **honesty floor stays every-turn, revisable, and never silent** — preserved exactly as it runs on the branch today.
8. [ ] Hook posture (block/warn) is **resolved per-surface from `polecat.yaml`** via an explicit named "is this a polecat surface?" resolver; an unconfigured **posture** surface fails loudly (halt-on-unresolved), never silently blocks.
9. [ ] Ida is a **self-contained agent**: it carries its full co-working disposition, quality floor, and academic disposition **inline** — it does not reference Junior or a shared disposition skill. It adds the research dispatch default (local-delegate-and-wait); auto-selected per research repo via `"agent": "ida"` in `.claude/settings.json`. _(Revised 2026-06-26 — was "thin sibling references the shared skill".)_

### Failure Modes (if ANY occur, the implementation is WRONG)

1. [ ] A hard Stop-gate BLOCK fires on a legitimately-held interactive turn (reconstructs #1978).
2. [ ] An agent is written as a **diff against another agent** — "near-twin / inherits / do not duplicate" framing, or a reference to a shared disposition skill in place of carrying its own disposition. _(Revised 2026-06-26: self-containment now overrides the no-duplication goal for agent disposition; the forbidden thing is subclassing, not duplication.)_
3. [ ] `junior.md`'s safety copy is removed **before** session-start injection is _observed_ reaching a real polecat transcript — opening a window where polecat-Junior boots with zero safety prose.
4. [ ] The "no code-level gate-mode defaults" change touches a **safety** gate (`SENTINEL_GATE_MODE`, `RBG_REVIEW_GATE_MODE`, etc.), silently disabling a fail-safe. The rule is fenced to the two **posture** gates only.
5. [ ] "Fail loudly" is implemented as silent-allow (fail-open) on a safety gate — the forbidden failure is silent-_allow_, not silent-block.
6. [ ] The non-polecat surface is handled by a literal "remove default, else error" that either errors out or re-blocks interactive sessions, instead of an explicit named resolver branch.
7. [ ] _(Obsolete after the 2026-06-26 revision — there is no shared skill.)_ The PKB-curation / save-progress floor is fine to state plainly in each agent: both Junior and Ida are framework agents (they carry the PKB MCP tools), so they always operate in the framework context — no "conditional" leak to guard against.
8. [ ] A replacement transcript sentinel is added, or new tests are added, in the hook PR (out of scope — see below).

---

## Context

**Date**: 2026-06-26
**Status**: approved

## Problem Statement

**What problem does this solve?** Interactive co-working felt like "the framework getting dumber." The root cause is **not a missing agent** — it is that **Junior's instructions conflate two things**: (a) a quality floor every agent should uphold, and (b) an autonomous _drive-to-completion_ that is only correct for batch/polecat work. Applied to interactive sessions, (b) makes the head-agent front-run plans, deflect self-answerable questions to the user, and chase "land the plane." Separately, the handover and honesty **Stop hooks fire hard on legitimately-held interactive turns** (#1978 — the highest-friction item).

**Why does this matter?** The framework is _already_ used interactively (the lived evidence is the 2026-06-25 sessions and the design session itself). Fixing the conflation once benefits both Junior and Ida; the hooks stop interrupting held turns; and the safety floor becomes a single SSoT instead of drifting per-agent copies.

## The reframe (load-bearing)

The real axis is **polecat (autonomous, drive-to-done) vs interactive (hold between steps, same quality floor)** — NOT junior-vs-ida. Junior and Ida are near-twins. They differ in only two things:

- **Default dispatch surface**: Junior → polecat, fire-and-forget, lands work in GitHub PRs. Ida → local background subagent in the single working dir, **delegate and wait** for the result while staying live with the user.
- **Disposition**: Ida carries the academic/research disposition (`academic-disposition` SSoT); Junior the framework-coordination one.

Everything else is shared. In particular: **both agents delegate** (for context hygiene — to avoid the interactive head burning hundreds of thousands of tokens and losing the user's original intent); neither does substantive work inline. The only thing done inline is the watched/read-only/durable-capture carve-out (below). The earlier "do the step inline" framing was wrong; the #1974 failure was **deflecting a self-answerable question to the user**, not failing to delegate — keep the delegation, kill the deflection.

## Shared vs differs — the layering

- **Universal (ALL agents, incl. polecats)**: Safety Invariants + PKB-HALT. Lives in the shipped **session-start context SSoT** (one copy, injected everywhere). NOT duplicated into any agent definition.
- **Shared interactive-coordinator disposition (Junior + Ida) → a SKILL both reference** (a skill, not an agent, not a copied block): delegate-for-context-hygiene; hold between steps (user drives the sequence); do not front-run or plan before asked; do not deflect self-answerable questions to the user. The **quality floor** lives here. Per `note-36c15a69`'s core-vs-framework-coupled boundary: the honest-synthesis / did-what-was-asked / references-and-confidence / no-deflection items are **core-portable**; "curated the PKB" + "saved progress to the task" are **framework-coupled** and MUST be kept **conditional** in the skill (stranger-repo Ida always loads it). The skill carries the FULL inline-vs-delegate arbitration rule (below), not a compressed "trivial self-serve only" gloss.
- **Polecat-only**: the autonomous drive-to-completion / "land the plane without returning to the user" behaviour, keyed to the polecat surface — NOT applied to every Junior session.
- **Junior delta**: framework coordination; dispatch to polecats + PRs; fire-and-forget.
- **Ida delta**: research; single local working dir; delegate to local subagents and wait; academic disposition. Auto-selected per research repo via the `"agent": "ida"` key in `.claude/settings.json` (the key is `"agent"`, not `defaultAgent` — `mem-e7b976da`).

**Inline-vs-delegate arbitration rule** (the corrected framing — encode this, not the superseded "do the step inline"): delegate substantive work; do it inline **iff** (a) the user is actively watching this step, OR (b) it is read-only, OR (c) it is the durable-capture write the step asked for. Trigger (a) is about the user being in the loop, not triviality — its absence is what caused #1974/#1975.

## Agent-definition work

1. **Lift universal safety (Safety Invariants + PKB-HALT) into the session-start SSoT** for all agents; then remove the per-agent copies from `junior.md` (and don't add to `ida.md`). **HARD GATE**: do NOT remove `junior.md`'s safety copy until the session-start injection is **VERIFIED by observation** (the injected prose seen in a real polecat transcript, NOT inferred from hook source — the injection is silently skipped if the source is absent). One SSoT, not a third copy.
2. **Extract the shared interactive-coordinator disposition (incl. the quality floor) into a SKILL**; `junior.md` and `ida.md` both reference it. **DELETE the inline copy from `junior.md`** (reference-only) — extraction without deletion recreates the duplication this spec exists to kill.
3. **Re-tune Junior's instructions** to be correct for the interactive register it is _already_ used in. Split the conflated lines: keep the quality floor as shared; move the autonomous drive-to-completion to polecat-only. (Worker briefs anchor on CONTENT, not line numbers — line numbers rot.)
4. **Build Ida as a thin sibling**: reference the universal safety SSoT + the shared skill; add ONLY the research dispatch default (local-delegate-and-wait) + the academic disposition. Drop everything that duplicates Junior.
5. **Salvage from PR #1987** (do NOT merge it as a unit): keep `academic-disposition.md`; fold the genuinely-shared parts of the interactive-posture prose into the shared skill (most of it is shared, not Ida-specific); **drop** the `session_type`-filtered hook policies, the standalone interactive template, the template-registry entry, and the 8 tests; **finish the analyst de-dup** (the PR added a pointer but did NOT remove `analyst/SKILL.md`'s duplicated immutability/reproducibility prose). Close or repurpose #1987.

## Hook work — ONE cohesive PR (the whole hook-router SSoT refactor stays together)

1. **Separate the handover gate from the honesty/Ida gate** (the template-level split is done; finish the wiring).
2. **Differentiation axis = polecat-vs-not**, via the polecat-resolved `*_GATE_MODE` env (the sanctioned signal). NOT a `session_type` classifier; NOT a launch-time autonomous/interactive mode switch (explicitly rejected).
3. **No code-level gate-mode defaults — for the POSTURE gates only (`HANDOVER_GATE_MODE` / `IDA_GATE_MODE`).** Posture (block/warn/deny) is DEFINED per-surface in `polecat.yaml` and explicitly resolved for every surface. Remove the `gate_config.py` fallbacks for those two posture gates. **SCOPE FENCE**: do NOT remove the other `_GATE_MODE_DEFAULTS` entries — `SENTINEL_GATE_MODE` / `RBG_REVIEW_GATE_MODE` etc. are deliberate safety fail-safes (Nic directive: a real DENY), not papered-over gaps. For any safety gate, "fail loudly" means **halt-on-unresolved, never fail-open** — the forbidden failure is silent-_allow_, not silent-block. **RESOLVER**: the non-polecat/interactive surface obtains its posture via an explicit **named resolver branch** keyed on "is this a polecat surface?" (which reads the SSoT config), distinct from any silent fallback — a literal "remove default, else error" would either error out or re-block non-polecat sessions.
4. **Interactive (non-polecat) handover = soft block-once-then-release; polecat = hard block-until-resolved.** On the target harness (CC 2.1.191) a non-blocking, agent-visible Stop channel DOES exist via `hookSpecificOutput.additionalContext`; the legacy "block is the only Stop channel" (2.1.158) is STALE. The real distinction is **delivery vs enforcement** — a non-blocking nudge can be ignored, so only block-mode _enforces_. "Soft" therefore means _inject once (via additionalContext), then open the gate so the turn proceeds_; it is not a silent warn. The **honesty floor stays every-turn, revisable, never silent**.
5. **Handover firing cadence**: fire only when work was done (`session_did_work`) AND avoid over-firing on every interactive work-turn. Restore a lighter interactive cadence (surface at natural close / rate-limit) while keeping polecat fully armed. Tune frequency; do NOT restore a hard block on the interactive path.
6. **Remove the brittle transcript filter** in `user_prompts.py` (the `"before you stop" && "be honest"` substring match — a deterministic rig doing a semantic job that broke the instant the reminder was reworded). **Do NOT add replacement sentinels.** The structural transcript-rendering fix is DEFERRED to a future PR.
7. **No new tests in this PR** (per Nic).

## Decomposition / branch placement (Nic decisions, 2026-06-26 — do not reinterpret)

**TWO PRs total:**

- **Hook PR** — all of the hook work above — lands on branch `refactor/hook-router-ssot` (**PR 1970**). Keep the whole hook-router SSoT refactor together on this one PR.
- **Agent-doctrine PR** — ALL agent-definition work above (safety SSoT relocation, shared interactive-coordinator skill, Junior re-tune, thin Ida, #1987 salvage) — lands on **ONE separate PR stacked on `refactor/hook-router-ssot`** (base = that branch, **NOT** dev).

**Every implementing PR updates `specs/ENFORCEMENT-MAP.md`** in the same change (hook-mechanism relocation, safety-SSoT relocation, and agent-persona edits all count as mechanisms) — or it fails rbg on `enforcement-map-currency`.

## Scope

### In Scope

- The polecat-vs-interactive reframe and the shared-vs-differs layering across Junior and Ida.
- Relocating universal safety to the session-start SSoT (with the observation-based HARD GATE).
- Extracting the shared interactive-coordinator skill (with the core-portable vs framework-coupled split) and deleting the inline copies.
- Re-tuning Junior; building Ida as a thin sibling; per-research-repo `"agent": "ida"` config.
- Separating the handover gate from the honesty gate; posture in `polecat.yaml`; soft-once interactive vs hard polecat; firing cadence; removing the `user_prompts.py` substring filter; named non-polecat resolver.
- Salvaging `academic-disposition.md` and shared posture prose from PR #1987; finishing the analyst de-dup.

### Out of Scope (explicitly rejected — do not let these ride)

- A launch-time autonomous/interactive mode switch that reconfigures hooks.
- Using the (broken) `session_type` classifier as the hook-differentiation axis.
- Merging PR #1987 as a unit.
- Adding replacement transcript sentinels now.
- Adding new tests now.
- Cramming the interactive posture into Junior as a single fat agent carrying two contradictory dispositions (resolved instead by the reframe + the shared skill).

**Boundary rationale**: This is one coherent change because the friction, its root cause, and the fix all sit on the single axis of _polecat-autonomous vs interactive-held_. The hook separation and the agent-doctrine work are split into two PRs (above) only for review cohesion, not because they are different problems.

## Follow-ups (separate tasks, out of these two PRs)

- **Fix or deprecate** the broken autonomous/interactive `session_type` classifier (a hand-typed interactive Junior session classified as `autonomous`). No longer load-bearing for hooks but still wrong. Relates to `epic-f133d439` (session taxonomy).
- **Verify** the session-start safety injection reaches polecats; verify both gates resolve posture from `polecat.yaml`.
- **Future PR**: proper structural transcript rendering of hook output (no sentinels) — the deferred replacement for the removed `user_prompts.py` filter.

## Dependencies

- [[polecat-system]] — the autonomous dispatch surface that the `*_GATE_MODE` posture and the polecat-vs-not axis key on.
- [[agent-definition-content]] — content-boundary rules that govern what may stay in `junior.md` / `ida.md` vs move to the shared skill or SSoT.
- [[agent-authority]] — frontmatter schema, skill-delegation and non-transit rules the thin-sibling Ida must satisfy.
- `specs/ENFORCEMENT-MAP.md` — must be updated by every implementing PR (enforcement-map currency).
- `.agents/CORE.md` (session-start SSoT) and the session-start injection hook — the destination for the relocated safety prose.
- The `academic-disposition` SSoT (salvaged from PR #1987) — Ida's research disposition source.

## Provenance

- Design dialogue / dated trail: [[mem-438429c5]] (this spec distils it; the note is retained as the provenance record).
- Decisions: [[mem-47da1659]] (no launch-time hook mode; polecat-vs-not BLOCK/WARN; no code defaults — posture in `polecat.yaml`), [[mem-d241b0c2]] (round-1 verdict + corrections), [[mem-e7b976da]] (`"agent"` key default-agent mechanism), [[mem-f164fc68]] (original Ida-elevation decision — now reframed by this spec), [[note-36c15a69]] (supervision architecture; core-vs-framework-coupled boundary).
- Tracking: fix-epic `aops-a3213dde`; decomposition `aops-8e826545`.
