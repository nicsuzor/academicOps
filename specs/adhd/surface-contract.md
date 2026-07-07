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

The **aops-adhd plugin** is the accommodations layer Nic needs "to function like
an adult" (RULING A1, `aops-fef39347`) — not a features wishlist. Two scope
disciplines bound every design decision in it: existing features are made
meaningful before new ones are built (A3), and `/email`/`/extract` capture
moves into this plugin rather than staying a stray front-end (A4).

This document specs **one** deliverable inside that plugin: the
**attention-surface contract** — what the daily note / morning brief must put
above the fold, and the rules that keep it trustworthy. It is the surface
contract ruled by Nic on 2026-07-07 (ruling A15), written up for his wording
review. It is not the plugin's full manifest, trait inventory, or a nesting
decision for the coordinator layer (A8) — those remain open, tracked
separately (see **Out of scope**, below). No implementation is proposed or
performed here; this is the contract a later build task implements against.

## The problem this contract solves: storage ≠ surfacing

The plugin's reason to exist is one lesson, arrived at the hard way in dogfood
session `aops-fef39347` on 2026-07-07:

> "My tasks are like an ocean I swim around in; I pick out a few every now and
> then, but most stuff doesn't get done." — Nic, 2026-07-07

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

## The surface contract (RULING A15, approved 2026-07-07)

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
carryover into today's ranking directly reverses the dogfood critique on
`aops-09ea502a` ("carryover tasks: do NOT separate from today's tasks").

### 2. Decide (2–3 questions)

Self-contained questions drip-fed from the judgment-pool — the backlog of
open calls only Nic can make. A question keeps resurfacing here until it is
dispositioned; it does not silently drop off after one showing. "Self-
contained" means answerable without opening another document: state the
choice and the options in the question itself, per the head-role-charter's
AC-17 (form and defend a position; a menu is a floor, not a finish line) and
anti-pattern 16 (density-compliant but unreadable) — this block must read
cold, not assume the reader remembers the thread.

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

This directly answers the dogfood finding on `aops-09ea502a`: Nic's real PR
surface is his own GitHub search, which already shows live state; the daily
note's job is to point at it, not re-derive a copy that goes stale within
hours.

## Intent capture: Priority 1 is the only lever

Stated intent ("I want to do Post CV today") is encoded as **Priority 1, and
only Priority 1** — never as a fabricated due date (`mem_624664d1`; the
taxonomy question is tracked on `nicsuzor/academicOps` PR #2137). Due dates
are real-world deadlines exclusively; a fabricated one poisons deadline trust
across every surface that reads `due`. This was a live correction: an earlier
session stamped `due=today` on a Post CV task as an ad hoc "intent marker" and
Nic reverted it hard.

Consequence for ranking: **Today**'s importance-as-of-today score is graph
weight combined with Nic's outstanding P1s — not a due-date proxy. If P1 ever
gets too crowded to signal (multiple competing P1s drown each other out), the
fix is demoting other P1s — Nic's call, made explicit — and, separately, a
server-side write-floor that keeps P1 from silently reinflating; that floor is
a companion task under `task-8ad584f6` and is **not** implemented by this
contract.

## Cold-open recovery: the prototype this contract builds on

The plugin's cold-open capability (US-1/US-5 in the interactive-experience
charter tradition) already has a working prototype, run overnight
2026-07-06→07 as charter §2a of the brain-canonical Junior charter (six
parallel cheap subagents: PKB tasks across all projects + stale claims,
session transcripts, local git across every checkout, GitHub across all repos,
daily notes, email/calendar) — see the produced brief, `note-fcd1b887`. Three
findings from that run are load-bearing for this contract:

- **Cost/latency**: ~560k subagent tokens, longest sweep ~5 minutes wall,
  head context stayed clean — viable as an overnight/session-close precompute,
  too heavy to re-run inline on every "catch me up."
