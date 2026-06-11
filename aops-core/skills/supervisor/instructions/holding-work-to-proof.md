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

**This discipline is dispatch-surface independent.** It is identical whether your workers are
polecat containers or Agent-tool background subagents — the motivating session ran entirely on
the Agent tool, with no polecat at all. Read every "worker," "dispatch," and "brief" below as
surface-agnostic; where polecat-specific mechanics appear, they are one surface's
implementation of the generic step.

## 0. Posture: supervise, don't do

- If the brief says "don't get involved yourself," that is literal. Delegate the actual work
  (investigation, code, QA) to workers. Your context is a scarce, principal-facing resource —
  do not fill it with the work itself.
- You hold the **conclusion**, not the file dumps. Read a worker's deliverable through its
  output file (grep/Read the parts you need); do not absorb a 30k-token narrative into your
  own context just to extract a one-line verdict. For anything bulky, hand it to the cheap
  summarizer agent (defined in §6) rather than reading it inline. (This is the single biggest
  context leak — see §6.)

## 0.5 Orient before the first dispatch — mandatory checklist

Run this **before ANY first dispatch on a problem**, no exceptions. Dispatching workers before
you have the map costs full QA cycles and produces briefs that have to be killed and re-issued.
The four steps:

1. **PKB semantic search** on the problem. Find prior diagnoses, recorded harnesses, related
   tasks, and known confounds before you brief anyone.
2. **Prior-art sweep**: open _and_ merged PRs and branches (`gh pr list --state all --search
   "<terms>"`, plus the branch list). A merged fix or an in-flight branch changes the brief.
3. **Identify the recorded SANCTIONED QA harness** for the artifact and require it in the
   brief. Refuse ad-hoc substitutes — a worker that invents its own test is not exercising a
   gate you can trust. **Where it is recorded:** the harness is the artifact of this ORIENT
   step, written into the epic ledger's ORIENT output (the `## Work Items` / `## Ledger`
   sections) and populated from, in order, (i) the PKB semantic search results of step 1, (ii)
   the artifact's own task / spec body, and (iii) recorded memory notes. **Boundary behaviour —
   none exists:** if that chain yields no designated harness, do **not** let any worker invent
   one silently and do **not** proceed on an ad-hoc substitute. **HALT and emit an `[ATTN]`
   block asking Nic to designate the sanctioned harness** for this artifact. A missing harness
   is an escalation, never a gap a worker fills on its own initiative.
4. **For any cross-client / cross-vendor integration surface, FETCH THE VENDOR'S AUTHORITATIVE
   DOCS as step zero.** Reverse-engineering binaries, configs, or strace output is a _fallback
   only_, used after the docs are exhausted — never the first move.

> Grounding: the motivating bug was a deviation from a public docs page that nobody had fetched
> for days, and the supervisor dispatched two agents _before_ the PKB search that would have
> rewritten both briefs (one had to be killed). Orientation is cheap; a wrong dispatch is not.

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

### 1a. The capstone verification — what "done" means

Final acceptance for the epic is one specific check, and all of these must hold at once:

