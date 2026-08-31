---
alias:
- kb_4d8dc3c6-wf-session-hook-forensics
- kb_4d8dc3c6
created: 2026-07-28T02:39:00.049328431+00:00
id: kb_4d8dc3c6
last_modified: 2026-07-28T03:01:21.927217011+00:00
modified: 2026-07-28T03:01:21.927215337+00:00
permalink: kb_4d8dc3c6
tags:
- wf-template
- workflow
- framework
- debugging
- hooks
- forensics
title: wf-session-hook-forensics
type: template
---

## What this step does

Reconstruct session events from hook logs to diagnose gate failures, state transitions, and hook crashes. Hook logs record every hook event with full context — this is the tool for questions a conversation transcript can't answer: did a gate actually fire, what verdict did it return, why did a tool call get blocked.

**Scope split** (preserved from source): this document is the JSONL forensics procedure — how to read raw hook log files and diagnose specific session artifacts. It is not the catalogue of which gates exist and how each behaves (that's a live spec, read separately) or the general framework-debugging pattern (see [[wf-debug-framework-issue]]).

## Quick start

1. Find the hooks log for a session (it lives next to that session's own log stream, not in a separate flat directory).
2. Get a quick summary: count `PostToolUse` events for total operations; count `verdict:"deny"` events for anything that got blocked.
3. Generate a readable transcript for the conversation side — raw JSONL is unreadable at a glance.
4. Check gate verdicts directly from the raw hook JSONL for `Stop` events — transcripts do not reliably surface gate verdicts (see Known Transcript Gap below), so this step cannot be skipped in favour of reading the transcript alone.

## Procedure

1. **Locate the files** — hook JSONL, session state file, and transcript all share one canonical base name per session (date-time-shorthash-shortform-slug); locate all of them via that shared base rather than searching each independently.
2. **Generate the transcript first** — always, for the conversation side. Hook verdicts and system messages should be merged into it, but confirm they actually appear (see Known Transcript Gap); when they don't, fall back to raw JSONL for anything gate-related.
3. **Check gate behaviour** — grep for the relevant hook events (`Stop`, `PreToolUse`, `SubagentStart`/`SubagentStop`) and read the `output.verdict` field on each. A `verdict: "deny"` on `PreToolUse` means the tool call was rejected; a run of denies followed by an allow on `Stop` usually means an escape-hatch/auto-approve mechanism fired, not that the agent complied.
4. **Reconstruct the event sequence** — focus on the last 10-20 events to diagnose failures at session end: did the session actually finish its work, commit, and hand over cleanly, or did it get blocked?
5. **Identify the pattern** — compare against Common Patterns below before concluding something is broken.
6. **File a bug report or a learning** — session ID, event sequence, root cause, fix location.

## Hook JSONL schema

Each line is a JSON object. Hook logs are local-only (not synced to a shared repo). Key fields:

| Field                | Type        | Description                                                                                                                                          |
| -------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `session_id`         | string      | Full session UUID                                                                                                                                    |
| `session_short_hash` | string      | First 8 chars of the UUID                                                                                                                            |
| `hook_event`         | string      | `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`, `SessionEnd`, `PreCompact`, `Notification` |
| `logged_at`          | string      | ISO 8601 timestamp                                                                                                                                   |
| `exit_code`          | int         | 0=allow, 1=warn, 2=block                                                                                                                             |
| `cwd`                | string      | Working directory at time of event                                                                                                                   |
| `tool_name`          | string/null | Tool that triggered the event (`PreToolUse`/`PostToolUse`)                                                                                           |
| `subagent_type`      | string/null | Agent type (`SubagentStart`/`SubagentStop`)                                                                                                          |
| `output`             | object/null | The gate verdict and messages — the single most important field for forensics                                                                        |

### The `output` field

```json
{
  "verdict": "allow" | "deny" | null,
  "system_message": "Text shown to agent or logged (may be null)",
  "context_injection": "Text injected into agent context (may be null)",
  "updated_input": null,
  "metadata": { "source": "..." }
}
```

`verdict` — `allow` means the gate passed, `deny` means it blocked (on `PreToolUse`, the tool call itself was rejected). `system_message` is the human-readable gate-state message — countdown markers, status icons, blocking reasons. `context_injection` is what actually reaches the agent's own context — compliance-check demands, routing instructions, and similar.

### Known transcript gap (verify before trusting a transcript for gate forensics)

A transcript parser reading a field that doesn't actually exist in hook JSONL will silently drop every gate verdict, system message, and context injection from the generated transcript. **Do not assume the transcript shows hook behaviour accurately — verify against raw JSONL before trusting it for gate forensics specifically.** This is exactly the kind of parser/schema drift that reappears as tooling evolves, so treat "the transcript shows nothing happened here" as a possible instrumentation gap, not evidence of nothing happening, until cross-checked against the raw log.

## File locations and cross-referencing

All artefacts for one session share a single canonical base name (`{date}-{time}-{shorthash}-{shortform}-{slug}`). Typical categories of artefact sharing that base name: session state, hook JSONL, any periodic-review audit output, the provider's own raw session JSONL, the rendered transcripts (`<base>.md` reading copy, `<base>.full.md` full text including subagents, `<base>.controller.md`; the pre-2026-07-13 `-abridged.md` artifact no longer exists), and a session summary. Only parsed/committed outputs (transcripts, summaries) belong in a git-tracked sessions directory — everything else (state, hook logs, gate context, raw provider stream) belongs in the provider's own local per-project temp directory and is not synced.

**Correlating task → session → artifacts**: a dispatched-worker branch naming convention (e.g. `<worker>/<task-id>`) is usually the anchor — search `git log --all --oneline` for the task id to find the worktree, then match the session by date and hash in the artefact filenames, then locate the transcript by the same session short-hash.

## Gate forensics

Gate mechanisms in this class of framework change over time — retired mechanisms leave forensic traces in old sessions even after the gate itself is gone from the code. Two concrete examples worth knowing as a pattern (not as current-state fact — verify against the live gate catalogue before relying on specifics):

- **A periodic compliance-counter gate** keyed to a rolling tool-call count (not turn count) is a common shape: threshold, a countdown window before the threshold, a counter incremented per qualifying tool call, reset on the compliance subagent's completion. If someone describes gate behaviour "at N turns," check whether they mean operations (tool calls) — a single turn can produce 5-10+ tool calls, and confusing the two misreads the log.
- **A Stop-time exit gate** enforcing session-completion requirements (commit, capture, evidenced handover) typically has an escape hatch — after some number of consecutive denies within a turn, it degrades to warn-and-allow rather than deadlocking the session. A run of denies followed by an allow is that escape hatch firing, not the agent successfully complying — investigate what the agent actually did between denies before concluding the gate worked as intended.

**Diagnostic pattern for either**: grep the relevant hook events, decode each `output.verdict`, and look specifically for `SubagentStart`/`SubagentStop` pairs (each pair is one compliance check cycle) or repeated `Stop` denies (each one is a rejected exit attempt) — then read the CC/agent session JSONL for what happened between the relevant events, since the hook log tells you a gate fired but not what the agent was doing when it did.

## Identifying polecat/worker sessions

Worker sessions can usually be distinguished from interactive ones by `cwd` containing a worktree-path marker in the first hook-log line. Distinguish providers by session-ID format where the framework supports more than one (e.g. a distinct ID prefix for a non-default provider) — do not assume a `model`/`client` field is populated; it is a known gap in at least one historical implementation that these fields read `unknown` for worker sessions, making session-ID format the only reliable discriminator.

## Common patterns

- **A compliance gate firing repeatedly in a long session** — normal; expected as operation count climbs.
- **Several consecutive Stop denies then an auto-approve** — the escape hatch, not compliance; investigate whether the agent tried to satisfy the gate between denies or just retried blindly.
- **Zero hook JSONL for an entire provider/class of session** — either that provider hasn't run under the current hook system, or its integration is broken; treat as an open question requiring its own investigation, not evidence of "nothing happened."
- **Operations-vs-turns confusion** — always decode a stated threshold or count against operations (tool calls), not turns (user prompts), unless a source explicitly says otherwise.

## When to include

Any session that behaved unexpectedly, was blocked by a gate for an unclear reason, crashed inside a hook, or where the exact sequence of infrastructure events (as opposed to conversational content) needs to be established. Composes as the forensic-evidence-gathering step feeding into [[wf-agentic-e2e-certification]]'s certification report, and shares its "computed ≠ delivered ≠ seen" evidentiary discipline with that template.

## Source

Recovered verbatim (condensed formatting only) from `.agents/skills/aops/workflows/09-session-hook-forensics.md` merged with its companion reference `.agents/skills/aops/references/forensics-details.md` (the stub summarised; the reference carried the actual schemas and diagnostic commands). Both deleted in the v0.6 plugin reorganisation (PR #2340) with no successor found anywhere in the rebuilt `plugins/` tree (confirmed by content-grep, not filename-only). Some cross-references in the original source (to `specs/adhd/surface-contract.md` and `specs/CLIENT-TRANSLATION.md`) point to files that are themselves no longer present on `v0.6` as of this recovery — re-verify before relying on those specific pointers; the forensics procedure and schema above do not depend on them.
