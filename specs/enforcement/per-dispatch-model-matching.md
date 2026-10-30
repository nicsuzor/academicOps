---
id: per-dispatch-model-matching
title: In-Session Subagent Model Matching and Resource Conservation
status: draft
type: spec
tags: [enforcement, model-selection, token-cost, dispatch, resource-conservation]
---

# In-Session Subagent Model Matching and Resource Conservation

This specification establishes the architectural standard, enforcement analysis, and operational invariants requiring every interactive agent dispatching in-session subagents to dynamically match the subagent's model to task complexity, erring on the side of cheaper models, and establishing the resource conservation rule in the enforcement doctrine.

- **Stated Purpose:** Eliminate unnecessary model spend during interactive sessions by requiring dispatching agents to select the cheapest model tier that suffices for each in-session subagent invocation, reserving flagship models strictly for complex architectural judgment.
- **Primary Audience:** Framework architects, system developers, agent authors, and review supervisors.
- **Governing Axioms and Rules:** Categorical Imperative (all actions justified by general rule), Proportionate (meet requests with least mechanism; weigh risk and cost), and Enforcement Architecture (proportional intervention options pass).

## 1. User Stories

### US-1: Dynamic Model Matching on Dispatch

As the framework principal (the user), I want interactive agents to match the model to the task on every in-session dispatch, so that routine queries and sanity checks do not consume expensive flagship model tokens.

- **AC-1.1**: Given an interactive agent preparing to dispatch an in-session subagent, when selecting the execution parameters, then the agent explicitly specifies a model parameter matched to task complexity rather than relying on inherited parent defaults.
- **AC-1.2**: Given a routine task (such as a read-only filesystem lookup, data formatting, preliminary diagnostic check, or quick question), when an agent dispatches a subagent, then the agent selects the light/cheapest model tier.
- **AC-1.3**: Given a standard task (such as multi-file implementation, test writing, or structured analysis), when an agent dispatches a subagent, then the agent selects the standard/workhorse model tier.
- **AC-1.4**: Given a complex or critical task (such as architectural synthesis, high-stakes dialectical review, or deep strategic reasoning), when an agent dispatches a subagent, then the agent selects the flagship model tier.

### US-2: Cross-Harness Model Tier Resolution

As an agent author, I want instruction templates and workflow definitions to use valid, harness-supported model identifiers, so that dispatch tool calls execute cleanly without parameter rejections across different runtime environments.

- **AC-2.1**: Given a dispatch call within an execution harness, when the dispatching agent sets the model override, then the value corresponds to a valid model identifier recognized by that harness.
- **AC-2.2**: Given existing review and execution workflow templates naming legacy or environment-mismatched model tiers, when reviewed or executed, then all model tier references resolve cleanly to supported runtime parameters or functional tier classifications without runtime failures.

## 2. Context and Problem Statement

### 2.1 Observed Runtime Cost Inefficiency

In interactive sessions, the conversational coordinator accounts for the majority of token consumption. Because top-level sessions often run on flagship models, in-session subagents dispatched without an explicit model override inherit the parent session's flagship model by default.

Empirical evaluation of session traces revealed:

1. Subagents dispatched for routine filesystem searches, documentation lookups, and basic formatting ran on flagship models, generating large token spend for tasks requiring only basic comprehension.
2. In-session dispatch tools support per-invocation model overrides, but no agent instruction, persona directive, or workflow template required dispatchers to select a model or err on the side of cheaper models.
3. Review templates and supervisor persona instructions explicitly named Gemini model identifiers (`flash`, `flash_lite`, `pro`) in contexts where the dispatch tool required Claude model identifiers (`haiku`, `sonnet`, `opus`), creating parameter incompatibility.
4. While batch container workers enforce model defaults, in-session subagent dispatches remained unconstrained.

### 2.2 Root Cause Analysis

1. **Absence of a Resource Conservation Rule:** The framework enforcement doctrine contained no general rule mandating resource conservation or cost-aware model matching during in-session dispatch.
2. **Missing Imperative Instructions at Dispatch Boundaries:** Dispatching agents lacked explicit instructions in their persona definitions to assess task complexity and pass a cost-minimized model parameter on dispatch.
3. **Model Name Drift Across Environments:** Workflow templates and review instructions hardcoded specific vendor model names that did not match the invocation parameters of the active dispatch harness.

