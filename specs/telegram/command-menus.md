---
title: Native Telegram Bot Command Menu for Ida
status: ready
---

# Native Telegram Bot Command Menu for Ida

This specification defines the native Telegram bot command menu registration and routing contract across all Ida bot instances in the `ida-telegram` plugin. It serves operators interacting with Ida across any channel window (Prime, Actual, Audre, or any other named channel) by presenting one unified native Telegram command menu dynamically built from all installed skills at poller start.

## Acceptance Criteria & Verifications

- **AC-1 (Zero persona variables or split lists):** Searching the plugin for `STRATEGIC_COMMANDS`, `resolvePersona`, `IDA_TELEGRAM_PERSONA` and `TELEGRAM_PERSONA` finds nothing.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`AC1: Searching the plugin for STRATEGIC_COMMANDS, resolvePersona, IDA_TELEGRAM_PERSONA and TELEGRAM_PERSONA finds nothing`) programmatically scans all plugin sources and asserts zero matches.
- **AC-2 (Uniform menu across channel folders):** A test shows `telegram-prime`, `telegram-actual`, `telegram-audre` and `telegram-ida` folders yield the exact same menu.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`AC2: telegram-prime, telegram-actual, telegram-audre and telegram-ida folders yield the same menu`) verifies that `loadConfig` across all channel folders returns identical `botCommands`.
- **AC-3 (Registered menu matches spec_7a9caca5 FR-8.1):** The registered menu matches `spec_7a9caca5` FR-8.1 ("every skill, always"), registering all installed skills with valid `[a-z0-9_]{1,32}` identifiers, descriptions between 1 and 256 characters, reserved commands omitted, and defined bare actions attached.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`AC3: registered menu matches spec_7a9caca5 FR-8.1`) validates command identifiers, descriptions, reserved exclusions, and bare action bindings.
- **AC-4 (Knowledge base audit):** `kb_c3b64912` no longer lists the persona variables.
  - _Check_: Primary-source audit of `kb_c3b64912` verifies zero occurrences of `IDA_TELEGRAM_PERSONA` or `TELEGRAM_PERSONA`.
- **AC-5 (Dynamic skill discovery without plugin code edits):** Adding, removing or renaming a skill changes the registered menu with no edit to plugin code, and every installed skill appears with a distinct, valid command name.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`AC5: adding, removing or renaming a skill changes the registered menu with no edit to plugin code, and every skill appears with a distinct, valid command name`) creates an isolated test skill root, adds, removes, and renames skills, induces cross-plugin collisions, and verifies dynamic menu resolution without modifying plugin code.

## User stories

### US-1 Shared Native Command Menu

As an operator interacting with Ida across any Telegram window (prime, actual, audre, or any named instance), I want the bot window to present the single shared command menu stated in `spec_7a9caca5` FR-8.1, so that all Ida instances share the exact same operational command surface without persona branching or folder-dependent menu splits.

- **AC-1.1 (Dynamic installed skills menu)** Given an Ida bot instance (running with `STATE_DIR` pointing to `telegram-prime`, `telegram-actual`, `telegram-audre`, `telegram-ida`, or any other directory), when command registration executes on startup, then the bot registers every skill available to Ida built dynamically from installed skills at poller start, scoped to each authorized chat.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` asserts `loadConfig` across `telegram-prime`, `telegram-actual`, `telegram-audre`, and `telegram-ida` folders yields the exact same menu matching `spec_7a9caca5` FR-8.1.
- **AC-1.2 (Custom override)** Given an explicit custom command configuration in `TELEGRAM_BOT_COMMANDS`, when command registration executes, then the custom configuration overrides the default menu.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` verifies custom JSON override parsing and reserved command filtration.

### US-2 Zero-Argument Tap Execution & Composite Commands

As an operator tapping a command button in the Telegram client menu, I want bare commands without arguments to route with sensible default actions and skill metadata, so that tapping a button triggers immediate, correct execution without requiring manual typing.

