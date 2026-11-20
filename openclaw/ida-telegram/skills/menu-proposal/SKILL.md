---
name: menu-proposal
description: Review and recommend the shared native Telegram command menu in interactive sessions. Samples telemetry, discovers plugin capabilities, normalizes skill names to snake_case Telegram commands, presents a proposal matrix, and writes approved overrides. Excludes headless worker lifecycle commands (/pull, /dump). Use when asked to review or update the Telegram command menu; exclude for headless workers or non-Telegram commands.
---

# Menu Proposal Workflow

Review, customize, and allocate the shared native Telegram command menu for interactive sessions.

## Procedure

### 1. Sample Telemetry and Discover Capabilities

1. **Sample recent invocations**: Query execution telemetry spans for skill runs and menu taps across interactive sessions and subagents to gather empirical invocation frequencies.
2. **Discover candidate skills and workflows**:
   - Enumerate installed plugin skills and common workflow templates.
   - Include user-facing coordination skills (`reify`, `dispatch`, `reconcile`, `daily`).
   - Exclude reserved platform commands (`start`, `help`, `status`) and headless worker lifecycle commands (`pull`, `dump`), because Telegram menus serve interactive sessions only.
3. **Inspect current allocations**: Check whether `TELEGRAM_BOT_COMMANDS` is set in the channel's `$STATE_DIR/.env`, or whether the instance uses the default menu generated from available skills at poller start.

### 2. Synthesize Recommendations

Evaluate candidate commands for the shared menu:

- **Shared allocation**: Prioritize high-frequency operational triage, capture, decision walk-throughs, task queueing, disambiguation, daily briefings, and worker dispatch (e.g., `/decide`, `/q`, `/reconcile`, `/hydrate`, `/up`, `/reify`, `/dispatch`, `/daily`).
- **Composite commands**: Propose single-tap composite commands where recurring multi-step patterns or common briefings appear (such as `/daily`).
- **Platform constraints**: Convert kebab-case names to `snake_case` by replacing hyphens with underscores (e.g., `strategic-review` -> `/strategic_review`, `menu-proposal` -> `/menu_proposal`). Every identifier must match `/^[a-z0-9_]{1,32}$/`, carry a 1-256 character description, and stay within 100 total commands.

### 3. Present Proposal Matrix

Present a scannable proposal table to the user:

- **Candidate pool summary**: Total candidates inspected and current menu allocations.
- **Recommendation table**: Columns for `Command`, `Type` (`skill`, `workflow`, or `composite`), `Usage` (telemetry count), `Proposed Inclusion` (`[Include]`, `[Exclude]`, or `[Optional]`), `Description`, and `Rationale`.
- **Interactive options**: Provide selectable option buttons or checkbox choices so the user can approve the recommendations or adjust allocations.

### 4. Codify and Verify Approved Allocations

1. Write the approved custom override list as a JSON array to `TELEGRAM_BOT_COMMANDS` in `$STATE_DIR/.env` so it registers on next poller start.
2. Validate every entry in the written JSON array against Telegram constraints (`/^[a-z0-9_]{1,32}$/`, 1-256 char description, <= 100 commands, and no reserved or headless commands).
3. Confirm the updated menu to the user.
