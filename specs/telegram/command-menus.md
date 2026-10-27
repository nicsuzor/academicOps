---
title: Telegram Bot Command Menus per Persona
status: ready
---

# Telegram Bot Command Menus per Persona

This specification defines the native Telegram bot command menu registration and routing contract across conversational agent personas in the `ida-telegram` plugin. It serves operators interacting with specialized agent personas (such as Ida Prime for routine operations and dispatch, and Strategic Ida for high-altitude reasoning and planning) through dedicated Telegram windows.

## User stories

### US-1 Persona-Tailored Command Menus

As an operator interacting with distinct agent personas in dedicated Telegram windows, I want each bot window to present native commands tailored to that persona's specific role and operational responsibilities, so that quick actions in the menu match the conversation context without clutter or irrelevant commands.

- **AC-1.1** Given a bot instance configured for the Prime persona, when command registration executes on startup, then the bot registers Prime-specific commands (`/decide`, `/q`, `/mine`, `/reconcile`, `/hydrate`, `/up`) scoped to each authorized chat.
- **AC-1.2** Given a bot instance configured for the Strategic persona, when command registration executes on startup, then the bot registers Strategic-specific commands (`/strategize`, `/remember`, `/decompose`, `/q`, `/hydrate`, `/up`) scoped to each authorized chat.
- **AC-1.3** Given an explicit custom command configuration in `TELEGRAM_BOT_COMMANDS`, when command registration executes, then the custom configuration overrides persona defaults.

### US-2 Zero-Argument Tap Execution

As an operator tapping a command button in the Telegram client menu, I want bare commands without arguments to route with sensible default actions and skill metadata, so that tapping a button triggers immediate, correct execution without requiring manual typing.

- **AC-2.1** Given a bare tap on an immediate zero-argument command (`/decide`, `/mine`, `/reconcile`, `/up`, `/strategize`, `/remember`, `/decompose`), when the inbound update arrives, then the event payload enriches the message with `meta.skill` and `meta.default_action` instructing the agent to execute immediately.
- **AC-2.2** Given a bare tap on a contextual command (`/q`, `/hydrate`), when the inbound update arrives, then the event payload enriches the message with `meta.skill` and `meta.default_action` instructing the agent to apply to preceding message context or prompt for input.

### US-3 Interactive Menu Proposal and Customization

As an operator managing Telegram bot command surfaces across multiple personas, I want an interactive skill that inspects all available skills, common workflows, and empirical usage metrics, and presents a structured proposal to customize and allocate commands per bot persona, so that Telegram menu commands reflect actual operational usage and can be easily evolved.

- **AC-3.1** Given an operator requesting a menu review or scheduled proposal, the skill inspects all available skills and common workflows, gathers usage counts from telemetry, and inspects configured and live menus across all bot personas.
- **AC-3.2** Given the inspected data, the proposal presents every skill and workflow without filtering out agent-run skills, alongside usage counts and current allocations, and prompts the operator to choose per bot ("Prime only", "Strategic only", "both", or "none") using multi-choice selection with free-text support.
- **AC-3.3** Given an operator defining a composite or new command, the skill accepts the custom command name, human-readable menu description, and execution meaning (`bareAction`), mapping it to the target persona(s).
- **AC-3.4** Given approved menu changes, the skill applies changes through the delivery pipeline: updates `PRIME_COMMANDS` and `STRATEGIC_COMMANDS` in `plugins/ida-telegram/src/telegram/commands.ts`, builds and tests the plugin, and restarts bot instances or triggers `setMyCommands` to update live menus.

## Design

### 1. Persona Resolution and Scoped Registration

1. **Persona Discovery:**
   - The plugin resolves persona from configuration:
     1. Explicit `IDA_TELEGRAM_PERSONA` or `TELEGRAM_PERSONA` environment variable (`prime` / `strategic`).
     2. Inferred from `STATE_DIR`: directories containing `telegram-pauli` or `telegram-prime` resolve to `prime`; directories containing `telegram-ida` or `telegram-strategic` resolve to `strategic`.
     3. Defaults to `prime` when unspecified.
2. **Registration Contract:**
   - `registerCommands()` invokes Telegram Bot API `setMyCommands` with `scope: { type: "chat", chat_id: chatId }` for each identifier in `allowFrom`.
   - Registration runs only when `isPrimary` is true and command list is non-empty.
   - Survives restarts and overrides global private chat defaults.
3. **Command Allocations:**
   - **Ida Prime (`prime`):**
     - `/decide`: Walk through open decisions from today's daily note one at a time (`ida:decide`).
     - `/q`: Capture an ask or idea onto the task graph (`ida:q`).
     - `/mine`: Track a must-not-drop ask or pass through tracked tasks (`ida:mine`).
     - `/reconcile`: Reconcile the task graph and update today's daily note (`ida:reconcile`).
     - `/hydrate`: Disambiguate terms or hydrate current conversation context (`ida:hydrate`).
     - `/up`: Step up a level on the last correction and fix the class (`ida:up`).
   - **Strategic Ida (`strategic`):**
     - `/strategize`: Reason at strategic altitude (`ida:strategize`).
     - `/remember`: Persist facts, decisions, and constraints to the PKB (`ida:remember`).
     - `/decompose`: Expand an objective into sub-objectives and decision forks (`ida:decompose`).
     - `/q`: Capture an ask or idea onto the task graph (`ida:q`).
     - `/hydrate`: Disambiguate terms or hydrate context from the PKB (`ida:hydrate`).
     - `/up`: Step up a level on the last correction and fix the class (`ida:up`).
4. **Exclusions:**
   - Official plugin reserved commands (`/start`, `/help`, `/status`) are excluded from registration.
   - Headless worker commands (`/pull`, `/dump`) are excluded from conversational menus.

