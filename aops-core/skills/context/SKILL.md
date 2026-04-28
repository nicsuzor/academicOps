---
name: context
type: skill
category: instruction
description: Session context loader for hookless runtimes — loads daily note summary, accommodations, and active task. Invoke once at session start when hooks are absent (Cowork, GHA, Desktop Code with broken hooks).
triggers:
  - "/context"
  - "load context"
  - "session context"
  - "what is my context"
  - "start of session"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Read,Bash,mcp__plugin_aops-core_pkb__list_tasks,mcp__plugin_aops-core_pkb__get_task,mcp__plugin_aops-core_pkb__task_search
version: 0.1.0
permalink: skills-context
---

# Context Skill

Load session context for hookless runtimes. In Claude Code (with working hooks), context is injected automatically at session start via the `UserPromptSubmit` hook. In Cowork, GHA, Antigravity, and Desktop Code (when hooks are broken), that injection does not happen. `/context` makes the invisible loading explicit: the user calls it once, the skill reads the same sources the hook would have read, and the session starts informed.

**This is not magic.** It is a named, visible action that produces a brief.

## When to invoke

- **Invoke** at the start of any non-trivial session in a hookless runtime — Cowork, GHA, Antigravity, or Desktop Code when hooks are known to be broken.
- **Do not invoke** in Claude Code with working hooks — context is already loaded. Invoking it there is harmless but redundant.
- The user calls this explicitly. Other skills do NOT chain into `/context` automatically — that would be a hook by another name.

## What this skill is not

Not a substitute for `/daily` (which writes and updates the daily note) or `/pull` (which claims and starts a task). `/context` reads state; it does not change state.

## Invocation

```
/context
```

No arguments. The skill discovers what is available and loads what it can.

## What it loads (v1 scope)

Three sources, read in parallel:

**1. Today's Status** (`$ACA_DATA/daily/YYYYMMDD-daily.md`)

Reads today's daily note and extracts only the `## Status` section (priority distribution, deadlines within 7 days, and today's calendar). Does not include inbox items, Work Log, or Today's Log — those are too large for a context brief.

If today's note does not exist, reports "No daily note for today." If the Status section is longer than 500 words, truncate and note it.

**2. Accommodations** (`$ACA_DATA/ACCOMMODATIONS.md`)

Persistent instructions for how to work with this user — cognitive preferences, communication style, known constraints. Include the full file contents.

If the file does not exist, reports "No accommodations file found."

**3. Active task** (PKB)

Calls `mcp__plugin_aops-core_pkb__list_tasks(status="in_progress")`. For each result, includes the task title, ID, and first sentence of its description. Typically zero or one active task.

If PKB is unavailable, reports "PKB unavailable — no active task loaded."

## Output format

```
## Context Brief — {YYYY-MM-DD}

### Accommodations
{ACCOMMODATIONS.md contents, or "No accommodations file found"}

### Status
{## Status section from daily note, or "No daily note for today"}

### Active Work
{task title} [{task-id}] — {first sentence of description}
{or: "No tasks currently in_progress in PKB"}
```

After outputting the brief, halt. Do NOT invoke any other skill.

## Token budget

Target: under 2 000 tokens for the full brief. To stay within budget:

- Accommodations: include in full (typically 200–500 words)
- Status section: cap at 500 words; note if truncated
- Active tasks: title + ID + first sentence only; at most three tasks

A tight brief respects the ADHD zero-friction principle: the user should be able to scan it in 30 seconds.

## Procedure

1. Run `date +%Y%m%d` and `date +%Y-%m-%d` to establish today's date.
2. **In parallel** (all three are independent reads):
   a. Read `$ACA_DATA/daily/{YYYYMMDD}-daily.md`. Locate and extract the `## Status` block (everything from `## Status` up to but not including the next `##` heading). If the file is absent, note it.
   b. Read `$ACA_DATA/ACCOMMODATIONS.md`. If absent, note it.
   c. Call `mcp__plugin_aops-core_pkb__list_tasks(status="in_progress")`. Extract title + ID + first sentence of each result's description.
3. Compose the brief in the output format above.
4. Output the brief and halt.

## Error handling

Load all three in parallel. If any source is unavailable (file not found, MCP error), note the gap in natural language and continue. A partial brief is better than no brief.

## Future scope (not v1)

- **Platform notes**: Once [[aops-f8bb3517]] (CORE.md SSoT) ships, add a fourth section that surfaces platform-specific constraints — which runtime is active, which MCP servers are available, and any hooks that are known to be absent. Deferred because the platform self-description layer does not yet exist.
- **Semantic project context**: Pull relevant PKB nodes based on what the user just said (requires PKB-over-HTTP, [[aops-d55f4696]]). Deferred; the current form loads fixed sources rather than query-driven context.
