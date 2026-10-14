---
id: enforcement-evidence-exchange
title: Evidence Exchange -- Report Format, Checking, and Enforcement
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, evidence-contract, premise-check, hooks]
---

# Evidence Exchange

This spec covers how agents pass claims to one another: the contract every report meets, who checks what, how reports travel, and how the obligation reaches each agent. It replaces `evidence-contract.md` and `report-verification.md`. Every enforcement measure is listed once, by state, in the [enforcement map](../ENFORCEMENT-MAP.md#evidence-exchange).

## One home per rule

- **The format** lives in the [`premise-check` skill](../../plugins/ida/skills/premise-check/SKILL.md): the report shape, the basis vocabulary, the verdict tokens, the verdict command and the kickback rule. This spec gives the design and the enforcement, and does not restate the format.
- **Every other instruction file** names the skill and adds nothing to it. That includes agent definitions, other skills and hook messages. The one exception is `/pull`'s direction to finish with `/dump`, which is a workflow step, not part of the format.
- **Handback envelope.** `/dump` defines the task handback envelope (VERDICT, GATE, CONFIDENCE, CONFOUND CHECK, Receipts). `/verify` uses the same envelope. Both write their Receipts per the skill.
- **The basis vocabulary** is the skill's. The hashtag list in the retired `evidence-contract.md` (`#observed`, `#not-observed`, `#inferred`, `#reported-by-another`, `#warrant`) is superseded.

## The contract

Every load-bearing claim made at a module or task boundary carries one of two things:

1. **Checkable evidence**: a pointer a downstream agent can open without reading the originating transcript, with its basis stated. Or:
2. **A stated failure reason.**

There is no third option.

- **Honest failure is always a legal exit.** "I could not do X, because Y" never violates the contract. Silence does, and so does a claim with no evidence.
- **Partial is a terminal state, not a failure.** A partial handback meets option 1 for the work that shipped, and discloses the deferred remainder under the partial-work coverage partition (`tested | declared-deferred | illegal-gap`, [`spec-partial-work-tight-loop-delivery.md`](../polecat/spec-partial-work-tight-loop-delivery.md)). A worker whose own deliverable is complete releases `done`, even while follow-ups such as QA, merge or deploy are still to run.
- **Status survives every hop.** No receiver promotes an inferred, assumed or reported claim to an observed one. A derived claim is no stronger than the weakest basis among its premises.
- **Negative and capability claims need a test.** They need a failed attempt with its verbatim error, or a bounded search with its query, scope and zero count. Absence of evidence never grounds "does not exist" or "cannot".

## Two checks, two roles

### Formal check: chain receivers (Ida, Sara)

A receiver judges the report's argument, not the world. It checks four things:

- whether the report has the skill's shape
- whether each material premise carries a basis and a pointer
- whether the inferences hold and the conclusion stays within the premises' scope
- whether the conclusion answers the original ask

It never opens a pointer, re-runs work, or re-determines an observed fact. Checking the substance of cited evidence is prohibited at this layer. Half of Ida's job is this formal check; the other half is protecting the user's attention.

Three rulings carry most of the weight:

- **Kickback.** A report not in the skill's shape gets the verdict REVISE `#format` and goes back to its sender. Nothing unchecked goes further up the chain, and a REVISE never reaches the user as a hedge.
- **Observed value.** A premise about the state of something outside the report quotes the observed value of the field that decides it, beside the pointer. The pointer says where to look; the value says what was seen.
- **Contrast test.** For each material state claim, the checker names the nearest other state that would change the reader's next action. If the stated evidence does not rule that state out, the verdict is REVISE `#missing`. This catches status words that cover opposite states: "blocked on review" fits both "awaiting review" and "changes requested".

When an incoming message relays a direction from the user, the receiver checks that the direction can be derived from the cited original ask. It flags any added detail, constraint or method the ask does not support, and passes the direction when it can be derived.

### Substance check: QA reviewers

The workflow's boundary-check and QA-around steps ([workflow.md](workflow.md#the-five-step-shape)), run through `/verify`, check the substance. The reviewer opens the pointer and confirms it says what the claim asserts.

#### Substance over form

- **A filled-in field is necessary but not sufficient.** A citation that does not support its claim is the same violation as no citation.
- **A self-graded form is not a boundary check.** Neither is a block that recites field names for a check that was never run.
- **Tick an acceptance criterion only on direct evidence of that item.** Substitute or indirect evidence never licenses a tick.

## How reports travel

**Persistent agents** talk on the bus: cross-session messages. **Internal subagents** return and halt: their final message is their report. Middle-level agents (Ida, Prime, Sara, Pauli) do not create named or persistent subagents; their settings files carry the same setting to that effect.

A report therefore reaches its receiver by one of four routes:

| Route               | Arrives as                                        | Hook event                      |
| ------------------- | ------------------------------------------------- | ------------------------------- |
| Foreground subagent | The Agent tool's result                           | `PostToolUse` on `Agent`        |
| Background subagent | `<task-notification>`                             | `UserPromptSubmit`              |
| Bus peer            | `<cross-session-message>` or `<teammate-message>` | `UserPromptSubmit`              |
| Container worker    | A handback written to the task record by `/dump`  | None: it is read by a tool call |

A `SubagentStop` hook's `decision: "block"` reason goes to the subagent, which keeps working (Claude Code hooks docs, SubagentStop). That makes `SubagentStop` the only event that can act on an outgoing report before it is delivered. To inject into the parent after a subagent returns, the documented route is `PostToolUse` on `Agent`.

## When the obligation reaches an agent

Reminders fire at the moment of use, once, and stay a line or two long. Each points to the skill; none restates it.

| Moment                               | Agents    | Reminder                                                                              | Carrier                                                                  |
| ------------------------------------ | --------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Session start, resume and compaction | All       | One line: reports follow `premise-check`, written in its shape and checked on receipt | `SessionStart` hook                                                      |
| A peer message arrives               | All       | `honesty.md`: your reply is a report; write it per the skill                          | `UserPromptSubmit`, peer envelope                                        |
| A report arrives                     | Ida, Sara | `hearsay.md`: check it per the skill; if it isn't in shape, REVISE and return it      | `UserPromptSubmit`, peer envelope; `PostToolUse` on a foreground `Agent` |
| Gate refusal or Stop block           | Ida, Sara | At most two lines naming the claim id and the skill. One line for the user            | `premise_check_handler`                                                  |

The `SessionStart` hook carries the session-wide line because a plugin's `CORE.md` does not reach its agents. The `@../CORE.md` line in `agents/*.md` is not expanded: Claude Code documents `@` imports only for `CLAUDE.md`, and a live Ida session received the line as literal text.

There is no reminder at `Stop`, `PostToolBatch` or mid-session.

## The premise-check gate

The gate is procedural friction that never evaluates substance. [enforcement.md](enforcement.md) authorises it as the exception to "no mechanical verdict".

- **Scope:** agent types `ida`, `ida:ida`, `sara` and `ida:sara`. Prime is Ida.
- **Arms:** on a peer envelope at `UserPromptSubmit`, and on `PostToolUse` of a foreground `Agent` call, judged by the structured `run_in_background` field. It never arms when a subagent is launched in the background (the report arms it when it arrives), and never on `PostToolBatch`. The user's own messages never arm it.
- **Holds:** while armed, it refuses these tools:
  - `Agent`, `Task` and `invoke_subagent`
  - `SendMessage`, `AskUserQuestion` and `Dump`
  - the channel reply tools (Telegram and Discord)

  It also blocks `Stop` once per stop chain.
- **Disarms:** a recorded verdict (PASS, REVISE or FAIL, with a reason), through the skill's verdict script. The command carries no pre-filled verdict. Harness notices are handled as the skill says.
- **Modes and override:**
  - `PREMISE_CHECK_GATE_MODE` is `block` by default; `warn` and `off` are the alternatives.
  - A truthy `PREMISE_CHECK_OVERRIDE`, `PREMISE_CHECK_GATE_OVERRIDE`, `AOP_FORCE` or `AOP_OVERRIDE` disables the gate.
  - Gate state is a per-session JSON file under `aops_premise_check/` in the system temp directory, overridable with `AOPS_PREMISE_CHECK_DIR`.
- **Telemetry:** each verdict emits one span, `premise_check_verdict`, carrying `premise_check.claim_id`, `.verification_id`, `.verdict` and `.reason`. Emission is best-effort.

## Escalation path

Measures are added only when the current level is shown to fail. The test is verdict telemetry: if PASS stays near 100% with REVISE rare, the agentic check is failing. The options in order, none in place:

1. A `SubagentStop` reminder, blocking once, that sends the skill's pointer back to the subagent before its report is delivered. A further option is to block only when `last_assistant_message` has no fenced `argdown` block.
2. A verdict script that refuses PASS or REVISE without a reconstruction file that parses.
3. A separate checker agent on arrival.

Handlers that are not needed stay in the code, unwired: `honest_output` (Stop, all agents) and `be_quiet` (Stop, Ida).

## Format design notes

These are the reasons behind the skill's format. The skill is operative.

- **Delivery by skill.** The full format loads when a report is written. Reminders name the skill, because repeating the format every turn costs context and adds nothing.
- **Pointers are identifiers.** Citation by identifier is preferred, and a pinpoint is best. A command counts only when its output is the evidence, and then the output is quoted.
- **Parsing is approximate.** `@argdown/cli` rejects unescaped underscores even inside backticks. Pointers stay verbatim, and a parse failure caused only by an underscore in a pointer is acceptable.
- **No horizontal rules.** The derivation is the named line `-- from … by … --`.
- **Fences.** An inner fence as long as its outer fence closes it early. `tests/test_markdown_fences.py` fails on such a collision.
- **Origin.** The ledger combines two strengths seen in workers' reports on 2026-10-06. Antigravity's reports made the logic easy to follow: outcome first, numbered premises, a named derivation. Claude Code's made the evidence easy to check: span ids, verbatim errors, bounded searches.

## Syntax checks are never verdicts

Parsers and presence checks may confirm well-formedness. No parser judges whether a pointer proves its claim or a warrant holds. That judgment stays with agents, under [enforcement.md](enforcement.md)'s governing principle.

## Where this binds

- **Layer 2:** `release_task` and `complete_task` ([task-contract.md](task-contract.md)). The completion claim meets this contract, and required fields are checked for presence only.
- **Layer 3:** workflow boundary-check and QA-around ([workflow.md](workflow.md#the-five-step-shape)), under Substance over form.
- **Layer 4:** principal sign-off ([sign-off.md](sign-off.md)): this contract at release-unit scale.
- **The chain:** worker to Sara to Ida to the user, under the formal check.

At every binding, the handback is written to the shared task record, including the output URL of the deliverable. It is never held only in a session transcript or a PR body.

**Grandfather policy.** Presence checks apply forward only, compared against the task's `created` timestamp. The agentic obligation binds immediately.
