---
id: enforcement-evidence-contract-enforcement
title: Enforcing the Evidence Contract
type: spec
status: draft
tags: [enforcement, verification, evidence-contract, premise-check, hooks]
---

# Enforcing the Evidence Contract

How the framework holds agents to the [evidence contract](evidence-contract.md). The measures in place today are listed in the [enforcement map](../ENFORCEMENT-MAP.md#evidence-contract). This spec gives the designed system.

## User story

As the user, I want each agent reminded of the contract at the moment it writes or receives a report, the chain held until a received report has a recorded verdict, and a PASS recorded only with a reason that can be held against the report, so that the contract is followed without being repeated every turn and a PASS shows what was tested.

- The format lives only in the `premise-check` skill. Every other instruction file, reminder and gate message names the skill and adds nothing to it.
- Each reminder fires once, at its moment, and is a line or two long.
- Ida and Sara cannot dispatch, message, reply on a channel or stop while a received report awaits a verdict.
- Agents judge each report. The verdict recorder checks the checker's reason mechanically, for its shape and its consistency with the judged block. Whether a rule yields its claim, whether the named rival is the nearest, whether an assumption line is complete, sufficiency against stakes, and whether a relayed sentence follows from its line stay with the agent and are never mechanised.
- Verdict content is counted in telemetry.

## Reminders

| Moment | Agents | Reminder |
| - | - | - |
| Session start, resume and compaction | All | One line: reports follow `premise-check`, written in its shape and checked on receipt |
| A peer message arrives | All | Your reply is a report; write it per the skill |
| A report arrives | Ida, Sara | Check it per the skill before you act on it, reply or dispatch |
| Gate refusal or `Stop` block | Ida, Sara | At most two lines naming the claim id and the skill; one line for the user |

A report arrives as a foreground subagent's result, a background subagent's notification or a peer message. A task record's `## Report` is a report too, but no hook marks its arrival. Each harness carries these moments on its own hook events; the event map is in [ARCHITECTURE.md](../ARCHITECTURE.md).

On agy the session-start line arrives with the first `PreInvocation` of each conversation. agy's hook payloads name no agent and carry no report: a subagent's reply arrives as a message file that starts a new turn. So the Ida and Sara reminders and the gate do not run on agy.

## The premise-check gate

The gate is procedural friction, the exception [enforcement.md](enforcement.md) authorises. It and the verdict recorder check form and consistency; every semantic judgement stays with the checking agent.

- **Scope:** Ida and Sara.
- **Arms:** when a report arrives: on a peer envelope or on a foreground subagent's result. The gate never arms when a subagent is launched, and never on the user's own messages.
- **Stores:** at arm time, the judged text and an explicit reference to it: the tool-use id or the envelope id.
- **Holds:** while armed, it refuses dispatch tools, messaging tools, `AskUserQuestion`, `Dump` and channel reply tools, and blocks `Stop` once per stop chain.
- **Disarms:** on a recorded verdict (PASS, REVISE or FAIL, with a reason) through the skill's verdict script. The command it offers carries no pre-filled verdict.
- **Configuration:** `PREMISE_CHECK_GATE_MODE` is `block` by default, or `warn` or `off`. A truthy `PREMISE_CHECK_OVERRIDE`, `PREMISE_CHECK_GATE_OVERRIDE`, `AOP_FORCE` or `AOP_OVERRIDE` lets an armed gate pass a blocked action. Override use is not counted. Gate state is a per-session file under `AOPS_PREMISE_CHECK_DIR`, by default `aops_premise_check/` in the system temp directory.

A container worker hands back through its task record. The gate does not arm on reading it: the arming and the override-counting span are built but bypassed in the code. The checker who reads the record checks it per the skill, with the task id as claim id, and adds `## Premise-Check Verdict` to the task with the verification id and verdict.

## The verdict recorder

The recorder holds the checker to the [checker's reason](../../plugins/ida/skills/premise-check/references/checker-reason.md). It gates the checker's reason, never the author's report.

The report argument it reads is the skill's fenced `argdown` block: parser-valid Argdown in standard form, with the asks, answers and endnotes in its frontmatter and the basis in words on each premise line. The recorder reads the block's structure itself; the Argdown parser is not run at record time.

- **PASS:** refused unless the reason carries the seven keyed lines and passes every mechanical cross-check the skill lists under "What the recorder refuses", run against the judged text the gate stored.
- **No claim:** a one-line `Judged: <claim id>; no claim -- ...` reason is accepted for PASS and the verdict is marked no-claim.
- **REVISE and FAIL:** recorded with any reason.
- **Records:** each verdict emits one `premise_check_verdict` span carrying the claim id, verification id, verdict, reason, the judged-text reference, one attribute per reason line, the ask ids, the weakest basis, the inference count, the defect tags and the no-claim flag.
- **Fails closed:** when tracing is unconfigured or the span export fails, no verdict is recorded and the gate stays armed.

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

## Escalation

Each level is built only when verdict telemetry shows the level below it rubber-stamping, with PASS near 100% and REVISE rare.

Level B, the verdict recorder above, is built: it gates the checker's reason. It is distinct from the author-side parse gate in step 2 below, which is not built.

Further steps, in order, each built only when the same trigger fires on the level below:

1. A one-time `SubagentStop` block that sends the skill's pointer back to the subagent before its report is delivered, and later one that blocks only a final message with no `argdown` block.
2. An author-side parse gate: the Argdown parser runs on the report's `argdown` block, and the recorder refuses any verdict on a block that does not parse.
3. A separate checker agent on arrival.
