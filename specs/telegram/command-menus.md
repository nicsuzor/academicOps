---
title: Native Telegram Bot Command Menu for Ida
status: ready
---

# Native Telegram Bot Command Menu for Ida

This specification defines how the `ida-telegram` plugin registers the native Telegram bot command menu and passes command taps to Ida. The plugin builds no menu of its own and attaches no action to a command: the menu is exactly the operator's configured `TELEGRAM_BOT_COMMANDS` list, and what each command does is left to the agent's instructions (the `telegram` skill).

## Acceptance Criteria & Verifications

- **AC-1 (Configured menu only):** The registered menu is the JSON list in `TELEGRAM_BOT_COMMANDS`, with names normalised to valid `[a-z0-9_]{1,32}` identifiers (hyphens become underscores), descriptions of 1 to 256 characters, and reserved and headless worker commands removed. Unset, empty or invalid configuration yields an empty menu.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`resolveBotCommands returns only the configured menu, filtering reserved and worker commands`).
- **AC-2 (No plugin-built menu):** The plugin reads no other plugin's files to build a menu; with no configuration the menu is empty.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`the plugin builds no menu from other plugins' files: no config means an empty menu`).
- **AC-3 (Uniform menu, zero persona variables):** Every channel folder and persona environment setting yields the same menu for the same configuration.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`every persona and state folder gets the same configured menu`).
- **AC-4 (Chat-scoped registration):** Registration calls `setMyCommands` scoped to each authorised chat and the menu survives a restart.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`registerCommands calls setMyCommands scoped to each allowFrom chat and survives restart`).
- **AC-5 (Bare commands carry no plugin-defined action):** A bare command reaches Ida as the command alone (`meta.command`, empty `meta.args`), with no `meta.skill` or `meta.default_action`; arguments and `@botname` suffixes are handled as stated in Design sections 1.2 and 2.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`bare command reaches Ida as the command alone, with no plugin-defined action`, `command with arguments preserves user arguments`, `command with @botname suffix is normalized cleanly`).
- **AC-6 (Configuration audit):** The Telegram configuration specifications and reference notes list no persona variables.
  - _Check_: Audit of Telegram configuration documentation finds zero occurrences of `IDA_TELEGRAM_PERSONA` or `TELEGRAM_PERSONA` as configuration.

## User stories

### US-1 Shared Native Command Menu

As an operator talking to Ida in any Telegram window, I want every Ida bot to present the same configured command menu, so that all Ida instances share one command surface without persona branching or folder-dependent menu splits.

- **AC-1.1 (Configured menu at startup)** Given an Ida bot instance with any `STATE_DIR`, when the primary poller starts, then it registers the `TELEGRAM_BOT_COMMANDS` menu scoped to each authorised chat.
  - _Check_: AC-3 and AC-4 tests.
- **AC-1.2 (Empty without configuration)** Given no `TELEGRAM_BOT_COMMANDS`, when the poller starts, then no menu is registered.
  - _Check_: AC-2 test.

### US-2 Tapping a Command

As an operator tapping a command in the Telegram menu, I want Ida to act on it without my typing anything further, so that a tap runs the right workflow.

- **AC-2.1 (Agent-side routing)** Given a bare tap on a menu command, when the inbound update arrives, then the plugin delivers the command unchanged (AC-5), and the `telegram` skill tells the agent to invoke the skill of that name (underscores standing for hyphens) on the current conversation: the message it replies to, the active topic, or by asking what it should act on.
  - _Check_: AC-5 test for the plugin side; `plugins/ida-telegram/skills/telegram/SKILL.md` (Bot Commands) for the agent instruction.
- **AC-2.2 (Commands with arguments)** Given a command with arguments, when the update arrives, then the arguments are preserved in `meta.args` and the agent processes them within the target workflow.
  - _Check_: AC-5 test.

### US-3 Telegram Menu Proposal Workflow

As an operator managing the Telegram command surface, I want an agent workflow that inspects installed skills and the active configuration and proposes a menu, so that the configured menu reflects actual operational needs without manual auditing.

- **AC-3.1 (Considered recommendation & identifier validity)** Given an operator requesting a menu review or update in an interactive session, when the menu proposal workflow runs, then the agent samples recent workflow and skill invocations from execution telemetry, inspects installed capabilities and the current `TELEGRAM_BOT_COMMANDS`, and presents a structured recommendation with empirical frequencies and rationale. Every recommended command identifier matches `^[a-z0-9_]{1,32}$`, converting hyphens to underscores (e.g. `/strategic_review`, `/argument_map`, `/menu_proposal`).
  - _Check_: The workflow recommendations match `^[a-z0-9_]{1,32}$` and normalise hyphenated skill names to snake_case.
- **AC-3.2 (Headless worker separation)** Headless worker lifecycle commands (`/pull`, `/dump`) and worker execution hooks are excluded from candidates and menus, keeping conversational menus apart from headless workers (`headless-workers.md`).
  - _Check_: `/pull` and `/dump` are absent from candidates and menus.
- **AC-3.3 (Platform compliance & codification)** Given the presented recommendation, when the operator approves it in an interactive session, then the approved list is written as JSON into `TELEGRAM_BOT_COMMANDS` in the channel's `$STATE_DIR/.env`, registered at the next poller start, with all names within platform constraints (1–32 lowercase alphanumeric and underscore characters, at most 100 commands).

## Design

### 1. Registration Contract

1. **Single menu for every Ida:** channel folder names and persona environment variables do not alter the menu; it comes only from `TELEGRAM_BOT_COMMANDS`.
2. **Resolution:** `resolveBotCommands()` parses the configured JSON list, normalises each name with `normalizeCommandName()` (strip leading `/` and any `@botname`, lowercase, hyphens to underscores, drop other invalid characters), and keeps only entries with a valid name, a 1–256 character description, and a name not excluded below. Unset, empty, non-array or unparseable configuration yields an empty menu; a parse error is logged.
3. **Exclusions:**
   - Official plugin reserved commands (`/start`, `/help`, `/status`) are never registered (Telegram functional specification FR-8.1).
   - Headless worker lifecycle commands (`/pull`, `/dump`) are never registered, per `headless-workers.md`.
4. **Registration:** `registerCommands()` calls the Bot API `setMyCommands` with `scope: { type: "chat", chat_id: chatId }` for each identifier in `allowFrom`. It runs at poller start, only when `isPrimary` is true and the menu is non-empty. Chat-scoped registration survives restarts and overrides global private chat defaults.

### 2. Inbound Commands

A message starting with `/` is parsed into a `bot_command` event: `meta.command` holds the normalised command (with leading `/`), `meta.args` the rest of the text, and the usual message, chat, thread and reply metadata are attached. The plugin adds nothing that says what the command means; routing a command to a skill is the agent's job, set out in the `telegram` skill.

### 3. Maintainer Note on Skill Renaming

The plugin does not track skills. When a skill is renamed, update `TELEGRAM_BOT_COMMANDS` (for example through the menu proposal workflow) so the menu command still names it; Telegram command identifiers allow only `[a-z0-9_]{1,32}`, so hyphens in skill names become underscores.
