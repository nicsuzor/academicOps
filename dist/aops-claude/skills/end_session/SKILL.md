---
name: end_session
alias: end-session
type: skill
category: instruction
description: Canonical session close — commit, push, PR, release_task, reflection blocks, handover. Use /dump for emergency bail (no commit/PR/reflection).
triggers:
  - "save work"
  - "handover"
  - "session end"
  - "close session"
  - "wrap up"
  - "session complete"
  - "task complete"
  - "stop hook blocked"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
permalink: skills/end-session
---

# /end-session: canonical session close and handover

Close a work session cleanly with the full quality bar: commit, push, PR, `release_task`, reflection blocks, handover.

For an **emergency bail** (mid-flight work, context full, restart needed) use `/dump` instead — it captures a resume task + short handover and skips commit/PR/reflection.

## Before you invoke this skill: did you actually finish?

This skill is for **closing** a session, not for **escaping** one. Two failure modes to check yourself against before running it:

- **Don't finish early.** If the bound task is not actually done and you are not blocked on user input or external dependencies, you are not at end-of-session yet — keep working. "I have written something plausible and now want to stop" is not a complete task. Re-read the task body and acceptance criteria; if any line is not satisfied and you have the capability to satisfy it, do that first.

- **Don't ask permission for work that is within your scope.** _Enforces `exercise-authority` Edge 2 (FM-1)._ Decisions inside the four corners of the bound task — and inside your declared area of expertise — are yours to make. Picking a library when the task says "implement X", choosing a sensible refactor, deciding test layout, naming things, fixing an obvious bug you hit along the way: do it, don't poll. Save user questions for: scope changes, irreversible/destructive actions, ambiguous requirements you cannot resolve from the task text, and decisions that depend on private context the user has and you don't. Commit + push at session end is non-askable for a clean working tree on a feature branch — that is exactly the workflow-required action `exercise-authority` obligates.

If you want to **keep going** rather than close, do not invent a short-form handover branch. Use the `AskUserQuestion` tool (or the equivalent question tool in your harness) with a **specific recommended next step** the user can approve or redirect. Example: "Recommend: extract the rate-limiter into a separate module, then land the PR. Proceed, or stop here?" — not "what should I do next?".

If you are genuinely at end-of-session, continue below.

## Contract

Per [[session-handover-contract]]:

- Terminal output is a terse 5–10 line markdown block in a strict parseable format.
- Structured session data is written to the task's YAML frontmatter via `release_task`.
- `$AOPS_SESSION_ID` is the join key that groups session artifacts. The bound task must carry it.

## Execution

### 1. Branch decision

Use the **Read-only Q&A** path if **all** of the following are true:

- No mutating tools (`Edit`, `Write`, `replace`, `write_file`, `NotebookEdit`, `MultiEdit`) have been used in the session.
- No `Bash` or `run_shell_command` tool has been used for anything other than read-only discovery (e.g. `git status`, `ls`, `grep`).
- No task is bound to the session (or the bound task has not been mutated).
- No new tasks have been created.

Otherwise, use the **Full-form** path. There is no longer a "Short-form" interactive shortcut — if more work remains and the session is continuing, you should not be invoking this skill yet (see the "did you actually finish?" preamble above). For mid-flight bail without finishing, use `/dump`.

### 2. Read-only Q&A path

1. **Emit one-liner**. Output `Output: none — read-only Q&A`.
2. **Finish**. Do NOT emit the handover block or call `release_task`.

### 3. Full-form path (standard close)

