---
name: premise-check
description: Write and review all agent-to-agent communication solely in prose Argdown blocks -- upfront ask and conclusion, every premise broken out as a separate numbered claim with its own stated source, plain-prose warrants, administrative-law review with zero de novo fact-checking, and appealable reasons. Use for every inter-agent message (briefs, handbacks, reports, reviews, clarifications, remands, and relays). Exclude standalone `.argdown` maps (`argdown-toulmin`, `argument-audit`).
---

# Premise Check

Inter-agent review is administrative-law judicial review on the face of the record:

- **Judicial review, not merits or formatting policing**: Judge whether each conclusion is capable of being supported by its stated premises under a standard of proof reasonable and appropriate in all the circumstances (subject to any standard set by the principal), alongside ask coverage, delegated authority, rule compliance, and appealable reasons. Defer to interpretation and judgment within the sender's remit that is not clearly wrong, and never remand over layout or phrasing.
- **Zero _de novo_ fact-checking**: Never open cited sources, re-read files, re-run commands, or task a third agent to verify facts or settle conflicts; remand gaps or conflicts (`REVISE`/`FAIL`) to the sender.
- **Self-contained, non-waivable floor**: Every block must carry its own supporting basis (never relying on unquoted prior briefs or opaque IDs). Unattributed smuggled claims, logical leaps, standards of proof inappropriate in the circumstances, dropped asks, _ultra vires_ overreach, or unwaived rule breaches never pass or relay upward.

## Writing Agent-to-Agent Communication

**Every agent-to-agent message** -- briefs, directions, handbacks, reports, reviews, clarifications, remands, and peer replies -- consists **exclusively** of unfenced prose Argdown blocks. Emit zero non-Argdown prose outside the argument blocks (no conversational framing, parallel summaries, trailing prose bullets, or wrapping the message in one code fence; readable scaffolding inside blocks -- such as bulleted `(n)` lines, short bold handles, or step back-references -- is fine). Direct replies to the user and published PR/issue comments or human-facing deliverables remain Markdown.

1. **Ask and conclusion first**: Lead with the full original ask (with ask/task ID) and bottom-line conclusion with earned qualifier.
2. **Break out every load-bearing premise as its own self-contained claim**:
   - Put each distinct claim that the warrant independently turns on -- observed fact, principal direction or governing rule, relayed finding, explicit assumption, or bounded open question (when paused or partial) -- in its own numbered premise with its stated basis inside the block (inline quote + locator, bounded search, principal ruling, or checked verdict ID + primary locator).
   - Never point to unquoted prior messages/IDs or smuggle an unattributed assertion via subordinate clauses, parentheticals, appositives, or omnibus relays (`"The same checked report found X and Y"`); summarizing the contents of an already-verified message (`verdict-...`) solely to identify or bound it without asserting new unverified claims is fine.
3. **Titled blocks & inline primary evidence**:
   - Group distinct questions, deliverables, or reasoning layers into titled blocks (numbering per block or continuously, whichever reads clearest).
   - Quote deciding output, exit code, count, SHA, or passage inline with locator plus version/timestamp for live state; supporting premises stay above `-- ... --`, conclusions below.
4. **Warrants, standard of proof, and exceptions**: No standard of proof is fixed in advance across situations; setting it is always the principal's choice. In `-- ... --`, state the licensing principle, why the standard of proof applied is reasonable and appropriate in all the circumstances (where unset by the principal and non-obvious), and the nearest rival/exception (whether ruled out or carried as a qualifier). Keep every noun and quantifier in `So` proportioned to what the premises and standard license, and never smuggle new facts into bars.
5. **Single complete delivery & non-report messages**: Await child subagents and send a report once when your assigned stopping point is met (never emit interim "still working" handbacks unless async tracking was requested, and never resend a duplicate report once an intervening verified message has settled the ask). Briefs, clarifications, and remands use the same compact prose Argdown block.
6. **Method and medium pairing**: Pair ask-specified methods, forms, mediums (canvas, diagram, map, code, spec), designs, or values beside what was done and note departures.
7. **Empty acknowledgements (`[no claim]`)**: Use a bare standalone `[no claim]` line (sole message content, zero accompanying prose) strictly for claim-free acknowledgements (including closing a stale remand whose ask was already delivered and verified in an intervening message).

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
2. **Phoenix traces only**: Never scrape local transcript or debug log files; query Arize Phoenix via `crew:phoenix`.
3. **Satisfiability and method bounds**: If demands exceed your stopping point (later stages, external merges) or add unverified caller method/template prescriptions outside `## Ask`, context, and objective, flag them to the supervisor in a prose Argdown block without declining, and execute your role.
4. **Disarming armed briefs & freezing deliverables**:
   - Skip `verdict.py` if unarmed; if armed, disarm first via `verdict.py --no-claim` (`--verdict REVISE --no-claim` as a clarification-hold gate token when waiting on missing inputs; `--verdict PASS --no-claim` when ready or flagging-and-executing).
   - Log verified deliverables as a frozen `## Acceptance` checklist before work (PKB task if tracked; in-turn context for subagents; none for lookups).

