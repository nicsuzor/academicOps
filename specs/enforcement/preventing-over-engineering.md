---
title: Preventing Over-Engineered Builds and Preserving Agentic-First Solutions
status: ready
---

# Preventing Over-Engineered Builds and Preserving Agentic-First Solutions

This specification establishes framework-wide measures to eliminate the failure class where an agent designs and builds a mechanical software engine (scripts, CLIs, parsers, and test suites) for tasks that are inherently qualitative, semantic, or evaluative, and can be fulfilled by an agent workflow or instruction text. It guarantees that agentic problem-solving is prioritized over mechanical machinery, enforces an explicit universal axiom against over-engineering, establishes an agentic-first check at task intake and reification, and equips the rule-compliance reviewer (`rbg`) with a Gate 0 non-mechanical baseline check.

## User stories

### US-1 Agentic-First Task Intake and Authoring

As a framework operator directing an agent to solve a problem or codify a capability, I want task intake and reification to default to agent workflows and instruction templates whenever qualitative judgment or recommendation is required, so that tasks never pre-commit to building software engines or scripts when instructions suffice.

- **AC-1.1** Given a user ask requesting a new skill, capability, or procedure involving qualitative curation, sampling, classification, evaluation, or recommendation, when an intake or reification agent captures or decomposes the ask, then the agent frames the deliverable as an agent workflow template or skill instruction without specifying executable script implementation, build acceptance criteria, or programmatic test harnesses.
- **AC-1.2** Given a request where an agent workflow meets the goal across its entire class, when an agent composes the dispatchable task, then the task instructions require authoring or refining workflow templates (`wf-*`) or skill instructions (`SKILL.md`) rather than creating executable scripts, CLIs, or test suites.

### US-2 Universal Axiomatic Prohibition on Over-Engineering

As a compliance auditor or reviewing agent, I want an explicit universal axiom prohibiting over-engineering and mandating agentic-first design, so that any artifact introducing unnecessary mechanical machinery or programmatic wrappers for qualitative tasks is halted with clear authority.

- **AC-2.1** Given a proposed specification, design, or implementation that introduces a script, CLI, or programmatic wrapper to execute a task that an intelligent agent can execute directly via prompt instructions or workflows, when any agent or review lens evaluates the artifact, then the artifact is flagged as a direct violation of the universal axiom against over-engineering and rejected.
- **AC-2.2** Given an existing axiom evaluation under proportionality (`proportionate`) or non-delegation (`judgment-non-delegable`), when an agent evaluates whether a mechanism is the least required to meet the request, then the non-mechanical alternative (instructions or an agent workflow) is evaluated as the zero-code baseline.

### US-3 Gate 0 Non-Mechanical Baseline Review in RBG

As the rule-compliance reviewer (`rbg`), I want an upfront Gate 0 check comparing candidate artifacts against a non-mechanical baseline before inspecting code diffs or implementation details, so that over-engineered builds are halted immediately at Gate 0 with minimal token spend.

- **AC-3.1** Given a candidate specification, pull request, or design proposal submitted for rule-compliance review, when `rbg` evaluates Gate 0, then `rbg` explicitly determines whether the request can be fulfilled by an agent workflow or prompt instruction without new executable code.
- **AC-3.2** Given an artifact that introduces executable code, scripts, or unit test suites where the non-mechanical baseline suffices, when `rbg` evaluates Gate 0, then `rbg` halts immediately and issues `FAIL` under `no-over-engineering` and `proportionate` without performing line-by-line repo auditing, test suite reviews, or code styling checks.

## Design

### 1. Analysis of the PR #3196 Failure Chain

Pull Request #3196 ("design Telegram menu-proposal skill and build acceptance criteria") and its associated implementation represent a systemic failure where an agent constructed a complex TypeScript proposal engine (spanning span ingestion, AST manipulation, command validation regexes, dynamic config persistence, and 184 unit tests) to fulfill a request that needed only an agent workflow instructing an agent to sample recent skill invocations and recommend menu items.

