---
id: enforcement-evidence-contract
title: Enforcement — The Evidence Contract (Universal Task-Boundary Contract)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, evidence-contract]
---

# Enforcement — The Evidence Contract

This is not a fifth `Layer` in the module-boundary layer model. It is the single
contract that each of those layers instantiates at its own boundary, so no layer
has to invent its own evidence format. Where it binds is listed at the end.

## The contract

Every load-bearing claim made at a module boundary carries one of two things:

1. **Checkable evidence** — a command and its observed output, a `file:line`
   pointer, a resolving URL, or a quoted source — such that a downstream agent
   can validate the claim without reading the originating transcript. Or:
2. **A stated failure reason.**

There is no third option. A claim with neither is not load-bearing — it is
noise, and a boundary check that lets it through has failed.

**Honest failure is always a legal exit.** An agent that could not complete the
work, could not verify a claim, or ran out of budget has not violated the
contract by saying so — clearly, with the reason stated — and stopping. The
contract is violated by silence, by a claim with no evidence, or by evidence
that does not actually support the claim. It is never violated by an honest "I
could not do X, because Y."

**A partial handback is distinct from a failure exit.** Partial completion is a
first-class terminal state, not a species of failure. It satisfies option 1 for
everything that shipped, plus explicit deferral disclosure for the remainder
under the partial-work spec's AC coverage partition (`tested |
declared-deferred | illegal-gap`, defined in
[`spec-partial-work-tight-loop-delivery.md`](../polecat/spec-partial-work-tight-loop-delivery.md)).
The two-option rule is untouched: partial is option 1 for the shipped chunk,
with the deferred remainder disclosed rather than silent.

## Substance over form

The reviewer at any boundary is checking that the **actual criterion named in
the task's acceptance gate was met**, not that the prescribed rhetorical form is
present. Detecting form-only compliance — a plausible-sounding block whose
claims do not survive a spot check — is exactly what the boundary-check and
QA-around steps exist to catch, and a reviewer who confirms only that the fields
are filled in has performed neither.

- A filled-in field is necessary but not sufficient. The reviewer opens the
  `file:line` and confirms it says what the claim asserts. A citation that does
  not support the claim it is attached to is the same violation as no citation,
  and a block reciting the right field names for a check never exercised — the
  confound never isolated, the command never run, the file never opened — is a
  contract violation, not a technicality.
- **A self-graded ritual does not satisfy this contract.** A worker asserting its
  own success in the prescribed format, unread by the workflow's reviewer, is not
  a boundary check — it is the worker completing a form. The six-field shape
  exists to make a claim _cheap to verify_, never to make verification optional.

This is the operative meaning of "boundary check" and "QA-around" in
[workflow.md](workflow.md#the-five-step-shape): each is a distinct agent
independently confirming the thing claimed is actually true.

## The canonical structured-handback format

This section is the single source of truth for the six-field handback shape.
Every other surface that uses it links here rather than restating the fields.

```
VERDICT: <PASS | PARTIAL | FAIL | BLOCKED | NEEDS-PRINCIPAL>
CLAIM: <one sentence — the conclusion>
GATE: <the acceptance criterion tested, and the observed result against it>
EVIDENCE: <pointers — command+output, file:line, resolving URL, quoted source — NOT pasted dumps>
CONFIDENCE: <high|med|low> + <what single check would falsify this>
CONFOUND CHECK: <did a clean-room/differential control run? result? — or "NOT RUN">
```

- `PARTIAL` = a legal partial completion — the existing PKB terminal status
  `partial`, not a new status. The shipped chunk carries checkable evidence,
  every remaining acceptance criterion is declared-deferred with a live continue
  task, and refused judgment calls are surfaced as decisions. The discriminator
  between partial and broken-ship lives in
  [`spec-partial-work-tight-loop-delivery.md`](../polecat/spec-partial-work-tight-loop-delivery.md#the-discriminator-partial-vs-broken-ship).
- `CONFOUND CHECK` is mandatory whenever the verdict blames anything outside the
  agent's own change. `NOT RUN` means the claim is not relayed as established
  until the control runs: any agent relaying a "not our bug" claim without a
  control is relaying an unverified claim.
- **CLAIM/EVIDENCE is a set of claim+evidence-pointer pairs, not a bare
  assertion.** Where a handback asserts more than one substantive fact, itemize
  each on its own line with its own evidence pointer — one `EVIDENCE` line does
  not silently cover several unrelated claims.
- **Every itemized load-bearing claim carries its BASIS tag:**
  - `[observed]` — the agent saw the primary evidence itself this session, and cites a pinpoint pointer (`file:line`, command + output, node ID, URL).
  - `[attempted-and-failed]` — an attempted action/command/tool execution with its verbatim error output attached. (Mandatory for capability claims.)
  - `[exhaustively-searched]` — a search whose query, tool, and exact boundary are explicitly stated (e.g. `rg -i "pattern" lib/` → 0 matches).
  - `[not-observed]` — data or event not seen within the specific scope examined. Never grounds an assertion of non-existence or inability.
  - `[inferred]` — a conclusion deduced from stated premises and warrants.
  - `[assumed]` — an explicit working hypothesis or premise.
  - `[reported-by-another]` — a finding reported by another agent, subagent, or transcript, citing the source and propagating its qualification.

## The hard gate on negative and capability claims

Negative claims ("X does not exist", "X failed", "X never ran") and capability
claims ("I don't have tool X", "I cannot run Y", "no Agent tool, no shell") are
gated hardest, because they are the claims an agent is most likely to assert
from absence rather than from a test.

1. **Attempt or scope required.** Such a claim is established only by
   `[attempted-and-failed: <command/tool> → <verbatim error>]` or
   `[exhaustively-searched: <tool/query/scope> → 0 results]`. Absent one of those,
   the state is strictly `[not-observed]` — which never grounds "does not exist".
   An agent must never assert a limit on its own capabilities or environment
   without having executed the test.
2. **Status survival (anti-laundering).** Downstream consumers and controllers
   are prohibited from promoting `[inferred]`, `[assumed]`, or
   `[reported-by-another]` claims to established fact. The basis qualifier must
   survive every hop.

## Why prose, not a schema

Markdown prose, not JSON or YAML, because inter-agent contracts framework-wide
stay prose rather than becoming structured formats agents must parse exactly. A
harness may check for the format's presence as a cheap, non-authoritative hint,
but the verdict is always an agent reading the content and judging whether the
claim holds — never a regex over field names. See the governing principle in
[enforcement.md](enforcement.md#governing-principle--agents-all-the-way-down):
no mechanical enforcement of quality, ever.

## Where this binds

- **Layer 2 — `release_task`/`complete_task`** ([task-contract.md](task-contract.md)).
  The completion claim itself must satisfy this contract.
- **Layer 3 — workflow boundary-check and QA-around**
  ([workflow.md](workflow.md#the-five-step-shape)). Both steps read a handback in
  this shape and apply Substance over form.
- **Layer 4 — principal sign-off** ([sign-off.md](sign-off.md)). The one-page
  prose brief is this contract at release-unit scale.
- **Supervisor per-tick handback** ([`specs/agents/sara.md`](../agents/sara.md)) —
  the same contract applied to a background worker reporting to its supervisor
  rather than a task boundary reporting to a reviewer.

At every binding, the handback — including the output URL of the deliverable —
is written to the PKB task record, the only message bus. It is never held only in
a session transcript or a PR body. The full unified worker return contract
(evidence + output URL, one deliverable per claimed task) lives in
[task-contract.md](task-contract.md).

## How the obligation is carried

There is **no mechanical gate that judges handback _content_** — that would be a
mechanical quality verdict, which the framework forbids. Two carriers instead:

1. **Agentically** — stop-event reminders instruct a stopping agent to hand back
   with checkable evidence or a stated failure reason, and a receiver-side
   reminder tells a caller to send back a report that arrived without proof.
   Beyond the reminders, the boundary-check and QA-around reviewers judge whether
   the evidence holds. Which handlers carry this, and whether each is currently
   live, is recorded in [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md).
2. **Structurally, presence-only** — `release_task`/`complete_task` make the
   required fields mandatory and advertise them as such, through non-empty checks
   and never content inspection.

**Grandfather policy.** The presence check is forward-only: it compares a task's
existing `created` frontmatter timestamp against its own ship date, and tasks
created earlier are not retroactively held to a stricter check than existed when
they were claimed. No new frontmatter field. The agentic obligation binds
immediately and universally.
