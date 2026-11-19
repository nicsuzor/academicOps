---
name: learn
description: Diagnose systemic root causes of framework faults from session execution records or non-traced CI runs, classify typed remedies, and consolidate shared-root-cause framework issues. Use for "diagnose this error", "why did the session fail", "learn from this run", or Class D PR review misses; the PKB custodian (Pauli) runs it. Exclude for traced sessions with missing Phoenix spans (halt instead), non-framework faults (including local problems in third-party repositories), or immediate task retries.
---

# Learn

Diagnose systemic framework faults using Arize Phoenix execution traces (or `gh` PR diffs, review comments, and instructions solely for non-traced CI / GitHub Actions runs). Scope covers faults in our own framework (including workflow, rule, or instruction defects surfaced while working in third-party repositories); exclude local third-party repo bugs, external services/CLIs, and direct application source-code inspection.

## Execution Environment

Run `/learn` in an isolated `academicOps` (`project: aops`) container environment so governance specifications (`specs/ENFORCEMENT-MAP.md`, `specs/enforcement/enforcement.md`, `plugins/rbg/skills/axioms/`) are present.

## Protocol

1. **Retrieve execution record and persist session outline**:
   - **Traced sessions (`ida:phoenix` only)**: Fetch spans via `ida:phoenix` declarative templates or an existing `out-<session_slug>` note alongside governance specs. If Phoenix spans exist without a saved note, persist `out-<session_slug>` via `pkb_create` (`type: "note"`, `title: "Outline: <session_slug> (<summary>)"`, `slug: "out-<session_slug>"`, `tags: ["phoenix", "outline", "learn"]`). Never fall back to local `.system_generated/logs/transcript*.jsonl` or `/tmp/aops_debug_hooks_*.jsonl`; if Phoenix spans are missing or unavailable, halt immediately and report the gap.
   - **Non-traced surface exception (CI / GitHub Actions)**: Solely when execution ran on a non-traced CI/GHA surface emitting no OTel spans, inspect PR diffs, review comments, check runs, and instructions via `gh`.

2. **Diagnose systemic framework cause (active voice, hearsay-free)**:
   - **Framework defect, never agent fault**: Agent choices, omitted steps, or capabilities are trace events, never root causes. Name the specific acting role in active voice (e.g. `"the coordinator dispatched without credentials"` -- passive voice prohibited), quote the exact instruction/skill/workflow/tool contract that led them to act, and identify the missing, contradicted, or ambiguous framework defect.
   - **Workflow compliance vs missing rules**: Skipped or misapplied workflow steps are workflow-compliance or ambiguous-wording failures under `"follow the applicable workflow"`, never grounds to invent per-workflow rules, specs, or enforcement-map rows.
   - **Authentication/login failures**: Stop immediately and report as configuration failure (file no issue, post no comment).
   - **Empirical trace evidence & hearsay bar**: Cite observed span mechanics (tool errors, schema mismatches, hook blocks, timeouts) and primary user prompts directly rather than agent self-explanations or unread application source code.

3. **Generalise instance & search existing controls**:
   - _General bug_: Name the mechanism generating the failure class, even if the instance is already patched.
   - _Verification miss_: Exhaustively search axioms, rules, skills, and `specs/ENFORCEMENT-MAP.md` for the governing control and explain why it failed to fire or block.

4. **Classify typed remedy & proportional ladder**:
   - Classify each remedy explicitly as either:
     - **`bug fix at source`**: single-incident defect in a tool, workflow, local rule, or instruction (addressed at the lowest effective tier).
     - **`recurring local-rule or one-step mechanism proposal`**: local project rule or single-step enforcement-pyramid escalation (`specs/enforcement/enforcement.md`) only when repeated instances prove single-incident fixes insufficient.
   - Remedy ladder (prefer patching existing artifacts cleanly; never copy narrative bloat):
     1. Project template (`type: template`, project-scoped) or local repo rules (`AGENTS.md`, `.agents/rules/`).
     2. User-scoped PKB template (`type: template`, `project: null`).
     3. Universal workflow (`plugins/ida/skills/workflow-library/workflows/wf-*.md` via standard PR into base; workflows bypass formal framework-change enforcement-map/spec gates and add 0 map rows).
     4. Framework enforcement issue (Tier 4 fallback for universal axioms, security bounds, or structural gates).

5. **Follow-up placement & clean completion (`headless-workers.md`)**:
   - Never modify third-party repository source directly from the framework container.
   - **Inside the user's own organisations and designated repositories**: When executed by custodian or container coordinator (`/supervise`), mint and wire the follow-up `/q` fix task (`typed remedy`, concise criteria, target repo/project); when run by a leaf `/pull` worker, record the structured `/q` proposal in `## Report` without mutating sibling tasks.
   - **Outside the user's boundary**: Keep proposed follow-up PRs/issues in `## Report` and the PKB for explicit prior user approval.
   - **Complete to `done`**: On traced sessions, verify `out-<session_slug>` is persisted; then release `done` (never `partial` solely because queued follow-ups remain).

6. **Shared-root-cause issue consolidation (`data-boundaries`)**:
   - File no issue for auth failures or for Tier 1–3 bugs **only when actually executed/persisted** (template created/updated, PR opened, or `/q` fix task queued -- unexecuted prose proposals must escalate to Tier 4).
   - Search open framework issues (`gh issue list`, `gh issue view`) before creating one: append an evidence comment citing the new instance when an open issue covers the shared root cause; otherwise draft/file one evidence-grounded issue using `.github/ISSUE_TEMPLATE/learn.md` (when present) scrubbed of personal names, credentials, private paths/domains, session IDs, internal trailers, and PKB note/task IDs.
   - **Boundary handling**: Inside **the user's own organisations and designated repositories**, create the consolidated issue or append the evidence comment directly; outside that boundary, hold the scrubbed draft in `## Report` / PKB pending explicit user approval.

## Output

Emit a concise Markdown report containing **Session outline / Target surface** (`[[out-<session_slug>]]` or CI/PR ref), **Evidence** (span IDs or `gh` CI excerpts), **Root cause** (active voice, named actor, quoted instruction, framework defect), **Verification miss**, **Typed Remedy** (classification + tier `1–4`), and **Follow-up `/q` tasks & Issue consolidation** (queued task IDs or `/q` proposal + single issue/comment URL or held draft). Return auth failures immediately as configuration failures.
