---
name: menu-proposal
description: Interactively review, customize, and allocate Telegram bot command menus across agent personas (Prime and Strategic). Discovers candidate skills and workflows, calculates telemetry invocation counts, presents per-bot placement proposals, captures custom composite commands, and synchronizes live menus via Telegram Bot API setMyCommands. Use when the user requests a Telegram menu review or command customization. Exclude for routine status reports or non-Telegram command configurations.
---

# Menu Proposal

Review, customize, and allocate native Telegram command menus across agent personas.

## Procedure

### 1. Discover Candidates and Empirical Usage

1. Run candidate discovery across installed plugin skills and workflow templates:
   - Enumerate all installed skills and common workflows. Operator-facing coordination skills (`reify`, `dispatch`, `mine`, `reconcile`) are included.
   - Filter out reserved commands (`start`, `help`, `status`) and headless worker commands (`pull`, `dump`).
   - Normalize kebab-case identifiers to Telegram-compliant snake_case command names (e.g. `strategic-review` becomes `strategic_review`).
2. Query telemetry invocation frequencies from runtime span storage (skill tool runs and `bot_command` turn events) across interactive turns and subagent runs.
3. Determine current allocations across bot personas (`[Prime]`, `[Strategic]`, `[Both]`, or `[None]`).

### 2. Present Proposal Matrix

Present the structured proposal table to the user with progressive disclosure:

- **Summary headline:** Total candidates discovered, current allocations per persona, and validation against the 100-command limit.
- **Proposal table:**
  - `Command`: Normalized command identifier (e.g. `/reify`).
  - `Type`: `skill`, `workflow`, or `custom`.
  - `Usage`: Empirical invocation count from telemetry spans.
  - `Allocation`: `[Prime]`, `[Strategic]`, `[Both]`, or `[None]`.
  - `Description`: Human-readable summary of the action.
- **Action options:** Offer structured choices to allocate commands per persona or define new composite commands.

### 3. Capture Allocations and Custom Commands

1. **Per-bot allocation:** Accept structured option button choices or free-text instructions (e.g. "put daily on both", "remove hydrate from prime", "strategic only for decompose").
2. **Custom / composite commands:** When the user defines a composite or custom command, capture and validate:
   - `command`: 1-32 characters, lowercase alphanumeric and underscores (`/^[a-z0-9_]{1,32}$/`), excluding reserved commands.
   - `description`: 1-256 characters.
   - `skill`: Target skill or workflow identifier.
   - `bareAction`: Concrete prompt instructions or target skill invocation injected when tapped without arguments.
     Reject invalid specifications with actionable syntax errors.

### 4. Persist and Synchronize Live Menus

1. **Live synchronization:** Invoke Telegram Bot API `setMyCommands` with `scope: { type: "chat", chat_id: chatId }` for each authorized chat across target bot personas, applying updates immediately.
2. **Configuration persistence:** Persist the approved configuration to `TELEGRAM_BOT_COMMANDS` (or persistent state `commands.json`). On startup, persisted configuration takes precedence over static default command arrays.
3. Reply to the user confirming updated menus per persona.