- It is the **exact previously-failing user-facing runtime check** — the same observable that
  defined the bug, not a proxy. **The supervisor supplies this**, read out of the epic ledger
  (`## Work Items` / `## Ledger`, where the original failing observable was recorded at the
  epic's first ORIENT) and stated in the capstone brief at dispatch time. The capstone agent
  does not reconstruct "what failing meant" — that is the supervisor's to hand over.
- Run on a **fresh instance / session** (no warm state that could mask the fault).
- Run by an agent who is **NOT the implementer** (no marking your own homework).
- Run with the **sanctioned harness** (§0.5 step 3), not an ad-hoc substitute.
- **Hallucination explicitly ruled out**: verify the observed output contains content that
  could only have come from the system under test — byte-match it to source — rather than
  content the agent could have echoed from its own prompt. A "pass" that the prompt could have
  produced without the system running is not a pass.

On the cohesive single-PR-epic surface this capstone is the **one cumulative `marsha` pass**
the supervisor commissions at final-stage promotion. The marsha brief must carry the three
supervisor-supplied specifics above — sanctioned harness, exact previously-failing check, and
the byte-match requirement; `marsha`'s own [[../../verify/SKILL.md]] already enforces the
fresh-instance / non-implementer / source-trace posture, so reference it rather than restating.
`marsha` then **either executes the check on a fresh instance/session itself, or commissions a
fresh-instance QA dispatch** (a non-implementer agent) and adjudicates its byte-matched
evidence. A miss is logged `capstone_fail`.

Only this capstone, satisfied in full, justifies promoting the epic's PR to ready.

## 2. The confound rule — the headline discipline

**A verdict that blames anything you don't own — "it's the platform," "upstream bug,"
"external blocker," "agy/library/OS does X" — is not believable, and you must not relay it,
until a differential control has ruled out our own code/config as the confound.**

- The control is a **clean-room isolation**: reproduce the failure with _our_ contribution
  removed (vanilla plugin-free config, minimal repro, stock setup) and a **positive control**
  in the same harness (something you know should work, to prove the harness can detect
  success). If the vanilla case works, the fault is ours, not theirs.
- **Derive the control from the AUTHORITATIVE SPEC, never by imitating the suspect artifact.**
  A control that copies the suspect's configuration replicates the suspect's bug and "confirms"
  it. In the motivating incident an adjudicator's sentinel hook copied our plugin's (broken)
  registration shape and _falsely confirmed a platform bug_; only the vanilla, docs-derived
  repro overturned it. Build the control from the vendor's docs (§0.5 step 4) — the suspect is
  what you are testing _against_, not what you copy.
- Convergent confidence is **not** the control. Convergent confidence from N agents that all
  share the same confound is worth nothing. In the incident that motivated this doctrine, two
  workers and one QA agent independently concluded "platform no-op" with strace + sentinel
  "methodology-independent" proof — and were all wrong, because every one of them tested _with
  our plugin installed_. The bug was our hooks.json registration shape. One clean-room control
  (vanilla hook fires fine) flipped the verdict instantly.
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
- **Never pre-seed skip permission.** State every assumption as a _testable hypothesis_ —
  "check whether X holds; if yes, run the check" — never as licence to skip — "you likely
  can't test X, so escalate." A stale "no-auth" assumption seeded into a brief once caused a
  worker to punt the one check that mattered, costing a full QA cycle. If you do not know
  whether a precondition holds, tell the worker to _determine it_, not to assume it away.

## 5. Report up honestly

- Every claim to the principal carries a **source and a confidence level**. "High confidence"
  is a promise that you have proofed it — spend it only after §2 and §3 are satisfied.
- **Correct your own prior conclusions out loud.** If a new control overturns what you said
  last turn, say so plainly and supersede the record (PKB note/memory) so no other agent
  inherits the stale verdict.
- **Escalate genuine frontiers; never fake-pass them.** If a check genuinely needs the
  principal's authenticated session or a human judgment, say so and hand over the exact
  one-line check — do not manufacture a green.

## 6. Protect your context — the context-economy contract

The orchestrator's context is the bottleneck — in the motivating session, supervising from an
interactive conversation, it burned ~170k tokens. The contract below is mandatory in **every**
mode, including supervisor-as-main-conversation-agent:

- **Capped structured handback, every brief.** Every worker brief must require the worker to
  **end with a capped, structured verdict**, evidence as POINTERS (session ids, file paths,
  PKB appends) and never inline narrative — and you read _that_, not the narrative:

  ```
  VERDICT: <PASS | FAIL | BLOCKED | NEEDS-PRINCIPAL>
  CLAIM: <one sentence — the conclusion>
  GATE: <the acceptance gate, and the observed result against it>
  EVIDENCE: <pointers — session id, log path, line refs — NOT pasted dumps>
  CONFIDENCE: <high|med|low> + <what single control/test would falsify this>
  CONFOUND CHECK: <did a clean-room/differential control run? result? — or "NOT RUN">
  ```

  The `CONFOUND CHECK` line is mandatory whenever the verdict blames anything we don't own. If
  it says `NOT RUN`, you do not relay the verdict — you commission the control (§2).
- **Delegate bulk reading to a cheap summarizer agent.** Large task bodies, transcripts, and
  log dumps are read by a _cheap summarizer agent_ that hands back pointers and a capped digest
  — never absorbed inline. Canonically, that agent is a **haiku/sonnet general-purpose
  Agent-tool dispatch** (or its `jr`/polecat equivalent on a surface without the Agent tool),
  whose entire brief is: _"read `<pointer>`, return the ≤N facts relevant to `<question>`."_ It
  reads the bulk so your context never has to. Keep each deliverable's full narrative in its
  output file and pull detail on demand via Read/grep against that file; never let the whole
  thing into your turn. Every other "cheap summarizer agent" mention in this doc and in SKILL.md
  refers to exactly this — do not redefine it.
- **The running ledger lives in the epic task body — always open an epic node.** Even when you
  are supervising from an interactive conversation with no pre-existing epic (the motivating
  session had none; all state lived in chat context, which is exactly how it burned 170k),
  open an epic node and keep the ledger there. Chat context is not durable state.

  **How (the minimal mechanics — do this, don't keep state in chat):** call
  `mcp__pkb__create_task` with `type=epic` (or `type=task` for a small one-off) under an
  appropriate parent, then seed the body with the three-section skeleton the ticks read and
  append to:

  ```markdown
  ## Work Items

  - [ ] <unit> — status, the sanctioned harness, and the exact previously-failing check

  ## Pattern Memory

  | Tick (ISO) | Decision | Class | Notes |
  | :--------- | :------- | :---- | :---- |

  ## Ledger

  <ORIENT output: PKB hits, prior-art PRs/branches, sanctioned harness, vendor docs>
  ```

  Capture the ORIENT findings (§0.5) into `## Ledger` and the original failing observable into
  `## Work Items` on the first tick — that is where the capstone (§1a) later reads the
  "exact previously-failing check" from. A junior in a `/goal` session must actually create
  this node, not narrate the ledger in chat.
- **Capped chat updates.** Between phases, a chat update to the principal is _one short
  paragraph_ — verdict + next action — not a transcript replay.
- Reduce avoidable churn: preload the tool schemas a supervisor predictably needs (task
  get/update, memory create, send/stop) once, and use the **exact** documented parameter
  names — repeated `ToolSearch` and parameter-error retries are pure context waste.

## One-line test before you report a conclusion

> Have I proofed this against a falsifiable gate, and — if it blames anything I don't own —
> has a clean-room control ruled out our code as the confound? If not, I am relaying a claim,
> not a finding.
