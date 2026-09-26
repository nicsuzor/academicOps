# Report verification: claim-ledger reports, premise-check at arrival, and the verdict trace

Status: **proposal** for `aops_89015fc6`. Nothing here is wired yet. Revised
after independent review; the questions left for Nic are in §9.

## The failure this answers

On 2026-09-26 Ida Prime relayed a peer's halt report on `aops_22659d3d` to Nic
unchecked. The blocker was a refused `ls` on a directory. Nothing showed that
the directory was the one the workflow-library skill specifies. The halt rested
on that unstated premise, and in prose the premise read as background.

Three things were missing:

1. A report shape that makes every inferential step visible, so an unstated
   bridging premise shows up as a gap.
2. A verification procedure that walks the report's inferences.
3. A trigger that puts the procedure in front of the receiver at the moment the
   report arrives, before it can be relayed.

This spec supplies all three. It also supplies a trace, so that whether the check
happened can be measured afterwards.

## Constraints this design obeys

- **Hooks deliver and never decide**
  ([enforcement.md](enforcement.md) line 18). Every element a hook carries below
  is a reminder (JIT injection). The verdict is always an agent's judgement. No
  element blocks, and none keys on the content of a report.
- **What a hook may key on.** A hook may key on fields the client sets
  (`tool_response.status`, the transcript's `origin` object, the harness-authored
  envelope at the head of a prompt). It never keys on words the reporting agent
  wrote ("BLOCKED", "cannot"). That would be content-sniffing
  ([enforcement.md](enforcement.md) line 20).
- **Reports stay prose.** The format is a hint to the reader, never "a regex
  over field names" ([evidence-contract.md](evidence-contract.md) lines 122–130).
  The claim ledger below consists of numbered English sentences. Nothing parses it.
- **Ida's verification is a logic check** (`plugins/ida/agents/ida.md:57`). She
  never opens a primary source. When a pointer needs spot-checking, she dispatches
  the spot-check.
- **Basis vocabulary is unchanged.** The design uses the seven tags at
  `evidence-contract.md:95-103` as they stand.
- **Least-invasive rung first** ([enforcement.md](enforcement.md) lines 58–62;
  design principles 2–3 at lines 77–78). Every hook element ships as JIT
  injection. Nothing is proposed at `structural → block`. Escalation waits until
  the coverage metric in §5 shows the reminders failing.

## 1. The report format: the claim ledger

The ledger builds on Argdown's numbered premises and `(uses: …)` inference
lines. From the claim-decomposition literature (FActScore, Claimify) it takes
atomic, self-contained sentences. From ACE and SBVR it takes explicit scope. From
Catala and Toulmin it takes defeaters (UNLESS) and written warrants. Research
record: PKB `ida_research_nl_output_contracts`.

The ledger is the body of the evidence contract's `CLAIM`/`EVIDENCE` fields.
Where the six-field handback is used, the ledger replaces a single
CLAIM/EVIDENCE pair with a numbered set. It does not replace the six fields.

### Rules

1. **The outcome line names its spine.** The report's status line (VERDICT /
   STATUS / HALTED / Summary) cites the lines it rests on:
   `VERDICT: BLOCKED (from C4)`. The spine is the outcome line plus every line it
   transitively uses. Only the spine must be in ledger form. Narrative and
   non-load-bearing detail may stay prose, below the ledger.
2. **One numbered line per claim (`C1`, `C2`, …).** Each line holds one fact and
   reads correctly out of context: name the thing, do not refer back to it.
3. **Every leaf line ends with a basis tag and a pinpoint pointer,** for example
   `[observed: plugins/ida/skills/pull/SKILL.md:25]`.
4. **A derived line names the lines it uses:**
   `C4. THEREFORE (C1, C2, C3): …`. A derived line carries no basis tag of its
   own. Its strength is the weakest basis among the leaves under it. That is the
   anti-laundering rule applied line by line.
5. **Written warrants.** If a THEREFORE needs a bridging fact, that fact is its
   own numbered line with its own basis. An unstated warrant is where a hidden
   premise lives. It is the specific thing the receiver hunts for.