## 3. The Operative Rule: In-Session Resource Conservation and Model Matching

> **Operative Rule:**
> Every interactive agent that dispatches an in-session subagent must evaluate task complexity and explicitly set the subagent's model parameter to the cheapest tier that suffices for the requested task. Erring on the side of cheaper models is mandatory:
>
> 1. **Light / Cheap Tier:** Used for read-only repository or filesystem lookups, factual disambiguation, syntax formatting, exploratory search, single-pass sanity checks, and routine questions.
> 2. **Standard / Workhorse Tier:** Used for standard multi-file implementations, component refactoring, test suite authoring, and standard dialectical review passes.
> 3. **Flagship / High-Capability Tier:** Reserved strictly for high-stakes architectural design, multi-round dialectical reconciliation across competing requirements, novel protocol synthesis, and deep strategic ambiguity.
>
> Relying on unconfirmed parent defaults or dispatching routine subagent tasks on flagship models without explicit operational justification is a violation of `proportionate` and the resource conservation rule.

## 4. Enforcement-Map Extract

The table below records the pre-change baseline versus the target enforcement state:

| Rule / Nudge | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| **Pre-Change (Current Baseline)**: Resource conservation and model matching on in-session dispatch | `doctrine only` | `advisory` (unmapped) | No entry in `specs/ENFORCEMENT-MAP.md` (unenforced). In-session subagents inherit parent flagship models by default. Workflow templates name mismatched vendor model tiers. |
| **Post-Change (Target Enforcement)**: Resource Conservation: In-Session Subagent Model Matching | `instructions` | `imperative` | Target files in `plugins/ida/`: Persona instructions (`ida.md`, `james.md`, `sara.md`), core definitions (`CORE.md`), and workflow templates (`strategic-review/SKILL.md`, `wf-review.md`, `wf-dialectical-design.md`, `pull/SKILL.md`). Mandates matching subagent model tier to task complexity, defaulting to cheapest sufficient model. |

## 5. Target Surfaces and File Locations

The model-matching instruction operates across eight specific surfaces:

1. **Shared Core (`plugins/ida/CORE.md`):**
   - Under execution rules, establishes the framework-wide invariant that all in-session subagent dispatches must explicitly supply a model parameter matched to task complexity, erring on cheaper models.
2. **Interactive Front Persona (`plugins/ida/agents/ida.md`):**
   - In ask routing and internal subagent spawning, mandates selecting the light tier (`haiku` / cheap) for internal search, lookups, and diagnostic questions.
3. **Lead Executor and Review Supervisor (`plugins/ida/agents/james.md`):**
   - In team delegation and dialectical review supervision, mandates setting model tiers according to calibrated proportionality (light tier for routine sanity checks, standard tier for typical tasks, flagship tier reserved for high-stakes architectural disputes).
4. **Headless Dispatcher (`plugins/ida/agents/sara.md`):**
   - In worker and lookup dispatching, mandates specifying the cheapest model tier that suffices for each dispatched subagent.
5. **Strategic Review Skill (`plugins/ida/skills/strategic-review/SKILL.md`):**
   - In supervisor calibration, replaces mismatched vendor model strings with runtime-supported model parameter options, defaulting to light models for single-pass checks.
6. **Universal Review Workflow (`plugins/ida/skills/workflow-library/workflows/wf-review.md`):**
   - In the shared review briefing and composite stages, reconciles model selection to functional tiers with runtime mappings.
7. **Dialectical Design Workflow (`plugins/ida/skills/workflow-library/workflows/wf-dialectical-design.md`):**
   - In supervisor calibration, updates model selection options to functional tiers and runtime parameters.
8. **Task Claiming and Execution Skill (`plugins/ida/skills/pull/SKILL.md`):**
   - In subagent coordination, instructs the claiming agent to match subagent models to task requirements, erring on cheaper models.

