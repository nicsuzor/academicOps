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
version: 1.1.0
permalink: skills-qa
---

# /qa Command Skill

QA skill covering both upstream (criteria design, QA planning) and downstream (verification, assessment) quality assurance.

> **Taxonomy note**: This skill provides domain expertise (HOW) for quality assurance. The modes below represent different types of QA expertise, not independent workflows. A workflow step that says "verify the work" invokes this skill; the mode determines which type of QA expertise to apply. See [[TAXONOMY.md]] for the skill/workflow distinction.

## Purpose

Provides rigorous verification that work **actually achieves** what the user needs — not just that tests pass or agents claim success. Also provides guidance for designing the criteria and plans that verification evaluates against.

## Usage

```
/qa
```

Or with context:

```
Skill(skill="qa", args="Verify the authentication feature is complete")
Skill(skill="qa", args="Design QA plan for the task map epic")
```

## Mode Selection

The QA skill has seven modes. Select based on what you're being asked to do:

| Mode                         | When                                                            | Reference                                |
| ---------------------------- | --------------------------------------------------------------- | ---------------------------------------- |
| **QA Planning**              | Designing acceptance criteria or QA plans BEFORE development    | [[references/qa-planning.md]]            |
| **Qualitative Assessment**   | Evaluating fitness-for-purpose AFTER development                | [[references/qualitative-assessment.md]] |
| **Acceptance Testing**       | Running test plans, tracking failures, creating fix tasks       | [[references/acceptance-testing.md]]     |
| **Quick Verification**       | Pre-completion sanity check (does it run?)                      | [[references/quick-verification.md]]     |
| **Integration Validation**   | Verifying structural/framework changes                          | [[references/integration-validation.md]] |
| **System Design**            | Designing QA infrastructure and criteria for a project          | [[references/system-design-qa.md]]       |
| **Agent Session Evaluation** | Evaluating agent session performance against quality dimensions | [[../eval/references/dimensions.md]]     |

### Routing Rules

- "Design criteria", "write acceptance criteria", "create QA plan" → **QA Planning**
- "Is this any good?", "evaluate against user stories" → **Qualitative Assessment**
- "Verify work is complete", "check before completion" → **Quick Verification** (default for `/qa` with no args)
- "Run the test plan", "execute acceptance tests" → **Acceptance Testing**
- "Validate framework integration" → **Integration Validation**
- "Design QA system for project" → **System Design**
- "Evaluate session", "how good was that", "assess agent performance", `/eval` → **Agent Session Evaluation**

## Execution

### Default (Quick Verification)

When invoked as `/qa` with no args, delegate to the QA agent for quick verification:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Verify the work is complete.

**Original request**: [hydrated prompt from session context]

**Acceptance criteria**:
[Extract from task or session state]

**Work completed**:
[Files changed, todos marked complete]

Check all three dimensions (Output Quality, Process Compliance, Semantic Correctness) and produce verdict.
")
```

### QA Planning

When the request is about designing criteria or plans:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
QA Planning mode. Read references/qa-planning.md first.

Design acceptance criteria and QA plan for [FEATURE] based on spec [SPEC].
Inhabit the user persona. Write qualitative dimensions with quality spectra,
not binary checklists. Design scenarios, not test cases.

Output: acceptance criteria for the spec + per-task QA + E2E evaluation suites.
")
```

### Qualitative Assessment

When evaluating an existing feature:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Qualitative Assessment mode. Read references/qualitative-assessment.md first.

Evaluate [FEATURE] against user stories in [SPEC/TASK].
If the task involves UI changes or visual artifacts, you MUST apply the Visual Analysis Protocol in references/visual-analysis.md.
Inhabit the user persona. Walk the scenarios. Evaluate fitness-for-purpose
in narrative prose. Is this good for the people it was designed for?
")
```

### Acceptance Testing

When running a test plan or tracking failures:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Acceptance Testing mode. Read references/acceptance-testing.md first.

Run acceptance tests for [FEATURE] against the test plan in [SPEC/TASK].
Black-box testing only — test as the user would. For each failure, create
a fix task. Produce a results table with qualitative scores.
")
```

