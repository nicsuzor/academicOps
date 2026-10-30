---
title: Telegram Bot Command Menus per Persona
status: ready
---

# Telegram Bot Command Menus per Persona

This specification defines the native Telegram bot command menu registration and routing contract across conversational agent personas in the `ida-telegram` plugin. It serves operators interacting with specialized agent personas (such as Ida Prime for routine operations, triage, and dispatch, and Strategic Ida / Ida Actual for high-altitude reasoning, decomposition, and planning) through dedicated Telegram windows.

## User stories

### US-1 Persona-Tailored Command Menus

As an operator interacting with distinct agent personas in dedicated Telegram windows, I want each bot window to present native commands tailored to that persona's specific role and operational responsibilities, so that quick actions in the menu match the conversation context without clutter or irrelevant commands.

- **AC-1.1 (Prime menu)** Given a bot instance configured for the Prime persona, when command registration executes on startup, then the bot registers Prime-specific commands (`/decide`, `/q`, `/mine`, `/reconcile`, `/hydrate`, `/up`, `/reify`, `/dispatch`, `/daily`) scoped to each authorized chat.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` asserts `resolveBotCommands("prime")` returns exactly these 9 commands in order.
- **AC-1.2 (Ida Actual menu & exclusivity)** Given a bot instance configured for the Strategic persona (Ida Actual), when command registration executes on startup, then the bot registers Strategic-specific commands (`/strategize`, `/remember`, `/decompose`, `/q`, `/hydrate`, `/up`, `/plan`, `/strategic_review`, `/argument_map`, `/reify`, `/dispatch`, `/daily`) scoped to each authorized chat; `/plan`, `/strategic_review`, `/argument_map`, and `/decompose` appear on Ida Actual's menu only.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` asserts `resolveBotCommands("strategic")` returns these 12 commands, and explicitly validates that `plan`, `strategic_review`, `argument_map`, and `decompose` are present on Strategic and absent from Prime.
- **AC-1.3 (Custom override)** Given an explicit custom command configuration in `TELEGRAM_BOT_COMMANDS`, when command registration executes, then the custom configuration overrides persona defaults.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` verifies custom JSON override parsing and reserved command filtration.

### US-2 Zero-Argument Tap Execution & Composite Commands

As an operator tapping a command button in the Telegram client menu, I want bare commands without arguments to route with sensible default actions and skill metadata, so that tapping a button triggers immediate, correct execution without requiring manual typing.

- **AC-2.1 (Immediate command execution)** Given a bare tap on an immediate zero-argument command (`/decide`, `/mine`, `/reconcile`, `/up`, `/strategize`, `/remember`, `/decompose`, `/plan`, `/strategic_review`, `/argument_map`, `/reify`, `/dispatch`, `/daily`), when the inbound update arrives, then the event payload enriches the message with `meta.skill` and `meta.default_action` instructing the agent to execute immediately.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` loops over all commands in `DEFAULT_IDA_COMMANDS` and `STRATEGIC_COMMANDS`, asserting `event.meta.skill` and `event.meta.default_action`.
- **AC-2.2 (Contextual command execution)** Given a bare tap on a contextual command (`/q`, `/hydrate`), when the inbound update arrives, then the event payload enriches the message with `meta.skill` and `meta.default_action` instructing the agent to apply to preceding message context or prompt for input.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` verifies `bareAction` text for `/q` and `/hydrate`.
- **AC-2.3 (/daily definition and execution)** Given an execution of `/daily` (via menu tap or chat input), the command routes to skill `ida:daily`, with default action to update today's daily note (via the PKB template `tpl_daily`) and reply with a scannable run-down of priorities, progress, and open decisions on Telegram.
  - _Check_: `plugins/ida-telegram/test/commands.test.ts` (`AC3: added commands map to their respective skills, and /daily updates daily note and replies on Telegram`) asserts `meta.skill === "ida:daily"` and verifies `meta.default_action` contains the daily note update and Telegram reply directive.

### US-3 Telegram Menu Proposal Workflow

As an operator managing Telegram bot command surfaces across multiple personas, I want an agent workflow that inspects installed skills, common workflows, and empirical usage metrics, and presents a considered menu recommendation per bot persona with an interactive checkbox proposal, so that command menus reflect actual operational needs without manual auditing.

- **AC-3.1 (Considered recommendation presentation & identifier validity)** Given an operator requesting a menu review or update in an interactive session, when the menu proposal workflow runs, then the agent samples recent workflow and skill invocations from execution telemetry, inspects installed capabilities, and presents a structured recommendation listing proposed commands per bot persona with their invocation frequencies and rationale. Every recommended command identifier is a valid Telegram command name matching `^[a-z0-9_]{1,32}$`, converting hyphens to underscores for skills whose names contain hyphens (e.g. `/strategic_review`, `/argument_map`, `/menu_proposal`).
  - _Check_: The workflow recommendations match `^[a-z0-9_]{1,32}$` and normalize hyphenated skill names to snake_case.
- **AC-3.2 (Persona-tailored command allocation & headless worker separation)** Given candidate commands, when the agent evaluates placement across bot personas, then operational and triage actions are recommended for Ida Prime, reflective and high-altitude actions are recommended for Ida Actual, and shared coordination actions are recommended for both. Headless worker lifecycle commands (`/pull`, `/dump`) and worker execution hooks are strictly excluded from candidate discovery and menus, keeping interactive conversational menus apart from headless workers (`headless-workers.md`).
  - _Check_: Verification that `/pull` and `/dump` are absent from candidate discovery and persona menus.
- **AC-3.3 (Composite command synthesis)** Given recurring multi-step action patterns observed in telemetry or operator requests, when the agent recommends commands, then composite commands synthesizing common workflows into a single menu action (such as daily status and briefing) are included with their intended behavior.
- **AC-3.4 (Interactive review and codification)** Given the presented recommendation, when the operator confirms or adjusts command placement in an interactive session, then the approved command menus are codified into the bot configuration, ensuring all command names comply with platform constraints (1–32 lowercase alphanumeric and underscore characters, maximum 100 commands per persona).

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
     - `/reify`: Compose dispatchable tasks on the graph from an objective (`ida:reify`).
     - `/dispatch`: Start polecat workers on queued tasks already on the graph (`ida:dispatch`).
     - `/daily`: Update the daily note and reply with a run-down on Telegram (`ida:daily`).
   - **Strategic Ida / Ida Actual (`strategic`):**
     - `/strategize`: Reason at strategic altitude and interrogate the core question (`ida:strategize`).
     - `/remember`: Persist facts, decisions, and constraints to the PKB (`ida:remember`).
     - `/decompose`: Expand an objective into sub-objectives and decision forks (`ida:decompose`). _Ida Actual only._
     - `/q`: Capture an ask or idea onto the task graph (`ida:q`).
     - `/hydrate`: Disambiguate terms or hydrate context from the PKB (`ida:hydrate`).
     - `/up`: Step up a level on the last correction and fix the class (`ida:up`).
     - `/plan`: Facilitate strategic exploration and structure plans under uncertainty (`ida:plan`). _Ida Actual only._
     - `/strategic_review`: Modular multi-agent dialectical review of an artifact (`ida:strategic-review`). _Ida Actual only._
     - `/argument_map`: Build a reviewable map of a text's argument in Argdown (`ida:argument-map`). _Ida Actual only._
     - `/reify`: Compose dispatchable tasks on the graph from an objective (`ida:reify`).
     - `/dispatch`: Start polecat workers on queued tasks already on the graph (`ida:dispatch`).
     - `/daily`: Update the daily note and reply with a run-down on Telegram (`ida:daily`).
4. **Exclusions and Headless Worker Separation:**
   - Official plugin reserved commands (`/start`, `/help`, `/status`) are excluded from registration.
   - Headless worker lifecycle commands (`/pull`, `/dump`) and worker execution hooks are strictly excluded from conversational menus. Per `headless-workers.md`, autonomous workers operate non-interactively and cannot pause for human input; conversational menus exclusively serve interactive chat sessions between human operators and conversational agent personas.

### 2. Maintainer Note on Skill Renaming

When an underlying skill is renamed in the framework (such as files in `plugins/ida/skills/`):

- Maintainers must update the corresponding command name, skill mapping (`skill` field), bare action text, and test assertions in `plugins/ida-telegram/src/telegram/commands.ts` and `plugins/ida-telegram/test/commands.test.ts`.
- Note that Telegram command identifiers only support characters `[a-z0-9_]{1,32}` (no hyphens).

### 3. Telegram Menu Proposal Workflow

1. **Telemetry Sampling, Capability Discovery, and Headless Worker Separation:**
   - The workflow queries recent execution telemetry across agent sessions and subagents to determine empirical invocation frequency for each installed skill and workflow template.
   - Discovers available capabilities across plugin skill directories and workflow libraries, including operator-facing coordination skills (`reify`, `dispatch`, `mine`, `reconcile`, `daily`).
   - Identifies candidate composite commands from recurring prompt patterns or multi-skill compositions.
   - Strictly excludes reserved platform commands (`start`, `help`, `status`) and headless worker lifecycle commands (`pull`, `dump`). Conversational command menus are reserved exclusively for interactive operator sessions; headless workers never pause for human input, and the interactive proposal workflow is conducted solely within interactive operator sessions (`headless-workers.md`).

2. **Qualitative Evaluation, Persona Allocation, and Identifier Normalization:**
   - Evaluates each candidate command against the operational mandate of each bot persona:
     - **Ida Prime:** Emphasizes fast triage, task queueing, daily review, single-step decisions, and worker dispatch.
     - **Ida Actual (Strategic Ida):** Emphasizes high-altitude strategizing, reflective reasoning, argument mapping, dialectical review, and goal decomposition.
     - **Shared:** Emphasizes cross-cutting workflow coordination.
   - Enforces Telegram platform invariants: command names must match `[a-z0-9_]{1,32}`, human-readable descriptions must be between 1 and 256 characters, and total registered commands must not exceed 100 per persona scope.
   - **Command identifier normalization:** Every recommended command must be a valid Telegram command identifier matching `^[a-z0-9_]{1,32}$` (no hyphens, lowercase alphanumeric and underscores only, length 1–32). For candidate skills or workflows named with hyphens (kebab-case, e.g. `strategic-review`, `argument-map`, `menu-proposal`, `session-trace`), the workflow normalizes the name by converting all hyphens to underscores (`strategic-review` $\rightarrow$ `/strategic_review`, `argument-map` $\rightarrow$ `/argument_map`, `menu-proposal` $\rightarrow$ `/menu_proposal`).

3. **Proposal Presentation and Operator Interaction:**
   - Conducted exclusively in interactive operator sessions:
   - Presents a scannable table or checkbox proposal detailing:
     - Proposed command name (normalized to `[a-z0-9_]{1,32}`) and type (skill, workflow, or composite).
     - Empirical invocation count from recent telemetry.
     - Recommended persona allocation (`[Prime]`, `[Strategic]`, or `[Both]`) with justification.
     - Description of action taken on bare tap.
   - Solicits operator approval or fine-tuning via structured options or natural language feedback.

4. **Codification and Delivery:**
   - Upon operator confirmation in the interactive session, the approved menu allocations are codified in the bot persona command definitions.
   - Updates become active on the next bot configuration load or deployment.