## 6. Model Tier Reconciliation Across Runtimes

Existing instructions contain vendor-specific model identifiers that cannot be passed to the dispatch tool in Claude Code. To maintain cross-runtime clarity without brittle version locks, the design reconciles model selection through functional tiers mapped to harness-supported parameters:

| Functional Tier | Target Workload | Claude Code Dispatch Parameter (`Agent` tool) | Antigravity Dispatch Parameter (`invoke_subagent`) |
| :- | :- | :- | :- |
| **Light / Cheap** | Read-only lookups, searches, single-pass sanity checks, quick questions | `haiku` | `flash_lite` (or `flash`) |
| **Standard / Workhorse** | Code implementation, test creation, standard reviews, synthesis | `sonnet` | `flash` (or `pro`) |
| **Flagship / High-Capability** | High-stakes architecture, multi-round dialectics, deep ambiguity | `opus` | `pro` |

In instruction text, references must either name functional tiers with clear harness mappings or supply the harness-appropriate parameter directly, eliminating bare references to vendor tiers where they cannot be selected. In accordance with standing framework naming doctrine, instructions calling for the top tier refer to "the flagship model" rather than pinning specific model version numbers.

## 7. Enforcement Pyramid and Proportionality Analysis

Per `specs/enforcement/enforcement.md`, interventions are evaluated from least-invasive to most-invasive:

1. **`doctrine only`**: Evaluated and rejected. Unwritten expectations failed to prevent expensive model inheritance.
2. **`instructions` (`imperative`)**: **Selected as the winning mechanism.** Clear imperative instructions at the persona and workflow level directly shape agent decision-making at dispatch time. Instructions represent the least invasive, most adaptable mechanism, carrying zero runtime performance penalty and avoiding fragile programmatic wrappers.
3. **`JIT injection`**: Evaluated and deferred. Dynamic prompt injection on dispatch tool hooks would add token overhead to every turn. If imperative instructions fail to achieve consistent compliance, JIT reminders on `PreToolUse` for dispatch tools can be considered.
4. **`structural`**: Evaluated and rejected. A mechanical validation hook blocking dispatch calls that omit model overrides or reject specific models would violate `judgment-non-delegable`, as determining whether a task is "complex" requires qualitative semantic understanding.
5. **`process` (`required gate`)**: Retained as verification. Dialectical review verifies that instructions and workflows comply with resource conservation doctrine.
6. **`post-hoc` (`observability`)**: Retained. Phoenix OpenTelemetry traces record model usage and token spend per dispatch span, enabling empirical cost tracking.

## 8. Next Escalation Step

If empirical cost monitoring reveals that token spend remains excessive during large-context document analysis or repository-wide reading, the next proportional escalation is:

- **Reinstate an in-session agy tool**: Authorize an in-session tool allowing the interactive front agent to delegate large-text queries and whole-document searches to Gemini via Antigravity, leveraging large context windows and low-cost cached reads.

## 9. Outcome-Level Build Criteria for Downstream Implementation

Downstream implementation task must satisfy the following verifiable build criteria:

- **BC-1 (Persona Instructions Updated):** The agent personas (`ida.md`, `james.md`, `sara.md`) and `CORE.md` carry the imperative instruction to match subagent models to task complexity on every in-session dispatch, defaulting to the cheapest sufficient model tier.
- **BC-2 (Workflow Templates Reconciled):** The dispatch skills and review workflow templates (`strategic-review/SKILL.md`, `wf-review.md`, `wf-dialectical-design.md`, `pull/SKILL.md`) specify valid, harness-selectable model parameters matching functional tiers, with zero unmapped vendor parameters.
- **BC-3 (No Invalid Model Tiers):** Verification via repository search confirms that zero occurrences remain in `plugins/ida/` of instructions directing an agent to select an unsupported model tier in the dispatch tool.
- **BC-4 (Enforcement Map Updated):** `specs/ENFORCEMENT-MAP.md` contains the new row under Agent instructions for resource conservation and model matching, citing all touched files, mechanism (`instructions`), severity (`imperative`), empirical failure context, and the next escalation step.
