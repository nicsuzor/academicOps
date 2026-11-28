---
name: learn
description: Diagnose systemic root causes of framework faults from session execution traces or non-traced CI runs, execute or persist tiered remedies, and consolidate shared-root-cause framework issues. Use for "diagnose this error", "why did the session fail", "learn from this run", or review misses. Exclude for traced sessions with missing Phoenix spans (halt instead), non-framework faults (including local problems in third-party repositories), or immediate task retries.
---

# Learn

Diagnose systemic failure classes in the framework from Arize Phoenix execution traces (or `gh` PR diffs, review comments, check runs, and instructions solely for non-traced CI / CI-workflow runs), verify outline persistence where the composed workflow directs, and execute or persist minimally effective remedies as the composed workflow directs.

- **Scope**: Framework faults only (including local workflow, rule, or instruction defects surfaced in third-party repos), never third-party repo bugs, external tools, models, or services.
- **Prerequisites**: Access to framework governance documents, `crew:axioms`, and the execution traces or CI artifacts under investigation.

## Protocol

1. **Retrieve execution record and persist outline**:
   - **Traced sessions (`phoenix` only)**: Query OpenTelemetry spans via `phoenix` or read the session outline alongside framework governance docs; if spans exist without a persisted outline, persist it at the destination specified by the composed workflow (e.g., `out-<session_slug>` in the PKB when directed).
   - **Strict trace boundary**: Never inspect repo source code or scrape local transcript/debug log files; if Phoenix spans are unavailable on a traced session, halt immediately and report.
   - **Non-traced CI / CI-workflow runs**: Solely when execution ran on a non-traced CI surface emitting no OTel spans, inspect PR diffs, review comments, check runs, and instructions via `gh`.
2. **Diagnose systemic framework cause (active voice, hearsay-free)**:
   - **Framework defect, never agent fault**: An agent's action is an intermediate trace event, never the root cause. Name the specific acting role in active voice (passive voice is forbidden), quote the exact instruction, workflow, contract, or tool gap that led them to act, and state the framework defect.
   - **Traces over hearsay**: Treat agent explanations as hearsay (`explanations-not-reasons`). Re-read primary user words and anchor on observed spans (`phoenix`) or `gh` CI artifacts.
   - **Workflow compliance vs missing rules**: Diagnose skipped or misapplied workflow steps as workflow compliance or unclear wording, never propose per-workflow enforcement rules or map rows.
   - **Auth failures are configuration failures**: Stop immediately on login/auth failures and report as a configuration failure; file no issue and post no comment.
3. **Generalise the instance**: Even if already fixed, state both:
   - _General bug_: the mechanism that produced this instance and will produce others like it.
   - _Verification miss_: the existing control (axiom, rule, skill, or test) governing the class and why it failed to fire or pass (exhaustive search required before claiming none exists).
4. **Classify typed remedy & execute/persist via the Remedy Ladder** (prefer lowest effective tier; workflows bypass framework enforcement mapping):
   - Classify each remedy as **`bug fix at source`** (single-incident defect in a tool, workflow, or instruction) or **`recurring local-rule or mechanism proposal`** (local rule or single-step enforcement escalation only after repeated instances prove single-incident fixes insufficient).
   - Execute or route remedies at the lowest effective tier as directed by the composed workflow rather than leaving unrouted prose proposals:
     1. **Local project workflow or instruction**: Update or propose a project-scoped workflow or instruction fix, or route a repo-targeted follow-up per the composed workflow within `data-boundaries`.
     2. **User-tier workflow**: Update or propose a user-tier workflow template as directed by the composed workflow.
     3. **Universal workflow**: Patch or route a follow-up for the universal workflow template as directed by the composed workflow.
     4. **Framework enforcement issue** (last resort for universal axioms, security bounds, or structural controls):
        - Where issue tracking is available and directed by the workflow, inspect open framework issues read-only to consolidate shared root causes.
        - Format with any repo learn template present or [issue-template.md](references/issue-template.md) scrubbed of personal names, credentials, private paths/domains, session IDs, internal trailers, and PKB/task IDs, and persist or route at the workflow-specified destination (holding external-audience items for explicit prior user approval per `data-boundaries`).
   - Hold any remote-repo or external-audience remedy outside the user's boundary at the workflow-specified destination pending explicit prior approval; never modify third-party repository source directly.
   - Before finishing a traced session, verify the session outline is persisted where the composed workflow specifies and release `done` once remedies or follow-ups are recorded as directed (never `partial` solely because follow-up tasks remain queued). Knowledge notes (`type: note`, `knowledge`, `memory`) never hold bug logs or issue commentary.

## Output

Return findings to calling agents covering these content layers:

- **Session outline / Target surface**: Persisted session outline location (e.g., `[[out-<session_slug>]]` when directed) or CI/PR reference.
- **Evidence**: Session/conversation ID, relevant OTel span IDs (or `gh` PR/CI excerpts), and tool/error/latency excerpts.
- **Root cause**: Active-voice diagnosis naming the actor, quoting the governing instruction, and stating the framework defect.
- **Verification miss**: Control that should have caught the class and why it missed.
- **Typed Remedy**: Classification (`bug fix at source` vs `recurring local-rule or mechanism proposal`), Remedy Ladder tier (`1-4`), and executed or routed artifact at the destination specified by the composed workflow.
- **Auth status**: Note when a login/auth failure was returned as a configuration failure with no issue filed.