6. **Explicit scope.** Write "every", "no", or "at least one", and always name
   the domain: "in `plugins/ida/`", "at `5382d880`", "in session `02a8…`".
7. **Negative and capability lines** carry `[attempted-and-failed: cmd →
   verbatim error]` or `[exhaustively-searched: tool/query/scope → 0]`. Otherwise
   the line is `[not-observed]` and grounds nothing.
8. **Connectives in capitals, used only as logic.** BECAUSE, THEREFORE (Cn…),
   IF … THEN, UNLESS, AND. UNLESS names a defeater the author has not ruled out,
   and carries its own basis, usually `[not-observed]`.

**Short form.** A report whose outcome rests on one observed fact needs no
THEREFORE: `STATUS: DONE (from C1)` and one tagged line. The ledger grows with
the number of inferential steps in the spine, not with the length of the report.

### The specimen, rewritten

What the peer would realistically have written in ledger form. It did not know
it had made an assumption, so it does not write one:

```
VERDICT: BLOCKED (from C2)
C1. `ls <dir>` exited "Operation not permitted". [attempted-and-failed: `ls <dir>` → "ls: <dir>: Operation not permitted"]
C2. THEREFORE (C1): the project template tier cannot be listed in this session.
```

Rule 4 forces C2 to name what it uses, and C1 alone does not get from "one
directory refused" to "the tier cannot be listed". The gap is on the page. §2
step 2 finds it without a tool: the missing warrant is "the workflow-library
skill reads project templates from `<dir>`, and from nowhere else". The receiver
RETURNs with "C2: cite the SKILL.md line that names `<dir>` as the only
project-template location."

A writer who had noticed the premise would have written it as its own tagged
lines, which caps the outcome where it belongs:

```
VERDICT: BLOCKED (from C4)
C1. `ls <dir>` exited "Operation not permitted". [attempted-and-failed: `ls <dir>` → "ls: <dir>: Operation not permitted"]
C2. The workflow-library skill reads project templates from <dir>. [assumed]
C3. The workflow-library skill names no other project-template location. [not-observed]
C4. THEREFORE (C1, C2, C3): the project template tier cannot be listed in this session.
    UNLESS the template tier is readable by a path the session is permitted to read. [not-observed]
```

Either way the report cannot pass as a capability limit. The first has a missing
warrant. The second rests on an `[assumed]` leaf and a `[not-observed]` negative,
which grounds nothing (rule 7). In the original prose, neither C2 nor C3 was
written at all, and there was no THEREFORE to expose the jump.

## 2. How the receiver verifies a report

This replaces the "Audit Criteria" in `plugins/ida/skills/premise-check/SKILL.md`
(lines 22–29). The existing six criteria map onto the steps below (noted in
brackets). Steps 1–6 are a logic check and need no tool.

0. **Normalise.** If the report is not in ledger form, rewrite only its spine
   into ledger lines yourself: the outcome and what it rests on.
   - Keep the sender's own basis tags. Attribution to the sender is carried on
     the whole report and on every restatement of it (`ida.md:94`). It is not a
     leaf basis and does not lower the cap.
   - Mark any warrant _you_ had to supply, because the report never stated it, as
     `SUPPLIED`. A spine that needs a supplied warrant cannot be accepted
     (step 7).
   - If you cannot tell from the prose what the outcome rests on, stop and
     RETURN with "state the outcome and the lines it rests on".
1. **Find the spine.** Start from the outcome line and collect every line it
   transitively uses. Ignore the other lines.
2. **Check each step** [criteria 4, 6]. For each THEREFORE, ask: taking only the
   lines it names as true, does it follow?
   - If one more fact is needed, write that fact down as a sentence. That
     sentence is the missing warrant.
   - This step is the one that catches the specimen.
3. **Check each leaf** [criteria 1, 3].
   - It has a basis tag.
   - The pointer is specific enough that someone else could check it.
   - A negative or capability leaf carries an attempt or a bounded search.
4. **Check scope** [criterion 5]. Compare the scope the leaf actually covered
   (the directory searched, the ref, the session) with the scope the step that
   uses it needs. A search of the wrong directory is a scope mismatch, even when
   the search itself was exhaustive.