## Reviewing a Message (Active Critique Protocol)

Accept single, atomic premises carrying their own inline primary quote/locator or cited principal direction/rule as given, and run five checks on the face of the record:

1. **Decompose premises & raw evidence first**:
   - Unpack every premise clause by clause before reading conclusions; reject unquoted external pointers and any bundled or embedded assertion that bears independent weight in the warrant without its own stated source or checked-verdict provenance (including omnibus relays like `"The same checked report found X and Y"`).
   - Reject non-Argdown inter-agent prose, secondary summary substitution on live state, premature "still working" handbacks, and unversioned failures. Never remand over Argdown formatting, numbering style, handles, or layout unless support relations are genuinely ambiguous.
2. **Gap & Standard-of-Proof Test**: Audit embedded claims inside premises and every new noun, quantifier, population, or exclusive (`"all"`, `"only"`, `"never"`) between premises and conclusion. Apply any standard of proof set by the principal; otherwise judge whether the writer's standard of proof is reasonable and appropriate in all the circumstances and whether the conclusion is capable of being supported by the stated premises without demanding certainty where none exists. Defer to interpretation and judgment within the sender's remit that is not clearly wrong, while catching missing bridges, circular warrants, proxy-to-construct jumps, generalisations outrunning what that standard supports, observation-surface overreach, and silent medium/method swaps.
3. **Contrast Test**: Build the simplest rival world where the stated premises hold yet the conclusion fails under the applicable standard of proof (beyond the writer's exception). Reject unprompted deferrals of choices within the sender's remit (`"their call"`) and bare hand-waving (`"obvious"`, engine output as authority) where the standard of proof is not justified in the circumstances.
4. **Ask, authority, rules, and duplicates**: Verify ask coverage (including proved unreachability or explicit open-issue premises at a principal-authorized pause/checkpoint), delegated authority (no _ultra vires_), non-waivable rule compliance judged in context (no unrequested approval holds; verified recovery from reporting anomalies is compliant), and substantive relays (`verdict-...` carries each checked claim's source, qualifiers, and disclosed breaches). Never query a sender about a refused transport once a verified report answers the ask; if a duplicate/superseded message arrives, inspect its actual lines (never copy-pasting prior reasons or line numbers) and record a concise verdict noting whether it matches or narrows the earlier `verdict-<id>` with zero new claims relayed.
5. **3-way remand triage**: On defect, remand (`REVISE`/`FAIL`) in a prose Argdown block naming the minimal cure -- (a) **narrow qualifier**, (b) **break out bundled/embedded premises or supply missing bridge/warrant**, or (c) **gather missing primary evidence**.

If judging complex, contested, or multi-hop messages, read `references/critique-guide.md` before ruling for defect patterns, edge cases, and reason exemplars.

## Recording Appealable Reasons and Disarming

- **PASS**: Valid on the record, every load-bearing premise atomic and self-contained, standard of proof reasonable and appropriate in all the circumstances (or as set by the principal), rivals ruled out or qualified, ask answered within authority, rules met.
- **REVISE**: Curable defect -- name defects and minimal cure; direct sender to load `ida:premise-check`.
- **FAIL**: Incoherence, evidence contradiction, _ultra vires_, rule breach, or unanswered ask. Never relay failed claims.

Write self-contained prose reasons to a file matched to the message's actual lines (never pasted from an earlier verdict; concise on superseded duplicates) so an auditor can judge facial validity: claim/asks; per-premise sourcing and why inferences hold or fail, rivals tested, and standard-of-proof fit in the circumstances; ask, authority, and rule compliance (with cures); and relayable conclusions with qualifiers.

```bash
uv run --project <plugin-dir> python <plugin-dir>/skills/premise-check/scripts/verdict.py --session <session_id> --claim <claim_id> --verdict <PASS|REVISE|FAIL> --reason-file <path> [--no-claim] [--agent <agent_id>] [--judged-file <path>]
```

Resolve `<plugin-dir>` via `Path.resolve()`. Pass `--no-claim` with a plain reason for armed direction briefs or claim-free messages, `--session` if unset, `--agent <agent_id>` for subagent slots, and `--judged-file <path>` for out-of-band reports. Recording fails closed until OTel export succeeds.
