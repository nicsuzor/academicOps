---
name: premise-check
description: Write and review inter-agent reports in clean Argdown prose -- upfront ask and conclusion, inline quoted evidence, plain-prose warrants, administrative-law review with zero de novo fact-checking, and appealable reasons. Use for handbacks, briefs, and relays. Exclude standalone `.argdown` maps (`argdown-toulmin`, `argument-audit`).
---

# Premise Check

Inter-agent review is administrative-law judicial review on the face of the record:

- **Formal compliance review**: Judge logical validity, evidence-to-stakes fit, ask coverage, delegated authority, rule compliance, and appealable reasons.
- **Zero _de novo_ fact-checking**: Never open cited sources, re-read files, re-run commands, or task a third agent to verify facts or settle conflicts; remand gaps or conflicts (`REVISE`/`FAIL`) to the sender.
- **Non-waivable floor**: Logical defects, weak evidence, dropped asks, _ultra vires_ overreach, or deliverable rule breaches never pass or relay upward.

## Writing a Report (Non-User-Facing Agents)

Report **only** in clean Argdown prose -- never bolt a block onto a parallel summary or wrap the report in one code fence.

1. **Ask and conclusion first**: Lead with the full original ask (with ask/task ID) and bottom-line conclusion with earned qualifier.
2. **Independent titled blocks**: Split distinct questions, deliverables, or layers (observation -> pattern -> diagnosis -> recommendation) into titled sections restarting at `(1)`, one atomic claim per premise.
3. **Inline primary evidence**: Quote deciding output, exit code, count, SHA, or passage inline with locator (`<path>:<line>`, command/exit, PR URL, bounded search) plus version/timestamp for live state. Observations above the bar; evaluations below.
4. **Plain-prose warrants and exceptions**: In `-- ... --`, state the inference rule and nearest rival/exception, noting whether premises rule it out or leave a qualifier. Chain with `So`, use plain punctuation (no closed vocabularies/endnotes), and never smuggle facts into bars.
5. **Method and medium pairing**: Pair ask-specified methods, forms, mediums (canvas, diagram, map, code, spec), designs, or values beside what was done and note departures.
6. **Claim-free notices (`[no claim]`)**: Standalone `[no claim]` (bare or fenced `argdown`, no extra prose) auto-disarms; prose notices arm the gate and clear via `verdict.py --no-claim`.

```markdown
**Original Ask (`<ask_id>`):** <Original ask in full>

**Main Conclusion:** <Bottom-line answer with earned qualifier>

### <Argument Title>

(1) <Atomic observation quoting deciding value and locator inline>.
(2) <Second observation, bounded search, or rule with source>.
-- <Plain-prose rule; nearest rival/exception and whether (1)-(2) rule it out or leave a qualifier.> --
(3) So, <earned qualifier>, <conclusion>.
```

If drafting complex or contested reports, read `references/critique-guide.md` before writing for multi-layer exemplars and traps.

## Checking an Incoming Direction Brief

1. **Turn-1 inputs and derivation**: Verify `## Ask` derivation (preserving user authorization without unrequested approval holds or user-assigned choices) and required inputs, task IDs, and artifacts. On missing inputs, ask the supervisor via direct message without declining (skip `verdict.py` if unarmed; if armed, disarm first via `verdict.py --verdict REVISE --no-claim` -- a gate-disarm token for a clarification hold, not a task refusal).
2. **Phoenix traces only**: Never scrape local transcript or debug log files; query Arize Phoenix via `ida:phoenix`.
3. **Satisfiability and method bounds**: If demands exceed your stopping point (later stages, external merges) or add unverified caller method/template prescriptions outside `## Ask`, context, and objective, flag them to the supervisor as a clarification via direct message without declining, and execute your role (disarming first via `verdict.py --verdict PASS --no-claim` if armed).
4. **Disarm ready briefs and freeze deliverables**: When an armed brief is ready to execute, disarm via `verdict.py --verdict PASS --no-claim` first (skip `verdict.py` if unarmed), then log verified deliverables as a frozen `## Acceptance` checklist before work (PKB task if tracked; in-turn context for subagents; none for lookups).

## Reviewing a Report (Active Critique Protocol)

Accept quoted primary observations with locators as given and run five checks on the face of the record:

1. **Raw evidence first**: Read quoted values, locators, version/commit currency, and bounded searches before conclusions. Reject secondary summary substitution on live state (task status, note, peer prose) and unversioned failures.
2. **Gap Test**: Audit every new noun, quantifier, population, or exclusive ("all", "only", "never") between premises and conclusion. Catch missing bridges, circular warrants, proxy-to-construct jumps, `n=1` leaps, observation-surface overreach, and silent medium/method swaps.
3. **Contrast Test**: Build the simplest rival world where quoted evidence holds yet the conclusion is false (beyond the writer's exception). Reject open user deferrals ("their call") and stakes laundering ("low-stakes", "reversible", "obvious", engine output as authority) on stakes-bearing claims.
4. **Ask, authority, and rules**: Verify ask coverage (or proved unreachability), delegated authority (no _ultra vires_), non-waivable rule compliance (no unrequested user approval holds outside invariant boundaries; disclosing out-of-scope breaches is compliant), and substantive relays (`verdict-...` carries reasoning, qualifiers, and disclosed breaches -- never bare `"passed verdict-X"` stubs).
5. **3-way remand triage**: On defect, remand (`REVISE`/`FAIL`) naming the minimal cure -- (a) **narrow qualifier**, (b) **supply missing bridge/warrant**, or (c) **gather missing primary evidence**.

If judging complex, contested, or multi-hop reports, read `references/critique-guide.md` before ruling for defect patterns, edge cases, and reason exemplars.

## Recording Appealable Reasons and Disarming

- **PASS**: Valid on the record, evidence (or verified relay) bears stakes, rivals ruled out or qualified, ask answered within authority, rules met.
- **REVISE**: Curable defect -- name defects and minimal cure; direct sender to load `ida:premise-check`.
- **FAIL**: Incoherence, evidence contradiction, _ultra vires_, rule breach, or unanswered ask. Never relay failed claims.

Write self-contained prose reasons to a file (no rigid schemas/line counts) so an auditor can judge facial validity: claim/asks; why inferences hold or fail, rivals tested, and evidence-to-stakes fit; ask, authority, and rule compliance (with cures); and relayable conclusions with qualifiers.

```bash
uv run --project <plugin-dir> python <plugin-dir>/skills/premise-check/scripts/verdict.py --session <session_id> --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path> [--no-claim] [--agent <agent_id>] [--judged-file <path>]
```

Resolve `<plugin-dir>` via `Path.resolve()`. Pass `--no-claim` with a plain reason for claim-free notices or armed direction briefs, `--session` if unset, `--agent <agent_id>` for subagent slots, and `--judged-file <path>` for out-of-band reports. Recording fails closed until OTel export succeeds.
