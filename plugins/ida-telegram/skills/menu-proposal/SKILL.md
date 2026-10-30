---
name: menu-proposal
description: Review and recommend native Telegram command menu allocations per agent persona (Prime and Strategic). Instructs agents to sample recent execution telemetry and skill invocations, inspect available skills and workflows, present a considered per-bot allocation matrix with rationale, and codify approved updates. Use when the user requests a Telegram command menu review, proposal, or customization. Exclude for non-Telegram bot commands or general task scheduling.
---

# Menu Proposal Workflow

Review, customize, and allocate native Telegram command menus across agent personas.

## Procedure

### 1. Sample Telemetry and Discover Capabilities

1. **Sample recent invocations:** Query execution telemetry spans (or inspect recent session logs) for skill runs and menu taps across interactive sessions and subagents to gather empirical invocation frequencies.
2. **Discover candidate skills and workflows:**
   - Enumerate installed skills across plugins (`plugins/*/skills/`) and common workflow templates.
   - Include operator-facing coordination skills (`reify`, `dispatch`, `mine`, `reconcile`, `daily`).
   - Exclude reserved platform commands (`start`, `help`, `status`) and headless worker lifecycle commands (`pull`, `dump`).
3. **Inspect current allocations:** Read configured commands for each bot persona in `plugins/ida-telegram/src/telegram/commands.ts` (`PRIME_COMMANDS`, `STRATEGIC_COMMANDS`).

### 2. Synthesize Considered Recommendations

Apply qualitative judgment to evaluate candidate commands against each persona's operational role:

- **Ida Prime (`prime`):** Prioritize fast operational triage, quick capture, decision walk-throughs, task queueing, daily briefings, and worker dispatch (e.g. `/decide`, `/q`, `/mine`, `/reconcile`, `/up`, `/reify`, `/dispatch`, `/daily`).
- **Strategic Ida / Ida Actual (`strategic`):** Prioritize reflective analysis, high-altitude strategizing, goal decomposition, dialectical reviews, argument audits, and durable capture (e.g. `/strategize`, `/remember`, `/decompose`, `/plan`, `/strategic_review`, `/argument_map`, `/daily`).
- **Shared:** Actions supporting general coordination workflows belong on both menus.
- **Composite commands:** Propose single-tap composite commands where recurring multi-step patterns or common briefings are identified (such as `/daily`).
- **Platform constraints:** Ensure all command identifiers match `/^[a-z0-9_]{1,32}$/`, descriptions are 1-256 characters, and total commands do not exceed 100 per persona.

### 3. Present Proposal Matrix

Present a scannable proposal table to the user:

- **Candidate pool summary:** Total candidates inspected and current allocations per persona.
- **Recommendation table:**
  - `Command`: Normalized identifier (e.g. `/reify`).
  - `Type`: `skill`, `workflow`, or `composite`.
  - `Usage`: Empirical invocation count from recent telemetry.
  - `Proposed Allocation`: `[Prime]`, `[Strategic]`, `[Both]`, or `[None]`.
  - `Description`: Clear functional summary.
  - `Rationale`: Why this command fits the recommended persona.
- **Interactive options:** Present checkbox proposals or structured options allowing the user to approve recommendations or adjust allocations in free text.

### 4. Codify Approved Allocations

1. Upon user confirmation, codify the approved command allocations in `plugins/ida-telegram/src/telegram/commands.ts` under `PRIME_COMMANDS` and `STRATEGIC_COMMANDS`.
2. Run test verification (`cd plugins/ida-telegram && bun test test/commands.test.ts`) to ensure command registration and bare action mapping pass cleanly.
3. Confirm updated menus to the user.
