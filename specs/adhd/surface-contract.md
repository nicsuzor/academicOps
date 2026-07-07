---
id: adhd-surface-contract
title: Attention-Surface Contract — aops-adhd Plugin
type: spec
status: draft
tier: core
depends_on: [head-role-charter]
tags: [spec, adhd, attention, surfacing, daily-note, cold-open, interactive-experience]
created: 2026-07-07
---

# Attention-Surface Contract — aops-adhd Plugin

## Scope of this document

The **aops-adhd plugin** is the accommodations layer Nic needs to function
day-to-day — not a features wishlist. Two scope disciplines bound every
design decision in it: existing features are made meaningful before new ones
are built, and `/email`/`/extract` capture moves into this plugin rather than
staying a stray front-end.

This document specs **one** deliverable inside that plugin: the
**attention-surface contract** — what the daily note / morning brief must put
above the fold, and the rules that keep it trustworthy. It is not the
plugin's full manifest, trait inventory, or a nesting decision for the
coordinator layer — those remain tracked separately (see **Out of scope**,
below). A related but distinct question — whether coordination should run as
a standing background process, and what the head↔coordinator interface is —
is now settled; its consequence for this plugin is folded into the
**Interaction contract** section below, since the plugin only _consumes_ that
capability rather than owning it. No implementation is proposed or performed
here; this is the contract a later build task implements against.

## The problem this contract solves: storage ≠ surfacing

The plugin's reason to exist is one lesson, arrived at the hard way:

> "My tasks are like an ocean I swim around in; I pick out a few every now and
> then, but most stuff doesn't get done." — Nic

An accurate PKB entry that never reaches Nic's attention does not get done.
Reporting "X is now stored at Y" is not a completion — the question a
surfacing-aware agent always answers is **when will this be SURFACED, and
where**. Three requirements follow, and they are the plugin's actual product,
not the graph itself:

1. Every task connected by edges/weights so graph importance is computable.
2. A surfacing mechanism that pushes the top of that ranking to Nic.
3. An audit loop for mis-ranked or invisible items.

The surface contract below is requirement (2) for the daily note / morning
brief specifically — the highest-traffic surface, not the only one.

## The surface contract

The top of the daily note / morning brief has exactly three blocks, in this
order. Everything else — full task lists, completed-work logs, historical
detail — sits below the fold or behind a link.

### 1. Today (max 5 lines)

Ranked by **importance-as-of-today**: graph weights combined with Nic's stated
P1 intents (see **Intent capture**, below). There is **no carryover section**.
Yesterday's undone items are not segregated from today's — they compete for
the same five lines on the same ranking, because a separate "carryover" block
is only useful when someone explicitly asks "what did I leave undone
yesterday," which is a different question from "what matters today." Folding
carryover into today's ranking directly reverses a specific dogfood critique:
carryover tasks must not be segregated from today's tasks.

### 2. Decide (2–3 questions)

Self-contained questions drip-fed from the judgment-pool — the backlog of
open calls only Nic can make. A question keeps resurfacing here until it is
dispositioned; it does not silently drop off after one showing. "Self-
contained" means answerable without opening another document: state the
choice and the options in the question itself, per the head-role-charter's
AC-17 (form and defend a position; a menu is a floor, not a finish line) —
this block must read cold, not assume the reader remembers the thread.

### 3. Live pointers, never copied state

Anything with an authoritative home elsewhere — Nic's PR search
(`https://github.com/pulls/2484647`), task status, calendar — is **linked and
verified-at-write**, never snapshotted into the note as a list. Concretely:

- **Point, don't copy.** A link plus one clause on why it matters, never a
  copied table of rows that will drift the moment the source changes.
- **Verify-at-write or don't assert.** Cross-check the authoritative source at
  composition time; do not carry forward a claim from a prior sweep without
  re-checking it.
- **Green-only PR surfacing.** Only surface a PR to Nic when it is actually
  ready (green / CI passing). A stale "five mergeable PRs" list that turns out
  red hours later is worse than no list — link to the live search instead.

This directly answers a specific dogfood finding: Nic's real PR surface is
his own GitHub search, which already shows live state; the daily note's job
is to point at it, not re-derive a copy that goes stale within hours.

## Intent capture: Priority 1 is the only lever

Stated intent ("I want to do Post CV today") is encoded as **Priority 1, and
only Priority 1** — never as a fabricated due date. Due dates are real-world
deadlines exclusively; a fabricated one poisons deadline trust across every
surface that reads `due`. This was a live correction: an earlier session
stamped `due=today` on a Post CV task as an ad hoc "intent marker" and Nic
reverted it hard.

Consequence for ranking: **Today**'s importance-as-of-today score is graph
weight combined with Nic's outstanding P1s — not a due-date proxy. If P1 ever
gets too crowded to signal (multiple competing P1s drown each other out), the
fix is demoting other P1s — Nic's call, made explicit — and, separately, a
server-side write-floor that keeps P1 from silently reinflating; that floor
is a companion follow-up and is **not** implemented by this contract.

## Cold-open recovery: the prototype this contract builds on

The plugin's cold-open capability (US-1/US-5 in the interactive-experience
charter tradition) already has a working prototype: a parallel-subagent sweep
across PKB tasks and stale claims, session transcripts, local git, GitHub,
daily notes, and email/calendar. Three findings from that prototype are
load-bearing for this contract:

- **Cost/latency**: roughly 560k subagent tokens and up to ~5 minutes wall
  time for the longest sweep, head context stayed clean — viable as an
  overnight/session-close precompute, too heavy to re-run inline on every
  "catch me up."