5. **Cap the conclusion** [criterion 4].
   - The outcome inherits the weakest basis among the spine's **leaves**.
     Derived lines do not lower it: a valid step from observed leaves yields an
     observed-grade conclusion.
   - A leaf the sender tagged `[inferred]`, `[assumed]`, or
     `[reported-by-another]` (the sender relaying a third party) caps the outcome
     at that level.
6. **Look for alternatives** [criterion 2].
   - For BLOCKED, FAIL, or "cannot": list the UNLESS lines the report _should_
     have had.
   - A missing obvious alternative is a finding.
7. **Decide on one token** and record it (§5):
   - **ACCEPT**: every step is valid, every leaf is adequately based, and the cap
     is `[observed]`, `[attempted-and-failed]`, or `[exhaustively-searched]`.
   - **DOWNGRADE**: every step is valid, but the cap is `[inferred]`, `[assumed]`,
     or `[reported-by-another]`. Relay the outcome only at the capped basis, and
     say so in the same sentence.
   - **RETURN**: there is a missing warrant, an invalid step, a scope mismatch, a
     negative claim without a search, or a supplied warrant.
     - Send the report back to its author, naming the line numbers.
     - Phrase each defect as the question the author must answer, for example:
       "C2: cite the SKILL.md line that names <dir>."
     - If the author has ended, dispatch the question to a new worker
       (`ida.md:70`).
     - After two RETURN rounds on the same line, stop the exchange. Record the
       task as `review` on the graph with the open question. It reaches Nic only
       if the question is one only he can answer.
   - **NO-CLAIM**: the message carries no outcome anything will act on, such as
     an acknowledgement, a question, or a RETURN list. Record it so the arrival
     is accounted for. There is nothing to check.
   - **Never repair a report by filling a gap with your own belief.** Checking a
     pointer is a separate job: dispatch it. For Ida it is never done in her own
     context (`ida.md:57`).

A RETURN never reaches Nic, hedged or otherwise (`premise-check/SKILL.md:39`). A
DOWNGRADE reaches him only with its cap stated and the sender named.

## 3. The write obligation

The write reminder must land **before** the report is written. A subagent that
hands back through `SubagentHandback` delivers its report before it stops (hooks
docs, "SubagentStop input"), so a `Stop`/`SubagentStop` reminder arrives after
the report it was meant to shape.

| Where                                                          | Change                                                                                                                                                                                                                                               |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `evidence-contract.md`                                         | Add a "Claim ledger" section containing §1 above. It is the single home of the rules, and every other surface links there.                                                                                                                           |
| `skills/dump/SKILL.md:52` ("Receipts")                         | Receipts become a claim ledger. The handover's Summary line names its spine: `Summary (from C3, C7)`.                                                                                                                                                |
| `skills/pull/SKILL.md:25`                                      | Replace the partial five-tag list with a pointer to the ledger rules. That also removes the omission of `[not-observed]` and `[reported-by-another]`.                                                                                                |
| Worker agents (`james.md`, `sara.md`, `marsha.md`, `pauli.md`) | One line: "Hand back as a claim ledger (evidence-contract § Claim ledger)."                                                                                                                                                                          |
| `SubagentStart` reminder (`honest_output`, `honesty.md`)       | Add one sentence: "Write the spine of your report as a numbered claim ledger; every THEREFORE names the lines it uses." `SubagentStart` context reaches the subagent before its first prompt. The registration is commented out (`handlers.py:497`). |
| Briefs Prime sends to twins                                    | The brief ends with the same sentence. A twin is a separate session and gets no `SubagentStart`.                                                                                                                                                     |

`honesty.md` currently reaches non-Ida sessions through the `search_the_pkb`
fallback on `UserPromptSubmit` (`handlers.py:158`). On a hand-back turn, the
receiver is therefore reminded how to _write_ a report at the moment it should
be _reading_ one (transcript `02a8997d`, entries 111–114). A2 replaces that
injection on report-arrival turns.

The write obligation is advisory at every rung (`instructions` →
`JIT injection`). A badly formed report is not blocked at the sender. It is caught
at the receiver, which is the only place the judgement can be made.

## 4. The read obligation: where the reminder attaches