### 5. Menu Proposal Skill (Interactive Customization)

1. **Enforcement and Placement Rationale:**
   - **Enforcement Pyramid Placement:** `instructions` (`imperative`), placed one step from current static configuration.
   - **Rationale:** The existing Telegram interaction contract operates via instructions (`plugins/ida-telegram/skills/telegram/SKILL.md`, mapped in `specs/ENFORCEMENT-MAP.md`). Proposing and configuring menu commands is an interactive, voluntary agent capability rather than an adversarial boundary. Following the enforcement pyramid default (instructions first), the skill is codified as procedural guidance in `plugins/ida-telegram/skills/telegram-menu-proposal/SKILL.md` (currently unenforced, with no prior row in the enforcement map). Escalation to structural hooks or mechanical gates is neither proportionate nor necessary.

2. **Data Sources:**
   - **Configured Menus:** Static definitions `PRIME_COMMANDS` and `STRATEGIC_COMMANDS` defined in `plugins/ida-telegram/src/telegram/commands.ts`.
   - **Live Menus:** Active commands registered with Telegram via the Bot API's `getMyCommands` endpoint for each bot instance / token.
   - **Installed Skills and Workflows:** Discovered across plugin directories (`plugins/*/skills/`, builtin agent skills) and universal workflow templates.
     - _Unfiltered Inclusion:_ Autonomous or agent-run skills (such as `reify`, `dispatch`, `pull`, `dump`) must be listed alongside conversational skills. Operators frequently expose agent-run skills to trigger background pipelines directly from chat.
   - **Telemetry Usage Metrics:** Span queries against Arize Phoenix:
     - `Skill` tool execution spans (including subagent dispatches).
     - Conversation turns with `event="bot_command"` tracking manual menu taps.

3. **Proposal Presentation and Operator Interaction:**
   - **Structured Proposal Matrix:** The skill tabulates every skill and common workflow, displaying:
     - Command / skill identifier.
     - Short description.
     - Empirical usage count from telemetry spans.
     - Current menu allocation (`[Prime]`, `[Strategic]`, `[Both]`, or `[None]`).
   - **Per-Bot Allocation Choice:**
     - The operator selects which bot persona exposes each command: Prime only, Strategic only, both, or remove from menus.
     - Interaction presents structured options (e.g. via `ask_user` checkbox / option buttons) while explicitly supporting free-text answers and adjustments.
   - **New and Composite Commands:**
     - The operator may invent new or composite commands (e.g. `/daily`: update the daily note and deliver a summary in Telegram).
     - For any new command, the skill prompts for and captures:
       1. `command`: Normalized command name (`/^[a-z0-9_]{1,32}$/`, excluding reserved commands `start`, `help`, `status`).
       2. `description`: Telegram menu description (1-256 characters).
       3. `skill`: Associated primary skill or handler.
       4. `bareAction`: Precise natural language prompt injected into `meta.default_action` when tapped without arguments.

4. **Delivery and Live Propagation Pipeline:**
   - A menu update reaches Telegram only through the full delivery chain:
     1. **Source Update:** The skill edits `PRIME_COMMANDS` and `STRATEGIC_COMMANDS` in `plugins/ida-telegram/src/telegram/commands.ts`.
     2. **Verification & Build:** Runs test suite (`npm test` in `plugins/ida-telegram/`) to ensure TypeScript compilation, valid command name regex, length constraints, and reserved command avoidance.
     3. **Live Deployment:** Triggers a restart of the bot process (or an administrative reload command) to invoke `setMyCommands` on the Telegram Bot API across active chats.

## Build Acceptance Criteria and Verification Matrix

The future build of the Telegram menu-proposal skill must satisfy the following outcome-level acceptance criteria, each validated by its corresponding verification check:

| ID | Outcome-Level Acceptance Criterion | Verification Check |
| - | - | - |
| **BAC-1** | Discovery enumerates all installed skills and workflows without filtering out agent-run or autonomous skills. | Unit test passing simulated plugin skill registry verifying that autonomous skills (`reify`, `dispatch`) appear in the proposal collection. |
| **BAC-2** | Telemetry ingestion accurately extracts invocation frequencies from Phoenix spans across both skill tools and bot command events. | Integration test querying mock/fixture Phoenix span store asserting correct aggregated use counts for each skill. |
| **BAC-3** | Proposal presentation renders every candidate with use count, current status, and per-bot placement options ("Prime", "Strategic", "Both", "None"). | Output formatting snapshot test verifying generated markdown/interactive proposal table contains all required columns and valid option schemas. |
| **BAC-4** | Interactive intake accepts structured checkbox choices as well as free-text replies for allocating commands per bot. | Interactive parser test validating that both structured option selections and unstructured free-text responses resolve to identical configuration states. |
| **BAC-5** | Custom / composite command creation enforces name constraints (regex `/^[a-z0-9_]{1,32}$/`, not reserved) and captures `bareAction` meaning. | Schema validation test asserting rejection of invalid names (`/start`, `/invalid-hyphen`, `toolong...`) and successful generation of `IdaCommandSpec` with valid `bareAction`. |
| **BAC-6** | Approved configurations are written to `plugins/ida-telegram/src/telegram/commands.ts` with valid TypeScript syntax and formatting. | Post-mutation check executing `npm run build` and `npm test` inside `plugins/ida-telegram/`, exiting 0. |
| **BAC-7** | Live command synchronization invokes Telegram `setMyCommands` with updated command arrays for each bot persona across authorized chat scopes. | Mocked Bot API integration test verifying `setMyCommands` payload matches updated `PRIME_COMMANDS` and `STRATEGIC_COMMANDS` per target chat ID upon bot restart/reload. |
