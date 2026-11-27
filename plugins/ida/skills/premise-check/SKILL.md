---
name: premise-check
description: Write and review all agent-to-agent communication solely in prose Argdown blocks -- upfront ask and conclusion, every premise broken out as a separate numbered claim with its own stated source, plain-prose warrants, administrative-law review with zero de novo fact-checking, and appealable reasons. Use for every inter-agent message (briefs, handbacks, reports, reviews, clarifications, remands, and relays). Exclude standalone `.argdown` maps (`argdown-toulmin`, `argument-audit`).
---

# Premise Check

Inter-agent review is administrative-law judicial review on the face of the record:

- **Formal compliance review**: Judge logical validity, per-premise source grounding, evidence-to-stakes fit, ask coverage, delegated authority, rule compliance, and appealable reasons.
- **Zero _de novo_ fact-checking**: Never open cited sources, re-read files, re-run commands, or task a third agent to verify facts or settle conflicts; remand gaps or conflicts (`REVISE`/`FAIL`) to the sender.
- **Non-waivable floor**: Material (answer-affecting) bundled or unsourced premises, logical defects, weak evidence, dropped asks, _ultra vires_ overreach, or deliverable rule breaches never pass or relay upward. Defects that cannot change the answer get `PASS` with a non-blocking note.

## Writing Agent-to-Agent Communication

**Every agent-to-agent message** -- briefs, directions, handbacks, reports, reviews, clarifications, remands, and peer replies -- consists **exclusively** of unfenced prose Argdown blocks. Emit zero non-Argdown prose (no conversational framing, parallel summaries, loose Markdown bullets, or wrapping the message in one code fence). Direct replies to the user and published PR/issue comments or human-facing deliverables remain Markdown.

1. **Ask and conclusion first**: Lead with the full original ask (with ask/task ID) and bottom-line conclusion with earned qualifier.
2. **Break out every premise as its own sourced claim**:
   - Put one atomic factual assertion, assumption, or relayed finding per numbered premise, carrying its own stated source (inline quote + locator, exact command + exit code/deciding output, bounded search, or checked verdict ID + primary locator). An agent's own first-person tool observations (`"I read..."`, `"I ran..."`, `"I checked..."`) are not exempt: each must carry a stated source/locator verifiable on the face of the record without the writer's transcript.
   - Never bundle claims or smuggle an unattributed assertion via subordinate clauses, parentheticals, appositives, or omnibus relays (`"The same checked report found X and Y"`); mark any assumed premise explicitly as its own numbered claim.
3. **Independent titled blocks & inline primary evidence**:
   - Split distinct questions, deliverables, or layers (observation -> pattern -> diagnosis -> recommendation) into titled sections restarting at `(1)`.
   - Quote deciding output, exit code, count, SHA, or passage inline with locator plus version/timestamp for live state; observations stay above `-- ... --`, evaluations below.
4. **Plain-prose warrants and exceptions**: In `-- ... --`, state the inference rule and nearest rival/exception, noting whether premises rule it out or leave a qualifier. Chain with `So`, use plain punctuation (no closed vocabularies/endnotes), and never smuggle facts into bars.
5. **Non-report messages**: Briefs, clarifications, and remands use the same compact prose Argdown block (premises citing the ask, missing input, or defect with locators; warrant stating why the route, clarification, or remand follows).
6. **Method and medium pairing**: Pair ask-specified methods, forms, mediums (canvas, diagram, map, code, spec), designs, or values beside what was done and note departures.
7. **Empty acknowledgements (`[no claim]`)**: Use a bare standalone `[no claim]` line (sole message content, zero accompanying prose) strictly for claim-free acknowledgements.

```markdown
**Original Ask (`<ask_id>`):** <Original ask in full>

**Main Conclusion:** <Bottom-line answer with earned qualifier>

### <Argument Title>

(1) <Single atomic observation quoting deciding value and locator inline>.
(2) <Second atomic observation, bounded search, or rule with its own source>.
-- <Plain-prose rule; nearest rival/exception and whether (1)-(2) rule it out or leave a qualifier.> --
(3) So, <earned qualifier>, <conclusion>.
```

If drafting complex, multi-hop, or contested messages, read `references/critique-guide.md` before writing for atomic exemplars and traps.

## Checking an Incoming Direction Brief