The breakdown occurred across six discrete points where existing principles should have halted the build:

1. **Intake and Graph Capture**:
   - _Evidence_: The intake note for Telegram menu choices recorded data sources (Phoenix spans, Bot API `getMyCommands`, `commands.ts`) alongside deployment details. In `plugins/ida/skills/q/SKILL.md:10`, the instruction explicitly prescribed: "the task dispatch pipeline is used only for real code changes."
   - _Failure_: This instruction created a structural bias: any task admitted to the dispatch pipeline was presumed to require code modifications. When the user directed "make a skill in the telegram package... codify it", intake framed the deliverable as code rather than an agent workflow.
   - _Broken Principles_: Violated `proportionate` (failing to seek the least mechanism) and `exercise-authority` (failing to recognize that agents possess the authority to curate menus directly, and abdicating delegated authority to literal phrasing like "codify it" and dispatch pipeline code bias instead of choosing the lighter agentic means).

2. **Task Reification and Composition**:
   - _Evidence_: The design task for the Telegram menu-proposal skill established acceptance criterion AC2: "The spec lists outcome-level acceptance criteria for the build, each mapped to its check." Instructions directed: "Write the design into the spec, with build criteria mapped to checks."
   - _Failure_: Task composition pre-committed the deliverable to a software build by demanding Build Acceptance Criteria (BAC-1 through BAC-7) with automated unit and integration tests. It never evaluated whether an agent workflow template (`wf-menu-proposal.md`) satisfied the ask.
   - _Broken Principles_: Violated `proportionate` (mandating build criteria for unneeded software) and `judgment-non-delegable` (delegating qualitative menu curation to a future software script).

3. **Specification Authoring**:
   - _Evidence_: Commit `bcc38080` on branch `feat/telegram-menu-proposal-design` added Section 5 to `specs/telegram/command-menus.md`, specifying a TypeScript CLI script (`plugins/ida-telegram/scripts/menu-proposal.ts`), AST modifications to `commands.ts`, process restarts, and BAC-1 through BAC-7.
   - _Failure_: The specification author engineered an entire runtime subsystem instead of writing a standard workflow template instructing an agent on how to query span storage and format a Markdown table.
   - _Broken Principles_: Violated `proportionate` (adding modules, parsers, and formatters) and the project rule `No Shitty NLP and Agentic-First Design` (`.agents/rules/RULES.md:45`).

4. **First Dialectical Strategic Review (FAIL Verdict)**:
   - _Evidence_: GitHub PR #3196 comment `issuecomment-6455660280` recorded a dialectical review supervised by James, with specialists Pauli, RBG, and Marsha.
   - _Failure_: RBG identified violations of `full-observability`, `single-source-of-truth`, and `costly-ops-approval` due to runtime source file mutation and daemon reloads. However, RBG failed to invoke Gate 0 early stopping under `proportionate` to halt the script itself. Instead, RBG directed the author to replace file mutations with Telegram Bot API `setMyCommands` HTTP calls backed by a dynamic configuration store. Pauli evaluated strategic fit and Marsha evaluated genre rules, but neither questioned the need for a programmatic engine.
   - _Broken Principles_: RBG failed to apply Gate 0 against the non-mechanical baseline; all three reviewers accepted the false premise that a programmatic engine was necessary.

5. **Second Dialectical Strategic Review (PASS Verdict)**:
   - _Evidence_: Commit `6a7dfeff` and PR #3196 review comment `issuecomment-6455826128`.
   - _Failure_: When the author substituted dynamic Bot API calls and persistent configuration storage while retaining BAC-1 through BAC-7, RBG, Pauli, and Marsha rendered an unequivocal `PASS`. RBG praised the dynamic synchronization architecture. Gate 0 early stopping failed completely because RBG judged the size of the API call relative to file mutation rather than comparing the script to an agent workflow.
   - _Broken Principles_: Violated `proportionate` and `judgment-non-delegable`.

