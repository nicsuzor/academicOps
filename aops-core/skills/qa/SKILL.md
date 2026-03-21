---
name: qa
type: skill
category: instruction
description: QA verification, qualitative assessment, criteria design, and test planning
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
version: 2.0.0
permalink: skills-qa
---

# /qa — Quality Assurance

## Philosophy

Every feature exists for a reason. That reason is expressed practically as user stories: someone needs something, and the feature is supposed to deliver it. QA answers one question: **is this feature actually achieving its goals and serving the people it was built for?**

This applies whether the feature is a UI dashboard, a gate in a hook pipeline, a batch processing script, an API endpoint, or a skill definition. The evidence might come from:

- Running the feature and observing its behavior
- Analyzing production logs, transcripts, or hook event data
- Driving a browser and evaluating what a user would see
- Reading test output and checking coverage
- Reviewing code against acceptance criteria
- Comparing actual outcomes to intended outcomes across real usage

QA is not a checklist. It is a judgment call: does this work serve the people it was made for? The agent's job is to figure out what evidence is needed, gather it, and evaluate honestly.

## What "Good QA" Looks Like

1. **Start from the user story**, not the implementation. What was this supposed to do? For whom? Why?
2. **Gather real evidence.** Don't evaluate against imagined scenarios — look at actual behavior, actual data, actual user experience.
3. **Evaluate fitness-for-purpose in narrative prose.** Binary pass/fail obscures the interesting parts. What works well? What almost works? What fails entirely? Why?
4. **Be honest about what you find.** A feature that passes its tests but doesn't serve its users is not good. A feature that has rough edges but genuinely helps is.
5. **Stop after the report.** QA evaluates and reports. It does not decompose, fix, or redesign. A separate session handles remediation.

## Usage

```
/qa                                           # Quick verification of current work
/qa Verify the authentication feature         # Specific feature verification
/qa Analyze custodiet gate effectiveness      # Operational effectiveness analysis
/qa Design QA criteria for the new epic       # Upstream criteria design
```

## Reference Materials

These references provide detailed guidance for specific QA activities. Read the ones relevant to your task — you don't need all of them for every QA invocation.

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

## Execution

When delegating to a QA subagent:

```
Agent(subagent_type="aops-core:qa", model="opus", prompt="
[What you need evaluated and why]

**User story / goal**: [What this feature is supposed to achieve]
**Evidence available**: [Where to find data — logs, transcripts, browser, tests, etc.]
**Acceptance criteria**: [If known — extract from task or spec]

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

When invoked as `/qa` with no arguments, do a quick verification of the current session's work:

1. Identify what was requested and what was done
2. Check: does the work actually achieve what was requested?
3. Produce a verdict (VERIFIED / ISSUES) with brief evidence

## Integration

- **Stop hook**: May require QA verification before session end
- **Task completion**: QA should verify before `complete_task()`
- **Gate tracking**: `post_qa_trigger()` detects QA invocation
- **Spec writing**: templates/spec.md references qa-planning.md for criteria design