0. **Resolve the bound task** (issue #739). Before any other step, determine which task this session is closing against. Source-of-truth order:

   1. **`/pull`-written binding file**. `/pull <task-id>` persists the claimed task at `$AOPS_SESSION_STATE_DIR/$AOPS_SESSION_ID-bound-task.txt` (see [[../../commands/pull.md]] Step 1.4). Read it with:

      ```bash
      state_dir="${AOPS_SESSION_STATE_DIR:-$HOME/.aops/sessions}"
      sid="${AOPS_SESSION_ID:-${GEMINI_SESSION_ID}}"
      bound_task_id=""
      if [ -n "$sid" ]; then
        bound_task_id="$(cat "$state_dir/${sid}-bound-task.txt" 2>/dev/null | head -n1 | tr -d '[:space:]')"
      fi
      ```

      If `$bound_task_id` is non-empty, use it as the `id=` for `release_task` in step 3. This is the **primary signal** — prefer it over any inference from session activity.

   2. **Explicit task argument**. If the user invoked `/end_session <task-id>`, that overrides any binding file.

   3. **Fallback**. No binding file and no explicit arg → fall through to `release_task`'s auto-create-ad-hoc branch (current behaviour). This is the genuine "unbound session" case.

   Record `$bound_task_id` (or its absence) and reuse it as the `<bound-task-id>` placeholder throughout the rest of this skill — the breadcrumb in step 2, the `id=` in step 3, and the handover block in step 5.

1. **Commit, push, file PR**. If file changes exist, commit them, push the branch, and run `gh pr create --fill`. If no file changes, skip. Never end a session with uncommitted work — if work is genuinely incomplete, use `/dump` instead so it is captured as a resume task rather than abandoned.

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

   Skip silently when: no bound task, no project can be resolved (via ancestor or slug), or the project field doesn't resolve to a slug in `$AOPS_SESSIONS/polecat.yaml`. Do not block the session close on a missing breadcrumb target.
3. **Call `release_task` once, with the full session payload.**

   _Pre-check children_: before calling `release_task` to transition the task to a terminal state (`done`, `cancelled`, `superseded`, or `merge_ready`), you MUST read the task using `mcp__pkb__get_task` and verify its `children[]` array. If any child is NOT in a terminal state (`done`, `cancelled`, `superseded`, or `archived`), you MUST REFUSE to close the task. Halt the session close and either surface the issue to the user, or resolve the children first.

   ```
   mcp__pkb__release_task(
     id="<bound-task-id>",                    # from step 0; required if a binding exists
     status="merge_ready" | "review" | "done" | "blocked",
     session_id="$AOPS_SESSION_ID",
     pr_url="https://github.com/...",         # omit if no PR
     branch="<branch-name>",
     issue_url="https://github.com/.../issues/...",  # omit if none
     follow_up_tasks=["task-xxxx", "task-yyyy"],     # task IDs only; must exist
     release_summary="<one sentence, result-oriented, <= 500 chars>"
   )
   ```

   - **Bound task resolved in step 0?** Pass it as `id=`. This is the fix for #739 — without it, sessions started via `/pull <task-id>` create stray ad-hoc records under `adhoc-sessions` instead of completing the actual epic.
   - **No task bound** (step 0 produced no id and no explicit arg)? `release_task` auto-creates a minimal ad-hoc task under the `adhoc-sessions` root ([[T4]]). Until T4 lands, fall back to `create_task` first, then `release_task` on the new id.
   - **On success, clean up the binding file** so a subsequent `/end_session` invocation in the same session (e.g. the gate reopens after follow-up edits) doesn't re-complete the same task:

     ```bash
     sid="${AOPS_SESSION_ID:-${GEMINI_SESSION_ID}}"
     if [ -n "$sid" ]; then
       state_dir="${AOPS_SESSION_STATE_DIR:-$HOME/.aops/sessions}"
       rm -f "$state_dir/${sid}-bound-task.txt"
     fi
     ```

     Skip cleanup if `release_task` failed — the next invocation will retry against the same binding.
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

4. **Emit the required reflection blocks** (`## Output`, `## Tasks worked`, `## Framework Reflection`).

   Full-form sessions MUST include all three blocks before the handover block. `transcript.py` extracts each into structured metadata (`framework_reflections`, `outputs`, `tasks_worked`, `references`, `quality_warnings`); missing or empty blocks emit warnings into `quality_warnings` rather than being silently dropped. See [[transcript-metadata-schema]] for the wire format.

   **Environment-Gated Behaviors:**
   Check the following environment variables and apply their rules to your closing output if set to `1` (or if marked default-on):
   - `AOPS_GATE_HEDGE_CLAIMS` (default-on, treat as always set): **Hedge your claims.** Your closing output names its load-bearing claims, the evidence behind each, your confidence, and — for anything you're less than highly confident in — the next most plausible alternative. Confidence floor is "I checked"; "should work" or "probably" are halts to convert into observations or hedges.
   - `AOPS_GATE_STATE_QA`: Closing output states: what was the user's question? What did you deliver?

   **a. `## Output` — required, explicit artefact link**

   Final summary MUST contain a `## Output` block with an explicit URL to the artefact produced — PR, commit, issue, deployed doc, etc. This is the forcing function: requiring a real link implicitly requires the agent to actually file the PR / push the commit / open the issue. **No link → /end-session does not pass.**

   Example:

   ```markdown
   ## Output

   - PR https://github.com/nicsuzor/academicOps/pull/847 (transcript.py: extract reflection metadata)
   ```

   If genuinely no artefact exists (pure planning session, blocked on input, etc.), state it explicitly: `Output: none — <reason>`. The extractor distinguishes "no output declared" (warning) from "explicit none" (acknowledged).

   **b. `## Tasks worked` — required, source-of-truth list**

   Enumerate every task created, updated, completed, or cancelled during the session. This is the authoritative list — `transcript.py` cannot reliably derive it from git or PKB without ambiguity, so it must be written explicitly.

   Format:

   ```markdown
   ## Tasks worked

   - task-5a54f813 (/end-session + transcript.py: require useful framework reflection) — updated, added quality bar
   - task-d4932f32 (audit find_existing_* early-returns) — created
   - task-acd9af54 (aops session inspect tool) — cancelled per user
   ```

   Each entry: `- <id> (<precis>) — <action>`. Action verbs the extractor recognises: `created`, `updated`, `completed`, `cancelled`, `referenced`. Bare ids without a precis fail the quality bar.

   **c. `## Framework Reflection` — required, must be useful**

   Must address, in concrete terms:

   - **Friction points**: One bullet per friction item encountered, containing ONLY the reference link (`gh issue #N` or `pkb task task-id`) that was filed via `/learn` at the point of discovery. No prose summaries or per-friction descriptions — the prose lives in the referenced records.
   - **One instruction or tool improvement** the agent would propose, with a pointer to the file/skill/agent it would change.
   - _(Optional)_ one thing that worked well and is worth keeping — short, specific, attributable.

   **Quality bar.** Reject reflections that are generic ("everything was fine", "the procedure was annoying"), propose new tools/features/skills/commands ("we should build an X"), pitch grand refactors, or contain bare identifiers without a precis. Accept reflections that document concrete experienced problems and (where applicable) file bug reports.

   The reflection's job is an **index of friction analysis and improvements**, not feature work. If you find yourself proposing a new capability, stop — invoke `/learn` to file the underlying friction instead.

   **Identifiers + precis.** Every reference to a task, PR, commit, issue, file, or other artefact MUST carry both:

   1. The **stable identifier** (`task-id`, `PR #NNN`, `org/repo#NNN`, commit SHA, etc.).
   2. A **short precis in parentheses** — what the thing is, in <60 chars.

   Required form: `task-acba1234 (/end-session: add explicit process reflection)`, `PR #847 (transcript.py: extract reflection metadata)`, `commit cf83b1f (pkb: broaden --allowed-hosts)`. A bare `task-acba1234` is non-compliant — `transcript.py` flags it as a `bare-identifier` quality warning.

   **Useful (require)** — accurate links to the issues/tasks filed during the session via `/learn`. Bug reports for things that look like real bugs must be filed immediately when encountered, not summarized here. Token-cost breakdown of friction should be placed in the issue/task itself.

   **Not useful (reject)** — new tool/feature suggestions ("an `aops session inspect <id>` command that pulls just the summary…" — reject; this exact reflection was filed and cancelled). Feature development tasks of any kind. Grand refactors ("split transcript_parser.py is 3,640 lines"). Generic procedure-griping.

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

6. **Thread Pickup (if multiple follow-ups).** If the handover lists 2 or more follow-up tasks across multiple distinct work threads, you MUST emit a "Thread Pickup" section immediately following the handover block.

   This section names the concrete first action a next session would take for every distinct work thread left open (not just every task — threads are user-facing groupings). It also surfaces any cross-thread dependencies.

   Example:
   ```markdown
   ### Thread Pickup

   - **Thread A**: apply combined revision list captured in transcript
   - **Thread D**: `/supervisor aops-7bb863b4` first because it unblocks Layer 0/1/2 of Thread A
   ```

   Do not emit this section if the session leaves one or zero follow-up tasks open.

7. **Halt.** Nothing follows the handover and thread pickup blocks.

## What this skill does NOT do

- Does **not** persist discoveries to memory, codify learnings, or file GitHub issues. Those are separate skills ([[remember]], [[learn]]) and belong in the session body, not the close.
- Does **not** loop on itself. If the gate reopens after further edits, run `/end-session` again.
- Does **not** substitute for `/dump`. If you are bailing mid-task without finishing, use `/dump` — it skips commit/PR/reflection and writes a resume task instead.