1. **Turn-1 inputs and derivation**: Verify `## Ask` derivation (preserving user authorization without unrequested approval holds or user-assigned choices) and required inputs, task IDs, and artifacts. If required inputs are missing, request them from the supervisor in a prose Argdown block without declining.
2. **Phoenix traces only**: Never scrape local transcript or debug log files; query Arize Phoenix via `ida:phoenix`.
3. **Satisfiability and method bounds**: If demands exceed your stopping point (later stages, external merges) or add unverified caller method/template prescriptions outside `## Ask`, context, and objective, flag them to the supervisor in a prose Argdown block without declining, and execute your role.
4. **Disarming armed briefs & freezing deliverables**:
   - Skip `verdict.py` if unarmed; if armed, disarm first via `verdict.py --no-claim` (`--verdict REVISE --no-claim` as a clarification-hold gate token when waiting on missing inputs; `--verdict PASS --no-claim` when ready or flagging-and-executing).
   - Log verified deliverables as a frozen `## Acceptance` checklist before work (PKB task if tracked; in-turn context for subagents; none for lookups).

## Reviewing a Message (Active Critique Protocol)

Accept single, atomic primary observations carrying their own inline quote and locator as given, and run five checks on the face of the record:

1. **Decompose premises & raw evidence first**:
   - Unpack every premise clause by clause before reading conclusions; treat unsourced first-person tool observations (`"I read..."`, `"I ran..."` with no locator or command/output) and any bundled premise or embedded assertion lacking its own primary source or checked-verdict provenance (including omnibus relays like `"The same checked report found X and Y"`) as unsourced.
   - Reject non-Argdown inter-agent prose, secondary summary substitution on live state, and unversioned failures.
2. **Gap Test**: Audit embedded claims inside premises and every new noun, quantifier, population, or exclusive (`"all"`, `"only"`, `"never"`) between premises and conclusion. Catch missing bridges, circular warrants, proxy-to-construct jumps, `n=1` leaps, observation-surface overreach, and silent medium/method swaps.
3. **Contrast Test**: Build the simplest rival world where quoted evidence holds yet the conclusion is false (beyond the writer's exception). Reject open user deferrals (`"their call"`) and stakes laundering (`"low-stakes"`, `"reversible"`, `"obvious"`, engine output as authority) on stakes-bearing claims.
4. **Ask, authority, and rules**: Verify ask coverage (or proved unreachability), delegated authority (no _ultra vires_), non-waivable rule compliance (no unrequested approval holds; disclosing out-of-scope breaches is compliant), and substantive relays (`verdict-...` carries each checked claim's source, qualifiers, and disclosed breaches -- never bare `"passed verdict-X"` stubs).
5. **3-way remand triage**: On a material defect that could change the answer (load-bearing premise, inference, stakes-bearing support, ask coverage, authority, or non-waivable rule breach), remand (`REVISE`/`FAIL`) in a prose Argdown block naming the minimal cure -- (a) **narrow qualifier**, (b) **break out bundled/embedded premises or supply missing bridge/warrant**, or (c) **gather missing primary evidence**. If a defect cannot change the answer (e.g., an unsourced non-load-bearing background claim about a brief or rule), do not remand: record `PASS` with a non-blocking note in the verdict reason and omit the ungrounded detail from upward relays.

If judging complex, contested, or multi-hop messages, read `references/critique-guide.md` before ruling for defect patterns, edge cases, and reason exemplars.

## Recording Appealable Reasons and Disarming

- **PASS**: Valid on the record, every load-bearing premise atomic and sourced, evidence (or verified relay) bears stakes, rivals ruled out or qualified, ask answered within authority, rules met. Any defect that cannot change the answer is recorded as a non-blocking note in the reason (and excluded from upward relays) rather than remanded.
- **REVISE**: Curable material defect (one that could change the answer or breaches a non-waivable floor) -- name defects and minimal cure; direct sender to load `ida:premise-check`.
- **FAIL**: Incoherence, evidence contradiction, _ultra vires_, rule breach, or unanswered ask. Never relay failed claims.

Write self-contained prose reasons to a file (no rigid schemas/line counts) so an auditor can judge facial validity: claim/asks; per-premise sourcing and why inferences hold or fail, rivals tested, and evidence-to-stakes fit; ask, authority, and rule compliance (with cures); and relayable conclusions with qualifiers.

```bash
uv run --project <plugin-dir> python <plugin-dir>/skills/premise-check/scripts/verdict.py --session <session_id> --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path> [--no-claim] [--agent <agent_id>] [--judged-file <path>]
```

Resolve `<plugin-dir>` via `Path.resolve()`. Pass `--no-claim` with a plain reason for armed direction briefs or claim-free messages, `--session` if unset, `--agent <agent_id>` for subagent slots, and `--judged-file <path>` for out-of-band reports. Recording fails closed until OTel export succeeds.
