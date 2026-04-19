---
name: dump
type: skill
category: instruction
description: Pauli — Comprehensive work handover and session closure (/dump) - commit changes, push, file a Pull Request, update tasks, file follow-ups, output Framework Reflection, halt
triggers:
  - "emergency handoff"
  - "save work"
  - "handover"
  - "interrupted"
  - "session end"
  - "stop hook blocked"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
allowed-tools: Bash, mcp__pkb__create_memory, mcp__pkb__update_task, mcp__pkb__release_task, mcp__pkb__create_task, TodoWrite, AskUserQuestion, Read
owner: pauli
permalink: skills/dump
---

# /dump - Session Handover & Context Dump

Force graceful handover when work must stop or session must end. This unified skill ensures clean session closure and context preservation.

## Ownership: Pauli

This skill is owned by **Pauli (The Logician)**. When you invoke it, you are stepping into Pauli's role to ensure the knowledge graph remains coherent across session boundaries. Use Pauli's deliberate, curatorial voice for the findings and reflection.

## Usage

```
/dump
```

To invoke programmatically mid-session: `activate_skill(name="aops-core:dump")`.

> When `/dump` is triggered as a slash command, the skill content is already injected into context — execute the steps directly without calling `activate_skill` again.

This skill is **mandatory** before session end. The framework stop gate blocks exit until `/dump` is invoked and completed.

## When to Use

- Session ending normally
- Session must end unexpectedly (Emergency)
- Context window approaching limit
- User needs to interrupt for higher-priority work
- Agent is stuck and needs to hand off

## Execution

Execute the [[base-handover]] workflow. The steps are:

1. **Commit, push, and file a Pull Request** (MANDATORY per P#24)
2. **Release task with progress** — use `release_task` to record what was done:
   ```
   mcp__pkb__release_task(
     id="<task-id>",
     status="merge_ready",
     summary="What was done and outcome",
     pr_url="https://github.com/..."
   )
   ```
   If no PR was filed: use `status="review"` with `reason="session ended, work incomplete"`.
   If no task was claimed, create a historical task first.
   **Fallback**: If `mcp__pkb__release_task` is not available, use `mcp__pkb__update_task(id="<task-id>", status="merge_ready")`.
   **Note (Gemini workers, #521)**: Calling `release_task` with a terminal status (done/merge_ready/blocked/cancelled) is what lets the polecat supervisor detect termination via PKB polling and shut the container down — Gemini has no Stop hook, so skipping this will leave the worker running until an external timeout.
3. **File follow-up tasks** (MANDATORY — [[capture-outstanding-work]])

   Every concrete follow-up **must** become a PKB task via `mcp__pkb__create_task`. Do NOT capture actionable items as prose in memory files, session notes, or daily notes — those are invisible to `/daily`, the task graph, and prioritisation.

   **The rule**: Memory = non-actionable context (learnings, discoveries, preferences). Task = anything someone should act on.

   For each follow-up:
   - **Clear scope?** → Create task with full AC, appropriate priority, and `parent` set to the current task or epic.
   - **Fuzzy scope?** → Create task with `status: seed`, minimal AC (even just a one-liner), and tag `draft`. A seed task with loose links is infinitely better than a prose bullet that nobody will ever see again. Refine later via `/planner`.

   Use [[decompose]] principles for structure. Every task must have a `parent`.

   **Do not put `- [ ]` checklists in parent task bodies** when filing subtasks — the subtask graph is the single source of truth. If the parent body has a checklist that duplicates the new subtasks, replace it with a reference to children.

   **Example — RIGHT pattern** (from a debugging session):
   ```
   mcp__pkb__create_task(
     title="Investigate [[New Integration]] for [[Project]]",
     parent="[[epic-project-maintenance]]",
     priority=3,
     tags=["[[project]]", "draft"],
     body="[[New Integration]] available. Evaluate whether it replaces current [[Existing Tool]] setup.\n\n## AC\n- [ ] Compare feature set with current setup\n- [ ] Decision: adopt or skip"
   )
   ```

   **Example — WRONG pattern**:
   ```
   # In a memory file or session notes:
   - TODO: look into [[New Integration]]
   - TODO: fix broken [[automation]]
   - TODO: reauth [[Third-Party Service]]
   ```
   These are invisible to the task graph. They will be forgotten.

4. **Persist discoveries to memory** (optional — non-actionable context only)
   4.5. **Codify learnings** — framework improvement → `gh issue create` in aops repo; project-scoped → update `./.agents/workflows/`; see [[references/handover-details]]
5. **Output Framework Reflection** (include `**Proposed changes**` field referencing what was filed/updated)
6. **Output Summary to user** — LAST step, after everything else (see format below)

> **CRITICAL**: Do not proceed past Step 1 until ALL changes are committed, pushed, and a Pull Request is filed. The only acceptable reason to skip is if you made NO file changes.

## Framework Reflection Format

Use `## Framework Reflection` as an **H2 heading** with `**Field**: value` lines. Minimum 3 fields:

```markdown
## Framework Reflection

**Outcome**: success
**Accomplishments**: Fixed the repo-sync cron script
**Next step**: None — PR merged, task complete
```

Do NOT use `**Framework Reflection:**` (bold text) — the parser requires a heading.

## Summary to User Format

After the Framework Reflection, output this as the **very last thing** before stopping. Nothing should follow it — it must be readable in the terminal without scrolling.

```
---
## Session Complete

**What was done**: [1–3 sentences]
**Task(s) worked**: [task-id-1], [task-id-2]
**Follow-up items** (each MUST be a PKB task — no prose-only items):
- [Description] → [task-id]  (or "None")

Next: `/pull <task-id>` to resume, or `/pull` to pick from queue.
---
```
