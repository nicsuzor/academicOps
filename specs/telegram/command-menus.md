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

- **AC-3.1** Given an operator requesting a menu review or scheduled proposal, when the proposal skill executes, then it enumerates all installed skills and workflows, retrieves usage frequency metrics from telemetry, and inspects currently configured and live menus across all bot personas.
- **AC-3.2** Given the inspected skills and usage metrics, when the proposal is presented, then every candidate skill is displayed with its usage count and current allocation without filtering out autonomous coordination skills, and the operator is prompted to assign each command per bot ("Prime only", "Strategic only", "both", or "none") using structured multi-choice options with free-text support.
- **AC-3.3** Given an operator defining a composite or new command, when the operator specifies the command name, menu description, and execution meaning, then the skill validates the command name against Telegram API constraints and captures the execution action for the designated bot persona(s).
- **AC-3.4** Given approved menu changes, when the operator confirms the update, then the system immediately invokes Telegram Bot API `setMyCommands` across authorized chat scopes for each target bot persona and persists the approved configuration so that changes survive restarts.

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

1. **Data Sources:**
   - **Configured Menus:** Static defaults and configured command mappings for each bot persona.
   - **Live Menus:** Active commands currently registered with the Telegram Bot API via `getMyCommands` for each bot token and authorized chat scope.
   - **Installed Skills and Workflows:** Discovered across installed plugin skill registries and universal workflow templates.
     - _Autonomous and Coordination Skills:_ Agent-run coordination skills (such as `reify`, `dispatch`, `mine`, `reconcile`) are included in candidate discovery because operators frequently trigger planning or dispatch pipelines directly from chat.
     - _Exclusions:_ Official reserved commands (`start`, `help`, `status`) and headless worker lifecycle commands (`pull`, `dump`) remain strictly excluded from conversational menus to protect worker isolation boundaries.
   - **Telemetry Usage Metrics:** Invocation frequencies retrieved from runtime span storage:
     - Tool execution spans recording skill invocations across interactive turns and subagents.
     - Channel turn events with `event="bot_command"` recording direct menu button taps.

2. **Proposal Presentation and Operator Interaction:**
   - **Structured Proposal Matrix:** Presents candidate skills and workflows displaying:
     - Command identifier.
     - Functional description.
     - Empirical usage count from telemetry spans.
     - Current menu allocation (`[Prime]`, `[Strategic]`, `[Both]`, or `[None]`).
   - **Per-Bot Allocation Choice:**
     - The operator assigns each command per bot persona: Prime only, Strategic only, both, or remove from menus.
     - The interface provides structured option buttons (e.g. checkbox selections) while accepting free-text replies and conversational adjustments.
   - **Custom and Composite Commands:**
     - The operator may define new or composite commands with custom execution semantics.
     - For each custom command, the skill captures and validates:
       1. `command`: Normalized command name (1-32 characters, lowercase alphanumeric and underscores `/^[a-z0-9_]{1,32}$/`, excluding reserved commands `start`, `help`, `status`). Leading slashes are stripped during normalization.
       2. `description`: Human-readable menu description (1-256 characters).
       3. `skill`: Target skill or workflow identifier.
       4. `bareAction`: Concrete natural language prompt or instructions injected into execution metadata when tapped without arguments.
   - **API Invariants:** Total registered commands per bot persona must not exceed the Telegram Bot API limit of 100 commands per scope.

3. **Delivery and Menu Synchronization Pipeline:**
   - **Immediate Live Menu Synchronization:** When menu updates are confirmed, the system immediately invokes the Telegram Bot API `setMyCommands` endpoint with `scope: { type: "chat", chat_id: chatId }` for each authorized chat across target bot personas, updating client menus in real time without downtime.
   - **Configuration Persistence:** The approved command configurations are saved to the bot instance's persistent configuration store (`TELEGRAM_BOT_COMMANDS` or persistent state), ensuring customized menus persist across restarts and environment rebuilds.

## Build Acceptance Criteria and Verification Matrix

The implementation of the Telegram menu-proposal skill must satisfy the following outcome-level acceptance criteria, each validated by its corresponding verification check:

| ID | Outcome-Level Acceptance Criterion | Verification Check |
| - | - | - |
| **BAC-1** | Candidate discovery enumerates installed skills and workflows including autonomous coordination skills (`reify`, `dispatch`), while strictly filtering out reserved commands (`start`, `help`, `status`) and headless worker commands (`pull`, `dump`). | Unit test passing simulated plugin skill registry asserting that `reify` and `dispatch` appear in candidate output while `pull`, `dump`, `start`, and `help` are excluded. |
| **BAC-2** | Telemetry ingestion calculates accurate invocation frequencies from span storage across skill executions and bot command events. | Integration test querying test span fixture asserting correct aggregated invocation counts for each skill. |
| **BAC-3** | Proposal formatting renders candidate skills with usage counts, current allocations, and per-bot placement options, enforcing the 100-command limit. | Snapshot test verifying rendered proposal markdown structure, placement options, and truncation/warning when candidate count exceeds Telegram API limits. |
| **BAC-4** | Interactive intake accepts structured multi-choice selections as well as free-text replies for allocating commands per bot. | Parser test verifying that structured selections and free-text inputs ("put daily on both, remove hydrate from prime") resolve to identical command allocations. |
| **BAC-5** | Custom / composite command creation enforces name constraints (1-32 characters, regex `/^[a-z0-9_]{1,32}$/`, non-reserved), description bounds (1-256 characters), and captures execution actions. | Schema validation test asserting rejection of invalid names (`/start`, `/invalid-hyphen`, names > 32 characters) and verification of command specification with valid `bareAction`. |
| **BAC-6** | Approved configurations are written to persistent configuration storage, surviving process restarts. | Persistence test verifying that configuration written during intake is restored identically after restarting the configuration provider. |
| **BAC-7** | Live command synchronization invokes Telegram `setMyCommands` with updated command arrays for each bot persona across authorized chat scopes. | Mocked Telegram Bot API integration test verifying `setMyCommands` payload matches approved command sets per target chat ID upon confirmation. |
