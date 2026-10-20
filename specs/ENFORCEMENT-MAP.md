---
id: enforcement_map
---

# Enforcement map

Current state list of measures in place to shape agent behavior per axiom.

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Axiom: Categorical Imperative](../plugins/rbg/skills/axioms/categorical-imperative.md) -- All actions must be justified as the application of a general rule covering all similar cases. |  |  |  |
| [Axiom: Cite Sources (No Plagiarism)](../plugins/rbg/skills/axioms/cite-sources.md) -- Attribute every non-trivial claim to an explicit source; never strip or separate citations. |  |  |  |
| [Axiom: Closure (No Other Truths)](../plugins/rbg/skills/axioms/closure.md) -- Derive all material decisions strictly from axioms, instructions, or directives; halt on conflict or silence. |  |  |  |
| [Axiom: Costly Ops Approval](../plugins/rbg/skills/axioms/costly-ops-approval.md) -- Operations with unbounded cost or blast radius require explicit prior approval naming scope and volume. |  |  |  |
| [Axiom: Data Boundaries](../plugins/rbg/skills/axioms/data-boundaries.md) -- Never emit private or identifying data across trust boundaries without authorization; scrub before transmission. |  |  |  |
| [Axiom: Delay Decisions](../plugins/rbg/skills/axioms/delay-decisions.md) -- Defer actions and decisions that can be postponed without compounding cost, expiring options, or blocking ready work. |  |  |  |
| [Axiom: Do One Thing](../plugins/rbg/skills/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, then return; do not exceed authority. |  |  |  |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts; update rather than duplicate in the knowledge base. |  |  |  |
| [Axiom: Research Data Immutable](../plugins/rbg/skills/axioms/evidence-immutable.md) -- Never alter, reformat, convert, or substitute research datasets or records in place; transformations must be versioned and auditable. |  |  |  |
| [Axiom: Excellence](../plugins/rbg/skills/axioms/excellence.md) -- Excellence is the standard; compliance is the floor. |  |  |  |
| [Axiom: Exercise Authority](../plugins/rbg/skills/axioms/exercise-authority.md) -- Exercise judgment decisively within delegated authority; do not create un-delegated friction or ask permission. |  |  |  |
| [Axiom: Fail-Fast](../plugins/rbg/skills/axioms/fail-fast.md) -- Halt and escalate on any infrastructure failure, conflict, or unconfirmed default; no workarounds. |  |  |  |
| [Axiom: Full Observability](../plugins/rbg/skills/axioms/full-observability.md) -- Persist material actions in git commits with clear rationale for complete auditability. |  |  |  |
| [Axiom: Halt on Failure](../plugins/rbg/skills/axioms/halt-on-failure.md) -- Halt immediately and surface failures verbatim when any instruction, tool, dependency, or validation fails. |  |  |  |
| [Axiom: Honest Epistemics (Don't Make Shit Up)](../plugins/rbg/skills/axioms/honest-epistemics.md) -- If you don't know, say so; tailor claims strictly to available evidence; negative claims require exhaustive search. |  |  |  |
| [Axiom: Judgment Is Non-Delegable](../plugins/rbg/skills/axioms/judgment-non-delegable.md) -- Never substitute deterministic techniques (regex, substring, heuristics) for semantic qualitative judgment; use LLMs. |  |  |  |
| [Axiom: Proportionate](../plugins/rbg/skills/axioms/proportionate.md) -- Build the least that meets the request; guard a risk by its likelihood × consequence. |  |  |  |
| [Axiom: Reasons](../plugins/rbg/skills/axioms/reasons.md) -- Give written, parseable reasons for every claim you rely on or communicate; the format lives in `premise-check`. |  |  |  |
| [Axiom: Single Source of Truth](../plugins/rbg/skills/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact. |  |  |  |

## Evidence contract

Measures in place that enforce the [evidence contract](enforcement/evidence-contract.md). The full design and escalation path are in [evidence-contract-enforcement.md](enforcement/evidence-contract-enforcement.md).

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Every evidence-backed report ends in the report argument: asks by immutable id, premises with their basis in words, warrants with their defeaters, every ask answered by id, every relayed sentence naming its line. | `instructions` | `imperative` | `plugins/ida/skills/premise-check/SKILL.md:12-29`; line shapes `references/report-form.md:26-35`; basis phrases and format items `references/vocabulary.toml`. All agents. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- No premise count: every premise on an inference line is a condition of its rule; avoid laundry lists. | `instructions` | `advisory` | `plugins/ida/skills/premise-check/SKILL.md:24`. All agents. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Source-opening prohibited: the checker takes an observed premise with a pointer as given and never opens a pointer or redoes the work; it judges every warrant, step and scope. | `instructions` | `absolute` | `plugins/ida/skills/premise-check/SKILL.md:33`. Ida, Sara. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Sufficiency testing required: four tests on every inference line (valid, supported, answered, sufficient); a format breach is waivable, an untested inference never passes. | `instructions` | `imperative` | `plugins/ida/skills/premise-check/SKILL.md:10`, `:35-50`. Ida, Sara. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Record every verdict with the seven-line checker's reason. | `instructions` | `imperative` | `plugins/ida/skills/premise-check/SKILL.md:52-64`; `references/checker-reason.md:1-27`. Ida, Sara. |
| [Persona: Ida](../plugins/ida/agents/ida.md) -- Check each report's argument by the four tests, sufficiency included, and protect the user's attention; source-opening prohibited. | `instructions` | `imperative` | `plugins/ida/agents/ida.md:12`, `:23-24`. Ida. |
| [Persona: Sara](../plugins/ida/agents/sara.md) -- Check each worker report by the four tests and synthesise a checked report argument; workers inspect sources, Sara does not. | `instructions` | `imperative` | `plugins/ida/agents/sara.md:16`, `:20`. Sara. |
| [Skill: dump](../plugins/ida/skills/dump/SKILL.md) -- The task handback and QA review carry a report argument written per `premise-check`. | `instructions` | `imperative` | `plugins/ida/skills/pull/SKILL.md:24`; `plugins/ida/skills/dump/SKILL.md:21`, `:65`; `plugins/ida/skills/verify/SKILL.md:68`. Task workers, QA reviewers. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Session-wide one-line pointer to the skill. | `JIT injection` | -- | `session_start` (`plugins/ida/hooks/handlers.py:482-488`) on `SessionStart` (startup, resume, compact). All agents. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- A reply to a peer message is a report written per the skill. | `JIT injection` | -- | `honesty_on_peer_message` (`plugins/ida/hooks/handlers.py:521`), `messages/honesty.md`, on `UserPromptSubmit` with a peer envelope. All agents. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Check an arrived report before acting on it. | `JIT injection` | -- | `rule_against_hearsay` (`plugins/ida/hooks/handlers.py:528`), `messages/hearsay.md`, on `UserPromptSubmit` (peer envelope) and `PostToolUse` on `Agent`. Ida, Sara. |
| [Spec: evidence contract enforcement](enforcement/evidence-contract-enforcement.md) -- The gate arms on a peer envelope or a foreground subagent result, storing the judged text and its reference. | `structural` | `friction` | `premise_check_arm` on `UserPromptSubmit` (peer envelope) and `PostToolUse` on `Agent`. Ida, Sara. |
| [Spec: evidence contract enforcement](enforcement/evidence-contract-enforcement.md) -- While armed, the gate refuses `Agent`, `Task`, `invoke_subagent`, `SendMessage`, `AskUserQuestion`, `Dump` and channel replies. | `structural` | `block` | `premise_check_handler` on `PreToolUse`. `PREMISE_CHECK_GATE_MODE=warn` lowers it to `warning`, `off` disables it; `PREMISE_CHECK_OVERRIDE`, `PREMISE_CHECK_GATE_OVERRIDE`, `AOP_FORCE`, `AOP_OVERRIDE` release it. Ida, Sara. |
| [Spec: evidence contract enforcement](enforcement/evidence-contract-enforcement.md) -- While armed, the gate blocks `Stop` once per chain. | `structural` | `block` | `premise_check_handler` on `Stop`. Ida, Sara. |
| [Spec: evidence contract enforcement](enforcement/evidence-contract-enforcement.md) -- Gate messages are two lines for the agent (claim and skill, then the verdict command with no pre-filled verdict) and one line for the user. | `JIT injection` | -- | `premise_check_handler`, `premise_check_arm`. Ida, Sara. |
| [Skill: premise-check](../plugins/ida/skills/premise-check/SKILL.md) -- Enforcement level B: the recorder refuses PASS unless the reason carries the seven keyed lines and passes the mechanical cross-checks against the judged block; a no-claim reason is accepted and marked; REVISE and FAIL take any reason. | `process` | `required gate` | `record_verdict` in `plugins/ida/hooks/premise_check_verdict.py`, run by `skills/premise-check/scripts/verdict.py`; checks listed at `references/checker-reason.md:29-43`, no-claim at `:45-47`. Ida, Sara. |
| [Spec: evidence contract enforcement](enforcement/evidence-contract-enforcement.md) -- Each verdict emits one span carrying one attribute per reason line, the ask ids, weakest basis, inference count, defect tags, no-claim flag and judged-text reference; a failed export records no verdict and leaves the gate armed. | `post-hoc` | `observability` | `record_verdict` and `emit_verdict_span` in `plugins/ida/hooks/premise_check_verdict.py`; span `premise_check_verdict`. Ida, Sara. |
| No named or persistent subagents for middle-level agents. | `structural` | `protection` | Settings files (dotfiles, outside this repo); expected `"teammateMode": "in-process"`. Ida, Prime, Sara, Pauli. |
| `release_task` carries its required fields, presence-only, on tasks created after the check shipped. | `structural` | `block` | PKB server (outside this repo). Task workers. |
| [Spec: workflow](enforcement/workflow.md) -- At boundary check and QA-around, the reviewer opens each pointer and confirms it supports its claim. | `process` | `advisory check` | `specs/enforcement/workflow.md:69-73`; `/verify`. QA reviewers. |