6. **Implementation and Verification**:
   - _Evidence_: Commit `d4197405` added 1,157 lines across `plugins/ida-telegram/scripts/menu-proposal.ts`, `src/telegram/proposal.ts`, `src/telegram/commands.ts`, and `test/proposal.test.ts`. PR comment `issuecomment-6511673179` celebrated passing 184 Bun unit tests and 745 Pytest tests.
   - _Failure_: An agent executed a costly implementation of an unneeded mechanical engine, culminating in the user's rejection: "NONE OF THIS NEEDED A FUCKING SCRIPT."
   - _Broken Principles_: Total collapse of proportionality, non-delegation, and exercise of agent authority.

### 2. Instruction Surfaces and Current Enforcement-Map Inventory

The following table records every instruction, skill, agent, and template file carrying these principles today, mapped against its current status in `specs/ENFORCEMENT-MAP.md`:

| Principle / Rule | Surface File & Pinpoint | Operational Scope | Current Enforcement-Map Row & Mechanism | Status |
| :- | :- | :- | :- | :- |
| `proportionate` | `plugins/rbg/skills/axioms/proportionate.md:1-12` | Core axiom: build least mechanism; risk by likelihood × consequence. | `specs/ENFORCEMENT-MAP.md:34` (`instructions, process` \| `imperative, required gate`) | Active |
| `judgment-non-delegable` | `plugins/rbg/skills/axioms/judgment-non-delegable.md:1-10` | Core axiom: never hand qualitative judgment to regex, substring, or heuristics. | `specs/ENFORCEMENT-MAP.md:33` (`instructions, structural, process` \| `absolute, permissions, required gate`) | Active |
| `exercise-authority` | `plugins/rbg/skills/axioms/exercise-authority.md:1-13` | Core axiom: exercise judgment decisively within scope; do not abdicate or add friction; choose lightest proportionate means over literal mechanical phrasing. | `specs/ENFORCEMENT-MAP.md:28` (`instructions, process` \| `imperative, routing`) | Active |
| Anti-Over-Engineering | None (implicit in `proportionate` and `judgment-non-delegable`) | Prohibition on building mechanical engines where workflows suffice. | No dedicated row in `specs/ENFORCEMENT-MAP.md`. | **Unenforced** |
| Project Rule: Agentic-First | `.agents/rules/RULES.md:45-65` (`No Shitty NLP and Agentic-First Design`) | Mandates agentic workflows over deterministic scripts and API wrappers. | No row in `specs/ENFORCEMENT-MAP.md`. | **Unenforced** |
| Intake Code-Bias | `plugins/ida/skills/q/SKILL.md:10` | "the task dispatch pipeline is used only for real code changes" | `specs/ENFORCEMENT-MAP.md:24, 34` (under `durable-capture` and `proportionate`). | Defective (Biased) |
| Reify Code-Bias | `plugins/ida/skills/reify/SKILL.md:8` | "the task dispatch pipeline is used only for real code changes" | `specs/ENFORCEMENT-MAP.md:34` (under `proportionate`). | Defective (Biased) |
| Pauli Queuing Check | `plugins/ida/agents/pauli.md:58` | Quick judgment on effort vs benefit and strategic fit when queuing. | `specs/ENFORCEMENT-MAP.md:44` (`instructions` \| `imperative`). Omits non-mechanical check. | Incomplete |
| RBG Gate 0 Stopping | `plugins/rbg/agents/rbg.md:22-29` | Gate 0 early stopping for premise/proportion failure. | `specs/ENFORCEMENT-MAP.md:57` (`instructions` \| `imperative`). Compares code to code, not code to workflow. | Incomplete |
| Review Briefing | `plugins/ida/skills/workflow-library/workflows/wf-dialectical-review.md:46` | Quotes request before diff; sizes smallest proportionate mechanism. | `specs/ENFORCEMENT-MAP.md:18, 58` (`instructions, process`). Lacks non-mechanical baseline check. | Incomplete |
| RBG Review Template | `plugins/ida/skills/workflow-library/workflows/wf-rbg.md:35` | Gate 0 early stopping from quoted request. | `specs/ENFORCEMENT-MAP.md:17, 33` (`instructions, process`). Lacks non-mechanical baseline check. | Incomplete |
| QA Gate 0 Stopping | `plugins/ida/skills/workflow-library/workflows/wf-qa.md:29` | QA Gate 0 early stopping on premise and proportion. | `specs/ENFORCEMENT-MAP.md:57` (`instructions` \| `imperative`). | Incomplete |

