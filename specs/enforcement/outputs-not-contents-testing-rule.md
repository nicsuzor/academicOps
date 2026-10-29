---
id: outputs-not-contents-testing-rule
title: Outputs-Not-Contents Testing Rule and Workflow Integration
status: draft
type: spec
tags: [enforcement, testing, tdd, instructions, rules]
---

# Outputs-Not-Contents Testing Rule and Workflow Integration

This specification governs the scope and assertions of testing across academicOps. It establishes the rule that tests verify observable outputs, never internal contents. Text documents and instruction files are not functions and produce no outputs, so they owe zero unit tests. For executable code, tests assert observable outputs and behavioral contracts, never that code contains a particular phrase, variable, enum, constant, or condition.

## Originating Ask & Evidence

User direction relayed on 2026-10-30:

> "never write unit tests for documentation or instruction files. testing rule should clearly say that we test OUTPUTS. we never test contents themselves. this applies to code too - i never want to see a test that asserts that our code says a particular phrase or uses a particular variable, enum, constant, condition, etc. Since text documents are not functions, they dont generate outputs, so we don't test them.
>
> update the TTD workflows at each level to make this clear as well."

## User Stories

### US-1: Documentation and Instruction Files Owe No Unit Tests

As a framework contributor and reviewer, I want documentation and instruction files excluded from unit testing, so that non-executable text documents are not wrapped in change-detector or mirror tests.

- **AC-1.1**: Given documentation, markdown, or agent instruction files, when evaluating test obligations, then zero unit tests are written because text documents are not functions and produce no executable outputs.
- **AC-1.2**: Given a change modifying documentation, specifications, or agent-facing instruction text, when verifying the change, then verification is demonstrated through inspection or fresh agent runs against acceptance criteria rather than programmatic unit test assertions.

### US-2: Code Tests Check Outputs, Never Contents

As a software engineer, I want unit tests for code to assert observable outputs and public interface behavior rather than internal syntactic contents, so that tests guard against regressions without coupling to implementation choices.

- **AC-2.1**: Given executable code under test, when authoring unit tests, then tests assert observable outputs and external effects through the public interface, never contents themselves.
- **AC-2.2**: Given executable code under test, when authoring test assertions, then no test asserts that code contains a particular phrase, variable, enum, constant, condition, or syntactic element.

### US-3: TDD Workflows Across All Library Levels Enforce Outputs-Not-Contents

As an agent composing or executing a test-driven development workflow, I want every TDD workflow across all library tiers to state this rule consistently, so that test-first development adheres strictly to testing outputs rather than contents.

- **AC-3.1**: Given the universal TDD workflow (`wf-tdd`), when an agent executes test-driven development, then the normative constraints explicitly mandate testing outputs and forbid unit tests for documents/instructions and forbid asserting internal code contents.
- **AC-3.2**: Given project-level development workflows (such as the academicOps development task workflow), when an agent executes development, then the build procedure and constraints state the identical rule.
- **AC-3.3**: Given any future PKB-tier TDD workflow, when composed, then it adheres to the identical outputs-not-contents contract.

## Design & Placement Analysis

### 1. Rule's Home

- **Canonical Home:** `.agents/rules/tests-verify-behaviour.md`
- **Current State:** The rule currently identifies change-detector (mirror) tests, tautological tests, implementation-coupled tests, and acceptance checks committed as tests as defects. It notes that instruction text changes owe no tests. However, it does not yet explicitly articulate the overarching principle: **we test outputs, never contents themselves**.
- **Placement Decision:** Update `.agents/rules/tests-verify-behaviour.md` to state the outputs-not-contents rule as the primary operational directive.

### 2. TDD Workflows Across All Library Levels

The workflow library operates across three resolution tiers (per `plugins/ida/skills/workflow-library/SKILL.md`):

1. **Universal Tier (`${CLAUDE_SKILL_DIR}/workflows/` / `plugins/ida/skills/workflow-library/workflows/`):**
   - **Target Workflow:** `wf-tdd.md` (`plugins/ida/skills/workflow-library/workflows/wf-tdd.md`).
   - **Integration Point:** `## Constraints (normative)`.
2. **Project Tier (PKB templates scoped to project):**
   - **Target Workflow:** `aops-wf-dev-task` (PKB node scoped to project `aops`, governing academicOps development tasks).
   - **Integration Point:** `Procedure` (Step 3: Build) and Output contract.