### Integration Validation

When verifying framework/structural changes:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
Integration Validation mode. Read references/integration-validation.md first.

Validate framework integration for [FEATURE]. Capture baseline state,
execute the feature, verify structural changes, report evidence table
(expected vs actual for each field/relationship).
")
```

### System Design

When designing QA infrastructure for a project:

```
Task(subagent_type="aops-core:qa", model="opus", prompt="
System Design mode. Read references/system-design-qa.md first.

Design QA infrastructure and criteria for [PROJECT]. Inventory existing
tests, analyze gaps, design qualitative acceptance criteria per
qa-planning.md, then design evaluation suites and workflow.
")
```

### Agent Session Evaluation

When evaluating agent session performance (invoked as `/eval` or when asked to assess how an agent worked):

**Step 1: Extract sessions**

```bash
cd "$AOPS"
PYTHONPATH=aops-core uv run python \
  aops-core/skills/eval/scripts/prepare_evaluation.py \
  --recent 10 --pretty
```

For a specific session: `--session-id <id-prefix>`

**Step 2: Evaluate**

```
Agent(subagent_type="aops-core:qa", model="opus", prompt="
Agent Session Evaluation mode. Read aops-core/skills/eval/references/dimensions.md first.

The extracted sessions (JSON) are above. For each session:

1. Decide whether it is worth evaluating. Skip sessions that are pure
   maintenance with nothing to judge (e.g., auto-commits, formatting runs,
   CI retries). You will recognise these from the prompts and tool usage.
   When in doubt, evaluate.

2. Read the session. Understand what the user needed, what the agent did,
   and what the outcome was.

3. Identify which of the universal dimensions from dimensions.md matter most
   for this session. Do not apply all seven mechanically — choose the 3-5
   that are most relevant to the nature of the work.

4. Evaluate in narrative prose. Cite specific evidence from the session.
   Inhabit the user's perspective: what did they need? Did the response serve
   that need?

Output findings to \$ACA_DATA/eval/YYYY-MM-DD-SESSION_ID.md
")
```

**Step 3: Batch trend report** (for `--recent 20` style evaluations)

The evaluator produces a trend report at `$ACA_DATA/eval/trends/YYYY-MM-DD-batch.md`
referencing prior findings to identify patterns, recurring weaknesses, and quality improvements.

**Evidence storage**:

```
$ACA_DATA/eval/
├── YYYY-MM-DD-<session-id>.md    # Individual session evaluations
├── trends/
│   └── YYYY-MM-DD-batch.md       # Batch trend reports
└── insights/
    └── YYYY-MM-DD-<topic>.md     # Cross-cutting quality insights
```

## Output

Varies by mode:

- **Quick Verification**: Verdict (VERIFIED/ISSUES) + dimension summary
- **QA Planning**: Acceptance criteria + per-task QA tables + E2E evaluation suites
- **Qualitative Assessment**: Narrative evaluation with evidence, synthesis, recommendations
- **Acceptance Testing**: Results table + failure tasks + qualitative scores
- **Integration Validation**: Evidence table (expected vs actual)
- **System Design**: QA infrastructure design + criteria + evaluation suites
- **Agent Session Evaluation**: Narrative per-session findings + optional batch trend report

## Integration

- **Stop hook**: May require QA verification before session end
- **Task completion**: QA should verify before `complete_task()`
- **Gate tracking**: `post_qa_trigger()` detects QA invocation
- **Spec writing**: SPEC-TEMPLATE.md references qa-planning.md for criteria design
- **Feature development**: Workflow 05 Phase 2 references qa-planning.md for requirements
- **Spec development**: Workflow 06 Step 4 references qa-planning.md for acceptance criteria
