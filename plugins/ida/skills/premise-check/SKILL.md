---
name: premise-check
description: Write and review inter-agent messages solely in unfenced prose Argdown blocks -- upfront ask, load-bearing premises proportionately sourced, administrative-law judicial review on the message alone (zero substantive checking outside it), effort and reasons scaled to stakes, material remands only. Exclude standalone `.argdown` maps (`argdown-toulmin`, `argument-audit`).
---

# Premise Check

Inter-agent review is administrative-law judicial review on the message alone:

- **Closed record -- zero substantive checking**: The record is the message under review and nothing outside it.
  - Take facially grounded premises as given; never rely on, consult, or test against anything outside the message (in-context state, prior turns, harness telemetry, tool logs, external sources, or other agents) to verify truth, execution, or values, and never escalate receipt precision as an anti-fabrication proxy at any stakes.
  - Separately check ask coverage against the originating ask and facial contradictions on the text (within the message, or unexplained material contradictions across the same sender's own revisions on an unchanged claim in an active remand); without a material facial defect, `PASS` (deliverable QA and `/learn` sit outside `premise-check`).
- **Proportionality, materiality, and severability**: Effort, evidentiary detail, and verdict reasons scale to stakes (do less on low-stakes, read-only, or cheaply redone work). Remand (`REVISE`/`FAIL`) only if curing a defect could change what is relayed or done next, or breaches non-waivable authority or standing rules; immaterial slips pass with a brief note omitted from relays. Sever clean independent parts rather than failing a whole message.
- **Judicial deference**: Judge whether conclusions are capable of being supported under any principal-set standard, or one reasonable and appropriate in all the circumstances. Defer to judgment within remit that is not clearly wrong; never remand over unambiguous layout or phrasing.

## Writing Agent-to-Agent Communication

**Every inter-agent message** consists **exclusively** of unfenced prose Argdown blocks, with zero prose outside blocks (internal scaffolding passes). Replies to the user and PR/issue outputs stay Markdown.

1. **Ask and conclusion first**: Lead with the full original ask (ask/task ID) and bottom-line conclusion with earned qualifier.
2. **Load-bearing premises with inline basis**:
   - Put each independent load-bearing claim -- observed fact, first-person tool claim (`"I read..."`, `"I ran..."`), rule/direction, relayed finding, assumption, or open question -- in its own numbered premise with inline basis (locator/output proportionate to stakes, bounded search, ruling, or `verdict-...` ID + primary locator), never pointing to unquoted prior briefs or opaque IDs.
   - Never smuggle claims via clauses, parentheticals, appositives, or omnibus relays (`"The same checked report found X and Y"`); identifying a verified `verdict-...` without new claims passes.
3. **Blocks & proportionate evidence**: Group distinct questions into titled blocks. Quote deciding output, exit code, count, SHA, or passage with locator proportionate to stakes; include version or freshness only if staleness could change the decision (never micro-precision). Premises sit above `-- ... --`, conclusions below.
4. **Warrants & standard of proof**: Setting the standard is the principal's choice. Obvious or routine warrants on low-stakes steps need no ceremony; otherwise state the rule in `-- ... --`, justify fit when unset and non-obvious, and note the nearest rival/exception (ruled out or qualified). Match `So` nouns/quantifiers to premises and standard; add no facts in bars.
5. **Single delivery & method pairing**: Await child runs and deliver once at your stopping point (no `"still working"` handbacks unless async tracking was requested; no duplicates once settled). Pair ask-specified methods, forms, mediums (canvas, diagram, map, code, spec), designs, or values beside what was done and note departures.
6. **Empty acknowledgements (`[no claim]`)**: Use a bare standalone `[no claim]` line (zero prose) strictly for claim-free acknowledgements, including closing settled stale remands.

```markdown
**Original Ask (`<ask_id>`):** <Original ask in full>

**Main Conclusion:** <Bottom-line answer with earned qualifier>

### <Argument Title>

(1) <Load-bearing observation with deciding value and locator proportionate to stakes>.
(2) <Second observation, bounded search, or rule with inline basis>.
-- <Plain-prose rule; nearest rival/exception where non-obvious.> --
(3) So, <earned qualifier>, <conclusion>.
```

For complex, multi-hop, or contested messages, read `references/critique-guide.md` before writing.

## Checking an Incoming Direction Brief

1. **Turn-1 intake**: Verify `## Ask` derivation (preserving user authorization without unrequested holds/choices) and required inputs, task IDs, and artifacts; request gaps in prose Argdown without declining.
2. **Traces & satisfiability**: Query Phoenix via `crew:phoenix` (never scrape local logs). Flag demands beyond your stopping point or unverified prescriptions outside `## Ask`, context, and objective in prose Argdown without declining, and execute your role.
3. **Disarm & freeze**: Skip `verdict.py` if unarmed; if armed, disarm first via `verdict.py --no-claim` (`REVISE --no-claim` clarification-hold gate token pending inputs; `PASS --no-claim` when ready or flagging). Log verified deliverables as a frozen `## Acceptance` checklist before work (PKB task if tracked; in-turn for subagents; none for lookups).

## Reviewing a Message (Active Critique Protocol)

Take facially grounded premises as given. A brief grounds check suffices on low-stakes, read-only, or cheaply redone work; reserve full decomposition and Contrast Testing for high-stakes, contested, multi-hop, or irreversible work:

1. **Load-bearing premises & materiality**:
   - Check load-bearing premises for unquoted pointers, unsourced first-person tool claims where stakes warrant a locator/output, or bundled assertions (including omnibus relays).
   - Reject non-Argdown prose, secondary summaries, premature `"still working"` handbacks, or unversioned failures only when material or obscuring grounds; pass benign low-stakes summaries, micro-precision omissions, and unambiguous layout.
2. **Gap, standard, & consistency**: Audit new nouns, quantifiers, populations, or exclusives (`"all"`, `"only"`, `"never"`) under the applicable standard without demanding certainty. Catch missing bridges, circular warrants, proxy-to-construct jumps, unsupported generalisations, observation-surface overreach, silent material swaps, and facial contradictions (never forensic checks).
3. **Contrast Test**: On high-stakes, contested, or multi-hop claims, test the simplest rival world where premises hold yet the conclusion fails beyond the writer's exception. Reject unprompted deferrals (`"their call"`) and bare hand-waving (`"obvious"`, engine output as authority) on contested, non-obvious, or stakes-bearing claims; accept routine/obvious warrants on low-stakes steps.
4. **Ask, authority, rules, & duplicates**: Verify ask coverage (including proved unreachability or open-issue premises at an authorized pause), authority (no _ultra vires_), contextual rule compliance (no unrequested holds; verified anomaly recovery complies), and relays (`verdict-...` with source, qualifiers, and disclosed breaches). Never query refused transports once settled; judge duplicates concisely on their actual lines (never pasting prior reasons), relaying zero new claims beyond the settled `verdict-<id>`.
5. **Remand triage & relaying remands**: Remand only material defects in prose Argdown naming the minimal cure -- (a) **narrow qualifier**, (b) **split bundled premises or supply bridge/warrant**, or (c) **gather missing primary evidence**. Relaying senders pass evidentiary remands down to the originating agent (or a fresh worker if exited or discredited) rather than opening primary sources.

For complex, contested, or multi-hop messages, read `references/critique-guide.md` before ruling.

## Recording Appealable Reasons and Disarming

- **PASS**: Valid on the message alone with grounds proportionate to stakes, ask answered within authority, rules met. Note immaterial slips non-blockingly (omitted from relays); when dropping an unneeded weak part, name strictly the supported relayable subset.
- **REVISE**: Curable material defect; name defect, minimal cure, and direct sender to load `ida:premise-check` (optionally noting clean independent parts with scope bounds so remand scopes only to the defect; those verified parts may relay under their scope bounds without relaying remanded claims).
- **FAIL**: Facial contradiction, incoherence, _ultra vires_, unwaived rule breach, or unanswered material ask (optionally noting clean independent parts with scope bounds that may relay separately; never relay failed claims).

Scale reason length to stakes, matching the message's actual lines (never pasted): a brief note (claim/ask, why grounds suffice, what relays) via `--reason "<brief note>"` suffices on low-stakes, read-only, cheaply redone, or duplicate `PASS`es; reserve full per-premise, rival, and compliance breakdowns via `--reason-file <path>` for high-stakes, contested, multi-hop, or `REVISE`/`FAIL` verdicts.

```bash
uv run --project <plugin-dir> python <plugin-dir>/skills/premise-check/scripts/verdict.py --session <session_id> --claim <claim_id> --verdict <PASS|REVISE|FAIL> (--reason "<brief note>" | --reason-file <path>) [--no-claim] [--agent <agent_id>] [--judged-file <path>]
```

Resolve `<plugin-dir>` via `Path.resolve()`. Pass `--no-claim` with a brief reason for armed briefs or claim-free messages, `--session` if unset, `--agent <agent_id>` for subagent slots, and `--judged-file <path>` for out-of-band reports. Recording fails closed until OTel export succeeds.
