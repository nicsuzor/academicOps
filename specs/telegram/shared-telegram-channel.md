---
title: Shared Telegram channel
status: draft
---

# Shared Telegram channel

The shared Telegram channel lets the user converse with an agent from Telegram with low cognitive load across both interactive sessions and isolated container runtimes. A mobile user reading between meetings needs scannable replies, immediate receipt feedback, tap-to-answer decision cards, and uninterrupted multi-turn context regardless of whether the agent runtime maintains a persistent in-memory session or executes one headless turn per invocation. One shared channel engine owns all Telegram protocol handling, message formatting, progressive disclosure, question brokering, and voice processing so every supported agent runtime presents the same conversational contract.

## User stories

### US-1 Multi-turn inbound conversation across runtimes

As a user on Telegram, I want my messages, commands, reply quotes, attachments, and voice notes to reach the agent and continue the active conversation for my chat, so that I can direct work seamlessly whether the agent runs in an interactive session or an isolated container.

- **AC-1.1** Given an authorized user sends a text message, command, attachment, or voice note in a Telegram chat, when the channel polls the update, then the channel places an eyes (`👀`) reaction on the message and delivers a normalized inbound event containing sender identity, chat and message identifiers, any quoted reply text, local attachment paths, and transcribed voice text to the agent runtime.
- **AC-1.2** Given an unauthorized user sends a message or taps a button, when the channel receives the update, then the channel drops the update without invoking the agent or emitting a reply.
- **AC-1.3** Given a chat already has a recorded session identifier, when a subsequent inbound event arrives for that chat, then the channel resumes that existing agent session so prior turn context is preserved across turns and container restarts.
- **AC-1.4** Given a turn is already running for a chat and auto-interrupt is enabled, when the user sends a follow-up free-text message in that chat, then the channel terminates the in-flight turn process group and starts a new turn combining the interrupted prompt with the follow-up message.

### US-2 Progressive-disclosure replies, reactions, and voice responses

As a user reading on a phone, I want agent replies formatted with scannable typography, expandable detail blocks, paragraph-level overflow protection, emoji reactions, and spoken audio when I spoke to the agent, so that every response is easy to scan without walls of text.

- **AC-2.1** Given the agent invokes the reply, react, or edit tool during a turn, when the channel processes the call, then the channel converts Markdown into plain text with UTF-16 entity offsets (including expandable blockquotes), splits replies exceeding 1,200 characters at whole-paragraph boundaries with a continuation notice, and delivers the payload to Telegram.
- **AC-2.2** Given the user's most recent inbound turn in a chat was a voice message and speech synthesis is configured, when the agent sends a reply in that chat, then the channel synthesizes spoken audio from the top-level summary text (excluding blockquotes and code blocks) and sends a Telegram voice note alongside the text.

### US-3 In-flight interactive questions

As a user asked to make a choice mid-turn, I want a vertical numbered button card on Telegram supporting single-select, multi-select, and custom text entry, so that I can answer from my phone and unblock the waiting turn in place.

- **AC-3.1** Given the agent invokes the question tool during a turn, when the channel sends the question card to Telegram, then the tool call waits for the user's selection while the channel continues polling Telegram updates without stalling.
- **AC-3.2** Given a pending question card in single-select, multi-select, or custom-reply mode, when the authorized user taps an option, confirms a multi-select set, or replies to the custom-input prompt, then the channel updates the card state on Telegram and returns the selected answer to the waiting tool call within the active turn.

### US-4 Asynchronous background completion and explicit failure reporting

As a user delegating background work or diagnosing a failed turn, I want completed background work to wake the conversation automatically and any runtime or transport error to surface verbatim, so that delegated results arrive without manual polling and failures are immediately inspectable.

- **AC-4.1** Given a turn finishes while a background subagent is still running, when the background subagent writes an undelivered completion message to the conversation's message store, then the channel starts a continuation turn on the same conversation so the agent processes the result and replies on Telegram.
- **AC-4.2** Given another poller instance holds the local lock or the Telegram API returns a `409 Conflict` response, when the poller attempts to fetch updates, then the poller backs off exponentially before retrying so only one consumer polls the bot token at a time.
- **AC-4.3** Given an agent turn process exits with a non-zero status, times out, references an invalid session identifier, or encounters a tool-bridge error, when the failure occurs, then the channel halts the turn immediately and surfaces the verbatim error output and exit status.

## Design

### Shared channel core and dual transport boundary

Outbound communication from the agent to Telegram is uniform across runtimes because every supported runtime invokes the same structured tool contract (`reply`, `react`, `ask_user`, `edit_message`, `anchor`, `download_attachment`). Inbound communication differs by runtime capability:

1. **In-session channel transport**: When the host runtime natively accepts asynchronous channel notifications over its tool stream, a single primary process runs the shared channel core, polls Telegram, executes outbound tools in-process, and pushes normalized inbound events directly into the live session.
2. **Container gateway and local tool-bridge transport**: When the runtime executes as a per-turn CLI process without native inbound channel notifications, a long-lived gateway process inside the container owns the shared channel core, polls Telegram, and listens on an authenticated local domain socket. For each inbound event, the gateway invokes a per-turn CLI process on a serial per-chat queue, passing the inbound event wrapped in a `<channel source="telegram" ...>` envelope and the chat's persisted session identifier. During the turn, the CLI's tool process connects to the gateway's local socket to execute outbound tool calls against the shared channel core.

Separating the shared channel core from the transport adapter allows one implementation of polling, authorization, UTF-16 entity formatting, 1,200-character paragraph overflow, question brokering, and voice processing to serve both runtimes without duplicating logic.

### State and invariants

- **Single-consumer polling**: Only a primary channel or gateway instance polls Telegram `getUpdates` or binds the local tool-bridge socket. Non-primary worker processes expose no Telegram tools unless connected to an active local gateway socket.
- **Session continuity**: The store maps each `chat_id` to its active runtime session identifier on persistent storage so multi-turn state survives across one-shot CLI turns and container restarts.
- **Non-blocking question resolution**: Pending questions are indexed by question identifier and prompt message identifier in the gateway process. While a turn process blocks on a local socket call waiting for an answer, the gateway's polling loop continues processing callback queries and force-reply messages to resolve the waiting promise in flight.
- **Strict failure propagation**: Every tool call goes through the explicit tool contract and every session resume uses the recorded session identifier. Any non-zero process exit, timeout, invalid session identifier, or socket failure halts the turn and propagates the raw error details verbatim.

## Open questions

- Should container gateway deployments enable the loopback web server for overflow details and review pages when a tunnel is configured, or keep the container gateway restricted to chat-native interactions until a tunnel requirement is specified?
