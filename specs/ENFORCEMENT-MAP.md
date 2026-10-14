---
id: enforcement_map
---

# Enforcement map

Current state list of measures in place to shape agent behavior per axiom.

| Rule                                                                                                                                                                                                                   | Mechanism | Severity | Detail |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | -------- | ------ |
| [Axiom: Categorical Imperative](../plugins/rbg/axioms/categorical-imperative.md) -- All actions must be justified as the application of a general rule covering all similar cases.                                     |           |          |        |
| [Axiom: Cite Sources (No Plagiarism)](../plugins/rbg/axioms/cite-sources.md) -- Attribute every non-trivial claim to an explicit source; never strip or separate citations.                                            |           |          |        |
| [Axiom: Closure (No Other Truths)](../plugins/rbg/axioms/closure.md) -- Derive all material decisions strictly from axioms, instructions, or directives; halt on conflict or silence.                                  |           |          |        |
| [Axiom: Costly Ops Approval](../plugins/rbg/axioms/costly-ops-approval.md) -- Operations with unbounded cost or blast radius require explicit prior approval naming scope and volume.                                  |           |          |        |
| [Axiom: Data Boundaries](../plugins/rbg/axioms/data-boundaries.md) -- Never emit private or identifying data across trust boundaries without authorization; scrub before transmission.                                 |           |          |        |
| [Axiom: Delay Decisions](../plugins/rbg/axioms/delay-decisions.md) -- Defer actions and decisions that can be postponed without compounding cost, expiring options, or blocking ready work.                            |           |          |        |
| [Axiom: Do One Thing](../plugins/rbg/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, then return; do not exceed authority.                                                  |           |          |        |
| [Axiom: Durable Capture](../plugins/rbg/axioms/durable-capture.md) -- Capture knowledge not verdicts; update rather than duplicate in the knowledge base.                                                              |           |          |        |
| [Axiom: Research Data Immutable](../plugins/rbg/axioms/evidence-immutable.md) -- Never alter, reformat, convert, or substitute research datasets or records in place; transformations must be versioned and auditable. |           |          |        |
| [Axiom: Excellence](../plugins/rbg/axioms/excellence.md) -- Excellence is the standard; compliance is the floor.                                                                                                       |           |          |        |
| [Axiom: Exercise Authority](../plugins/rbg/axioms/exercise-authority.md) -- Exercise judgment decisively within delegated authority; do not create un-delegated friction or ask permission.                            |           |          |        |
| [Axiom: Fail-Fast](../plugins/rbg/axioms/fail-fast.md) -- Halt and escalate on any infrastructure failure, conflict, or unconfirmed default; no workarounds.                                                           |           |          |        |
| [Axiom: Full Observability](../plugins/rbg/axioms/full-observability.md) -- Persist material actions in git commits with clear rationale for complete auditability.                                                    |           |          |        |
| [Axiom: Halt on Failure](../plugins/rbg/axioms/halt-on-failure.md) -- Halt immediately and surface failures verbatim when any instruction, tool, dependency, or validation fails.                                      |           |          |        |
| [Axiom: Honest Epistemics (Don't Make Shit Up)](../plugins/rbg/axioms/honest-epistemics.md) -- If you don't know, say so; tailor claims strictly to available evidence; negative claims require exhaustive search.     |           |          |        |
| [Axiom: Judgment Is Non-Delegable](../plugins/rbg/axioms/judgment-non-delegable.md) -- Never substitute deterministic techniques (regex, substring, heuristics) for semantic qualitative judgment; use LLMs.           |           |          |        |
| [Axiom: Proportionate](../plugins/rbg/axioms/proportionate.md) -- Build the least that meets the request; guard a risk by its likelihood × consequence.                                                                |           |          |        |
| [Axiom: Single Source of Truth](../plugins/rbg/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact.                                                          |           |          |        |

## Evidence contract

Every measure that enforces the [evidence contract](enforcement/evidence-contract.md) on reports passed between agents. Under **State**:

- **in place:** on `dev`.
- **decided:** approved design, to be built (`aops_d26b4416`).
- **remove:** in place now, to be taken out (`aops_d26b4416`).
- **unwired:** kept in the code, not registered.
- **future:** an escalation option, not built. These are listed in escalation order, and each is built only when verdict telemetry shows the level below it failing: PASS near 100%, with REVISE rare.
- **gap:** nothing covers it.

| Measure                                                                                   | Carrier                                      | Applies to                 | Severity          | State    |
| ----------------------------------------------------------------------------------------- | -------------------------------------------- | -------------------------- | ----------------- | -------- |
| Report format, basis vocabulary, verdict tokens, verdict command, kickback rule           | `premise-check` skill                        | All agents                 | Guidance          | in place |
| Observed-value rule and contrast test                                                     | `premise-check` skill                        | Report writers / receivers | Guidance          | decided  |
| Report argument in the task handback                                                      | `/pull`, `/dump`                             | Task workers               | Guidance          | in place |
| `/verify` uses `/dump`'s envelope, with Receipts per the skill                            | `/verify` skill                              | QA reviewers               | Guidance          | decided  |
| Restated format rules replaced by a pointer to the skill                                  | `sara.md`, `/pull` §3, `ida.md`              | Sara, workers, Ida         | Guidance          | decided  |
| Ida's role: formal checking and attention protection; substance checks prohibited         | `ida.md`                                     | Ida                        | Guidance          | decided  |
| Session-wide one-line pointer                                                             | `SessionStart` (startup, resume, compact)    | All agents                 | Reminder          | decided  |
| Reply-format reminder (`honesty.md`)                                                      | `UserPromptSubmit`, peer envelope            | All agents                 | Reminder          | decided  |
| `honesty.md` in the `search_the_pkb` fallback                                             | `UserPromptSubmit`                           | All but Sara, James        | Reminder          | remove   |
| `honesty.md` in the channel-reply gate (keep `quiet.md` only)                             | `PreToolUse`, channel reply                  | Ida                        | Block once        | remove   |
| Check reminder (`hearsay.md`) on a peer envelope                                          | `UserPromptSubmit`                           | Ida, Sara                  | Reminder          | in place |
| Check reminder (`hearsay.md`) on a foreground subagent result                             | `PostToolUse` on `Agent`                     | Ida, Sara                  | Reminder          | decided  |
| Gate arms on a peer envelope                                                              | `UserPromptSubmit`                           | Ida, Sara                  | Friction          | in place |
| Gate arms on a foreground subagent result                                                 | `PostToolUse` on `Agent`                     | Ida, Sara                  | Friction          | decided  |
| Gate arms on any dispatch, including background launch                                    | `PostToolUse`, `PostToolBatch`               | Ida, Sara                  | Friction          | remove   |
| Gate refuses `Agent`, `Task`, `invoke_subagent`, `SendMessage`, `AskUserQuestion`, `Dump` | `PreToolUse`                                 | Ida, Sara                  | Refuse            | in place |
| Gate refuses channel reply tools                                                          | `PreToolUse`                                 | Ida, Sara                  | Refuse            | decided  |
| Gate blocks `Stop` once per chain                                                         | `Stop`                                       | Ida, Sara                  | Block             | in place |
| Gate messages at most two lines (agent) and one line (user), naming claim and skill       | `premise_check_handler`, `premise_check_arm` | Ida, Sara                  | Friction          | decided  |
| Verdict command with `--verdict PASS` pre-filled                                          | `premise_check_gate.py`                      | Ida, Sara                  | Friction          | remove   |
| Verdict recording and span                                                                | `verdict.py`, `premise_check_verdict.py`     | Ida, Sara                  | Record            | in place |
| Gate modes and override variables                                                         | Environment                                  | Ida, Sara                  | Config            | in place |
| No named or persistent subagents for middle-level agents                                  | Settings files                               | Ida, Prime, Sara, Pauli    | Prevention        | decided  |
| `release_task` required fields, presence-only, on tasks created after the check shipped   | PKB server                                   | Task workers               | Prevention        | in place |
| Substance check: the reviewer opens each pointer and confirms it supports its claim       | Workflow steps, `/verify`                    | QA reviewers               | Verdict (agentic) | in place |
| Container-worker handbacks read from the task record arm no gate                          | None                                         | Sara                       | --                | gap      |
| `honest_output`                                                                           | `Stop`                                       | All agents                 | Block once        | unwired  |
| `be_quiet`                                                                                | `Stop`                                       | Ida                        | Block once        | unwired  |
| Reminder sent back to a subagent before its report is delivered                           | `SubagentStop`                               | Subagents                  | Block once        | future   |
| Fenced `argdown` block required in a subagent's final message                             | `SubagentStop`                               | Subagents                  | Block once        | future   |
| Verdict refused without a reconstruction file that parses                                 | `verdict.py`                                 | Ida, Sara                  | Refuse            | future   |
| Separate checker agent on arrival                                                         | Hook-spawned agent                           | Ida, Sara                  | Verdict (agentic) | future   |
