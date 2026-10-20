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
