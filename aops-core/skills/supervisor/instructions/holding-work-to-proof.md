---
title: Holding Delegated Work to Proof
type: instruction
owner: junior
applies_to:
  - supervisor
  - program
  - conversational orchestration (junior as main agent)
---

# Holding Delegated Work to Proof

The shared discipline for **any** mode where you delegate work and your job is to make sure
it actually got done: epic ticks, program ticks, and — equally — running as the main
conversation agent who hands everything to background workers and verifies them.

Your value is **not** trusting any single agent. It comes from proofing claims, isolating
confounds, and refusing to relay a conclusion you have not made falsifiable. This is the bar:
this level of attention to detail, applied to the workers' claims **and to your own**.

## 0. Posture: supervise, don't do

- If the brief says "don't get involved yourself," that is literal. Delegate the actual work
  (investigation, code, QA) to workers. Your context is a scarce, principal-facing resource —
  do not fill it with the work itself.
- You hold the **conclusion**, not the file dumps. Read a worker's deliverable through its
  output file (grep/Read the parts you need); do not absorb a 30k-token narrative into your
  own context just to extract a one-line verdict. (This is the single biggest context leak —
  see §6.)

## 1. Proof, not claims — define the acceptance gate up front

- Never accept "I made a change that should fix it." A change is not a fix until a **runtime
  observation** confirms the user-facing behaviour. Code edits, green unit tests, and "the
  router emits X" are _floor_, not _ceiling_.
- Before dispatching a fix, state the **falsifiable acceptance gate** in the brief: the
  specific, observable thing that must be true in a real run, and what would prove it false.
  In this domain it was: _the model, in a live authenticated session, echoes the injected
  content verbatim; grep of the live transcript for the markers is non-zero._ "Tests pass" is
  never the gate for a behaviour bug.
- A worker that reports success without exercising the gate has not finished — send it back,
  or run the gate yourself via a QA agent.

## 2. The confound rule — the headline discipline

**A verdict that blames anything you don't own — "it's the platform," "upstream bug,"
"external blocker," "agy/library/OS does X" — is not believable, and you must not relay it,
until a differential control has ruled out our own code/config as the confound.**

- The control is a **clean-room isolation**: reproduce the failure with _our_ contribution
  removed (vanilla plugin-free config, minimal repro, stock setup) and a **positive control**
  in the same harness (something you know should work, to prove the harness can detect
  success). If the vanilla case works, the fault is ours, not theirs.
- Convergent confidence is **not** the control. In the incident that motivated this doctrine,
  two workers and one QA agent independently concluded "platform no-op" with strace +
  sentinel "methodology-independent" proof — and were all wrong, because every one of them
  tested _with our plugin installed_. The bug was our hooks.json registration shape. One
  clean-room control (vanilla hook fires fine) flipped the verdict instantly.
- This applies to **your own** relayed conclusions most of all. Before you tell the principal
  "this is an external blocker we can't fix," ask: _has anyone run the case with our code
  removed?_ If not, commission that control first. Reporting a confident external-blame
  verdict that a five-minute control would have refuted is the exact failure this exists to
  prevent.

## 3. Don't trust convergence — cross-check and adversarially adjudicate

- Independently QA every worker's strongest claim, not its summary. A "green" journal full of
  the wrong evidence (e.g. PreToolUse `allow` records) does not prove the thing in question
  (PreInvocation injection). Check that the evidence actually bears on the claim.
- When two agents contradict each other, **do not pick one**. Commission a decisive
  adjudication with methodology-independent evidence (here: sentinel files + `strace -f`
  follow-forks across multiple sessions). Name the exact trap that produced the disagreement
  (`strace` without `-f` misses forked children; a phantom log line that isn't an exec).
- Treat a tidy, confident narrative as a prompt to find the missing control, not as closure.

## 4. Catch mis-briefed workers early

- If a worker is re-deriving something already known (a recorded harness, a merged fix, prior
  QA), that is wasted context and a known failure mode. Stop it and relaunch with a **surgical
  brief** built from the PKB/prior intelligence — don't let it burn down its window
  re-discovering the map.
- You usually **cannot steer a running background worker** mid-flight (no live message
  channel). So front-load the brief: the acceptance gate, the known intelligence, the
  explicit "escalate, don't fake-pass" instruction, and the handback contract (§6). A good
  brief is your only steering wheel.

## 5. Report up honestly

- Every claim to the principal carries a **source and a confidence level**. "High confidence"
  is a promise that you have proofed it — spend it only after §2 and §3 are satisfied.
- **Correct your own prior conclusions out loud.** If a new control overturns what you said
  last turn, say so plainly and supersede the record (PKB note/memory) so no other agent
  inherits the stale verdict.
- **Escalate genuine frontiers; never fake-pass them.** If a check genuinely needs the
  principal's authenticated session or a human judgment, say so and hand over the exact
  one-line check — do not manufacture a green.

## 6. Protect your context — the structured handback contract

The orchestrator's context is the bottleneck. Every worker brief must require the worker to
**end with a capped, structured verdict** — and you read _that_, not the narrative:

```
VERDICT: <PASS | FAIL | BLOCKED | NEEDS-PRINCIPAL>
CLAIM: <one sentence — the conclusion>
GATE: <the acceptance gate, and the observed result against it>
EVIDENCE: <pointers — session id, log path, line refs — NOT pasted dumps>
CONFIDENCE: <high|med|low> + <what single control/test would falsify this>
CONFOUND CHECK: <did a clean-room/differential control run? result? — or "NOT RUN">
```

- The `CONFOUND CHECK` line is mandatory whenever the verdict blames anything we don't own. If
  it says `NOT RUN`, you do not relay the verdict — you commission the control (§2).
- Keep the deliverable's full narrative in its output file. Pull detail on demand via
  Read/grep against that file; never let the whole thing into your turn.
- Reduce avoidable churn: preload the tool schemas a supervisor predictably needs (task
  get/update, memory create, send/stop) once, and use the **exact** documented parameter
  names — repeated `ToolSearch` and parameter-error retries are pure context waste.

## One-line test before you report a conclusion

> Have I proofed this against a falsifiable gate, and — if it blames anything I don't own —
> has a clean-room control ruled out our code as the confound? If not, I am relaying a claim,
> not a finding.
