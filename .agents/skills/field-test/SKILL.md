---
name: field-test
description: Procedural guide for validating a framework change end to end — audit the instruction surface, then prove the behaviour where it actually runs. Use when changing instructions, hooks, or execution plumbing; when certifying a release; or when a change has passed every static check and still needs to be believed. Prescribes goals and checks, not techniques — tools drift, obligations do not.
---

# Field-test — prove it where it runs

Each phase states a goal and the check that settles it. Techniques — which
harness, which flags, where today's logs live — drift; get current mechanics
from the tool's own help and the project's debugging skill. The obligations
below are what stay true.

## 0. Pre-register the claim

**Goal: know what you are testing before any evidence exists.**

- Before gathering evidence, write one sentence: what should be observably
  different, on which surface, for whom.
- Score every later result against that sentence, never against "the session
  looked fine". A pass condition chosen after seeing the output measures
  nothing.

## 1. Stand on verified ground

**Goal: classify against documents that exist, as they are now.**

- Open every document your judgment relies on before relying on it. A citation,
  an index row, or a brief's pointer is a claim that the document exists — not
  evidence.
- A missing ground-truth document is a finding to report, and it narrows what
  you may conclude. Never substitute a plausible reconstruction of what it
  probably said.

## 2. Distrust reported absence

**Goal: delegate the sweep, own the verdict.**

- Fan searching and inventory out to other agents freely; before acting on any
  load-bearing claim, reproduce its decisive evidence yourself.
- Read "X does not exist" as scoped to what the reporter could see. A name can
  resolve in a layer the reporter had no access to; check every layer a name
  can live in before deleting anything on the strength of its absence.

## 3. Prove the artifact, not the source

**Goal: the deployable carries the change.**

- Build the real deliverable and confirm the change is present in the built
  artifact — the thing that ships, not the tree you edited.
- A cached build that looks rebuilt is evidence of nothing. Know how your build
  proves freshness, and use that proof before certifying anything.

## 4. Drive the changed path, live, on every surface

**Goal: observed behaviour everywhere the change ships.**

- Walk the layers in order — structure, boot, a trivial interaction, then the
  specific path your pre-registered sentence names — and stop at the first
  failure: results from later layers are uninterpretable once an earlier one is
  broken.
- Repeat the whole walk once per client, per execution environment. A pass on
  one surface is no evidence for another; asymmetric breakage is the common
  case, not the edge case.
- Exercising an arbitrary path proves the machinery and says nothing about your
  change. The driven path must run through what you touched.

## 5. Judge from the authoritative record

**Goal: verdicts read off durable evidence, not rendered views.**

- For each claim, name the channel that is authoritative for it — a transcript,
  a structured log, an exit code — and judge from that. What a UI renders is
  evidence of neither delivery nor non-delivery.
- Where the claim is "event X happens", find the instrumented record of events
  and count occurrences. Do not infer runtime behaviour from reading source.

## 6. Force the quiet failures

**Goal: graceful degradation observed degrading, loudly, from inside.**

- A mechanism that degrades rather than fails is presumed off until you have
  observed it working in the deployed environment. Its degradation notice is the
  only thing that makes the silent state findable — confirm the notice fires and
  that something reads it.
- Every value that crosses an isolation boundary — an address, a path, an
  identity, anything that means "this machine" — must be re-checked from the far
  side: does it still name the same thing there? Test reachability from inside
  the environment, never only from where you launched it.

## 7. Deletion has consumers

**Goal: nothing surviving depends on what you removed.**

- After any removal, sweep inbound references and repair each — then go further
  and re-derive the behaviour of every surviving consumer. Reference checks
  passing is not that: the characteristic regression is a contract that
  silently became empty and still reads as valid.
- Budget at least one blind run: a contextless agent, given only the revised
  surface and a representative task, finds the dead end your checks cannot.

## 8. Gates must be decidable by their reader

**Goal: every halt-or-proceed condition is checkable from what its reader may
read.**

- A gate that turns on a term defined outside the reader's permitted materials
  is undecidable, and undecidable gates get resolved by mood — differently by
  every capable reader.
- Reference other modules by function, never by their internals. If an
  instruction needs another module's internals to be intelligible, the boundary
  is drawn wrong; move the gate's trigger onto something local.

## 9. A tripped guard is information — about one of you

**Goal: guards get sharper or deleted, never dodged.**

- When your change trips an existing check, first ask what the check actually
  tests. One that pins a copy of a setting or source text against the same
  literal held in the test is drift dressed as a guard: replace the duplicate
  with one shared source of truth, or delete the check outright.
- Where the check does test behaviour, either your change is wrong or the check
  states its intent too coarsely — determine which and fix that one, in the
  open. Rephrasing your change so the check stops seeing it is forbidden, and
  always visible in review.

## 9b. Oddity defaults to drift, not design

**Goal: nothing survives review because someone assumes it was meant.**

- An exception, a special case, or an inconsistency in the existing surface is
  more likely stale than intentional. The burden of proof sits on keeping it:
  an exception earns its place with a stated necessity, or it goes.
- "The carve-out is coherent" is not that proof — a rationale you can construct
  after the fact is exactly what drift looks like from inside.

## 10. Close the loop on the original observation

**Goal: "fixed" means the originally-failing observation now passes.**

- Re-run the exact observation that failed, in the environment where it failed,
  and record the before and after with the cause.
- File what you fixed and what you deliberately left, each with its evidence,
  where the next session will find it.

## 11. Publish the grades where the next round starts

**Goal: the next session starts from your verdicts, not your transcript.**

- Grade every component you drove against the real bar: **green** — observed
  working end-to-end _and_ efficient and useful; **amber** — works, but with
  caveats, pending operator action, or usefulness unproven; **unmarked** — not
  field-tested. "Technically working" is not a grade. Repeated injections,
  redundant token spend, and noise a user must wade through are amber findings
  even when the mechanism functions.
- **Mark the grades on the project's wired map** (the excalidraw file the
  umbrella epic names). Convention: append-only badge elements placed beside the
  component — green `✅` / amber `⚠` text, each badge dated and naming the PR it
  came from — plus one legend stating the bar and that unmarked means untested.
  Append with index keys after the current maximum, then verify the file
  re-parses with element order preserved before leaving it: the map can pass
  every referential check and still be unopenable, and an unopenable map is
  worse than no marks.
- **Stale badges lie.** On a later round, update or remove any badge your new
  evidence supersedes before adding your own.
- File one evidence record per finding — wins as well as friction — and put the
  per-component grade table on the round's task record, which is the only
  surface a cold session is guaranteed to read.

## Fitness test

A stranger holding only your report can tell which claims were observed and on
what channel, re-run each decisive check from what you cited, and state what
remains unproven. A claim that cannot be traced to a channel named under §5
means the walk is not done.
