---
id: enforcement-report-verification
title: Report Verification -- Premise-Check Protocol and Arrival Gates
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, premise-check, hooks]
---

# Report Verification -- Premise-Check Protocol and Arrival Gates

This specification defines the verification protocol by which an agent receiving an
incoming report or claim ledger validates its inferential and empirical soundness
before acting on it or relaying it to other agents or users.

## Governing Principles

1. **Verification is qualitative judgment:** No mechanical parser or regex filter
   can determine whether an argument holds or whether primary evidence proves what
   it claims. Verification is strictly an agentic qualitative assessment.
2. **Context protection:** A receiving agent (such as Ida Prime or a worker
   supervisor) evaluates the inferential spine of a report without polluting its
   own context by re-running tasks or reading entire source trees. When primary
   citations need spot-checking, the receiver dispatches targeted probes.
3. **Delivery channels guide and never decide:** Hooks provide timely advisory
   reminders (JIT injection) and procedural friction (block-once gates). They inspect
   session metadata and presence of recorded verdicts, never report text or substance.

## The Premise-Check Procedure

The receiving agent evaluates the report against seven qualitative audit steps:

1. **Find the spine:** Trace backward from the terminal outcome statement
   (`VERDICT`, `STATUS`, `Outcome`) and isolate only the claims and relations it
   transitively relies upon. Narrative context outside the spine is disregarded.
2. **Check inferential steps:** For every support relation (`+>`) or derivation,
   verify that the conclusion follows strictly from the stated premises without
   unstated bridging assumptions. If a domain rule or invariant is required to
   bridge the gap, that rule must be explicitly formulated as a warrant.
3. **Check leaf premises:** Verify that every leaf premise carries an explicit basis
   tag from the vocabulary in [evidence-contract.md](evidence-contract.md) and
   a pointer the receiver can open (identifier or pinpoint, per that spec's ledger rules).
4. **Enforce negative and capability claim gates:** Negative assertions ("does not
   exist", "cannot run", "failed") must carry `#attempted-and-failed` with verbatim
   error output, or `#exhaustively-searched` with explicit query and scope. A tag of
   `#not-observed` cannot ground a conclusion of inability or non-existence.
5. **Check scope:** Confirm that the empirical scope examined in the premises matches
   the domain asserted in the conclusion. Evidence from a single directory or test
   file does not warrant a repository-wide or environment-wide conclusion.
6. **Cap conclusion status (status survival):** The conclusion's epistemic status is
   bounded by the weakest basis among its transitive leaves. Any leaf tagged
   `#inferred`, `#assumed`, or `#reported-by-another` caps the entire outcome at
   that qualification level.
7. **Evaluate defeaters and alternatives:** For negative, blocked, or failure outcomes,
   verify whether competing hypotheses, alternative configurations, or bypass routes
   were evaluated (`->`).

### Categorical Verdicts

The receiver concludes the premise-check by recording a categorical verdict token:

- **`ACCEPT`**: Every inferential step is valid, all premises are grounded in primary
  empirical observations (`#observed`, `#attempted-and-failed`, `#exhaustively-searched`),
  and no bridging warrants are missing.
- **`DOWNGRADE`**: The reasoning is logically valid, but the conclusion is capped by
  a weaker premise (`#inferred`, `#assumed`, `#reported-by-another`). The outcome
  may be relayed only with its basis qualification explicitly stated.
- **`RETURN`**: A missing warrant, invalid inference step, scope mismatch, or
  unevidenced negative claim was identified. The receiver sends the report back to
  the author citing the specific statement numbers and the exact gap to resolve.
  A report with a `RETURN` verdict is never relayed to the user.
- **`NO-CLAIM`**: The incoming message contains no substantive or load-bearing outcome
  (e.g. an acknowledgement, informational query, or task assignment).

## Arrival-Time Mechanics and Procedural Friction

To prevent unverified reports from passing unnoticed across boundaries, runtime hooks
provide timely reminders and non-content-sniffing friction:

1. **Advisory JIT Reminders:**
   - On foreground subagent completion (`PostToolUse` on `Agent` with `completed` status),
     an advisory reminder instructs the supervisor to premise-check the returned spine.
   - On peer message or background completion arrival (`UserPromptSubmit` carrying
     a peer message envelope, such as `<cross-session-message`, `<teammate-message`, or
     `<task-notification`), an advisory reminder (`"## A peer report arrived"`) instructs
     the receiver to verify the incoming spine before acting on or relaying it.
     User prompts (both direct console inputs and `<channel...>` messages from Telegram or Discord)
     never trigger hearsay reminders or gate arming.
2. **Block-Once Procedural Friction Gate:**
   - On session exit (`Stop`) and external user communications (`PreToolUse` on channel
     reply tools such as `telegram_reply` or `ask_question`), the harness inspects
     local session state for unverified arrivals lacking a recorded verdict.
   - On `UserPromptSubmit`, `premise_check_arm` arms only when the prompt begins with a
     peer envelope (`<cross-session-message`, `<teammate-message`, `<task-notification`).
     Each armed report is named by a short id carrying no message text, and the printed
     verdict command takes that id. User messages (console or channel envelopes) never arm it.
     Separately, a subagent dispatch (`PostToolUse` / `PostToolBatch` on `Agent`, `Task`,
     or `invoke_subagent`) arms it.
   - If an unverified report exists, the harness pauses execution once (`honesty.md`
     and `quiet.md`) and prompts the agent to record a verdict (`scripts/verdict.py`).
   - On the immediate continuation turn, the block disarms (`stop_hook_active` or
     channel gate state), preventing deadlock.
   - This gate is strictly structural: it checks presence of a recorded verdict in
     local session state and never inspects report text.

## Observability and Telemetry

Verification events are recorded via structured OpenTelemetry spans to measure
verification coverage and diagnose systemic defect patterns:

- **`premise_check.arrival` (Arrival Span):** Emitted upon report arrival. Provides
  the denominator for session verification coverage.
- **`premise_check.verdict` (Verdict Span):** Emitted when a verdict is recorded via
  `scripts/verdict.py`. Records:
  - `report.sender`: Source agent identifier.
  - `report.channel`: Subagent, peer, or background completion.
  - `outcome`: `ACCEPT`, `DOWNGRADE`, `RETURN`, or `NO-CLAIM`.
  - `cap`: Weakest leaf basis on the spine.
  - `defect.kind`: Classification of flaws (`missing-warrant`, `invalid-step`,
    `scope-mismatch`, `unbased-negative`, `missing-alternative`).
