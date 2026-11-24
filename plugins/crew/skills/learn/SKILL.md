---
name: learn
description: Diagnose systemic root causes of framework faults from session execution traces or non-traced CI runs, execute or persist tiered remedies, and consolidate shared-root-cause framework issues. Use for "diagnose this error", "why did the session fail", "learn from this run", or review misses; the PKB custodian (Pauli) runs it. Exclude for traced sessions with missing Phoenix spans (halt instead), non-framework faults (including local problems in third-party repositories), or immediate task retries.
---

# Learn

Diagnose systemic failure classes in the framework from Arize Phoenix execution traces (or `gh` PR diffs, review comments, check runs, and instructions solely for non-traced CI / CI-workflow runs), verify `out-<session_slug>` persistence, and execute or persist minimally effective remedies before escalating to framework enforcement issues.

- **Scope**: Framework faults only (including local workflow, rule, or instruction defects surfaced in third-party repos), never third-party repo bugs, external tools, models, or services.
- **Executor**: The PKB custodian (`pauli`) runs this skill inside an isolated container in `project: aops` with access to framework governance documents and `crew:axioms`.

## Protocol

1. **Retrieve execution record and persist outline**:
   - **Traced sessions (`crew:phoenix` only)**: Query OpenTelemetry spans via `crew:phoenix` or read `out-<session_slug>` alongside framework governance docs; if spans exist without a note, save `out-<session_slug>` via `pkb_create` (`type: "note"`, `title: "Outline: <session_slug> (<summary>)"`, `slug: "out-<session_slug>"`, `tags: ["phoenix", "outline", "learn"]`).
   - **Strict trace boundary**: Never inspect repo source code or scrape local transcript/debug log files; if Phoenix spans are unavailable on a traced session, halt immediately and report.
   - **Non-traced CI / CI-workflow runs**: Solely when execution ran on a non-traced CI surface emitting no OTel spans, inspect PR diffs, review comments, check runs, and instructions via `gh`.
2. **Diagnose systemic framework cause (active voice, hearsay-free)**:
   - **Framework defect, never agent fault**: An agent's action is an intermediate trace event, never the root cause. Name the specific acting role in active voice (passive voice is forbidden), quote the exact instruction, workflow, contract, or tool gap that led them to act, and state the framework defect.
   - **Traces over hearsay**: Treat agent explanations as hearsay (`explanations-not-reasons`). Re-read primary user words and anchor on observed spans (`crew:phoenix`) or `gh` CI artifacts.
   - **Workflow compliance vs missing rules**: Diagnose skipped or misapplied workflow steps as workflow compliance or unclear wording, never propose per-workflow enforcement rules or map rows.
   - **Auth failures are configuration failures**: Stop immediately on login/auth failures and report as a configuration failure; file no issue and post no comment.
3. **Generalise the instance**: Even if already fixed, state both:
   - _General bug_: the mechanism that produced this instance and will produce others like it.
   - _Verification miss_: the existing control (axiom, rule, skill, or test) governing the class and why it failed to fire or pass (exhaustive search required before claiming none exists).
4. **Classify typed remedy & execute/persist via the Remedy Ladder** (prefer lowest effective tier; workflows bypass framework enforcement mapping):
   - Classify each remedy as **`bug fix at source`** (single-incident defect in a tool, workflow, or instruction) or **`recurring local-rule or mechanism proposal`** (local rule or single-step enforcement escalation only after repeated instances prove single-incident fixes insufficient).
   - Execute or persist Tier 1-3 remedies rather than leaving prose-only proposals (unexecuted prose proposals must escalate to Tier 4):
     1. **Local project workflow or instruction**: Create/update a project-scoped PKB template (`type: template`, `project: <project_id>`) or, inside `data-boundaries` for another repo, queue a follow-up `type: task` via `/q` targeting that repo.
     2. **User PKB workflow**: Create or update a user-scoped PKB template (`type: template`, `project: null`).
     3. **Universal workflow**: Open a PR patching an existing universal workflow template (or queue the follow-up task).
     4. **Framework enforcement issue** (last resort for universal axioms, security bounds, or structural controls):
        - Check open framework issues read-only (`gh issue list`, `gh issue view`) to consolidate shared root causes (append an evidence comment to a matching open issue, or prepare one new issue).
        - Format with any repo learn template present or [issue-template.md](references/issue-template.md) scrubbed of personal names, credentials, private paths/domains, session IDs, internal trailers, and PKB/task IDs, then queue a `type: task` node carrying [issue-template.md](references/issue-template.md) (holding external-audience items for explicit prior user approval per `data-boundaries`).
   - Hold any remote-repo or external-audience remedy outside the user's boundary in the report and PKB pending explicit prior approval; never modify third-party repository source directly from the framework container.
   - Before finishing a traced session, verify `out-<session_slug>` is persisted in the PKB and release `done` once remedies/queued tasks are recorded (never `partial` solely because follow-up tasks remain queued). Knowledge notes (`type: note`, `knowledge`, `memory`) never hold bug logs or issue commentary.

## Output

Return findings to calling agents solely in prose Argdown blocks per `ida:premise-check` (reserving Markdown for persisted PKB/issue artifacts or direct user replies), covering these content layers:

- **Session outline / Target surface**: PKB wikilink (`[[out-<session_slug>]]`) or CI/PR reference.
- **Evidence**: Session/conversation ID, relevant OTel span IDs (or `gh` PR/CI excerpts), and tool/error/latency excerpts.
- **Root cause**: Active-voice diagnosis naming the actor, quoting the governing instruction, and stating the framework defect.
- **Verification miss**: Control that should have caught the class and why it missed.
- **Typed Remedy**: Classification (`bug fix at source` vs `recurring local-rule or mechanism proposal`), Remedy Ladder tier (`1-4`), and executed/persisted artifact (PKB template link, PR link, queued `/q` task ID, or queued Tier 4 `type: task` carrying [issue-template.md](references/issue-template.md) / held external draft).
- **Auth status**: Note when a login/auth failure was returned as a configuration failure with no issue filed.