There is no "message received" event. Reports arrive through these channels:

| #  | Channel                                                                                    | What fires in the receiver                                                                                                                                                                                                                                                                                               | Basis                                                                                                                                                                                                                                                                                                                 |
| -- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1 | Foreground subagent that returns its report as text                                        | `PostToolUse` on `Agent` with `tool_response.status == "completed"` and the report in `tool_response.content`. It can return `additionalContext`.                                                                                                                                                                        | [observed: hooks docs, PostToolUse "Agent" `tool_response` table, and hooks.md:2428]. A minority case: subagents run in the background by default since v2.1.198, so `PostToolUse` fires at launch with `status: "async_launched"`; and a `SubagentHandback` subagent's `content` is only a note about the hand-back. |
| R2 | Hand-back, background completion, or peer/twin message arriving while the receiver is idle | A new turn starts and `UserPromptSubmit` fires. The prompt opens with the harness envelope "Another Claude session sent a message: `<agent-message from=…>`". The transcript entry carries `origin: {kind: "peer", from, senderTaskId, body}` and `promptSource: "system"`. A human turn carries `origin.kind: "human"`. | [observed: transcript `02a8997d`, entries 111 and 191, each followed by a `UserPromptSubmit` injection (113–114, 194)]. Both senders there were subagents handing back; a twin-to-twin message is the same case by inference. Probe P1.                                                                               |
| R3 | Background completion arriving **mid-turn**                                                | The `<task-notification>` is queued as a `queued_command` attachment, and `UserPromptSubmit` fires for it mid-turn.                                                                                                                                                                                                      | [observed: transcript `02a8997d`, entries 132–134 and 170–171]. Undocumented. Whether a cross-session peer message arriving mid-turn behaves the same way is unestablished. Probe P2.                                                                                                                                 |
| R4 | Report read from the graph (`/gather`, `/reconcile`, `/pull` reading a task body)          | No hook. This is instruction text in the reading skill.                                                                                                                                                                                                                                                                  | [inferred]                                                                                                                                                                                                                                                                                                            |

**One report, two arrivals.** A background subagent that hands back produces a
peer message _and_ a later task-notification (transcript `02a8997d`: entries 111
and 132 both name sender `a640bfcadd21af5a6`). Reminders and the coverage count
de-duplicate on the sender id (`origin.from`, `senderTaskId`, `<task-id>`).

### Attachments

- **A1: R1 reminder.** On `PostToolUse(Agent)` in Ida's and James's sessions,
  when `tool_response.status == "completed"`, inject one line: "A report just
  arrived. Run premise-check on its spine before acting on it or relaying it."
  - This is `rule_against_hearsay` (`handlers.py:339-346`), which is currently
    unregistered (`handlers.py:496`). Re-registering it needs three fixes:
    - Move it from `PostToolBatch` to `PostToolUse` with the status condition.
      As written it fires when a background agent is launched.
    - Change `aops:james` to `ida:james`.
    - Rewrite `hearsay.md`. Its "verify claims against primary sources"
      contradicts `ida.md:57`.
- **A2: R2/R3 reminder.** On `UserPromptSubmit`, inject the same line, naming the
  sender, when the arrival is a report from another agent.
  - Key, in order of preference:
    1. The harness envelope at the head of the payload's `prompt`. It is in the
       payload, so it cannot lag.
    2. The transcript entries written since the previous `UserPromptSubmit`: a
       user entry with `origin.kind == "peer"`, or a `queued_command` attachment
       carrying a `<task-notification>`. Scan back through them. Do not read only
       the last entry: on a mid-turn fire, the last entry is the attachment.
  - Both keys are client-set structure, not the reporter's words. Neither is
    documented, and the transcript "may lag the in-memory conversation"
    (hooks.md:754). A hand-back body is indented line by line, so a column-zero
    envelope inside a report would be a forgery (the frame text in
    `origin.body` says so).
  - If neither key can be read, the hook logs and injects a one-line notice that
    it could not classify the turn. It does not skip silently.
  - `origin.kind == "human"`: no reminder. Nic's statements are not reports to
    premise-check (`ida.md:92`). Whether a channel (Telegram) message arrives as
    `human` is unestablished. Probe P5.
  - If both keys prove unstable, there is no hook fallback. An every-turn
    reminder costs every turn and trains the reader to skip it. Fall back to
    instructions and measure with §5.
