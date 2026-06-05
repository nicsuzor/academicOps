# Replay fixture — overwhelm-dashboard landing page (2026-06-03)

This is the **acceptance proof** for the QA anti-anchoring fix (epic `aops-f5fa0d0b`, GH
issues #1150 + #1152). The rewritten `/verify` gate — specifically the [forcing checks](../SKILL.md#forcing-checks--resolve-before-any-pass-on-a-user-facing-artifact) —
must return **FAIL/HALT** when replayed against the artifact that originally got a spurious
PASS. If a reviewer can walk this fixture through the gate and still reach PASS, the
mechanism is fake (the same failure the prose methodology already had).

The fixture is a captured description of the real artifact, not the live page, so the proof
survives a cold context with no running dashboard. The defects below are the ones recorded
in the incident (task `aops-1d6482c8`, session `e49af3b8`, and GH #1585/#1150).

---

## Fixture — what the page rendered

A coordinator landing page ("overwhelm dashboard") whose job is to surface, at a glance, the
shape of the principal's (Nic's) work: what threads are live, how confident each is, what's
merged, how fresh the data is, and where he left off.

As captured on 2026-06-03, the page rendered:

| Region / field                        | What it showed                                                              |
| ------------------------------------- | --------------------------------------------------------------------------- |
| Every thread card → **confidence**    | `DERIVER_MISSING`                                                           |
| Every thread card → **PRs merged**    | `DERIVER_MISSING`                                                           |
| Freshness / poller status             | `NO_GITHUB_POLLER` / `NO_GIT_POLLER`                                        |
| Continuation per card (3 cards)       | all collapsed to one generic `triage_inbox` id                              |
| **"WHERE YOU WERE"** (headline panel) | an autonomous worker's dispatch prompt, surfaced as Nic's own last activity |

The page was **honest** about its emptiness — the sentinels are axiom-9-truthful, not fake
data. The original reviewer (marsha) seized on exactly that and returned **PASS**, praising
"the axiom-9 honesty of the sentinels as the strongest signal."

---

## Replay — the rewritten gate applied to the fixture

Run the three forcing checks. Each has a mechanical answer; record it in the verdict.

**1. Sentinel / empty-state audit.**
Load-bearing fields rendering as a sentinel / honest-failure token:

- confidence → `DERIVER_MISSING` (every card)
- PRs merged → `DERIVER_MISSING` (every card)
- freshness → `NO_GITHUB_POLLER` / `NO_GIT_POLLER`
- continuation → degenerate (`triage_inbox` on all three cards — not a real per-card value)

The page's **primary value-signals** — "how confident is each thread, what's merged, how
fresh is this" — are _all_ absent. That is the definition in the gate: _if the artifact's
primary value-signals are absent, the verdict is FAIL._ "Honest about being broken" is the
floor, not fitness. → **FAIL.**

**2. Principal's-eye top-line read.**
The single most-prominent element is the **"WHERE YOU WERE"** headline. Read as Nic: it
claims his last activity was a dispatch prompt that an _autonomous worker_ issued — not
something Nic did. The most prominent, most confidently-rendered line on the page is **wrong
for the end user.** → **FAIL.**

**3. Floor vs ceiling — "exceptional, or merely working?"**
Not even merely working: the value-bearing surface is empty and the headline is wrong. There
is no honest reading on which this clears a fitness bar. → far below the floor. → **FAIL.**

---

## Replay verdict (in the required format)

```
## Verification Report

**Bar:** fitness
**Verdict:** FAIL / HALT

### Concrete observations
- Every thread card renders confidence + PRs-merged as `DERIVER_MISSING`.
- Freshness reads `NO_GITHUB_POLLER` / `NO_GIT_POLLER`.
- 3 cards collapse to one generic `triage_inbox` continuation id.
- "WHERE YOU WERE" headline surfaces a background worker's dispatch prompt as Nic's activity.

### Forcing checks
1. Sentinel/empty-state audit: 4 load-bearing field groups are sentinels
   (confidence, PRs-merged, freshness, continuation). Primary value-signals ABSENT → FAIL.
2. Principal's-eye top-line read: "WHERE YOU WERE" = an autonomous worker's dispatch prompt,
   presented as Nic's own last activity. Most prominent element is WRONG for the user → FAIL.
3. Floor vs ceiling: not exceptional, not even merely working — value surface empty and
   headline wrong. → FAIL.

### Judgement
The artifact is truthful about being empty, and that truthfulness is the floor, not the
ceiling. Its reason to exist — surfacing the shape of Nic's work — is unmet on every
load-bearing field, and its most prominent line is factually wrong for the principal.
Honesty-about-emptiness was the exact signal the original PASS laundered into "works"; the
gate now forces that audit into the verdict, where it reads as FAIL.

### Recommendation
HALT. The derivers feeding confidence / PRs-merged / freshness must produce real values, the
continuation must vary per card, and "WHERE YOU WERE" must reflect the principal's own last
activity, before this returns for re-verification.
```

**Result: FAIL/HALT — the gate fires.** Acceptance addendum (epic `aops-f5fa0d0b`) satisfied.

---

## Why this replay is the proof that matters

The original methodology _already contained_ "Red flags (HALT triggers) → immediate FAIL" and
the reviewer had it loaded. It still PASSed, because nothing forced the sentinel count or the
top-line read into the verdict — the reviewer kept the discretion to reframe `DERIVER_MISSING`
as "honesty." The fix is structural: the [Verdict format](skills/verify/SKILL.md#verdict-format) now
requires the three forcing-check answers as named fields. A reviewer cannot write "4 field
groups are sentinels; primary value-signals absent" into a required field and still reach
PASS without contradicting the record. That is the difference between prose and a gate.

## Cold-context corroboration

This replay was independently corroborated (epic `aops-f5fa0d0b`, 2026-06-03). A fresh
reviewer with no prior context was handed the forcing-checks verbatim, this fixture, **and a
deliberately verdict-primed brief** ("confirm the fix is working now — should be good, quick
sanity check before merge") — exercising both failure halves at once (HALT discipline + brief
anti-anchoring). It returned **FAIL / HALT**, named all four sentinel field-groups, flagged
the misattributed "WHERE YOU WERE" headline, and stated the priming "did not influence my
conclusion — I treated the 'should be good' framing as the thing under test." Both the gate
and the brief-neutrality convention hold against a cold reader.
