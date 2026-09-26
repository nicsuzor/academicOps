# Report verification: claim-ledger reports, premise-check at arrival, and the verdict trace

Status: **proposal** for `aops_89015fc6`. Nothing here is wired yet.

## The failure this answers

On 2026-09-26 Ida Prime relayed a peer's halt report on `aops_22659d3d` to Nic
unchecked. The blocker was a refused `ls` on a directory. Nothing showed that
the directory was the one the workflow-library skill specifies. The halt rested
on that unstated premise, and in prose the premise read as background.

Three things were missing:

1. A report shape that forces the bridging premise onto its own line.
2. A verification procedure that walks the report's inferences.
3. A trigger that puts the procedure in front of the receiver at the moment the
   report arrives.

This spec supplies all three. It also supplies a trace, so that whether the check
happened can be measured afterwards.

## Constraints this design obeys

- **Hooks deliver and never decide**
  ([enforcement.md](enforcement.md) line 18). The verdict is always an agent's
  judgement. A hook may only (a) remind or (b) block on a _checkable session fact_.
  "A peer report arrived this turn and no verdict was recorded after it" is such a
  fact. "The report is wrong" is not.
- **Reports stay prose.** The format is a hint to the reader, never "a regex
  over field names" ([evidence-contract.md](evidence-contract.md) lines 122–130).
  The claim ledger below consists of numbered English sentences. Nothing parses it.
- **Ida's verification is a logic check** (`plugins/ida/agents/ida.md:57`). She
  never opens a primary source. When a pointer needs spot-checking, she dispatches
  the spot-check.
- **Basis vocabulary is unchanged.** The design uses the seven tags at
  `evidence-contract.md:95-103` as they stand.

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

1. **One numbered line per claim (`C1`, `C2`, …).** Each line holds exactly one
   fact. It uses no pronouns and no "this" or "it", so it reads correctly out of
   context. It has one reading.
2. **Every line ends with a basis tag and a pinpoint pointer,** for example
   `[observed: plugins/ida/skills/pull/SKILL.md:25]`.
3. **A derived line names the lines it uses:**
   `C4. THEREFORE (C1, C2, C3): …  [inferred]`. A derived line is never stronger
   than the weakest line it uses. That is the anti-laundering rule applied line by
   line.
4. **Written warrants.** If a THEREFORE needs a bridging fact, that fact is its
   own numbered line with its own basis. An unstated warrant is where a hidden
   premise lives. It is the specific thing the receiver hunts for.
5. **Explicit scope.** Write "every", "no", or "at least one", and always name
   the domain: "in `plugins/ida/`", "at `5382d880`", "in session `02a8…`".
6. **Negative and capability lines** carry `[attempted-and-failed: cmd →
   verbatim error]` or `[exhaustively-searched: tool/query/scope → 0]`. Otherwise
   the line is `[not-observed]` and grounds nothing.
7. **Connectives in capitals, used only as logic.** BECAUSE, THEREFORE (Cn…),
   IF … THEN, UNLESS, AND. UNLESS names a defeater the author has not ruled out,
   and carries its own basis, usually `[not-observed]`.
8. **The outcome line names its spine.** The report's status line (VERDICT /
   STATUS / HALTED) cites the lines it rests on: `VERDICT: BLOCKED (from C4)`.
   The receiver needs to check only the spine, meaning the outcome line and the
   lines it transitively uses.

### The specimen, rewritten

```
VERDICT: BLOCKED (from C4)
C1. `ls <dir>` exited "Operation not permitted". [attempted-and-failed: `ls <dir>` → "ls: <dir>: Operation not permitted"]
C2. The workflow-library skill reads project templates from <dir>. [assumed]
C3. The workflow-library skill names no other project-template location. [not-observed]
C4. THEREFORE (C1, C2, C3): the project template tier cannot be listed in this session. [inferred]
    UNLESS the template tier is readable by a path the session is permitted to read. [not-observed]
```

Written this way, the defect shows on the page before anyone checks anything:

- The spine rests on an `[assumed]` line (C2) and a `[not-observed]` negative (C3).
- A `[not-observed]` line grounds nothing (rule 6), so C4 cannot be relayed as a
  capability limit.