3. **PKB Tier (Portable personal workflows with no project):**
   - **Target Workflow:** Currently absent (no standalone generic TDD template exists in the PKB tier; resolution falls through to Universal `wf-tdd.md`).
   - **Invariant:** Any future generic TDD workflow created at the PKB tier inherits the outputs-not-contents rule verbatim.

### 3. Enforcement Map Status

- **Current State in `specs/ENFORCEMENT-MAP.md`:** Neither `.agents/rules/tests-verify-behaviour.md` nor `wf-tdd.md` nor `aops-wf-dev-task` currently has an entry in `specs/ENFORCEMENT-MAP.md`. This absence is formally recorded.
- **Proposed Entry for Stage 2 (Build):**
  ```markdown
  | [Project Rule: Tests verify behaviour (outputs, not contents)](../.agents/rules/tests-verify-behaviour.md) -- Tests assert observable outputs, never contents themselves; no unit tests for documentation or instruction files (text documents are not functions and produce no outputs); no test asserts that code contains a particular phrase, variable, enum, constant, condition, or similar. | instructions | imperative | `.agents/rules/tests-verify-behaviour.md:6-28`; `plugins/ida/skills/workflow-library/workflows/wf-tdd.md:25-40`; `aops-wf-dev-task` |
  ```

### 4. Enforcement Pyramid & Proportionality Analysis

Following `specs/enforcement/enforcement.md`:

1. **`doctrine only`**: Evaluated and rejected. High-level principles without explicit directives at the operative testing boundary fail to prevent agents from writing unit tests for markdown docs or grepping code for phrases.
2. **`instructions` (`imperative`)**: **Selected mechanism.** Clear, prominent instructions in the canonical project rule (`tests-verify-behaviour.md`) and in the TDD workflow templates across tiers directly guide agent behavior during test authoring. Default to instructions.
3. **`JIT injection`**: Evaluated and deferred. JIT injection adds prompt overhead on every turn. If post-hoc reviews show persistent violation of the instruction, JIT reminders on test file authoring can be evaluated.
4. **`structural`**: Evaluated and rejected. AST parsing or regex linters blocking string assertions or assertions in test files would violate `judgment-non-delegable` and "agents all the way down", causing false rejections of legitimate tests (e.g. asserting that a parser outputs a specific error message or that a CLI outputs expected help text).
5. **`process` (`required gate`)**: Retained as verification backstop. Multi-lens PR review (`wf-review`, `strategic-review` with `rbg` and `marsha`) checks test assertions against the rule during code review.
6. **`post-hoc` (`observability`)**: Retained. Pull request diffs and test suites remain fully observable and auditable in git history.

## Proposed Wording for Implementation (Stage 2)

The proposed wording covers documents, instructions, and code, states outputs-not-contents, and adds nothing beyond the ask.

### Target 1: `.agents/rules/tests-verify-behaviour.md`

Add directly under the main heading:

```markdown
## Tests verify behaviour, not our own code

We test outputs; we never test contents themselves.

- **No unit tests for documentation or instruction files**: Text documents are not functions and produce no outputs, so we do not test them.
- **Code tests check outputs, never contents**: We never write a test that asserts that code says a particular phrase or uses a particular variable, enum, constant, condition, or similar. Tests assert observable outputs and behavioral contracts of functions and execution, never internal contents.
```

### Target 2: `plugins/ida/skills/workflow-library/workflows/wf-tdd.md`

In `## Constraints (normative)`, update and sharpen the constraints:

```markdown
- Tests check outputs, never contents. Never write unit tests for documentation or instruction files: text documents are not functions and produce no outputs, so we do not test them. For code, never write a test that asserts that code says a particular phrase or uses a particular variable, enum, constant, condition, or similar; assert observable outputs, never contents themselves.
```

### Target 3: `aops-wf-dev-task` (PKB Project Tier Workflow)

In `## Procedure`, Step 3 (Build):

```markdown
3. **Build** -- a change to code that executes is built test-first: for each changed behaviour, name the defect the test catches, write a failing test, run it against the pre-change code and capture the failure, implement the minimum change that fits the module's existing conventions to pass, and finish with the full test suite and linter green. Tests check outputs, never contents: never write unit tests for documentation or instruction files (text documents are not functions and produce no outputs, so we do not test them), and never assert that code says a particular phrase or uses a particular variable, enum, constant, condition, or similar. A change to agent-facing instruction text, docs, or specs adds no unit test; its evidence is a baseline-vs-changed run or check reported in the PR.
```

## Open Questions

None. The design, placement, tier mapping, and exact wording are fully resolved.
