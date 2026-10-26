---
id: enforcement-evidence-contract-enforcement
title: Enforcing the Evidence Contract
type: spec
status: draft
tags: [enforcement, verification, evidence-contract, premise-check, hooks]
---

# Enforcing the Evidence Contract

How the framework holds agents to the [evidence contract](evidence-contract.md). The measures in place today are listed in the [enforcement map](../ENFORCEMENT-MAP.md#evidence-contract). This spec gives the designed system.

## User stories

### US-1 Report checking

As the user, I want each agent reminded of the contract at the moment it writes or receives a report, and the chain held until a received report has a recorded verdict, so that the contract is followed without being repeated every turn.

- The format lives only in the `premise-check` skill. Every other instruction file, reminder and gate message names the skill and adds nothing to it.
- Each reminder fires once, at its moment, and is a line or two long.
- Agents cannot dispatch, message, reply on a channel or stop while a report or direction that arrived as an incoming agent message awaits a verdict.
- Agents judge each report. Parsers and presence checks confirm well-formedness only, under [enforcement.md](enforcement.md)'s governing principle.
- **AC-1.1** Given an agent with no report awaiting a verdict, when an incoming agent message carrying a report or direction arrives on `UserPromptSubmit` (a cross-session message, a teammate message, a task notification with a `<result>`, a subagent hand-back, or a direction/brief from above), then the agent's next dispatch, message or channel reply is refused until it records a verdict, and its first `Stop` is blocked.
- **AC-1.2** Given an agent with no report awaiting a verdict, when a foreground subagent returns its result on `PostToolUse` (for `Agent`, `invoke_subagent`, or `Task`), then the gate arms and holds the next dispatch, message, channel reply or stop until a verdict is recorded. When a subagent is launched or spawned rather than returned (`async_launched`, the default when `run_in_background` is omitted, or `teammate_spawned`), or any other of the agent's own tool calls completes, the check remains disarmed, and a claim already pending stays the one armed.
- **AC-1.3** Given an agent with no report awaiting a verdict, when the user's own message arrives, typed or over a channel, then the agent's next dispatch goes through without arming the gate, and the user prompt is hydrated from the PKB.
- **AC-1.4** When the incoming agent message is a direction, the receiving agent checks that it derives from `## Ask` and refuses unverified caller method or template prescriptions before logging deliverables as a frozen acceptance checklist on a PKB task.

## Reminders

| Moment | Agents | Reminder |
| - | - | - |
| Session start, resume and compaction | All | One line: reports follow `premise-check`, written in its shape and checked on receipt ([`plugins/ida/hooks/handlers.py:817-858`](../../plugins/ida/hooks/handlers.py#L817-L858)) |
| A subagent starts (`SubagentStart`) | All subagents | Your reply is a report; write it per the skill ([`plugins/ida/hooks/handlers.py:136-141,1094-1096`](../../plugins/ida/hooks/handlers.py#L136-L141)) |
| A report or direction arrives (`UserPromptSubmit` or `PostToolBatch`) | All | Check it per the skill; if a direction, check that it derives from `## Ask` and refuse unverified prescriptions before logging deliverables; if a report isn't in shape, REVISE and return it ([`plugins/ida/hooks/handlers.py:891-895,1086-1088`](../../plugins/ida/hooks/handlers.py#L891-L895), [`plugins/ida/hooks/hearsay_gate.py:805-845,881-949`](../../plugins/ida/hooks/hearsay_gate.py#L805-L845)) |
| Gate refusal or `Stop` block | All | At most two lines naming the claim id and the skill; one line for the user ([`plugins/ida/hooks/hearsay_gate.py:487-510,886-949`](../../plugins/ida/hooks/hearsay_gate.py#L487-L510)) |

A report arrives as a foreground subagent's result, a background subagent's notification, or a peer message. Each harness carries these moments on its own hook events; the event map is in [ARCHITECTURE.md](../ARCHITECTURE.md).

On agy the session-start line arrives with the first `PreInvocation` of each conversation. agy's hook payloads carry no report: a subagent's reply arrives as a `SYSTEM_MESSAGE` step that starts a new turn, which the gate reads from the transcript.

## The premise-check gate

The gate is procedural friction, the exception [enforcement.md](enforcement.md) authorises. It and the verdict recorder check form and consistency; every semantic judgement stays with the checking agent.

- **Scope:** All agents receiving messages from teammates or in-session agents, independent of receiving or sending agent identity.
- **Arms:** on every report that reaches any agent as an incoming message from a teammate or an in-session agent, whatever the receiving or sending agent's identity: on `UserPromptSubmit`, when an incoming agent message carries a report or direction (a cross-session message `<cross-session-message>`, a teammate message `<teammate-message>` whether arriving via `SendMessage` or a teammate `idle_notification` event, unwrapped from Claude Code's peer preamble `Another Claude session sent a message:`, a subagent hand-back `<subagent-handback>` or `<agent-message>`, a task notification carrying a `<result>`, or a direction/brief from above); on `PostToolUse` of `Agent`, `Task` or `invoke_subagent`, when a foreground subagent returns its result (`status: "completed"`). Every peer message requires a fenced Argdown block: the null form clears the gate with no agent action; when an expected block is absent, the gate does not open and PASS is refused, so the receiver's only way through is to send the message back for revision (recording REVISE to return it for resending). Nothing else arms it: not a spawn or launch acknowledgement (`async_launched`, `teammate_spawned`, "Spawned successfully"), not a task notification with no `<result>` (a background command finishing), not a pointer saying the report was delivered by hand-back, not any other tool result, and not the user's own prompts. On agy, a `SYSTEM_MESSAGE` turn arms it only when its `[Message]` comes from another agent's conversation (`sender=<conversation-id>`) or is a system notice quoting an idle subagent's last response; the session's own command tasks and timers (`sender=<conversation-id>/task-N`), other system notices, and stop-hook refusals leave it disarmed. Arming adds the arriving report's claim to those pending and never replaces one. The arming notice reminds the receiver to check that incoming directions derive from `## Ask` and refuse unverified caller method or template prescriptions before logging deliverables as a frozen acceptance checklist on a PKB task.
- **Stores:** at arm time, the judged text (unwrapping JSON `result` strings from teammate `idle_notification` payloads so fenced `argdown` blocks can be parsed) and an explicit reference to it: the tool-use id, task id, or the envelope id.
- **Holds:** while armed, it refuses dispatch tools, messaging tools (`SendMessage`, `send_message`), `AskUserQuestion`, `Dump`, `dump`, and channel reply tools, matched case-insensitively, and blocks `Stop` once per stop chain.
- **Disarms:** on a recorded verdict (PASS, REVISE or FAIL, with a reason) through the skill's verdict script, or automatically for an expected null form. An absent expected block refuses PASS and clears only when returned for revision via REVISE.
- **Configuration:** `PREMISE_CHECK_GATE_MODE` is `block` by default, or `warn` or `off`. A truthy `PREMISE_CHECK_OVERRIDE`, `PREMISE_CHECK_GATE_OVERRIDE`, `AOP_FORCE` or `AOP_OVERRIDE` lets an armed gate pass a blocked action. Override use is not counted. Gate state is a per-session file under `AOPS_PREMISE_CHECK_DIR`, by default `aops_premise_check/` in the system temp directory.

A container worker hands back through its task record. The decentralised workflow cannot enforce on polecat or other workers; the task contract is the key boundary, and enforcement regulates when it is read from. The gate does not arm on reading it: the arming and the override-counting span are built but bypassed in the code. The checker who reads the record checks it per the skill, with the task id as claim id; `record_verdict` accepts verdicts recorded against a task id without requiring an armed hearsay gate in the session, mints a verification id, emits the verdict span, and the checker adds `## Premise-Check Verdict` to the task with the verification id and verdict.

## The verdict recorder

The recorder holds the checker to the [checker's reason](../../plugins/ida/skills/premise-check/references/checker-reason.md). It gates the checker's reason, never the author's report.

The report argument it reads is the skill's fenced `argdown` block: parser-valid Argdown in standard form, with the asks, answers and endnotes in its frontmatter and the basis in words on each premise line. On PASS, `verdict.py` runs deterministic machine checks (syntax errors, unconnected statements with no relations or argument membership, and undercuts not aimed at an inference; expecting `argdown` on `PATH` without fallbacks). On an invalid argument, it refuses PASS with an actionable error, leaving the gate armed.

- **PASS:** refused unless the block passes deterministic Argdown parser checks, and the reason carries the seven keyed lines and passes every mechanical cross-check the skill lists under "What the recorder refuses", run against the judged text the gate stored.
- **No claim:** a one-line `Judged: <claim id>; no claim -- ...` reason is accepted for PASS and the verdict is marked no-claim.
- **REVISE and FAIL:** requires at least one failing inference step (`Valid: (n) fails -- <defect>`) or unanswered ask (`Answered: <ask id> unanswered` or `Ask: ... -> unanswered`); refused when `Valid:` is non-empty and every `Valid:` entry has status `holds` with no unanswered ask. When `Valid:` is omitted (e.g. absent block return), any reason is accepted.
- **Records:** each verdict emits one `premise_check_verdict` span carrying the claim id, verification id, verdict, reason, the judged-text reference, one attribute per reason line, the ask ids, the weakest basis, the inference count, the defect tags, the no-claim flag, and the machine flag when generated mechanically.
- **Fails closed:** when tracing is unconfigured, the span export fails, or the Argdown parser execution, decode, or timeout fails, no verdict is recorded and the gate stays armed.

## Telemetry

Three measures are queryable in Phoenix from the verdict span attributes; the fourth, override count, has no span while override counting is bypassed:

1. Defect-tag rate per inference line: sum of `premise_check.defect_tag_count` over sum of `premise_check.inference_count`, on `premise_check_verdict` spans.
2. Strength distribution: count of `premise_check_verdict` spans by `premise_check.verdict` and `premise_check.weakest_basis_term`.
3. The contents of `Waived`: count of each entry of the `premise_check.waived_items` array.
4. Override count: count of `premise_check_override` spans by `premise_check.override_var` and `premise_check.override_tool`, once the span is enabled.

Each is one SQL query over the project's spans, for example measure 1:

```sql
SELECT sum(CAST(s.attributes->>'$.premise_check.defect_tag_count' AS INTEGER)) * 1.0
     / nullif(sum(CAST(s.attributes->>'$.premise_check.inference_count' AS INTEGER)), 0)
FROM spans s JOIN traces t ON s.trace_rowid = t.id JOIN projects p ON t.project_rowid = p.id
WHERE p.name = '<project>' AND s.name = 'premise_check_verdict'
```

Measure 3 expands the array with `json_each(s.attributes->'$.premise_check.waived_items')`.

## Proportional interventions

Each mechanism is added only when verdict telemetry shows the active checks rubber-stamping, with PASS near 100% and REVISE rare:

- **Verdict recorder** (built, above): gates the checker's reason (`premise_check_verdict.py`).
- **Argdown parser check on PASS** (built, above): runs deterministic Argdown parser checks on the report's `argdown` block (`report_argument.py`, expecting `argdown` on `PATH` without fallbacks), refusing PASS with an actionable error when the block fails syntax, connectedness, or undercut-target checks.
- **Subagent stop reminder** (not built): a one-time `SubagentStop` block that sends the skill's pointer back to the subagent before its report is delivered, or blocks a final message with no `argdown` block.
- **Dedicated arrival checker** (not built): a separate checker agent invoked on report arrival.
