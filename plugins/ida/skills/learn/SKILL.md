---
name: learn
description: Diagnose systemic root causes of framework faults from session execution records, recommend minimally effective workflow remedies first, and persist session outlines. Use for "diagnose this error", "why did the session fail", "learn from this run", or session post-mortems; the PKB custodian (Pauli) runs it. Exclude for non-traceable sessions, non-framework faults (including local problems in third-party repositories), or immediate task retries.
---

# Learn

Diagnose systemic failure classes in the framework from OpenTelemetry execution traces, persist condensed session outlines, and recommend minimally effective workflow remedies before escalating to framework enforcement changes. `/learn` handles framework faults only (including local workflow, rule, or instruction problems when working on third-party repos), never third-party repo bugs, external tools, models, or services. The PKB custodian (Pauli) runs this skill exclusively inside an isolated container in the framework repository (`project: aops`) with access to framework governance documents and `rbg:axioms`.

## Protocol

1. **Retrieve execution trace and outline**:
   - Query OpenTelemetry spans via `ida:phoenix` (or read existing outline note `out-<session_slug>`) alongside framework governance and enforcement documents.
   - If spans exist without a persisted outline, save a condensed note via `pkb_create` (`type: "note"`, `title: "Outline: <session_slug> (<summary>)"`, `slug: "out-<session_slug>"`, `tags: ["phoenix", "outline", "learn"]`).
   - Ground analysis strictly in Phoenix traces and governance specifications. Never inspect application source code or scrape local transcript or debug log files. If Phoenix traces are unavailable, halt and report.
2. **Diagnose systemic framework cause**:
   - **Root causes are framework defects, never agent faults**: An agent's action is an intermediate trace event, never the root cause. Locate and quote the instruction, workflow, contract, or tool gap that permitted or caused the failure.
   - **Active voice; name actor and quote instruction**: Passive voice is forbidden across findings, issues, and reports. Name who acted (e.g. "The coordinator sent the run to the custodian"), immediately quote the governing instruction (`"..."`), and state the framework defect.
   - **Traces over hearsay**: Treat agent explanations as hearsay (`explanations-not-reasons`). Re-read the primary user words and anchor on trace evidence (tool inputs, error payloads, schema mismatches, hook blocks, latency spikes).
   - **Workflow non-compliance is not a missing rule**: Diagnose skipped or misapplied workflow steps as poor workflow compliance or unclear workflow wording, never propose per-workflow enforcement rules, specifications, or checks.
   - **Auth failures are configuration failures**: For login or authentication failures, stop and tell the caller it is a configuration failure; file no issue and post no comment.
3. **Generalise the instance**: Even if already fixed, state both:
   - _General bug_: the mechanism that produced this instance and will produce others like it.
   - _Verification miss_: the existing control (axiom, rule, skill, or test) governing the class and why it failed to fire or pass (exhaustive search required before claiming none exists).
4. **Proportional Workflow Remedy Ladder** (prefer the lowest effective tier; workflow changes bypass framework enforcement mapping):
   1. **Local project workflow or instruction**: Patch or propose a project-scoped template (`type: template`, `project: <project_id>`) or local project instructions.
   2. **User PKB workflow**: Patch or propose a user-scoped template (`type: template`, `project: null`).
   3. **Universal workflow**: Propose a minimally effective patch to an existing universal workflow template in the workflow library (PR to `dev`).
   4. **Framework enforcement issue** (last resort, e.g. security bounds, credential leakage, container isolation, universal axiom rules): Read any repository learn issue template, if present, or [issue-template.md](references/issue-template.md) before formatting the payload. Check existing repo issues read-only (`gh issue view`, `gh issue list`) to avoid duplicates. Format one issue (or evidence-bump comment on an existing issue) with trace data scrubbed of personal names, credentials, private paths, session IDs, telemetry domains, and PKB/task IDs, and queue a `type: task` node on the PKB graph for a repository-capable worker (requiring prior user approval on external-audience surfaces per `data-boundaries`).
5. **Cross-repository and persistence boundaries**:
   - Never modify remote repositories from the framework container. For Tier 1-3 remedies in another repository inside `data-boundaries`, queue a follow-up `type: task` via `/q` targeting that repository and release as `partial`; for external-audience repositories, hold the proposal in the report and PKB for explicit user approval first.
   - Knowledge notes (`type: note`, `knowledge`, `memory`) never hold bug logs or issue commentary.

## Output

Return a markdown report containing:

- **Session outline**: PKB wikilink (`[[<outline_note_id>]]`).
- **Evidence**: Session/conversation ID, relevant OTel span IDs, and tool/error/latency excerpts.
- **Root cause**: Active-voice diagnosis naming the actor, quoting the governing instruction, and stating the framework defect.
- **Verification miss**: Control that should have caught the class and why it missed.
- **Remedy**: Proposed minimally effective fix with Remedy Ladder tier and draft template patch, PR link, or formatted Tier 4 issue/evidence-bump payload per [issue-template.md](references/issue-template.md).
- **Queued tasks & artifacts**: PKB IDs of queued `type: task` follow-ups and links to created/updated PKB templates or PRs (or note that login/auth failure is a configuration failure with no issue filed).