- **Three-part synthesis, not one**: what happened (activity), what Nic was
  actually trying to do (intent vs. yak-shave), and dropped threads (opened,
  never closed). A single-source catch-up (one task body, one repo's PR list)
  is not an acceptable substitute — see anti-pattern 18.
- **The TrustCon lesson**: the same overnight brief asserted "registration
  closes tomorrow" as the headline from email/calendar traces, when the
  underlying task (`admin-3aac6be1`) had in fact been closed a week earlier.
  The failure was in the sweep, not the capture: it asserted urgency without
  cross-checking structured task status first. **Any cold-open sweep feeding
  this surface contract must cross-check structured status (task `status`,
  not just prose/email traces) before asserting urgency** — the same
  verify-at-write discipline that governs the PR-pointer rule above applies
  here too.

This contract does not itself move the brain-canonical charter's §2a sweep
into the plugin — that migration (personal prototype → plugin-owned
capability) is future implementation work, referenced here as the evidence
base, not absorbed into this spec.

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
  prose questions (head-role-charter AC-17; anti-patterns 16/18/19).

Two related hook-text changes were in flight at the time of this ruling and
are referenced, not specified, here: the Ida honesty-at-Stop notice moving to
a silent self-check with no repetition, and background-task notifications
moving to "act, don't surface unless important." Both are wiring work on the
enforcement side (`specs/enforcement/GATES.md`), not attention-surface
contract content, and are out of scope for this document.

## Related work — referenced, not absorbed

This contract deliberately does not duplicate or take over the following
adjacent efforts. Each owns its own scope; this document only points at them
where the surface contract depends on their eventual output.

| Task                                                                        | Relationship to this contract                                                                                                                                                                                                                                                             |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `task_bd1d28ba` — prompt-ledger `/sleep` miner                              | Feeds the capture→circulation gap (why stated decisions go uncaptured); this contract assumes capture already happened and focuses on surfacing what was captured.                                                                                                                        |
| `overwhelm-dashboard-7b8eacff` — session visibility via overwhelm dashboard | A head's read-path into in-progress sessions; a candidate future input to **Today**'s ranking, not built into this contract.                                                                                                                                                              |
| `aops-09ea502a` — daily-note redesign feedback                              | Its detailed critique list is the empirical input this contract answers (summary utility, deadline duplication, priorities≠intent, stale PR list, carryover segregation); treat that task's checklist as the acceptance test for an eventual daily-note implementation against this spec. |
| `task_5dd6cc88` — recent-interactive-transcripts navigation                 | A separate navigation surface (browsing session history), not part of the daily-note/morning-brief attention surface.                                                                                                                                                                     |
| H11 (per-prompt hint slot, `ENFORCEMENT-MAP.md`)                            | The UserPromptSubmit skills-routing hint's target home is `aops-pkb`/`aops-adhd`; wiring that injection is enforcement-layer work, not this contract.                                                                                                                                     |

## Out of scope for this document

- The aops-adhd plugin's full manifest, trait inventory, and package
  scaffolding (not yet ruled — Nic drives that conversation separately).
- The junior/Ida coordinator-nesting question (A8) — open, unruled.
- Disposition of in-session enforcement hooks (agenda 2 of `aops-fef39347`,
  already resolved separately as rulings H1–H18; unrelated to this surface).
- The server-side P1 write-floor (`task-8ad584f6`).
- Any actual implementation of the daily note / morning brief against this
  contract — a follow-up build task, once this spec is confirmed.

## Provenance

All rulings cited here were made live with Nic on 2026-07-07 in session
`aops-fef39347` (parent task; full session log on that task's body). Summary:

| Ruling                               | What it settled                                                                               |
| ------------------------------------ | --------------------------------------------------------------------------------------------- |
| A1, A3, A4                           | Plugin scope: accommodations-to-function framing; existing-features-first; `/email` moves in. |
| Storage≠surfacing (`mem_7e2e9864`)   | The core lesson this whole plugin answers.                                                    |
| A15                                  | The three-block surface contract (Today / Decide / live pointers) specified above.            |
| A14, `mem_624664d1`                  | Intent capture is P1-only; no fabricated due dates.                                           |
| A12, `mem-398f664e`, `note-fcd1b887` | Cold-open sweep prototype, its cost/latency evidence, and the TrustCon cross-check lesson.    |
| A13/A14 comms corrections            | Interaction contract: cold-reader invariant, no play-by-play, headings, `AskUserQuestion`.    |