- **AC-2.1 (Immediate command execution)** Given a bare tap on an immediate zero-argument command (`/decide`, `/mine`, `/reconcile`, `/up`, etc.), when the inbound update arrives, then the event payload enriches the message with `meta.skill` and `meta.default_action` instructing the agent to execute immediately.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` loops over installed commands asserting `event.meta.skill` and `event.meta.default_action`.
- **AC-2.2 (Contextual command execution)** Given a bare tap on an argument-taking contextual command (`/q`, `/hydrate`, `/reify`, `/dispatch`), when the inbound update arrives, then the event payload enriches the message with `meta.skill` and `meta.default_action` instructing the agent to apply to preceding message context or prompt for input.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` verifies `bareAction` text for contextual commands.

### US-3 Telegram Menu Proposal Workflow

As an operator managing Telegram bot command surfaces, I want an agent workflow that inspects installed skills and active configuration, reviews platform invariants, and presents an interactive proposal if custom overrides are requested, ensuring the menu reflects actual operational needs without manual auditing.

- **AC-3.1 (Considered recommendation presentation & identifier validity)** Given an operator requesting a menu review or update in an interactive session, when the menu proposal workflow runs, then the agent samples recent workflow and skill invocations from execution telemetry, inspects installed capabilities, and presents a structured recommendation for the shared menu with empirical frequencies and rationale. Every recommended command identifier is a valid Telegram command name matching `^[a-z0-9_]{1,32}$`, converting hyphens to underscores for skills whose names contain hyphens (e.g. `/strategic_review`, `/argument_map`, `/menu_proposal`).
  - _Check_: The workflow recommendations match `^[a-z0-9_]{1,32}$` and normalize hyphenated skill names to snake_case.
- **AC-3.2 (Shared command allocation & headless worker separation)** Given candidate commands, when the agent evaluates placement for the shared menu, commands are evaluated for the single shared Ida menu. Headless worker lifecycle commands (`/pull`, `/dump`) and worker execution hooks are strictly excluded from candidate discovery and menus, keeping interactive conversational menus apart from headless workers (`headless-workers.md`).
  - _Check_: Verification that `/pull` and `/dump` are absent from conversational candidate discovery and menus.
- **AC-3.3 (Platform compliance & codification)** Given the presented recommendation, when the operator confirms custom overrides in an interactive session, then the approved configuration is codified into `TELEGRAM_BOT_COMMANDS`, ensuring all command names comply with platform constraints (1–32 lowercase alphanumeric and underscore characters, maximum 100 commands).

## Design

### 1. Unified Registration Contract

1. **Single Menu for Every Ida:**
   - Every Ida instance -- prime, actual, audre, or any other channel name -- registers the exact same command menu.
   - Persona split is eliminated: channel folder names (`telegram-prime`, `telegram-actual`, `telegram-audre`, `telegram-ida`) and persona environment variables do not alter command selection.
2. **Dynamic Skill Discovery:**
   - At poller startup, `discoverInstalledSkills()` discovers all skills available to Ida across installed plugins.
   - For each skill, `name` and `description` are parsed from frontmatter in `SKILL.md`.
   - Command names follow skill names, converting hyphens to underscores (`^[a-z0-9_]{1,32}$`).
   - If two plugins ship a skill with the same name, distinct valid command names are assigned using the plugin prefix.
   - If total discovered commands exceed 100, the condition is logged and reported loudly per FR-8.1.
3. **Registration Contract:**
   - `registerCommands()` invokes Telegram Bot API `setMyCommands` with `scope: { type: "chat", chat_id: chatId }` for each identifier in `allowFrom`.
   - Registration runs only when `isPrimary` is true and command list is non-empty.
   - Survives restarts and overrides global private chat defaults.
4. **Exclusions and Headless Worker Separation:**
   - Official plugin reserved commands (`/start`, `/help`, `/status`) are excluded from registration.
   - Headless worker lifecycle commands (`/pull`, `/dump`) and worker execution hooks are strictly excluded from conversational menus per `headless-workers.md`.

### 2. Maintainer Note on Skill Renaming

When an underlying skill is renamed in the framework (such as files in `plugins/ida/skills/`):

- The command menu updates automatically on next startup without code modifications in the plugin.
- Note that Telegram command identifiers only support characters `[a-z0-9_]{1,32}` (no hyphens; hyphens are converted to underscores).
