---
id: enforcement_map
---

# Enforcement map

Current state list of measures in place to shape agent behavior per axiom.

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Axiom: Categorical Imperative](../plugins/rbg/axioms/categorical-imperative.md) -- All actions must be justified as the application of a general rule covering all similar cases. |  |  |  |
| [Axiom: Cite Sources (No Plagiarism)](../plugins/rbg/axioms/cite-sources.md) -- Attribute every non-trivial claim to an explicit source; never strip or separate citations. |  |  |  |
| [Axiom: Closure (No Other Truths)](../plugins/rbg/axioms/closure.md) -- Derive all material decisions strictly from axioms, instructions, or directives; halt on conflict or silence. |  |  |  |
| [Axiom: Costly Ops Approval](../plugins/rbg/axioms/costly-ops-approval.md) -- Operations with unbounded cost or blast radius require explicit prior approval naming scope and volume. |  |  |  |
| [Axiom: Data Boundaries](../plugins/rbg/axioms/data-boundaries.md) -- Never emit private or identifying data across trust boundaries without authorization; scrub before transmission. |  |  |  |
| [Axiom: Delay Decisions](../plugins/rbg/axioms/delay-decisions.md) -- Defer actions and decisions that can be postponed without compounding cost, expiring options, or blocking ready work. |  |  |  |
| [Axiom: Do One Thing](../plugins/rbg/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, then return; do not exceed authority. |  |  |  |
| [Axiom: Durable Capture](../plugins/rbg/axioms/durable-capture.md) -- Capture knowledge not verdicts; update rather than duplicate in the knowledge base. |  |  |  |
| [Axiom: Research Data Immutable](../plugins/rbg/axioms/evidence-immutable.md) -- Never alter, reformat, convert, or substitute research datasets or records in place; transformations must be versioned and auditable. |  |  |  |
| [Axiom: Excellence](../plugins/rbg/axioms/excellence.md) -- Excellence is the standard; compliance is the floor. |  |  |  |
| [Axiom: Exercise Authority](../plugins/rbg/axioms/exercise-authority.md) -- Exercise judgment decisively within delegated authority; do not create un-delegated friction or ask permission. |  |  |  |
| [Axiom: Fail-Fast](../plugins/rbg/axioms/fail-fast.md) -- Halt and escalate on any infrastructure failure, conflict, or unconfirmed default; no workarounds. |  |  |  |
| [Axiom: Full Observability](../plugins/rbg/axioms/full-observability.md) -- Persist material actions in git commits with clear rationale for complete auditability. |  |  |  |
| [Axiom: Halt on Failure](../plugins/rbg/axioms/halt-on-failure.md) -- Halt immediately and surface failures verbatim when any instruction, tool, dependency, or validation fails. |  |  |  |
| [Axiom: Honest Epistemics (Don't Make Shit Up)](../plugins/rbg/axioms/honest-epistemics.md) -- If you don't know, say so; tailor claims strictly to available evidence; negative claims require exhaustive search. |  |  |  |
| [Axiom: Judgment Is Non-Delegable](../plugins/rbg/axioms/judgment-non-delegable.md) -- Never substitute deterministic techniques (regex, substring, heuristics) for semantic qualitative judgment; use LLMs. |  |  |  |
| [Axiom: Proportionate](../plugins/rbg/axioms/proportionate.md) -- Build the least that meets the request; guard a risk by its likelihood × consequence. |  |  |  |
| [Axiom: Reasons](../plugins/rbg/axioms/reasons.md) -- Give written, parseable reasons for every claim you rely on or communicate; the format lives in `premise-check`. |  |  |  |
| [Axiom: Single Source of Truth](../plugins/rbg/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact. |  |  |  |

## Evidence contract

Measures in place that enforce the [evidence contract](enforcement/evidence-contract.md). The full design and escalation path are in [evidence-contract-enforcement.md](enforcement/evidence-contract-enforcement.md).

| Measure | Carrier | Applies to | Severity |
| - | - | - | - |
| Report format, basis vocabulary, observed-value rule, contrast test, verdict tokens, verdict command, return | `premise-check` skill | All agents | Guidance |
| Report argument in the task handback and QA review | `/pull`, `/dump`, `/verify` | Task workers, QA reviewers | Guidance |
| Pointer to `premise-check` (no restated format rules) | `sara.md`, `/pull` §3, `ida.md` | Sara, workers, Ida | Guidance |
| Ida's role: formal checking and attention protection; substance checks prohibited | `ida.md` | Ida | Guidance |
| Session-wide one-line pointer | `SessionStart` (startup, resume, compact) | All agents | Reminder |
| Reply-format reminder (`honesty.md`) on a peer envelope | `UserPromptSubmit`, peer envelope | All agents | Reminder |
| Check reminder (`hearsay.md`) on a peer envelope or foreground subagent result | `UserPromptSubmit` (peer envelope), `PostToolUse` on `Agent` | Ida, Sara | Reminder |
| Gate arms on an incoming peer message or completion notification, not on a foreground subagent result | `UserPromptSubmit` (peer or task-notification envelope) | Ida, Sara | Friction |
| Gate refuses `Agent`, `Task`, `invoke_subagent`, `SendMessage`, `AskUserQuestion`, `Dump`, channel replies | `PreToolUse` | Ida, Sara | Refuse |
| Gate blocks `Stop` once per chain | `Stop` | Ida, Sara | Block |
| Gate messages two lines (agent: claim and skill, then the verdict command with no pre-filled verdict) and one line (user, no command) | `premise_check_handler`, `premise_check_arm` | Ida, Sara | Friction |
| Verdict recording and span | `verdict.py`, `premise_check_verdict.py` | Ida, Sara | Record |
| Gate modes and override variables | Environment | Ida, Sara | Config |
| No named or persistent subagents for middle-level agents | Settings files (dotfiles, outside this repo); expected `"teammateMode": "in-process"` | Ida, Prime, Sara, Pauli | Prevention |
| `release_task` required fields, presence-only, on tasks created after the check shipped | PKB server | Task workers | Prevention |
| Substance check: the reviewer opens each pointer and confirms it supports its claim | [Workflow](enforcement/workflow.md) steps 3-4, `/verify` | QA reviewers | Verdict (agentic) |
