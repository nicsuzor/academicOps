---
name: dump
alias: end_session
type: skill
category: instruction
description: Complete session handover. Interactive sessions may use the Short-form branch (task delta + follow-up); the Full-form path is commit + push + PR + release_task + halt.
triggers:
  - "emergency handoff"
  - "save work"
  - "handover"
  - "interrupted"
  - "session end"
  - "close session"
  - "wrap up"
  - "session complete"
  - "stop hook blocked"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
permalink: skills/dump
---

# /dump: session close and handover

Close a work session cleanly. This skill supports two paths — see §1 Branch decision below for the canonical rule:

1. **Short-form** (interactive sessions only, when work is continuing).
2. **Full-form** (everything else: normal end-of-session, autonomous/headless, emergency, cross-machine, interrupted).

## Contract

Per [[session-handover-contract]]:

- **Full-form** terminal output is a terse 5–10 line markdown block in a strict parseable format. **Short-form** output is a one-or-two-line next-step statement.
- **Full-form** writes structured session data to the task's YAML frontmatter via `release_task`. **Short-form** writes a delta to the task body via `update_task` and does not mutate frontmatter (other than ensuring `session_id` is set — see step 1 below).
- `$AOPS_SESSION_ID` is the join key that groups session artifacts. Both branches must ensure the bound task carries it.

## Execution

### 1. Branch decision (canonical)

This is the canonical decision rule. [[session-handover-contract]] §1 and the stop-gate handover-block template both reference this section rather than restating the conditions; do not duplicate the rule elsewhere.

Use **Short-form** only if **all** of the following are true:

- The session is **interactive** — the user is steering the conversation in real time, not an autonomous/headless polecat or cron worker.
- The bound task is **not complete** — more work remains, or you are blocked on input/decisions from the user.
- You have a **clear single next step or block** to state in one or two lines.
- The session is **continuing**, not ending.

Use **Full-form** in **every other case**, including: task complete, end-of-day close, autonomous/headless run (any polecat or cron-dispatched worker), emergency handover, cross-machine or cross-environment transfer, or the gate has reopened after further mutating tool calls.

### 2. Short-form Branch (Interactive)

1. **Update the task**. Use `update_task` to (a) write the latest delta — what was just done, what is left — to the **task body**, and (b) ensure the task's `session_id` frontmatter field equals `$AOPS_SESSION_ID`. Do not modify other frontmatter fields here; those are reserved for `release_task`.
2. **Present follow-up**. Output a one or two-line summary: "Next: [X]" or "Blocked on: [Y]".
3. **Finish**. Do NOT emit the handover block or halt. The gate is satisfied for this turn. If the gate reopens after further mutating tool calls, you must run the Full-form branch on the next close.

### 3. Full-form Branch (Standard)

1. **Commit, push, file PR**. If file changes exist, commit them, push the branch, and run `gh pr create --fill`. If no file changes, skip. Never end a session with uncommitted work.

2. **Update the project breadcrumb** (project → active epic → task linkage).

   The hierarchy stops being useful when you start from the project file and can't see what's actually being worked on. Leave a timestamped breadcrumb so a future reader landing on the project can find active epics with one hop.

   Procedure:

   1. Resolve the **current epic** from the bound task. Walk up the parent chain via `mcp__pkb__get_task`:
      - If the bound task's `frontmatter.type == "epic"`, it IS the current epic.
      - Otherwise, traverse `parent` until you reach a node with `type == "epic"`, OR until the next parent is `type == "project"` (in which case the last task before the project is the current epic), OR until there is no parent.
      - If no epic ancestor and no project ancestor exist and `frontmatter.project` is absent or empty, skip this step entirely.
   2. Resolve the **project node**. Prefer the bound task's `frontmatter.project` slug — resolve it directly via `mcp__pkb__get_document(id=<slug>)`. Only walk up from the epic to find a `type == "project"` ancestor as a fallback when the slug is missing or unresolvable. Do not infer project membership from task ID prefixes.
   3. Append a one-line breadcrumb to the project file's **Active Epics** section:

      ```
      mcp__pkb__append(
        id="<project-id-or-permalink>",
        section="Active Epics",
        content="- [[<epic-id>]] — <epic title> (task [[<bound-task-id>]], PR <url-or-'none'>)"
      )
      ```

      The `append` tool prepends a UTC timestamp and creates the section if missing. Existing entries are preserved — never rewrite the section.
   4. If the bound task IS the epic, drop the trailing `(task [[...]] ...)` clause.

   Skip silently when: no bound task, no project can be resolved (via ancestor or slug), or the project field doesn't resolve to a `type: project` document. Do not block the session close on a missing breadcrumb target.

