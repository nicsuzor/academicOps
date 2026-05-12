---
name: verify
type: skill
category: instruction
description: QA verification, qualitative assessment, criteria design, and test planning. Bundled methodology invoked by agents (marsha, james, junior, pauli) — the methodology lives here, not in the agent prompts.
triggers:
  - "verify"
  - "QA check"
  - "acceptance test"
  - "quality check"
  - "is it done"
  - "validate work"
modifies_files: true
needs_task: true
mode: execution
domain:
  - quality-assurance
allowed-tools: Task,Read,Glob,Grep
version: 1.0.0
permalink: skills-verify
---

# /verify — Verification & QA Methodology

## Philosophy

Every feature exists for a reason. That reason is expressed practically as user stories: someone needs something, and the feature is supposed to deliver it. Verification answers one question: **is this feature actually achieving its goals and serving the people it was built for?**

This applies whether the feature is a UI dashboard, a gate in a hook pipeline, a batch processing script, an API endpoint, or a skill definition. The evidence might come from:

- Running the feature and observing its behavior
- Analyzing production logs, transcripts, or hook event data
- Driving a browser and evaluating what a user would see
- Reading test output and checking coverage
- Reviewing code against acceptance criteria
- Comparing actual outcomes to intended outcomes across real usage

Verification is not a checklist. It is a judgment call: does this work serve the people it was made for? The agent's job is to figure out what evidence is needed, gather it, and evaluate honestly.

## What "Good Verification" Looks Like

1. **Start from the user story**, not the implementation. What was this supposed to do? For whom? Why?
2. **Gather real evidence.** Don't evaluate against imagined scenarios — look at actual behavior, actual data, actual user experience.
3. **Evaluate fitness-for-purpose in narrative prose.** Binary pass/fail obscures the interesting parts. What works well? What almost works? What fails entirely? Why?
4. **Be honest about what you find.** A feature that passes its tests but doesn't serve its users is not good. A feature that has rough edges but genuinely helps is.
5. **Stop after the report.** Verification evaluates and reports. It does not decompose, fix, or redesign. A separate session handles remediation.

## Usage

```
/verify                                           # Quick verification of current work
/verify Verify the authentication feature         # Specific feature verification
/verify Analyze enforcer gate effectiveness      # Operational effectiveness analysis
/verify Design QA criteria for the new epic       # Upstream criteria design
```

## Cynical Verification Protocol

When verifying completed work, apply this protocol before declaring anything done.

**Default assumption: IT'S BROKEN.** You must PROVE it works, not confirm it works.

**Triple-Check Protocol** (for every claim):

1. READ THE FULL OUTPUT — not summaries, not first lines
2. LOOK FOR EMPTY/PLACEHOLDER DATA — empty sections, repeated headers, unfilled templates
3. VERIFY SEMANTIC CONTENT — does the data MAKE SENSE? Is it REAL or GARBAGE?

### Three Verification Dimensions

**Dimension 1 — Output Quality**: Does the result match what was specified?

| Check         | Question                               |
| ------------- | -------------------------------------- |
| Completeness  | Are all required elements present?     |
| Correctness   | Do outputs match spec requirements?    |
| Format        | Does output follow expected structure? |
| Working state | Does code run without errors?          |

**Dimension 2 — Process Compliance**: Did the work follow required workflow?

| Check           | Question                               |
| --------------- | -------------------------------------- |
| Workflow used   | Was the correct workflow applied?      |
| Steps completed | Were all TodoWrite items addressed?    |
| Tests run       | If code changed, were tests executed?  |
| No scope drift  | Did work stay within original request? |

**Dimension 3 — Semantic Correctness**: Does the result make sense for its purpose?

| Check              | Question                                       |
| ------------------ | ---------------------------------------------- |
| Content sensible   | Does the output make logical sense?            |
| No placeholders    | No `{variable}`, `TODO`, `FIXME` in production |
| No garbage data    | Content is real, not template artifacts        |
| Useful to consumer | Would the intended user find this useful?      |

### Red Flags (HALT triggers)

Any of these require immediate investigation:

- Repeated section headers (template/variable bug)
- Empty sections between headers
- Placeholder text (`{variable}`, `TODO`, `FIXME`)
- Suspiciously short output for complex operations
- "Success" claims without showing actual output
- Tests that check existence but not content
- Silent error handling (try/except swallowing errors)

