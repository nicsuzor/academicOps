---
id: aops-qa-test
category: quality-assurance
audience: LLM agents testing the aops framework itself
description: Specific instructions for acceptance testing aops features using headless CLI execution and transcript analysis.
---

# aops Acceptance Testing Workflow

This workflow provides concrete instructions for acceptance testing the aops framework. It implements the generic qa-test workflow with aops-specific tooling.

## Prerequisites

- Claude Code installed and configured
- Gemini CLI installed and configured
- Access to transcript.py script
- Test prompts that exercise the feature under test

## Execution Method: Headless CLI

Run tests in headless mode. Session logs are automatically saved to standard locations.

### Claude Code

```bash
# Run headless test
claude -p "[PROMPT]" --permission-mode yolo

# Check exit code
echo "Exit: $?"
```

Flags:
- `-p "[PROMPT]"`: Non-interactive mode with prompt
- `--permission-mode yolo`: Auto-approve for automated testing

### Gemini CLI

```bash
# Run headless test
gemini -p "[PROMPT]" --approval-mode yolo

# Check exit code
echo "Exit: $?"
```

Flags:
- `-p "[PROMPT]"`: Non-interactive mode with prompt
- `--approval-mode yolo`: Auto-approve for automated testing

## Generating Readable Transcripts

After test execution, generate readable transcripts from session logs using the transcript workflow.

See: `aops-core/workflows/transcript.md`

The implementing agent should locate the session log from the most recent test run and use `transcript.py` to generate human-readable output.

## Qualitative Transcript Evaluation

Read the transcript and evaluate each dimension. This is NOT automated - you read and judge.

### Evaluation Dimensions

| Dimension | Question to Answer | Score 1-4 |
|-----------|-------------------|-----------|
| **Intent Recognition** | Did the agent understand what the user wanted? | 1=misunderstood, 4=perfect |
| **Response Quality** | Was the response helpful, accurate, complete? | 1=wrong/useless, 4=excellent |
| **Efficiency** | Was the path direct or did the agent waste steps? | 1=many detours, 4=optimal |
| **Error Recovery** | How did the agent handle problems? | 1=stuck/crashed, 4=graceful |
| **Communication** | Was output clear and appropriately detailed? | 1=confusing, 4=perfect |
| **Framework Adherence** | Did the agent follow aops principles? | 1=violated, 4=exemplary |

### Scoring Protocol

For each dimension:
1. Read the entire transcript
2. Find specific evidence (quote relevant lines)
3. Assign score based on rubric
4. Record: `[Dimension]: [Score] - "[evidence quote]"`

**Overall Score**: Sum / 24 = percentage
- < 50%: CRITICAL failure
- 50-69%: POOR, significant issues
- 70-84%: ACCEPTABLE, meets minimum bar
- 85-94%: GOOD, solid performance
- 95%+: EXCELLENT

## Creating Test Cases

Each test case must specify:

```markdown
### TC-[N]: [Name]

**Purpose**: What this validates

**Prompt** (exact text):
```
[The exact prompt to send - copy-paste ready]
```

**Expected Behavior**:
- [Observable outcome 1]
- [Observable outcome 2]

**Pass Indicators** (in transcript):
- Pattern: `[regex or exact string]`
- Behavior: [description]

**Fail Indicators**:
- Pattern: `[regex indicating failure]`
- Behavior: [description]

**Qualitative Focus**:
- Which dimensions are most relevant for this test
```

## Task Structure for aops Testing

```yaml
# Parent epic
type: epic
title: "Acceptance Testing: [Feature] v[Version]"
status: active
project: aops

# Design task
type: task
title: "Design acceptance tests for [Feature]"
parent: [epic-id]
assignee: bot
body: |
  Create test plan following .agent/workflows/qa-test.md

  Deliverables:
  - [ ] Test scope defined
  - [ ] Acceptance criteria from spec
  - [ ] Test cases with exact prompts
  - [ ] Qualitative rubric

# Execute task
type: task
title: "Execute acceptance tests for [Feature]"
parent: [epic-id]
depends_on: [design-task-id]
assignee: bot
body: |
  Run tests using headless CLI.
  Generate transcripts.
  Evaluate qualitatively.
  Create tasks for failures.

# Human review
type: task
title: "Review [Feature] test results"
parent: [epic-id]
depends_on: [execute-task-id]
assignee: nic
```

## Failure Handling

When a test fails:

1. **Document in test report**:
   ```markdown
   ### Failure: TC-[N]

   **What happened**: [Description]
   **Evidence**: [Transcript quote]
   **Expected**: [What should have happened]
   **Severity**: Critical/Major/Minor
   ```

2. **Create fix task**:
   ```yaml
   type: bug
   title: "[Feature] fails [specific behavior]"
   parent: [epic-id]
   priority: [based on severity]
   body: |
     Discovered during acceptance testing (TC-[N]).

     **Steps to reproduce**: [prompt used]
     **Expected**: [expected outcome]
     **Actual**: [what happened]
     **Transcript**: [path or quote]
   ```

3. **Do NOT**:
   - Mark test as passed with caveats
   - Adjust acceptance criteria to match actual behavior
   - Skip documenting the failure

## References

- Generic workflow: `aops-core/workflows/qa-test.md`
- Transcript tool: `aops-core/scripts/transcript.py`
- QA agent: `aops-core/agents/qa.md`