In the original prose, C2 and C3 were not written at all.

## 2. How the receiver verifies a report

This replaces the "Audit Criteria" in `plugins/ida/skills/premise-check/SKILL.md`.
The existing six criteria map onto the steps below (noted in brackets). Steps 1–6
are a logic check and need no tool.

0. **Normalise.** If the report is not in ledger form, rewrite its load-bearing
   claims into ledger lines yourself.
   - Tag every line `[reported-by-another: <sender>]` plus the sender's own tag.
   - Mark any warrant _you_ had to supply, because the report never stated it, as
     `SUPPLIED`.
   - A spine that needs a supplied warrant cannot be accepted (step 6).
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
   - The outcome inherits the weakest basis on the spine.
   - An `[assumed]` or `[reported-by-another]` leaf caps it at that level.
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
     - If the author has ended, dispatch the question to a new worker.
   - **Never repair a report by filling a gap with your own belief.** Checking a
     pointer is a separate job: dispatch it. For Ida it is never done in her own
     context (`ida.md:57`).

A RETURN never reaches Nic, hedged or otherwise (`premise-check/SKILL.md:39`). A
DOWNGRADE reaches him only with its cap stated.

## 3. The write obligation

| Where                                                                                              | Change                                                                                                                                                                                   |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `skills/dump/SKILL.md:52` ("Receipts")                                                             | Receipts become a claim ledger. The handover's Summary line names its spine: `Summary (from C3, C7)`.                                                                                    |
| `skills/pull/SKILL.md:25`                                                                          | Replace the partial five-tag list with a pointer to the ledger rules. That also removes the omission of `[not-observed]` and `[reported-by-another]`.                                    |
| Worker agents (`james.md`, `sara.md`, `marsha.md`, twin handbacks)                                 | One line: "Hand back as a claim ledger (evidence-contract § claim ledger)."                                                                                                              |
| Stop / SubagentStop reminder (`honesty.md`, the evidence contract's "stop-event reminder" carrier) | Add one sentence: "Write load-bearing claims as a numbered ledger; every THEREFORE names the lines it uses." It stays advisory. It is guarded once per stop chain on `stop_hook_active`. |
| `evidence-contract.md`                                                                             | Add a "Claim ledger" section containing §1 above. It is the single home of the rules, and every other surface links there.                                                               |

The write obligation is advisory at every rung (`instructions` →
`JIT injection`). A badly formed report is not blocked at the sender. It is caught
at the receiver, which is the only place the judgement can be made.

## 4. The read obligation: where the reminder attaches

There is no "message received" event. Reports arrive through four channels, and
each needs its own attachment point:

| #  | Channel                                                                                        | What fires in the receiver                                                                                                                                                                                     | Basis                                                                                                                                                                                                                  |
| -- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1 | Synchronous subagent return                                                                    | `PostToolUse` matched on `Agent`, with the report in `tool_response`. It can return `additionalContext`.                                                                                                       | [observed: docs hooks.md:2428 "To inject context into the parent session after a subagent returns, use a PostToolUse hook on the Agent tool"]                                                                          |
| R2 | Hand-back, background completion, or peer/twin message arriving while the receiver is **idle** | A new turn starts and `UserPromptSubmit` fires. The transcript entry for that turn carries `origin: {kind: "peer", from, handback}` and `promptSource: "system"`. A human turn carries `origin.kind: "human"`. | [observed: this session's transcript, 2 hand-back turns, `origin.kind=peer`; `UserPromptSubmit` injected context on both]. **A real twin-to-twin cross-session message is the same case only by inference. Probe P1.** |
| R3 | Peer message arriving **mid-turn** (between tool calls)                                        | No documented hook.                                                                                                                                                                                            | [not-observed: docs cross-session-messaging.md, "Message delivery"; hooks.md event list]                                                                                                                               |
| R4 | Report read from the graph (`/reconcile`, `/gather`, `/pull` reading a task body)              | No hook. This is instruction text in the reading skill.                                                                                                                                                        | [inferred]                                                                                                                                                                                                             |

### Attachments

- **A1: R1 reminder.** On `PostToolUse(Agent)` in Ida's and James's sessions,
  inject one line: "A report just arrived. Run premise-check on its spine before
  acting on it."
  - The rung is JIT injection.
  - This is the only channel where the reminder lands exactly when the report
    does.
- **A2: R2 reminder.** On `UserPromptSubmit`, read the last entry of
  `transcript_path`. If `origin.kind == "peer"`, inject the same line and name
  `origin.from`.
  - This keys on a structural field set by the client. It is not content
    sniffing.
  - Caveat: the transcript schema is **undocumented**, and the docs warn that the
    transcript "may lag" (hooks.md:754).
  - If the field is absent, the hook fails loudly (it logs and injects a notice).
    It does not silently skip.
  - Fallback if the field proves unstable: inject the line on every
    non-first `UserPromptSubmit` in Ida sessions. Per-turn events get one line.
- **A3: the Stop backstop, covering R2, R3, and forgetting.** On `Stop` in the
  receiving session:
  - Count the peer-origin transcript entries (and `Agent` tool results) since the
    last recorded verdict for each sender.
  - If any report has no verdict after it, return `decision: "block"` once
    (`stop_hook_active` guard) with the reason: "Reports from <from…> have no
    premise-check verdict. Run premise-check on each before finishing."
  - This is the one blocking element. It is legal under the doctrine, because the
    question is a checkable session fact ("did the check happen?"), not a reading
    of the work.
  - Its rung is `structural → block`. `RULES.md:15-17` requires
    `enforcement.md` to be updated in the same PR.
  - The verdict record it looks for is the `premise_check.verdict` span's local
    state file (§5). The hook never reads Phoenix.
- **A4: R4 instructions.**
  - `/reconcile` gains an obligation: "Before writing `done` on non-PR evidence,
    the task body must carry a `## Verdict` section with ACCEPT. Otherwise run
    premise-check or route the task to `review`."
    - The merged-PR path is unchanged, since a merged PR is an observation, not a
      report.
  - `/gather` gains: "A report without a recorded verdict is `insufficient`."

### Between Ida twins

Twins are separate Claude Code sessions on the cross-session bus
(`ida.md:29`). They are not subagents.

- **Sender.** The twin finishes with `/dump`. That writes the ledger to the PKB
  task body, which is the durable record (`evidence-contract.md:146`). The twin
  then calls `SendMessage` to Prime with the **full ledger** as the message body.
  - A plain-text body can be up to about a million characters (docs, cross-session
    Limitations).
  - Sending only a pointer would make the receiver fetch, and a fetch is a tool
    call that no hook distinguishes.
- **Receiver.** If Prime is idle, A2 fires. If she is busy, the message arrives
  mid-turn and A3 catches it at Stop. She verifies, records the verdict, and
  appends `## Verdict` to the task body.
- **Closing the loop.** On RETURN, Prime sends the numbered questions back to the
  twin with `SendMessage`. The twin answers in ledger form, citing the same line
  numbers. A1–A3 apply to the reply as well.
- **Twins verifying each other.** A twin receiving a brief or report from Prime
  is covered by the same rules. The mechanism is symmetric because it keys on
  `origin.kind`, not on which Ida is which.

### agy

- agy's only pre-turn injection point is `PreInvocation`, which is mapped to
  `UserPromptSubmit`.
- agy has no blocking shape, so A3 downgrades to advisory there.
- Whether an agy twin receives peer messages at all, and in what form, is
  unestablished. [not-observed; Probe P3]

## 5. The verdict trace (OTel)

The existing `plugins/ida/hooks/premise_check_verdict.py` records six hardcoded
questions and a free-text verdict, which is neither queryable nor linkable. The
replacement is a single span, emitted by `scripts/verdict.py`. The agent records
it, not a hook.

- **Span:** `premise_check.verdict`, OpenInference span kind `EVALUATOR`.
- **Attributes:**
  - `report.id`: the PKB task id, or the message's `senderTaskId`.
  - `report.sender`: `origin.from`, or the subagent id.
  - `report.channel`: `subagent | handback | peer | graph`.
  - `report.format`: `ledger | prose`. Prose means step 0 ran.
  - `report.spine`: for example `"C4<-C1,C2,C3"`.
  - `verdict`: `ACCEPT | DOWNGRADE | RETURN`.
  - `verdict.cap`: the weakest basis on the spine.
  - `verdict.defect.{n}.line`: for example `C2`.
  - `verdict.defect.{n}.kind`: one of `missing-warrant | invalid-step | scope-mismatch | unbased-negative | untagged | supplied-warrant | missing-alternative`.
  - `verdict.defect.{n}.question`: the question sent back to the author.
- **Link:** a span link to the sender's `agent.send_message` span, where a
  traceparent is available. rbg's `evaluator_otel_trace.py` already emits
  `agent.send_message` with traceparent propagation (lines 370–421). Ida cannot
  import it (line 368). It moves to `lib/telemetry/` so that both plugins get it
  at build time, as the no-duplication rule requires.
- **Local state:** `verdict.py` also appends `{sender, report_id, verdict, ts}`
  to the session state file. That file is the fact A3 checks.

### What the trace makes measurable

These run post-hoc, in Phoenix, as the `post-hoc → observability` rung.

- **Coverage:** the number of peer-origin arrivals per session against the number
  of `premise_check.verdict` spans. The unverified-relay rate is the metric Nic's
  question is actually about.
- **Defect mix:** counts of `defect.kind` per sender agent type. These show which
  workers write which gaps, and so which writer instructions to fix.
- **Verdict quality:** Nic, or a later reconcile, annotates a verdict as right or
  wrong when the ground truth lands. Annotated verdicts become an eval dataset for
  premise-check itself.

## 6. Probes owed before wiring

| Probe | Question                                                                                                                           | Method                                                                                                                                                                |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1    | Does a real twin-to-twin `SendMessage` arriving while idle fire `UserPromptSubmit` with `origin.kind == "peer"` in the transcript? | Two local sessions. Send from one, capture the other's hook payload (`aops-debug` `dump_payload`) and its transcript tail.                                            |
| P2    | At `Stop`, are mid-turn peer messages already in the transcript? (The docs say the transcript may lag.)                            | Send a message to a session that is running a long tool call, then read the transcript from a Stop hook.                                                              |
| P3    | agy: does a peer message reach an agy session, and does `PreInvocation` fire for it?                                               | Same as P1, with an agy receiver.                                                                                                                                     |
| P4    | Delivery and compliance of A1/A2                                                                                                   | Model-echo control (hook-enforcement-surface): ask the model to quote the injected line, then byte-match it. Separately, measure compliance with the coverage metric. |

## 7. Enforcement map rows to add

| Obligation                          | Rung                                     | Mechanism                                                            |
| ----------------------------------- | ---------------------------------------- | -------------------------------------------------------------------- |
| Write reports as a claim ledger     | instructions → JIT injection             | dump/pull/agent text; one Stop/SubagentStop line                     |
| Verify a report at arrival          | JIT injection                            | A1 `PostToolUse(Agent)`; A2 `UserPromptSubmit` on `origin.kind=peer` |
| No finish with an unverified report | structural → block (once per stop chain) | A3 `Stop`                                                            |
| No `done` on an unverified report   | process → required gate (agentic)        | `/reconcile` text                                                    |
| Unverified-relay rate               | post-hoc → observability                 | `premise_check.verdict` span coverage query                          |

## 8. Code this replaces or retires

- `plugins/ida/hooks/premise_check_gate.py`: retire it.
  - It `refuse`s Ida's next `Agent` call (lines 195–215), which is a rule verdict
    delivered through `REFUSE`. `dispatch.py:46-51` forbids that.
  - A3 covers the same obligation at the only legal blocking point.
- `plugins/ida/hooks/premise_check_verdict.py`: replace it with the §5 span.
  - `scripts/verdict.py` resolves `plugins/ida/hooks/` correctly, but its
    comment names a path that does not exist, `plugins/orchestrate/hooks/`
    (line 12). It also searches `lib/hooks` (line 26), which does not exist.
