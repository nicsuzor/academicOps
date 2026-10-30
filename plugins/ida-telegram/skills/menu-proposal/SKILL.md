---
name: menu-proposal
description: Review and recommend native Telegram command menu allocations per persona (Prime and Strategic) in interactive sessions. Samples telemetry, inspects capabilities, converts hyphenated skill names to valid snake_case Telegram commands, presents an interactive proposal matrix, and codifies approved updates. Strictly excludes headless worker commands (/pull, /dump) per headless-workers.md. Use when an operator requests a menu review or update. Exclude for headless workers or non-Telegram commands.
---

# Menu Proposal Workflow

Review, customize, and allocate native Telegram command menus across agent personas.

## Procedure

### 1. Sample Telemetry and Discover Capabilities

1. **Sample recent invocations:** Query execution telemetry spans (or inspect recent session logs) for skill runs and menu taps across interactive sessions and subagents to gather empirical invocation frequencies.
2. **Discover candidate skills and workflows:**
   - Enumerate installed skills across plugins (`plugins/*/skills/`) and common workflow templates.
   - Include operator-facing coordination skills (`reify`, `dispatch`, `mine`, `reconcile`, `daily`).
   - Strictly exclude reserved platform commands (`start`, `help`, `status`) and headless worker lifecycle commands (`pull`, `dump`).
3. **Separate interactive menus from headless workers (`headless-workers.md`):**
   - Telegram command menus exclusively serve interactive operator sessions. Headless worker lifecycle commands (`pull`, `dump`) must never appear on conversational menus or in candidate pools.
   - Autonomous workers operate non-interactively and cannot pause for human input; the menu proposal workflow is designed exclusively for interactive operator dialogue and must never be dispatched to a headless worker.
4. **Inspect current allocations:** Read configured commands for each bot persona in `plugins/ida-telegram/src/telegram/commands.ts` (`PRIME_COMMANDS`, `STRATEGIC_COMMANDS`).

### 2. Synthesize Considered Recommendations

Apply qualitative judgment to evaluate candidate commands against each persona's operational role:

- **Ida Prime (`prime`):** Prioritize fast operational triage, quick capture, decision walk-throughs, task queueing, daily briefings, and worker dispatch (e.g. `/decide`, `/q`, `/mine`, `/reconcile`, `/up`, `/reify`, `/dispatch`, `/daily`).
- **Strategic Ida / Ida Actual (`strategic`):** Prioritize reflective analysis, high-altitude strategizing, goal decomposition, dialectical reviews, argument audits, and durable capture (e.g. `/strategize`, `/remember`, `/decompose`, `/strategic_review`, `/argument_map`, `/daily`).
- **Shared:** Actions supporting general coordination workflows belong on both menus.
- **Composite commands:** Propose single-tap composite commands where recurring multi-step patterns or common briefings are identified (such as `/daily`).
- **Command identifier normalization & platform constraints:**
  - Convert kebab-case skill and workflow names to valid Telegram command identifiers (`snake_case`) by replacing hyphens with underscores (e.g. `strategic-review` $\rightarrow$ `/strategic_review`, `argument-map` $\rightarrow$ `/argument_map`, `menu-proposal` $\rightarrow$ `/menu_proposal`, `session-trace` $\rightarrow$ `/session_trace`).
  - Ensure all command identifiers strictly match `/^[a-z0-9_]{1,32}$/` (no hyphens, lowercase alphanumeric and underscores only, length 1–32).
  - Descriptions must be 1–256 characters, and total registered commands must not exceed 100 per persona.

### 3. Present Proposal Matrix

Present a scannable proposal table to the user (in interactive operator sessions only; headless workers cannot pause for human input):

- **Candidate pool summary:** Total candidates inspected and current allocations per persona.
- **Recommendation table:**
  - `Command`: Normalized identifier matching `/^[a-z0-9_]{1,32}$/` with hyphens converted to underscores (e.g. `/reify`, `/strategic_review`).
  - `Type`: `skill`, `workflow`, or `composite`.
  - `Usage`: Empirical invocation count from recent telemetry.
  - `Proposed Allocation`: `[Prime]`, `[Strategic]`, `[Both]`, or `[None]`.
  - `Description`: Clear functional summary.
  - `Rationale`: Why this command fits the recommended persona.
- **Interactive options:** Present checkbox proposals or structured options allowing the user to approve recommendations or adjust allocations in free text.

### 4. Codify Approved Allocations

1. Upon user confirmation in the interactive session, codify the approved command allocations in `plugins/ida-telegram/src/telegram/commands.ts` under `PRIME_COMMANDS` and `STRATEGIC_COMMANDS`.
2. Run test verification (`cd plugins/ida-telegram && bun test test/commands.test.ts`) to ensure command registration and bare action mapping pass cleanly.
3. Confirm updated menus to the user.
