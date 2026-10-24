---
id: enforcement_map
---

# Enforcement map

Current state list of measures in place to shape agent behavior per axiom.

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Axiom: Categorical Imperative](../plugins/rbg/skills/axioms/categorical-imperative.md) -- All actions must be justified as the application of a general rule covering all similar cases. |  |  |  |
| [Axiom: Cite Sources (No Plagiarism)](../plugins/rbg/skills/axioms/cite-sources.md) -- Attribute every non-trivial claim to an explicit source; restatements judged by meaning and distinctions; directions checked for derivation from the ask and refused on mismatch. | instructions | imperative | `plugins/rbg/skills/axioms/cite-sources.md:13-14`: When sending a direction, attach a short citation; restatements are judged by fidelity to meaning and distinctions; on receiving a direction, verify derivation from quoted user words and authority, and refuse any request that does not fit the ask. Observation: Senders cite authorising asks; receivers verify derivation and refuse mismatches (#3086, #3087). |
| [Axiom: Closure (No Other Truths)](../plugins/rbg/skills/axioms/closure.md) -- Derive all material decisions strictly from axioms, instructions, or directives; halt on conflict or silence. |  |  |  |
| [Axiom: Costly Ops Approval](../plugins/rbg/skills/axioms/costly-ops-approval.md) -- Operations with unbounded cost or blast radius require explicit prior approval naming scope and volume. |  |  |  |
| [Axiom: Data Boundaries](../plugins/rbg/skills/axioms/data-boundaries.md) -- Never emit private or identifying data across trust boundaries without authorization; scrub before transmission. |  |  |  |
| [Axiom: Delay Decisions](../plugins/rbg/skills/axioms/delay-decisions.md) -- Defer actions and decisions that can be postponed without compounding cost, expiring options, or blocking ready work. |  |  |  |
| [Axiom: Do One Thing](../plugins/rbg/skills/axioms/do-one-thing.md) -- Execute precisely the requested task to the specified standard, then return; do not exceed authority. |  |  |  |
| [Axiom: Durable Capture](../plugins/rbg/skills/axioms/durable-capture.md) -- Capture knowledge not verdicts; update rather than duplicate in the knowledge base. |  |  |  |
| [Axiom: Research Data Immutable](../plugins/rbg/skills/axioms/evidence-immutable.md) -- Never alter, reformat, convert, or substitute research datasets or records in place; transformations must be versioned and auditable. |  |  |  |
| [Axiom: Explanations Are Not Reasons](../plugins/rbg/skills/axioms/explanations-not-reasons.md) -- An agent's explanation of what it did is not its reason; self-reports are hearsay and never taken at face value. | instructions | imperative | `plugins/rbg/skills/axioms/explanations-not-reasons.md:10-12`: Never accept an agent's stated reason at face value. Establish root causes from external evidence, never from self-reported intent or interpretation. Observation: Diagnoses and audits treat self-explanations as hearsay and require external runtime evidence. |
| [Axiom: Excellence](../plugins/rbg/skills/axioms/excellence.md) -- Excellence is the standard; compliance is the floor. |  |  |  |
| [Axiom: Exercise Authority](../plugins/rbg/skills/axioms/exercise-authority.md) -- Exercise judgment decisively within delegated authority; do not create un-delegated friction or ask permission. |  |  |  |
| [Axiom: Fail-Fast](../plugins/rbg/skills/axioms/fail-fast.md) -- Halt and escalate on any infrastructure failure, conflict, or unconfirmed default; no workarounds. |  |  |  |
| [Axiom: Full Observability](../plugins/rbg/skills/axioms/full-observability.md) -- Persist material actions in git commits with clear rationale for complete auditability. |  |  |  |
| [Axiom: Halt on Failure](../plugins/rbg/skills/axioms/halt-on-failure.md) -- Halt immediately and surface failures verbatim when any instruction, tool, dependency, or validation fails. |  |  |  |
| [Axiom: Honest Epistemics (Don't Make Shit Up)](../plugins/rbg/skills/axioms/honest-epistemics.md) -- If you don't know, say so; tailor claims strictly to available evidence; negative claims require exhaustive search; incident diagnosis treats agent self-account as hearsay and searches existing controls. | instructions | imperative | `plugins/ida/skills/learn/SKILL.md:19,23`: Treat an agent's account of its causes as hearsay; search for existing controls governing the failure class before diagnosing verification misses. Observation: Learn investigates primary records rather than adopting caller framing (#3088). |
| [Axiom: Judgment Is Non-Delegable](../plugins/rbg/skills/axioms/judgment-non-delegable.md) -- Never substitute deterministic techniques (regex, substring, heuristics) for semantic qualitative judgment; use LLMs. |  |  |  |
| [Axiom: Proportionate](../plugins/rbg/skills/axioms/proportionate.md) -- Build the least that meets the request; guard a risk by its likelihood × consequence. | instructions | imperative | `plugins/ida/agents/pauli.md:51`: Whenever queuing a task, follow-ups included, Pauli makes a quick judgment without investigating on effort vs benefit and user ask/strategic fit; scales down or rejects with reasons. Observation: Pauli rejects or scales down disproportionate tasks with reported reasons without investigating. |
| [Axiom: Reasons](../plugins/rbg/skills/axioms/reasons.md) -- Give written, parseable reasons for every claim you rely on or communicate; format in `premise-check`; relaying a report upward requires its premise-check verdict. | instructions | imperative | `plugins/ida/skills/premise-check/SKILL.md:23`: Relaying a report upward requires its premise-check verdict. Observation: Unchecked reports are not relayed upward (#3087). |
| [Axiom: Single Source of Truth](../plugins/rbg/skills/axioms/single-source-of-truth.md) -- Maintain exactly one authoritative copy of every fact, rule, or artifact. |  |  |  |

## Agent instructions

Measures in place in agent definitions and instruction files to steer persona behavior.

| Rule | Mechanism | Severity | Detail |
| - | - | - | - |
| [Persona: Pauli](../plugins/ida/agents/pauli.md) -- Proportionality check on queuing: quick judgment on effort vs benefit and user ask / strategic fit before queuing tasks or follow-ups. | instructions | imperative | `plugins/ida/agents/pauli.md:51`: Whenever queuing a task, follow-ups included, Pauli makes a quick judgment without investigating on effort vs benefit and user ask/strategic fit; scales down or rejects with reasons. Observation: Pauli rejects or scales down disproportionate tasks with reported reasons without investigating. |
| [Persona: Ida](../plugins/ida/agents/ida.md) -- Requests to Pauli must state the user's initial ask and the project's strategic fit. | instructions | imperative | `plugins/ida/agents/ida.md:45`: Every request Ida sends to Pauli states the user's initial ask and the project's strategic fit. Observation: Requests sent from Ida to Pauli state the user's initial ask and the project's strategic fit. |
| [Persona: Ida](../plugins/ida/agents/ida.md) -- Restate user words into clear, complete directions by meaning and distinctions; judge reports by fidelity to meaning, not wording. | instructions | imperative | `plugins/ida/agents/ida.md:36,41`: Restates user asks by meaning and distinctions; judges reports strictly by fidelity to meaning and distinctions, faulting only for lost, added, or distorted meaning. Observation: Ida accepts faithful restatements and faults only lost, added, or distorted distinctions. |
| [Persona: Ida](../plugins/ida/agents/ida.md) -- Briefing rules on returned work: bottom line first, hard cap of ≤ 3 bullets unless detail requested, no open-decision roll-ups, and exactly one decision or question per message. | instructions | imperative | `plugins/ida/agents/ida.md:71-77`: Bottom line first, hard cap of ≤ 3 bullets unless detail requested, no "waiting on you" or aggregated lists of open decisions, and exactly one decision or question for the user per message. Observation: Ida structures briefs to protect user attention and cognitive load. |
| [Skill: Telegram](../plugins/ida/skills/telegram/SKILL.md) -- Chat replies must stay under ~100 words length budget. | instructions | imperative | `plugins/ida/skills/telegram/SKILL.md:14`: Chat replies must stay under ~100 words (Glance Rule, D9). Observation: Telegram replies are budgeted to ~100 words with details moved to the Mini App. |
| [Persona: Sara](../plugins/ida/agents/sara.md) -- Recompose asks into clear logical structures by meaning and distinctions; judge restatements by meaning, not verbatim wording. | instructions | imperative | `plugins/ida/agents/sara.md:16,46`: Sara recomposes asks citing message IDs, keeping exact words only in ## Ask; judges restatements by fidelity to meaning and distinctions, not wording. Observation: Sara does not fault workers for rewording or expect verbatim wording in outputs. |
| [Persona: Pauli](../plugins/ida/agents/pauli.md) -- Restate user asks into clear, complete tasks and notes by meaning and distinctions; keep exact words only in ## Ask. | instructions | imperative | `plugins/ida/agents/pauli.md:37`: Pauli restates asks into clear tasks and notes by meaning and distinctions; kept words exist only in ## Ask for verification. Keeping exact words in PKB outputs is not a goal. Observation: PKB tasks and notes hold synthesized goals and knowledge without verbatim quotes. |
| [Persona: Marsha](../plugins/ida/agents/marsha.md) -- Verify deliverables against user meaning, distinctions, and acceptance criteria rather than verbatim prompt wording. | instructions | imperative | `plugins/ida/agents/marsha.md:15`: Marsha measures deliverables against requester meaning, distinctions, and acceptance criteria; judges restatements by fidelity to meaning, completeness, and lack of overreach. Observation: QA reviews do not fault deliverables or restatements for rewording. |

## Evidence contract

Measures in place that enforce the [evidence contract](enforcement/evidence-contract.md). The full design and escalation path are in [evidence-contract-enforcement.md](enforcement/evidence-contract-enforcement.md).

| Measure | Carrier | Applies to | Severity |
| - | - | - | - |
| Argdown grammar, basis vocabulary, observed-value rule, tags | `argdown-toulmin` skill | All agents | Guidance |
| Report format, contrast test, verdict tokens, verdict command, return | `premise-check` skill | All agents | Guidance |
| Relaying a report upward requires its premise-check verdict | `premise-check` skill (`plugins/ida/skills/premise-check/SKILL.md:23`) | All agents | Imperative |
| Restatement fidelity: kept words in `asks` / `## Ask` exist so checkers test restatements for fidelity, completeness, and overreach; judged by meaning and distinctions, not wording | `premise-check` skill, `reify`, `q` | Checkers (Ida, Sara), task authors (Pauli, workers) | Guidance |
| Report argument in the task handback and QA review | `/pull`, `/dump`, `/verify` | Task workers, QA reviewers | Guidance |
| Pointer to `premise-check` (no restated format rules) | `sara.md`, `/pull` §3, `ida.md` | Sara, workers, Ida | Guidance |
| Ida's role: formal checking and attention protection; substance checks prohibited | `ida.md` | Ida | Guidance |
| Session-wide one-line pointer | `SessionStart` (startup, resume, compact) | All agents | Reminder |
| Reply-format reminder (`honesty.md`) on a peer envelope | `UserPromptSubmit`, peer envelope | All agents | Reminder |
| Check reminder (`hearsay.md`) on a peer envelope, subagent handback, direction or foreground subagent result | `UserPromptSubmit` (peer envelope / agent message), `PostToolUse` on dispatch tools | Ida, Sara | Reminder |
| Gate arms only when a report or direction arrives: an incoming agent message (peer message, completion notification with a `<result>`, subagent handback, direction) or a foreground subagent's `completed` result, storing judged text and reference; never on a spawn or launch acknowledgement, other tool result, or an agy wake from the session's own tasks, timers or system notices; directions prompt frozen acceptance checklist | `UserPromptSubmit` (peer, task-notification, agent-message envelope; agy `SYSTEM_MESSAGE` from another agent), `PostToolUse` on dispatch tools (`Agent`, `invoke_subagent`, `Task`) with `status: "completed"` | Ida, Sara | Friction |
| Gate arms on a PKB task read with a `## Report` and no `## Premise-Check Verdict` | `PostToolUse` of PKB task read tool | Ida, Sara | [DISABLED] Friction; bypassed in code pending a decision |
| Gate refuses `Agent`, `Task`, `invoke_subagent`, `SendMessage`, `AskUserQuestion`, `Dump`, channel replies | `PreToolUse` | Ida, Sara | Refuse |
| Gate blocks `Stop` once per chain | `Stop` | Ida, Sara | Block |
| Gate messages two lines (claim and skill, then the verdict command with no pre-filled verdict) and one line (user, no command) | `premise_check_handler`, `premise_check_arm` | Ida, Sara | Friction |
| Enforcement level B: the recorder refuses PASS unless the reason carries the seven keyed lines and passes mechanical cross-checks against the judged block; no-claim reason accepted and marked; REVISE and FAIL take any reason | `record_verdict` in `plugins/ida/hooks/premise_check_verdict.py`, run by `skills/premise-check/scripts/verdict.py` | Ida, Sara | Required gate |
| Verdict recording and span emission carrying one attribute per reason line, ask ids, weakest basis, inference count, defect tags, no-claim flag and judged-text reference | `premise_check_verdict.py` | Ida, Sara | Observability |
| Count each override that lets an armed gate pass a blocked action | `premise_check_handler` span `premise_check_override` | Ida, Sara | [DISABLED] Observability; bypassed in code pending a decision |
| Gate modes and override variables | Environment | Ida, Sara | Config |
| No named or persistent subagents for middle-level agents | Prime-only instructions (`prime/CLAUDE.md` in `nicsuzor/ida`), settings files (dotfiles, outside this repo); expected `"teammateMode": "in-process"` | Prime, Sara, Pauli | Prevention |
| `release_task` required fields, presence-only, on tasks created after the check shipped | PKB server | Task workers | Prevention |
| Substance check: the reviewer opens each pointer and confirms it supports its claim | [Workflow](enforcement/workflow.md) steps 3-4, `/verify` | QA reviewers | Verdict (agentic) |