- **Three-part synthesis, not one**: what happened (activity), what Nic was
  actually trying to do (intent vs. yak-shave), and dropped threads (opened,
  never closed). A single-source catch-up (one task body, one repo's PR list)
  is not an acceptable substitute.
- **Cross-check structured status before asserting urgency**: an early
  prototype run asserted a stale deadline from email/calendar traces without
  checking that the underlying task had already closed. The failure was in
  the sweep, not the capture. **Any cold-open sweep feeding this surface
  contract must cross-check structured status (task `status`, not just
  prose/email traces) before asserting urgency** — the same verify-at-write
  discipline that governs the PR-pointer rule above applies here too.

This contract does not itself move that sweep into the plugin — that
migration (personal prototype → plugin-owned capability) is future
implementation work, referenced here as the evidence base, not absorbed into
this spec.

## Interaction contract (binds every aops-adhd surface, not just the daily note)

These rules govern any message this plugin's surfaces produce — daily note,
morning brief, or a live chat turn — and are carried over from the
interactive-experience head-role-charter rather than restated as new
obligations:

- **Cold-reader invariant.** Every message is self-contained; there is no
  reliable "current attention state" to compress for, so density is not
  modulated by a guessed reader state (see head-role-charter, Fitness
  Criteria). IDs, ruling codes, and task hashes get a one-clause
  reintroduction, never bare references.
- **No play-by-play.** Report outcomes, not process — a subagent's thread,
  worker ID, or log path never belongs in a surface Nic reads (anti-pattern:
  "logging state anywhere other than the PKB" / "restating instruction back as
  warning").
- **Final-message-full-state.** The last thing Nic sees reflects the complete
  current state, not an intermediate step glossed as final.
- **Headings recalling the task.** Any heading assumes the reader is coming in
  cold hours later — it names what the section is about, not just a ruling
  label.
- **`AskUserQuestion` for decisions.** Genuine judgment calls use the
  structured decision surface, pre-resolved to options, rather than open-ended
  prose questions (head-role-charter AC-17).

### Coordinator boundary

The **no play-by-play** rule above is not just a style preference — it is a
deliberate scope boundary:

- **No standing background coordinator.** A daemon, cron tick, or persistent
  `/supervisor` process was considered and rejected. Coordination (dispatch,
  worker lifecycle, reconcile) stays **in the interactive session**, but runs
  **out of the head's context** — offloaded to an in-session coordinator
  subagent. The head remains the summarise-and-liaise veneer this contract
  specs; it never itself grinds the queue.
- **Boundary split by durability.** The coordinator subagent owns _durable_
  coordination state: queue, dispatch, worker lifecycle, reconcile. The head
  keeps only cheap, disposable subagents for conversation-serving lookups
  (read a file, check one status) — never for anything that must persist
  across turns.
- **Architectural home.** The coordinator _capability_ belongs to
  supervisor/aops-polecat machinery, not to this plugin. **aops-adhd consumes
  it**, it does not build or own it: the plugin's only stake is the
  interaction-contract consequence above — a calm liaison head, with no
  time-based ruling-log ever dumped on Nic as a substitute for the
  three-block surface contract. Any coordinator implementation work (queue
  mechanics, dispatch logic) is out of scope here; see **Out of scope**,
  below.

The head↔coordinator **interface contract** has also been probed live (a
multi-chore coordinator-subagent session) and ratified as probed:

- **One persistent coordinator subagent per interactive session.** Spawned on
  the session's first coordination need, then **resumed by message per
  chore** — not spawn-per-chore, and not a daemon. Cross-chore memory
  demonstrated its value in the probe: the coordinator surfaced a red CI
  check unprompted because its earlier chore's state made the anomaly
  visible. It owns durable coordination per the boundary above.
- **The durable seam is a rolling PKB state note**, kept in rank-and-narrate
  style: live pointers plus one line of why-it-matters each, verify-at-write,
  with a self-expiry hedge — never copied state snapshots. The head sends the
  coordinator **goal-briefs**, receives **outcome-only reports**, and
  narrates to Nic **from the note** — never from a time-based log.
- **Act-don't-surface over-suppression risk: the retirement trigger is
  sufficient.** No extra safety valve is needed now for the task-notification
  guidance injection (the "act, don't surface unless important" behaviour
  referenced below). The trigger stands: retire the mechanism if the next 5
  `/retro` reviews show over-suppression incidents — and retros watch for
  exactly this.

This defines the **contract**, not the machinery: how the coordinator is
implemented (subagent plumbing, message-resume mechanics, state-note tooling)
remains supervisor/aops-polecat work, out of scope for this plugin.

Two related hook-text changes were in flight at the time of this contract and
are referenced, not specified, here: the Ida honesty-at-Stop notice moving to
a silent self-check with no repetition, and background-task notifications
moving to "act, don't surface unless important." Both are wiring work on the
enforcement side (`specs/enforcement/GATES.md`), not attention-surface
contract content, and are out of scope for this document.

## Out of scope for this document

- The aops-adhd plugin's full manifest, trait inventory, and package
  scaffolding — not yet decided; Nic drives that conversation separately.
- The junior/Ida coordinator-nesting question — open, undecided.
- The coordinator subagent capability itself — queue, dispatch, worker
  lifecycle, reconcile mechanics, and the plumbing that implements the
  head↔coordinator interface contract (the contract itself is specified
  above) — owned by supervisor/aops-polecat machinery, not this plugin (see
  **Coordinator boundary** above). This document consumes their consequence,
  not their implementation.
- Disposition of in-session enforcement hooks — already resolved separately;
  unrelated to this surface.
- The server-side P1 write-floor.
- Any actual implementation of the daily note / morning brief against this
  contract — a follow-up build task, once this spec is confirmed.
