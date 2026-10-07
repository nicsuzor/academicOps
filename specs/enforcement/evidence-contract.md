---
id: enforcement-evidence-contract
title: Enforcement -- The Evidence Contract (Universal Task-Boundary Contract)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, evidence-contract]
---

# Enforcement -- The Evidence Contract

This is not a fifth Layer in the module-boundary layer model. It is the single
contract that each layer instantiates at its own boundary, so no layer
has to invent its own evidence format.

## The Contract

Every load-bearing claim made at a module or task boundary carries one of two things:

1. **Checkable evidence** -- a command and its observed output, a `file:line`
   pointer, a resolving URL, or a quoted source -- such that a downstream agent
   can validate the claim without reading originating transcripts. Or:
2. **A stated failure reason.**

There is no third option. A claim with neither is not load-bearing -- it is
noise, and a boundary check that lets it through has failed.

**Honest failure is always a legal exit.** An agent that could not complete the
work, could not verify a claim, or ran out of budget has not violated the
contract by saying so -- clearly, with the reason stated -- and stopping. The
contract is violated by silence, by a claim with no evidence, or by evidence
that does not actually support the claim. It is never violated by an honest "I
could not do X, because Y."

**A partial handback is distinct from a failure exit.** Partial completion is a
first-class terminal state (`partial`), not a species of failure. It satisfies
option 1 for everything that shipped, plus explicit deferral disclosure for the
remainder under the partial-work coverage partition (`tested | declared-deferred | illegal-gap`,
defined in [`spec-partial-work-tight-loop-delivery.md`](../polecat/spec-partial-work-tight-loop-delivery.md)).
The two-option rule is untouched: partial is option 1 for the shipped chunk,
with the deferred remainder disclosed rather than silent.

## Substance Over Form

The reviewer at any boundary checks that the **actual criterion named in the
task's acceptance gate was met**, not that the prescribed rhetorical form is
present. Detecting form-only compliance -- a plausible-sounding block whose
claims do not survive a spot check -- is exactly what boundary-check and
QA-around steps exist to catch. A reviewer who confirms only that fields
are filled in has performed neither.

- A filled-in field is necessary but not sufficient. The reviewer opens the
  `file:line` and confirms it says what the claim asserts. A citation that does
  not support the claim it is attached to is the same violation as no citation.
  A block reciting the right field names for a check never exercised -- the
  confound never isolated, the command never run, the file never opened -- is a
  contract violation, not a technicality.
- **A self-graded ritual does not satisfy this contract.** A worker asserting its
  own success in the prescribed format, unread by the workflow's reviewer, is not
  a boundary check -- it is the worker completing a form. The structured handback
  shape exists to make a claim _cheap to verify_, never to make verification optional.