3. **Call `release_task` once, with the full session payload.**

   ```
   mcp__pkb__release_task(
     id="<task-id>",
     status="merge_ready" | "review" | "done" | "blocked",
     session_id="$AOPS_SESSION_ID",
     pr_url="https://github.com/...",         # omit if no PR
     branch="<branch-name>",
     issue_url="https://github.com/.../issues/...",  # omit if none
     follow_up_tasks=["task-xxxx", "task-yyyy"],     # task IDs only; must exist
     release_summary="<one sentence, result-oriented, <= 500 chars>"
   )
   ```

   - **No task bound?** `release_task` auto-creates a minimal ad-hoc task under the `adhoc-sessions` root ([[T4]]). Until T4 lands, fall back to `create_task` first, then `release_task` on the new id.
   - **`release_summary` quality**: this field is the primary signal for the Recent Sessions dashboard, where it appears in a long stack of unrelated handovers from other sessions. **Write it for that audience — a future reader who has none of this session's context.**

     Three requirements:

     1. **Result-oriented**, not activity-oriented. "Implemented YAML schema extension for session handover", not "I worked on the schema".
     2. **Self-contained**. Every artifact you reference must carry enough description that the reader can identify it without opening the session. Name things: which workflow, which incident, which agent, which file, which issue#. References by role alone ("the enforcer", "the orchestrator", "the flag", "the failure") are useless out of context — name what specifically.
     3. **Concrete IDs with description**. Issue and PR references must be `org/repo#NNN` AND a phrase saying what the issue/PR is about, so the line is parseable without clicking through.

     Bad (real example, do not write summaries like this):
     > Root cause analysis completed. Identified the failure as instruction-weighting + detection-failure (enforcer had discretionary language and chose not to block; orchestrator should have treated the flag as actionable). GitHub issue filed.

     Why it's bad: which failure? which enforcer? which orchestrator? which flag? which issue? In a stack of 30 handovers, this conveys nothing.

     Good:
     > Root-caused why agent-merge-prep silently approved 3 PRs on 2026-04-25 without enforcer veto. Cause: enforcer prompt said "consider blocking" (discretionary) and the orchestrator treated WARN as ALLOW. Filed nicsuzor/academicOps#612 (harden enforcer language + orchestrator WARN handling).

     Length budget: ≤ 500 chars. Tight is fine. Cryptic is not.
   - **Follow-ups**: every concrete future action must be a real PKB task before you list it here. Do not put bullet prose into `release_summary` or session notes — the dashboard and `/recap` only see structured fields.
   - **Fallback**: if `release_task` is unavailable, `update_task(id=..., status="merge_ready")` keeps the supervisor unblocked, but the dashboard loses this session.
   - **Polecat note**: calling `release_task` with a terminal status is what lets the polecat supervisor detect termination via PKB polling. Skipping this leaves Gemini workers running until external timeout (#521).

4. **Emit the required reflection blocks** (`## Framework Reflection`, `## Output`, `## Tasks worked`).

   Full-form sessions MUST include all three blocks before the handover block. `transcript.py` extracts each into structured metadata (`framework_reflections`, `outputs`, `tasks_worked`, `references`, `quality_warnings`); missing or empty blocks emit warnings into `quality_warnings` rather than being silently dropped. See [[transcript-metadata-schema]] for the wire format.

   **a. `## Framework Reflection` — required, must be useful**

   Must address, in concrete terms:

   - **One real friction point** the agent hit (tool, instruction, hook, gate), with enough context to act on it. NOT generic procedure-griping — only flag procedures that are truly awful or broken.
   - **One instruction or tool improvement** the agent would propose, with a pointer to the file/skill/agent it would change.
   - _(Optional)_ one thing that worked well and is worth keeping — short, specific, attributable.

   **Quality bar.** Reject reflections that are generic ("everything was fine", "the procedure was annoying"), propose new tools/features/skills/commands ("we should build an X"), pitch grand refactors, or contain bare identifiers without a precis. Accept reflections that document concrete experienced problems and (where applicable) file bug reports.

   The reflection's job is **bug reports + friction analysis**, not feature work. If you find yourself proposing a new capability, stop — file the underlying friction instead.

   **Identifiers + precis.** Every reference to a task, PR, commit, issue, file, or other artefact MUST carry both:

   1. The **stable identifier** (`task-id`, `PR #NNN`, `org/repo#NNN`, commit SHA, etc.).
   2. A **short precis in parentheses** — what the thing is, in <60 chars.

   Required form: `task-acba1234 (/dump: add explicit process reflection)`, `PR #847 (transcript.py: extract reflection metadata)`, `commit cf83b1f (pkb: broaden --allowed-hosts)`. A bare `task-acba1234` is non-compliant — `transcript.py` flags it as a `bare-identifier` quality warning.

   **Useful (require)** — concrete description of friction, surprises, dead-ends, wasted token paths, environment mismatches, instructions that were wrong or absent. Bug reports for things that look like real bugs (`$AOPS_SESSIONS=...` referenced but doesn't exist on worker container — file it). Token-cost breakdown of friction is the most useful framing.

   **Not useful (reject)** — new tool/feature suggestions ("an `aops session inspect <id>` command that pulls just the summary…" — reject; this exact reflection was filed and cancelled). Feature development tasks of any kind. Grand refactors ("split transcript_parser.py is 3,640 lines"). Generic procedure-griping.

   **b. `## Output` — required, explicit artefact link**

   Final summary MUST contain a `## Output` block with an explicit URL to the artefact produced — PR, commit, issue, deployed doc, etc. This is the forcing function: requiring a real link implicitly requires the agent to actually file the PR / push the commit / open the issue. **No link → /dump does not pass.**

   Example:

   ```markdown
   ## Output

   - PR https://github.com/nicsuzor/academicOps/pull/847 (transcript.py: extract reflection metadata)
   ```

   If genuinely no artefact exists (pure planning session, blocked on input, etc.), state it explicitly: `Output: none — <reason>`. The extractor distinguishes "no output declared" (warning) from "explicit none" (acknowledged).

   **c. `## Tasks worked` — required, source-of-truth list**

   Enumerate every task created, updated, completed, or cancelled during the session. This is the authoritative list — `transcript.py` cannot reliably derive it from git or PKB without ambiguity, so it must be written explicitly.

   Format:

   ```markdown
   ## Tasks worked

   - task-5a54f813 (/dump + transcript.py: require useful framework reflection) — updated, added quality bar
   - task-d4932f32 (audit find_existing_* early-returns) — created
   - task-acd9af54 (aops session inspect tool) — cancelled per user
   ```

   Each entry: `- <id> (<precis>) — <action>`. Action verbs the extractor recognises: `created`, `updated`, `completed`, `cancelled`, `referenced`. Bare ids without a precis fail the quality bar.

5. **Emit the handover block**. Exactly this shape, 5–10 lines:

   ```markdown
   ### Session Handover

   - **Session ID**: `$AOPS_SESSION_ID`
   - **Primary Task**: `<task-id>` (<short title>)
   - **PR**: <url>
   - **Branch**: `<branch>`
   - **Issue**: <url or "none">
   - **Follow-ups**: `<task-id> (<short title>)`, `<task-id> (<short title>)` (or "none")
   - **Summary**: <release_summary value — must satisfy the self-contained quality bar above>
   ```

   Omit `PR` and `Issue` lines if not set. Omit `Follow-ups` if empty. Do not add any prose before or after the block.

   Follow-up task IDs must each carry a short parenthetical title for the same reason `release_summary` must — a stack-of-handovers reader can't resolve `task-0f7d3877` without it.

6. **Halt.** Nothing follows the handover block.

## What this skill does NOT do

- Does **not** persist discoveries to memory, codify learnings, or file GitHub issues. Those are separate skills ([[remember]], [[learn]]) and belong in the session body, not the close.
- Does **not** loop on itself. If the gate reopens after further edits, run `end_session` again.