### Verification Output Format

```
## Verification Report

**Verdict**: VERIFIED / ISSUES

### Verification Summary
- Output Quality: PASS / FAIL
- Process Compliance: PASS / FAIL
- Semantic Correctness: PASS / FAIL

[If ISSUES: list each finding with Dimension, Severity (Critical/Major/Minor), and Fix]
```

## Reference Materials

These references provide detailed guidance for specific verification activities. Read the ones relevant to your task — you don't need all of them for every invocation.

| Reference                                | When useful                                                  |
| ---------------------------------------- | ------------------------------------------------------------ |
| [[references/qa-planning.md]]            | Designing acceptance criteria or QA plans before development |
| [[references/qualitative-assessment.md]] | Evaluating fitness-for-purpose after development             |
| [[references/acceptance-testing.md]]     | Running structured test plans, tracking failures             |
| [[references/quick-verification.md]]     | Pre-completion sanity checks                                 |
| [[references/integration-validation.md]] | Verifying structural/framework changes                       |
| [[references/system-design-qa.md]]       | Designing QA infrastructure for a project                    |
| [[references/visual-analysis.md]]        | UI changes or visual artifacts                               |
| [[../eval/references/dimensions.md]]     | Agent session performance evaluation                         |

## Delegation

Marsha is the primary verification agent. When delegating verification work:

```
Agent(subagent_type="aops-core:marsha", model="opus", prompt="
[What you need verified and why]

**User story / goal**: [What this feature is supposed to achieve]
**Evidence available**: [Where to find data — logs, transcripts, browser, tests, etc.]
**Acceptance criteria**: [If known — extract from task or spec]

Invoke /verify for methodology. Evaluate fitness-for-purpose. Cite specific evidence. Report honestly.
")
```

Other agents can also invoke /verify directly when verification methodology is needed without commissioning marsha — e.g., james running a verification pass on a PR, pauli verifying a PKB consolidation, junior checking work before completing a task.

### Delegation Guidance for Callers

**Preserve qualitative framing.** The delegation prompt determines output quality. Never reframe verification as pass/fail or checklist compliance — this causes the agent to regress to mechanical evaluation. The prompt must ask for judgment, not tallying.

**Anti-pattern**: "Check each user story and report pass/fail" → produces DOM element counting, loses all interpretive value.

**Good pattern**: "Evaluate fitness-for-purpose. Is this serving the user it was built for? Cite evidence." → produces genuine qualitative assessment.

**For features with data pipelines** (dashboards, transcripts, reports, generated artifacts), explicitly instruct the agent to trace the pipeline, not just inspect output:

```
Agent(subagent_type="aops-core:marsha", model="opus", prompt="
Qualitative assessment of [FEATURE] against user stories in [SPEC].

Invoke /verify for methodology. For each section: trace the data pipeline from source to output.
1. Verify data freshness, not just existence. Check updates over time for real-time displays.
2. Explicitly test fallback chains. Disable them and verify the primary source works independently.
3. Verify during an active session (real runtime state).
4. Identify design-level findings: if data is misleading or UX doesn't serve its purpose, report it.

Evaluate fitness-for-purpose. Cite specific evidence. Report honestly.
")
```

For agent session evaluation, extract sessions first:

```bash
cd "$AOPS"
PYTHONPATH=aops-core uv run python \
  aops-core/skills/eval/scripts/prepare_evaluation.py \
  --recent 10 --pretty
```

Evidence storage for evaluations:

```
$ACA_DATA/eval/
├── YYYY-MM-DD-<session-id>.md    # Individual session evaluations
├── trends/
│   └── YYYY-MM-DD-batch.md       # Batch trend reports
└── insights/
    └── YYYY-MM-DD-<topic>.md     # Cross-cutting quality insights
```

## Default (no args)

When invoked as `/verify` with no arguments, do a quick verification of the current session's work:

1. Identify what was requested and what was done
2. Check: does the work actually achieve what was requested?
3. Produce a verdict (VERIFIED / ISSUES) with brief evidence

## Integration

- **Stop hook**: May require verification before session end
- **Task completion**: Verify before `complete_task()`
- **Gate tracking**: `prepare_qa_review` custom action fires on marsha/verify subagent start/stop
- **Spec writing**: templates/spec.md references `verify/references/qa-planning.md` for criteria design