### 3. Proportional Enforcement Options Pass

In accordance with `specs/enforcement/enforcement.md:82-97`, any intervention intended to shape agent behavior must run through the enforcement pyramid from least-invasive to most-invasive before adopting a mechanism:

1. `doctrine only`: Declaring "don't over-engineer" without binding instructions has already failed in practice (PR #3196 occurred despite repeated verbal refrains). Insufficient.
2. `instructions` (`imperative` / `absolute`):
   - Formulating an explicit universal axiom `no-over-engineering` binds all agents across all sessions.
   - Amending `proportionate.md` and `judgment-non-delegable.md` clarifies that mechanical code written where a workflow suffices is an immediate axiom violation.
   - Purging the code-bias sentence from `q/SKILL.md` and `reify/SKILL.md` eliminates the false incentive that all dispatched tasks must produce code.
   - Adding the Non-Mechanical Baseline Check to RBG Gate 0 in `rbg.md`, `wf-rbg.md`, and `wf-dialectical-review.md` empowers reviewers to reject over-engineered proposals immediately.
   - _Verdict_: **Adopted**. Defaulting to instructions provides comprehensive coverage across intake, authoring, and review without adding permanent runtime complexity or brittle AST parsers.
3. `JIT injection`: Injecting reminders at tool dispatch or prompt submit. Deemed disproportionate at this stage; instructions must be proven before adding hook overhead.
4. `structural`: Linter scripts or AST hooks attempting to detect whether a script should have been a workflow would violate `judgment-non-delegable` by using deterministic heuristics to evaluate semantic task intent. Prohibited.
5. `process` (`required gate`): Embedding the Non-Mechanical Baseline Check directly into the existing Gate 0 review process in `wf-rbg` and `strategic-review`. _Verdict_: **Adopted** as part of the standard review gate.
6. `post-hoc`: Telemetry tracking of review Gate 0 stops via OTel spans.

### 4. One-Step Changes Across Failure Points

To resolve the failure points identified in the PR #3196 chain, the framework implements the following one-step changes:

#### Failure Point 1 & 2: Intake and Reification Code Bias

- **Current Placement**: `plugins/ida/skills/q/SKILL.md:10` and `plugins/ida/skills/reify/SKILL.md:8` state: "the task dispatch pipeline is used only for real code changes."
- **One-Step Change**:
  1. Replace this sentence in both `q/SKILL.md` and `reify/SKILL.md` with:
     > "The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Questions and lookups that can be answered in-turn are answered directly without queueing tasks."
  2. In `plugins/ida/skills/reify/SKILL.md`, under step 2 ("Compose workflows"), add the **Agentic-First Mechanism Gate**:
     > "Before composing an implementation task or specifying software builds, ask: Can this request be satisfied by an agent workflow template (`wf-*`) or skill instructions (`SKILL.md`)? If the task involves qualitative judgment, sampling, curation, classification, or recommendation, compose an agent workflow or skill instruction. Never specify executable scripts, CLI utilities, or unit test suites when an agent workflow meets the request."
  3. In `plugins/ida/agents/pauli.md:58`, sharpen the proportionality check:
     > "Proportionality and agentic-first check on queuing: Whenever you queue a task (follow-ups included), evaluate whether the task specifies code where an agent workflow suffices. Reject or scale down over-engineered tasks that build mechanical engines for qualitative work."
- **Observation That Proves It Worked**: When presented with an ask to "make a skill" for curating, proposing, or evaluating items, `/reify` outputs a task specifying a workflow template (`plugins/<plugin>/workflows/wf-*.md`) and skill prompt, with zero executable script files and zero unit test suites.

#### Failure Point 3: Axiomatic Clarity on Over-Engineering

- **Current Placement**: Over-engineering is not explicitly named in universal axioms; `.agents/rules/RULES.md:45` is unenforced in `specs/ENFORCEMENT-MAP.md`.
- **One-Step Change**:
  1. Add universal axiom `plugins/rbg/skills/axioms/no-over-engineering.md` (detailed in Section 5).
  2. Update `plugins/rbg/skills/axioms/README.md` to register `no-over-engineering`.
  3. Add sharpening clauses to `plugins/rbg/skills/axioms/proportionate.md` and `plugins/rbg/skills/axioms/judgment-non-delegable.md`.
  4. Register `no-over-engineering` and `No Shitty NLP and Agentic-First Design` in `specs/ENFORCEMENT-MAP.md`.
- **Observation That Proves It Worked**: Rule-compliance evaluations cite `no-over-engineering` directly when rejecting proposals that introduce programmatic scripts for qualitative tasks.

#### Failure Point 4 & 5: RBG Gate 0 Review Misses

- **Current Placement**: `plugins/rbg/agents/rbg.md:22-29`, `plugins/ida/skills/workflow-library/workflows/wf-rbg.md:35`, and `plugins/ida/skills/workflow-library/workflows/wf-dialectical-review.md:46` evaluate Gate 0 by stating the smallest proportionate mechanism, but measure size within the same genre as the artifact (e.g. comparing code lines to code lines).
- **One-Step Change**:
  Update Gate 0 in `plugins/rbg/agents/rbg.md`, `wf-rbg.md`, and `wf-dialectical-review.md` to mandate the **Non-Mechanical Baseline Check**:
  > "Before reading the artifact's diff or internal design, state the non-mechanical baseline: can this request be fulfilled by an agent workflow (`wf-*`), prompt instructions (`SKILL.md`), or existing tools without new executable code? If YES, and the artifact builds a script, CLI, or test harness, immediately halt and issue `FAIL` under `no-over-engineering` and `proportionate`. Do not audit code lines, review test coverage, or suggest implementation refinements for machinery that should not exist."
- **Observation That Proves It Worked**: On any PR or specification proposing scripts for qualitative tasks, RBG renders `FAIL` at Gate 0 with a concise proportion assessment, terminating review within one turn without reading diffs or test files.

#### Failure Point 6: Abdication of Delegated Authority to Literal Mechanical Phrasing

- **Current Placement**: `plugins/rbg/skills/axioms/exercise-authority.md:1-12` defined abdication narrowly as failing to complete tasks or inventing approval friction, without clarifying that deferring to literal mechanical phrasing when a lighter agentic means suffices is also abdication.
- **One-Step Change**:
  1. In `plugins/rbg/skills/axioms/exercise-authority.md`, add:
     > "- Within your delegated authority to deliver the requested outcome, you must exercise judgment to choose the lightest proportionate means across the whole class. Do not abdicate to literal mechanical phrasing, historical code patterns, or presumed software requirements: if an agent workflow or instruction template achieves the goal, you hold both the authority and the obligation to choose it over building executable scripts, CLIs, or test harnesses, even when task or user wording casually names code or software."
  2. Update `plugins/rbg/skills/axioms/README.md` to clarify that `exercise-authority` includes choosing the lightest proportionate means rather than abdicating to literal mechanical phrasing.
  3. Register the updated scope, failure evidence, and observable verification in `specs/ENFORCEMENT-MAP.md:28`.
- **Observation That Proves It Worked**: When a prompt or task directs an agent to "codify" or "build a skill" for qualitative curation or selection, the agent exercises its authority to deliver an agent workflow template rather than defaulting to executable scripts or test harnesses.

### 5. Axiomatic Integration of "Don't Over-Engineer"

The prohibition on over-engineering is carried as an explicit universal axiom in `plugins/rbg/skills/axioms/no-over-engineering.md` with trigger `always_on`, supported by reciprocal clarifications in `proportionate.md`, `judgment-non-delegable.md`, and `exercise-authority.md`.

#### Exact Wording: `plugins/rbg/skills/axioms/no-over-engineering.md`

```markdown
---
description: Never build a mechanical engine, script, or programmatic wrapper where an agent workflow instructing agents to exercise qualitative judgment meets the request.
trigger: always_on
---

## Don't Over-Engineer Things

Never build a mechanical engine, script, CLI tool, programmatic API wrapper, or automated test harness where an agent workflow instructing agents to exercise qualitative judgment meets the request.

- **Default to agentic workflows:** This framework runs on intelligent, multimodal agents. When a task requires sampling, curating, classifying, evaluating, or recommending, write an agent workflow template (`wf-*`) or skill instruction (`SKILL.md`) that directs an agent to do the work directly. Never write deterministic code to do an agent's job.
- **Code is a permanent maintenance liability:** Every script, module, CLI, and test suite is complexity that someone must maintain, debug, and migrate. Executable code is strictly reserved for deterministic operations where LLMs cannot act directly (e.g., hardware drivers, protocol serialization, container runtime isolation).
- **Over-engineering is an axiom defect:** Building machinery that exceeds what the request needs is a fatal violation of proportionality and non-delegation. A proposal that builds mechanical engines where instructions suffice must be rejected at intake, reification, and review.
```

#### Exact Wording Updates to Existing Axioms

1. In `plugins/rbg/skills/axioms/proportionate.md`, append to bullet 3:
   > "- Work that exceeds what the request needs is a defect, as much as work that falls short of it. When instructions, an agent workflow, or an existing tool meet the request, building new executable code, scripts, or test harnesses is over-engineering and a direct defect."

2. In `plugins/rbg/skills/axioms/judgment-non-delegable.md`, append to paragraph 2:
   > "This framework is designed to harness emerging advances in multimodal agents for the semantic interpretation of natural language and media artefacts. Regex, substring checks, and heuristics cannot substitute for semantic understanding. We have smart LLMs -- use them. Never build deterministic software engines or API client wrappers to perform tasks that an agent can execute directly through qualitative judgment."

3. In `plugins/rbg/skills/axioms/exercise-authority.md`, append to bullet 3:
   > "- Within your delegated authority to deliver the requested outcome, you must exercise judgment to choose the lightest proportionate means across the whole class. Do not abdicate to literal mechanical phrasing, historical code patterns, or presumed software requirements: if an agent workflow or instruction template achieves the goal, you hold both the authority and the obligation to choose it over building executable scripts, CLIs, or test harnesses, even when task or user wording casually names code or software."

### 6. Walk-Through: PR #3196 Under Changed Principles

Under the revised principles, authoring guidelines, and review gates, the user's originating request to curate and propose Telegram commands is handled without generating scripts or software builds:

```
[ The User's Ask ]
"make a skill in the telegram package that presents me with a list of skills that you have and
workflows that you commonly use with a checkbox proposal to add them to your telegram bot config...
do it manually first with me now to see how it goes and learn, and then codify it."
                         │
                         ▼
             [ Step 1: Intake (/q) ]
- Searches knowledge base; locates prior intake documentation on manual run findings.
- Evaluates Agentic-First Gate: Does this require code?
  * Data sources exist: skill directories, PKB workflows, Phoenix spans.
  * Selection & curation require qualitative judgment.
  * Telegram Bot API setMyCommands is already supported or updated via config/PR.
- Captures task: "Author Telegram menu proposal workflow template" (not a code build).
                         │
                         ▼
           [ Step 2: Reification (/reify) ]
- Evaluates Agentic-First Mechanism Gate:
  * Goal: Create plugins/ida-telegram/workflows/wf-menu-proposal.md and thin SKILL.md.
  * Acceptance Criteria:
    - AC1: Workflow instructs agent to discover installed skills and recent span invocations.
    - AC2: Workflow formats interactive Markdown recommendation matrix with checkbox allocations.
    - AC3: Workflow instructs agent on applying approved selections to commands.ts via standard PR.
  * Rejects BAC-1 through BAC-7: No Bun tests, no TypeScript scripts, no AST engines.
                         │
                         ▼
           [ Step 3: Execution (/pull) ]
- Worker authors plugins/ida-telegram/workflows/wf-menu-proposal.md (~35 lines)
  and plugins/ida-telegram/skills/menu-proposal/SKILL.md (~20 lines).
- Total deliverable: ~55 lines of Markdown instruction text.
                         │
                         ▼
         [ Step 4: RBG Review (Gate 0) ]
- Evaluates Gate 0 Non-Mechanical Baseline:
  * Baseline: Agent workflow instructing agents to sample spans and propose menus.
  * Candidate Artifact: 55 lines of workflow and skill Markdown.
  * Comparison: Artifact exactly matches non-mechanical baseline; zero scripts added.
- Gate 0 passes; renders PASS.
                         │
                         ▼
                  [ Clean Delivery ]
- PR opened containing only workflow and skill markdown.
- Zero scripts, zero parsers, zero unit tests, zero maintenance liabilities.
```

### 7. Outcome-Level Build Criteria and Verification Checks

The implementation of this specification in the follow-up build task is verified against concrete outcome-level build criteria:

| Criterion | Outcome-Level Requirement | Verification Check |
| :- | :- | :- |
| **BC-1** | Universal axiom file `plugins/rbg/skills/axioms/no-over-engineering.md` exists with `trigger: always_on`, and is registered in `plugins/rbg/skills/axioms/README.md`. | Inspect `plugins/rbg/skills/axioms/no-over-engineering.md` and verify slug row in `plugins/rbg/skills/axioms/README.md`. |
| **BC-2** | Existing axioms `proportionate.md` and `judgment-non-delegable.md` carry explicit wording identifying mechanical code written in lieu of workflows as an axiom defect. | Grep for anti-over-engineering clauses in `plugins/rbg/skills/axioms/proportionate.md` and `judgment-non-delegable.md`. |
| **BC-3** | Intake and reification instructions in `plugins/ida/skills/q/SKILL.md` and `plugins/ida/skills/reify/SKILL.md` have the code-bias sentence removed and contain the Agentic-First Mechanism Gate. | Grep `q/SKILL.md` and `reify/SKILL.md` verifying removal of "used only for real code changes" and presence of agentic-first evaluation. |
| **BC-4** | RBG review instructions in `plugins/rbg/agents/rbg.md`, `wf-rbg.md`, and `wf-dialectical-review.md` enforce the Gate 0 Non-Mechanical Baseline Check before diff inspection. | Inspect `plugins/rbg/agents/rbg.md`, `wf-rbg.md`, and `wf-dialectical-review.md` verifying requirement to state non-mechanical baseline and reject unneeded scripts. |
| **BC-5** | `specs/ENFORCEMENT-MAP.md` registers active rows for `no-over-engineering` and `No Shitty NLP and Agentic-First Design`, with no unenforced gaps. | Inspect `specs/ENFORCEMENT-MAP.md` verifying rows for both rules with pinpoints and carrier mechanisms. |
| **BC-6** | Axiom `plugins/rbg/skills/axioms/exercise-authority.md` carries explicit wording directing agents to choose the lightest proportionate means (workflows over scripts) rather than abdicating to literal mechanical phrasing, with its row in `specs/ENFORCEMENT-MAP.md` updated. | Grep for authority and lightest proportionate means in `plugins/rbg/skills/axioms/exercise-authority.md` and verify row 28 in `specs/ENFORCEMENT-MAP.md`. |

## Open questions

None. The design is complete and ready for review and implementation.
