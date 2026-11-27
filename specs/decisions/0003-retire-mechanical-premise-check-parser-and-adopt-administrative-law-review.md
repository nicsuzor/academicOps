---
status: "accepted"
date: 2026-11-20
amended: 2026-11-27
decision-makers: ["user"]
---

# Retire Mechanical Premise-Check Parser and Adopt Administrative-Law Review

## Context and Problem Statement

The premise-check system previously paired a recipient-scoped hearsay gate and OpenTelemetry verdict recorder with a deterministic programmatic parser that validated a restricted Argdown subset, a closed basis vocabulary, a rigid seven-keyed-line checker reason schema, absent-block gating, and pre-handback block checks.

Empirical audits across recent evaluation windows showed that programmatic syntax parsing achieved a 0% substantive logical-defect catch rate across 87+ mechanical refusals and 21 confirmed true positives, while driving 21--27% call-level refusal churn, coercing 13/15 clear false positives and 36% (9/25) of multi-hop revision chains into zero-substance syntax churn, and inducing judged-file tampering. By contrast, conceptual argumentation structure (explicit defeaters, inline quoted provenance, and ask-coverage mapping) exposed 57% (8/14) of argumentation true positives, and independent qualitative review drove 71% of confirmed true positives overall with 1/25 substantive multi-hop false positives.

Beyond poor empirical performance, deterministic parsing of inter-agent prose and checker reasons directly violated `human-readability-first`, `judgment-non-delegable`, and `no-over-engineering`. How should the framework preserve the high-value epistemic rigor and gate friction of premise-check while eliminating mechanical syntax bureaucracy and _de novo_ factual re-checking by evaluators?

## Considered Options

- Retain and tune the programmatic Argdown and seven-line reason parser
- Drop structured argumentation and premise checking entirely
- Retire the mechanical parser, preserve hearsay gate friction and fail-closed tracing, and adopt human-readable Argdown-only prose under administrative-law formal compliance review

## Decision Outcome

Chosen option: "Retire the mechanical parser, preserve hearsay gate friction and fail-closed tracing, and adopt human-readable Argdown-only prose under administrative-law formal compliance review", because it eliminates zero-yield syntax churn and axiom breaches while retaining the two mechanisms empirically responsible for catching real reasoning defects: structured Toulmin argumentation and independent qualitative review enforced by recipient-scoped gate friction.

Core architectural principles adopted:

1. **Administrative-law formal compliance review (zero _de novo_ fact-checking):** Checking agents act as reviewing tribunals judging strictly on the face of the record -- testing logical validity, sufficiency of inline quoted primary evidence for the stakes, plausible rival explanations, full coverage of the original ask, delegated authority bounds (no _ultra vires_ overreach), and non-waivable rule compliance. Checkers never open cited sources, re-read files or records, re-run commands, or commission third-agent fact-checking (removing the prior conflict-settling source-read carve-out); missing, weak, or conflicting evidence on the record is remanded via `REVISE` or `FAIL` to the originating agent.
2. **Human-readable Argdown-only reporting for non-user-facing agents:** All non-user-facing agent reports and internal handbacks are written solely as clean, human-readable Argdown prose matching the depth of an academic argument critique -- leading with the original ask and bottom-line conclusion across independent titled blocks restarting at `(1)`, quoting deciding evidence and provenance inline, and stating warrants and exceptions in plain prose without parallel summary prose, closed basis vocabularies, or parser escape workarounds. Formal `.argdown` grammar and `@argdown/cli` validation remain scoped strictly to standalone `.argdown` maps and audits (`argdown-toulmin`).
3. **Deeper critique guidance and appealable natural-language reasons:** Evaluators draw on a dedicated critique guide for complex, contested, or multi-hop reports and record self-contained, appealable natural-language reasons on the record (replacing the retired seven-keyed-line schema) so higher auditors can judge facial validity and authority on the record.
4. **Minimal procedural gate and fail-closed tracing:** The hearsay gate retains recipient-scoped `(session_id, agent_id)` arming and action holding across dispatch, messaging, channel replies, and stop (with strict whole-message null-claim auto-disarm for standalone `[no claim]` notices), and the verdict recorder retains token validation (`PASS`, `REVISE`, `FAIL`), non-empty reason presence, explicit `--no-claim` marking without prose scraping, slot/owner and already-disarmed guards, optional `--judged-file` content integrity, verification ID minting, and fail-closed OpenTelemetry span emission, while retiring all Argdown/reason syntax parsing, absent-block gating, and pre-handback block checks.

### Consequences

- Good, because mechanical refusal churn, zero-substance syntax loops, and judged-file tampering pressure are eliminated while aligning enforcement with `human-readability-first`, `judgment-non-delegable`, and `no-over-engineering`.
- Good, because retiring ~1,600 lines of parser code and dedicated parser test suites removes a permanent maintenance liability without weakening gate isolation or OTel auditability.
- Good, because inter-agent prose becomes directly readable by humans and higher auditors, and strict zero-_de-novo_ review stops coordinators from drifting into redundant source inspection.
- Bad, because mechanical span telemetry attributes previously derived by parsing seven-line reasons (`defect_tag_count`, `weakest_basis_term`, `waived_items`, `inference_count`) are retired; longitudinal quality audits now inspect verdict distributions, remand rates, and recorded natural-language reasons directly.
- Bad, because substantive rigor relies on agentic compliance with `premise-check` instructions and independent review rather than deterministic syntax checks, requiring ongoing telemetry monitoring for rubber-stamping.

## Amendment (2026-11-27): thread reports arm the gate

Observed traces showed that a Claude projects coordinator receives a thread session's report as a `UserPromptSubmit` harness wake (`<wake reason="thread-activity">` wrapping the thread's `<message from="agent">`), not as any tool call or result, so a coordinator-side `PostToolUse` rule never sees it, a thread-side `PostToolUse` fires only after the report is already posted, and a thread-side `PreToolUse` hold would leave the thread judging its own report. The gate's arming envelopes therefore extend to that wake: each triggering agent message in a thread-activity wake arms the coordinator's slot exactly as a subagent hand-back does, and human, system and quiet wakes arm nothing. This widens what counts as an incoming peer report under principle 4; it changes no other part of this decision.

- Good, because thread reports now face the same recipient-side check as subagent hand-backs before the coordinator relays them, at the one point every report demonstrably passes through.
- Bad, because detection depends on the projects harness keeping its wake markup (`reason="thread-activity"`, `from="agent"`, `trigger="true"`); a change there silently disarms it until the matcher follows.
