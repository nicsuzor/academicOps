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
- Ida and Sara cannot dispatch, message, reply on a channel or stop while a report that arrived as an incoming message awaits a verdict.
- Agents judge each report. Parsers and presence checks confirm well-formedness only, under [enforcement.md](enforcement.md)'s governing principle.
- **AC-1.1** Given Ida or Sara with no report awaiting a verdict, when a cross-session message, a teammate message or a background subagent's or worker's completion notification arrives, then the agent's next dispatch, message, channel reply or `Stop` is refused until it records a verdict.
- **AC-1.2** Given Ida or Sara with no report awaiting a verdict, when a foreground subagent returns its result, a background subagent is launched, or any other of the agent's own tool calls completes, then the agent's next dispatch goes through.
- **AC-1.3** Given Ida or Sara with no report awaiting a verdict, when the user's own message arrives, typed or over a channel, then the agent's next dispatch goes through.

## Reminders

| Moment | Agents | Reminder |
| - | - | - |
| Session start, resume and compaction | All | One line: reports follow `premise-check`, written in its shape and checked on receipt |
| A peer message arrives | All | Your reply is a report; write it per the skill |
| A report arrives | Ida, Sara | Check it per the skill; if it isn't in shape, REVISE and return it |
| Gate refusal or `Stop` block | Ida, Sara | At most two lines naming the claim id and the skill; one line for the user |

A report arrives as a foreground subagent's result, a background subagent's notification, or a peer message. Each harness carries these moments on its own hook events; the event map is in [ARCHITECTURE.md](../ARCHITECTURE.md).

## The premise-check gate

The gate is procedural friction that never evaluates substance, the exception [enforcement.md](enforcement.md) authorises.

- **Scope:** Ida and Sara.
- **Arms:** when an incoming message carries a report: a cross-session message, a teammate message, or the notification that a background subagent or worker has finished. A foreground subagent's result is the agent's own tool output and leaves the gate as it was.
- **Holds:** while armed, it refuses dispatch tools, messaging tools, `AskUserQuestion`, `Dump` and channel reply tools, and blocks `Stop` once per stop chain.
- **Disarms:** on a successfully recorded verdict (PASS, REVISE or FAIL, with a reason, and acknowledged OTel span emission) through the skill's verdict script. The command it offers carries no pre-filled verdict. A failed or unconfigured span emission exits non-zero and leaves the gate armed.
- **Records:** each verdict emits one span, `premise_check_verdict`, with the claim id, verification id, verdict and reason. Span emission failures halt loudly without fallback.
- **Configuration:** `PREMISE_CHECK_GATE_MODE` is `block` by default, or `warn` or `off`. A truthy `PREMISE_CHECK_OVERRIDE`, `PREMISE_CHECK_GATE_OVERRIDE`, `AOP_FORCE` or `AOP_OVERRIDE` disables the gate. Gate state is a per-session file under `AOPS_PREMISE_CHECK_DIR`, by default `aops_premise_check/` in the system temp directory.

Container-worker handbacks are read from the task record, so no report arrives and the gate does not arm. Nothing yet covers that route.

## Changes from what is in place

- The gate adds channel reply tools to what it refuses, and its messages shrink to the lengths above.
- The pre-filled `--verdict PASS` leaves the verdict command.
- `honesty.md` leaves the `search_the_pkb` fallback, and becomes the peer-message reminder.
- `sara.md`, `/pull` and `ida.md` replace their restated format rules with a pointer to the skill.
- The skill adds the observed-value rule, the contrast test and the return of an off-shape report as REVISE.
- `/verify` uses `/dump`'s handback envelope.
- `ida.md` states Ida's role: judge each report's argument, and protect the user's attention.
- Handlers no longer needed stay in the code, unregistered: `honest_output`, `be_quiet` and `quiet_channel_reply`.

## Escalation

Each step is built only if verdict telemetry shows the current level rubber-stamping, with PASS near 100% and REVISE rare. In order:

1. A one-time `SubagentStop` block that sends the skill's pointer back to the subagent before its report is delivered, and later one that blocks only a final message with no fenced `argdown` block.
2. A verdict script that refuses PASS or REVISE without a reconstruction file that parses.
3. A separate checker agent on arrival.