This is the operative meaning of "boundary check" and "QA-around" in
[workflow.md](workflow.md#the-five-step-shape): each is a distinct agent
independently confirming the thing claimed is actually true.

## The Canonical Structured-Handback Format

This section is the design source for the handback shape and claim ledger. The
operative ledger format agents follow is the
[`claim-ledger` skill](../../plugins/ida/skills/claim-ledger/SKILL.md). Agents
load it when they write a report; the per-message honesty reminder names it.

A task handback couples the boundary verdict and epistemic safeguards with a
plain-prose answer and a native Argdown claim ledger in the receipts section:

```markdown
VERDICT: <PASS | PARTIAL | FAIL | BLOCKED | NEEDS-PRINCIPAL>
GATE: <the acceptance criterion tested, and observed result against it>
CONFIDENCE: <high | med | low> + <what single check would falsify this>
CONFOUND CHECK: <did a clean-room/differential control run? result? -- or "NOT RUN">

<One to three sentences of plain prose: the answer.>

RECEIPTS:

<the claim ledger, per the claim-ledger skill>
```

- `PARTIAL` = a legal partial completion -- the existing terminal status `partial`.
  The shipped chunk carries checkable evidence, every remaining acceptance criterion
  is declared-deferred with a live continue task, and refused judgment calls are
  surfaced as decisions.
- `CONFOUND CHECK` is mandatory whenever the verdict blames anything outside the
  agent's own change. `NOT RUN` means the claim is not relayed as established
  until the control runs: any agent relaying a "not our bug" claim without a
  control is relaying an unverified claim.

### Ledger rules

The ledger combines two strengths seen in workers' reports on 2026-10-06. Antigravity
ledgers made the logic easy to follow: outcome first, numbered premises, and a
derivation line naming the premises and warrant. Claude Code receipts made the
evidence easy to check: span ids, verbatim errors, and searches bounded by query
and scope. Each was weak where the other was strong. Antigravity cited its own
transcript steps and drew conclusions wider than its premises. Claude Code gave
no outcome line and no derivation. The skill's rules take each side's strength.

Design choices behind the skill:

- **Delivery.** The full format lives in a skill, loaded when a report is written.
  The honesty reminder injected on every incoming message stays a few lines long and
  names the skill, because repeating the full format on every turn costs context
  without adding information.
- **Pointers are identifiers.** The user's ruling: citation by identifier is
  preferred, and a pinpoint is best. A command that merely fetches something with
  an identifier is not a pointer. A command counts only when its output is the
  evidence, and then the output is quoted.
- **Parsing is approximate.** `@argdown/cli` rejects any unescaped underscore, even
  inside backticks. Escaping would break copy-paste of the pointer, so pointers stay
  verbatim, and a parse failure caused only by an underscore in a pointer is
  acceptable. Titles, tags, relations, and the named derivation line should parse.
- **No horizontal rules.** The derivation is the named line `-- from … by … --`.
  A bare `----` reads as a horizontal rule and says less, so it is not used.
  Reports use no `---` separators either.
- **Fences.** An inner fence as long as its outer fence closes the outer one early,
  and the formatter then swallows the following prose into a code block.
  `tests/test_markdown_fences.py` fails on such a collision. The formatter also
  trims leading spaces inside inline code, so indented Argdown goes only in fenced
  blocks.

### Worked example

From the 2026-10-06 comparison of worker reports:

```argdown
[Outcome]: The 2026-10-06 morning Claude Code workers were never asked for a claim ledger, so their reports cannot show whether the model can write one.

<Unequal prompts>: Why the comparison does not isolate the model.

(1) [Claude prompt]: The honesty text Claude Code workers received asks for "verifiable extracts" and never mentions a ledger. #observed `nicsuzor/academicOps@5324e68:plugins/ida/hooks/messages/honesty.md:5-10`
(2) [Seen in traces]: That text appears in the recorded prompts of Claude Code sessions 7b76832d, 6cbf8525 and ce707f7a. #exhaustively-searched `Phoenix spans since 2026-10-06T19:00Z, attributes LIKE '%Verifiable extracts%'` → 3 Claude Code sessions
(3) [Agy prompt]: Antigravity session bccf078e received "Itemize receipts as a claim ledger" from its second turn. #observed `nicsuzor/academicOps@e49f1a0:plugins/ida/hooks/messages/honesty.md:3`
(4) [Rule]: Two runs compare models only when both received the same instruction. #warrant
-- from (1), (2) and (3) by (4) --
(5) [Outcome]

[Unrecorded prompts]: Phoenix does not record the injected prompt for the other Claude Code sessions that morning, so their instruction is not observed. #not-observed
  -> [Outcome]
```

## Epistemic Basis Vocabulary

Every itemized load-bearing claim carries its basis tag:

- `#observed` -- the agent saw the primary evidence itself this session, and cites a pointer to it.
- `#attempted-and-failed` -- an attempted action, command, or tool call, with its verbatim error output attached. (Mandatory for capability claims.)
- `#exhaustively-searched` -- a search whose tool, query, exact boundary, and result count are stated (e.g. `rg -i "pattern" lib/` → 0 matches).
- `#not-observed` -- data or event not seen within the specific scope examined. Never grounds an assertion of non-existence or inability.
- `#inferred` -- a conclusion deduced from stated premises and warrants.
- `#assumed` -- an explicit working hypothesis or premise.
- `#reported-by-another` -- a finding reported by another agent, subagent, or transcript, citing the source and propagating its qualification.
- `#warrant` -- a rule or invariant that bridges premises to a conclusion. The reader judges whether it holds.

## The Hard Gate on Negative and Capability Claims

Negative claims ("X does not exist", "X failed", "X never ran") and capability
claims ("I don't have tool X", "I cannot run Y", "no Agent tool, no shell") are
gated hardest, because they are the claims an agent is most likely to assert
from absence rather than from a test.

1. **Attempt or scope required.** Such a claim is established only by
   `#attempted-and-failed` with the command and its verbatim error, or
   `#exhaustively-searched` with the tool, query, scope, and zero count. Absent one
   of those, the state is strictly `#not-observed`, which never grounds "does not exist".
   An agent must never assert a limit on its own capabilities or environment
   without having executed the test.
2. **Status survival (anti-laundering).** Downstream consumers and controllers
   are prohibited from promoting `#inferred`, `#assumed`, or
   `#reported-by-another` claims to established fact. The basis qualifier must
   survive every hop. A derived claim's strength is strictly bounded by the
   weakest basis among its transitive premises.

## Syntax, Tooling, and Qualitative Assessment

Inter-agent contracts use simple, native Argdown as a structured prose notation:

1. **Authoring discipline:** Argdown forces the drafting agent to decompose
   arguments into atomic propositions, provide explicit basis tags and pointers,
   and make inferential dependencies visible rather than burying unstated assumptions
   in rhetorical narrative.
2. **Structural check vs qualitative verdict:** Mechanical parsers (such as `@argdown/cli`)
   or presence checks may verify syntactic well-formedness (valid statement syntax,
   parseable relations, presence of required sections). However, **syntax validation
   is never a quality verdict.**
3. **Assessment remains qualitative and agentic:** No mechanical parser can judge
   whether an empirical pointer proves what it claims, whether a warrant holds, or
   whether a confound check was sound. That assessment belongs strictly to
   reviewing agents reading the text and verifying primary sources.

This boundary upholds the governing principle of [enforcement.md](enforcement.md):
mechanical tooling handles structural presentation and presence; quality judgment
is non-delegable to mechanical parsers.

## Where This Binds

- **Layer 2 -- `release_task`/`complete_task`** ([task-contract.md](task-contract.md)).
  The completion claim itself must satisfy this contract.
- **Layer 3 -- workflow boundary-check and QA-around**
  ([workflow.md](workflow.md#the-five-step-shape)). Both steps read a handback in
  this shape and apply Substance over form.
- **Layer 4 -- principal sign-off** ([sign-off.md](sign-off.md)). The one-page
  prose brief is this contract at release-unit scale.
- **Supervisor per-tick handback** ([`specs/agents/sara.md`](../agents/sara.md)) --
  the same contract applied to a background worker reporting to its supervisor
  rather than a task boundary reporting to a reviewer.

At every binding, the handback -- including the output URL of the deliverable --
is written to the shared task record, the durable message bus. It is never held
only in an ephemeral session transcript or a PR body.

## How the Obligation is Carried

There is **no mechanical gate that judges handback content** -- that would be a
mechanical quality verdict, which the framework forbids. Two carriers instead:

1. **Agentically** -- stop-event reminders instruct a stopping agent to hand back
   with checkable evidence or a stated failure reason, and a receiver-side
   reminder tells a caller to send back a report that arrived without proof.
   Beyond the reminders, the boundary-check and QA-around reviewers judge whether
   the evidence holds.
2. **Structurally, presence-only** -- `release_task`/`complete_task` make the
   required fields mandatory and advertise them as such, through non-empty checks
   and never content inspection.

**Grandfather policy.** The presence check is forward-only: it compares a task's
existing `created` timestamp against its ship date, and tasks created earlier
are not retroactively held to a stricter check than existed when they were
claimed. The agentic obligation binds immediately and universally.