- **A3: Stop reminder, for forgetting.** On `Stop` in the receiving session, if
  the local state (§5) shows a de-duplicated arrival with no verdict after it,
  return `additionalContext`, not `decision: "block"`: "Reports from <from…>
  have no recorded premise-check verdict. Record one for each, or NO-CLAIM,
  before finishing."
  - Stop `additionalContext` already keeps the conversation going, under the same
    `stop_hook_active` guard and 8-continuation cap as a block (hooks docs, "Stop
    decision control"). A block adds only a hook-error label. The rung is
    therefore `JIT injection`, not `structural → block`, and `dispatch.py`
    already renders a `warn()` on `Stop` in this shape.
  - It cannot prevent a relay. Prime's reply to Nic is written before `Stop`
    fires, so A3 only prompts a correction after the fact. A1 and A2 are the
    only elements that land before a relay.
  - It keys on counts (arrivals against verdicts), never on report text. Whether
    even that counts as a "mechanical verdict on process" is open (§9).
- **A4: R4 instructions.**
  - `/gather` step 2 ("Check each one on the papers") becomes: run §2 on the
    task body's report, and record the verdict. ACCEPT or DOWNGRADE may be
    `needs-nic`. RETURN is `insufficient`, with the RETURN questions as "what is
    missing".
  - `/reconcile` never writes `done` on non-PR evidence
    (`reconcile/SKILL.md:21`, `gather/SKILL.md:76`). Its read obligation
    therefore attaches where it acts on a report rather than on an observation:
    a demotion (obligation 4) or cancellation (obligation 5) whose trigger is
    evidence a worker wrote into the body. Before acting, the body must carry a
    `## Verdict` section with ACCEPT. Otherwise run premise-check, or route the
    task to `review`. The merged-PR path is unchanged, since a merged PR is an
    observation.

### Between Ida twins

Twins are separate Claude Code sessions on the cross-session bus
(`ida.md:29`). They are not subagents.

- **Sender.** The twin finishes with `/dump`. That writes the ledger to the PKB
  task body, which is the durable record (`evidence-contract.md:145-147`). The
  twin then calls `SendMessage` to Prime with the **full ledger** as the message
  body.
  - Sending only a pointer would make the receiver fetch, and a fetch is a tool
    call that no hook distinguishes. It would also put a read in Prime's own
    context.
  - The message-size limit is from the cross-session messaging docs, which this
    review did not have. [not-observed]
- **Receiver.** If Prime is idle, A2 fires. If she is busy, P2 decides whether A2
  fires mid-turn. A3 reminds at Stop either way. She verifies, records the
  verdict, and appends `## Verdict` to the task body.
- **Closing the loop.** On RETURN, Prime sends the numbered questions back to the
  twin with `SendMessage`. The twin records the RETURN list as NO-CLAIM and
  answers in ledger form, citing the same line numbers. The answer is a new
  arrival and gets the same reminder. The two-round limit in §2 step 7 ends a
  ping-pong.
- **Twins verifying each other.** A twin receiving a brief or report from Prime
  gets the same reminder, because A2 keys on the envelope and `origin`, not on
  which Ida is which. A brief that makes no claim the twin will act on is
  NO-CLAIM.

### agy

- agy's only pre-turn injection point is `PreInvocation`, which is mapped to
  `UserPromptSubmit` (`dispatch.py`, `TO_CANONICAL`).
- agy has no blocking shape (`dispatch.py`, `_render_agy`;
  `tests/policy.toml`, `allow_blocking_agy = false`). Every element here is
  advisory, so agy loses nothing. agy's `Stop` is mapped, so A3 can fire there.
- Whether an agy twin receives peer messages at all, and in what form, is
  unestablished. [not-observed; Probe P3]

## 5. The verdict trace (OTel)

The existing `plugins/ida/hooks/premise_check_verdict.py` emits one `TOOL` span
carrying six hardcoded question texts and a free-text verdict. It cannot be
aggregated by outcome or by defect. The replacement records a structured
verdict. `skills/premise-check/scripts/verdict.py` emits it through ida's own
`claude_code_tracer`, parented to the current turn's trace as today
(`premise_check_verdict.py:74-79`). The agent records it, not a hook.

- **Verdict span:** `premise_check.verdict`, OpenInference span kind
  `EVALUATOR`. Every attribute sits under `premise_check.`, so that no name is
  both a value and a namespace:
  - `report.id`: the PKB task id, or the message's `senderTaskId`.
  - `report.sender`: `origin.from`, or the subagent id.
  - `report.channel`: `subagent | handback | peer | notification | graph`.
  - `report.format`: `ledger | prose`. Prose means step 0 ran.
  - `report.spine`: for example `"C4<-C1,C2,C3"`.
  - `outcome`: `ACCEPT | DOWNGRADE | RETURN | NO-CLAIM`.
  - `cap`: the weakest leaf basis on the spine.
  - `round`: the RETURN round, starting at 1.
  - `defect.{n}.line`: for example `C2`.
  - `defect.{n}.kind`: one of `missing-warrant | invalid-step | scope-mismatch | unbased-negative | untagged | supplied-warrant | missing-alternative | no-spine`.
  - `defect.{n}.question`: the question sent back to the author.
- **Arrival span:** A1 and A2 each emit `premise_check.arrival` (`report.sender`,
  `report.channel`, and `report.id` where known) when they fire. This is
  observability, not a verdict. It is the denominator every metric below needs:
  without it, arrivals are not in Phoenix at all.
- **No cross-session span link.** rbg's `record_send_message`
  (`evaluator_otel_trace.py:370-422`) computes a traceparent and stores it only
  as an attribute on its own span. `dispatch.py:399` discards the return value,
  and nothing puts the traceparent into the message. The span also goes to rbg's
  OTLP JSON file sink (`COPE_EVALUATOR_OTEL_TRACE_PATH`), not to the sink ida's
  tracer uses. The receiver therefore has no traceparent to link to. Sender and
  receiver are joined post-hoc on `report.sender` and `report.id`, which both
  sides already know. Nothing needs to move to `lib/telemetry/` for this design.
- **Local state:** `verdict.py` appends `{sender, report_id, outcome, ts}` to
  the session state file, and A1/A2 append `{sender, report_id, ts}` arrivals to
  the same file. Both key it on `$AOPS_SESSION_ID`, which holds the root
  session's id in the root and in every subagent
  (`claude_code_tracer.py:448-455`), so a verdict a subagent records counts for
  the root. A3 reads that file. The hook never reads Phoenix.

### What the trace makes measurable

These run post-hoc, in Phoenix, as the `post-hoc → observability` rung.

- **Coverage:** de-duplicated `premise_check.arrival` spans per session against
  `premise_check.verdict` spans recorded before the session's next `Stop`. The
  unverified-relay rate is the metric the specimen is about. It is also the
  evidence that would justify escalating any element beyond JIT injection.
- **Defect mix:** counts of `defect.kind` per sender agent type. These show which
  workers write which gaps, and so which writer instructions to fix.
- **Format uptake:** the share of `report.format = ledger` per sender, showing
  whether the write obligation is landing.
- **Verdict quality:** Nic, or a later reconcile, annotates a verdict as right or
  wrong when the ground truth lands. Annotated verdicts become an eval dataset for
  premise-check itself.

## 6. Probes owed before wiring

| Probe | Question                                                                                                                                                                           | Method                                                                                                                                                                                           |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P1    | Does a twin-to-twin `SendMessage` arriving while idle fire `UserPromptSubmit`? Does the payload's `prompt` carry the envelope? Is the `origin` entry written before the hook runs? | Two local sessions. Send from one. Capture the other's hook payload (`aops-debug` `dump_payload`) and the transcript tail as read from inside the hook.                                          |
| P2    | Does a cross-session peer message arriving **mid-turn** queue like a task-notification and fire `UserPromptSubmit`?                                                                | Send a message to a session that is running a long tool call, and capture payloads as in P1.                                                                                                     |
| P3    | agy: does a peer message reach an agy session, and does `PreInvocation` fire for it?                                                                                               | Same as P1, with an agy receiver.                                                                                                                                                                |
| P4    | Delivery and compliance of A1/A2.                                                                                                                                                  | Model-echo control: ask the model to quote the injected line, then byte-match it. Separately, measure compliance with the coverage metric.                                                       |
| P5    | What `origin.kind` does a channel (Telegram) message from Nic carry?                                                                                                               | Send one, then read the transcript entry.                                                                                                                                                        |
| P6    | Is the ledger light enough to write, and does it expose gaps to a reader?                                                                                                          | Dogfood. Rewrite five real hand-backs, including the specimen, in ledger form. Give each one blind to a fresh premise-check run. Record the words added and the defects found against the prose. |

## 7. Enforcement map rows to add

Rows go in [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md), using the
four-column schema of [enforcement.md](enforcement.md) lines 38–45.
`.agents/rules/RULES.md` lines 15–17 require `enforcement.md` to be updated in
the same PR as the wiring.

| Rule / nudge                                     | Mechanism     | Severity      | Detail                                                                      |
| ------------------------------------------------ | ------------- | ------------- | --------------------------------------------------------------------------- |
| Write the report spine as a claim ledger         | instructions  | imperative    | evidence-contract § Claim ledger; dump, pull, worker agents, twin briefs    |
| Write the report spine as a claim ledger         | JIT injection | n/a           | `SubagentStart` `honest_output`                                             |
| Verify a report at arrival                       | JIT injection | n/a           | A1 `PostToolUse(Agent)` on `completed`; A2 `UserPromptSubmit` on an arrival |
| Do not finish with an unverified report          | JIT injection | n/a           | A3 `Stop` `additionalContext`                                               |
| No action on a worker's report without a verdict | process       | required gate | `/gather` step 2; `/reconcile` obligations 4–5                              |
| Unverified-relay rate                            | post-hoc      | observability | arrival against verdict span coverage query                                 |

## 8. Code this replaces or retires

- `plugins/ida/hooks/premise_check_gate.py`: delete it.
  - It `refuse`s Ida's next `Agent` call while armed (lines 196–215). A REFUSE is
    reserved for structural impossibility and "is never a rule verdict"
    (`dispatch.py:48-51`).
  - It is not registered (`handlers.py:489-498`), so deleting it changes no live
    behaviour. A1–A3 cover the obligation.
  - Nic's note at its line 4 asks for a verdict before contacting the user
    (channel reply tools, `AskUserQuestion`). See §9.
- `plugins/ida/hooks/premise_check_verdict.py`: replace it with the §5 span. It
  imports `disarm` from the gate (line 20), so both go together.
- `plugins/ida/skills/premise-check/scripts/verdict.py`: keep it as the entry
  point. Its comments name `plugins/orchestrate/hooks/` and
  `dist/orchestrate-*/hooks/` (lines 12–13), which do not exist. It also
  searches `lib/hooks` (line 26), which does not exist. Fix both when it is
  rewritten.

## 9. Open for Nic

- **Is A3 legal?** It conditions a reminder on a mechanical count of arrivals
  without a recorded verdict. That is a presence-only check of the kind
  evidence-contract.md lines 163–165 permits. It is also a hook deciding whether
  a process step happened, which enforcement.md line 18 excludes. This proposal
  ships it as advisory only. Dropping it loses the only reminder for arrivals
  the hooks cannot see (P2).
- **Gating contact with Nic.** A reminder on `PreToolUse` of a channel reply
  tool or `AskUserQuestion` lands with the tool result, after the message has
  been sent (hooks docs, PreToolUse `additionalContext`). Only a REFUSE would
  land before it, and `dispatch.py:48-51` forbids REFUSE for anything but
  structural impossibility. Holding a relay until it is verified therefore rests
  on instructions and on A1/A2, unless the doctrine changes.
- **Rollout order.** Proposed order:
  1. P6 runs first.
  2. The ledger section in evidence-contract, and the §2 procedure in
     premise-check (instructions only).
  3. The §5 verdict and arrival spans, so a baseline exists.
  4. A1 and A2, after P1 and P2.
  5. A3, once the baseline shows whether it is needed.
