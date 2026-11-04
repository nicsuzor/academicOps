---
title: Telegram Threaded Conversations by Default
status: ready
---

# Telegram Threaded Conversations by Default

This specification defines the default message routing contract for Telegram forum topics and message threads in the `ida-telegram` plugin. It ensures that conversational agents operating in supergroups with forum topics enabled receive incoming messages with their thread context, and all outbound paths (replies, voice notes, question cards, message edits, and reactions) stay within that same thread without requiring opt-in settings.

## User stories

### US-1 Inbound Thread Identity Delivery

As an operator communicating with an agent inside a specific Telegram forum topic or thread, I want messages, bot commands, attachments, voice notes, callback queries, and reactions delivered to the agent with their thread identity, so that conversation history and context remain isolated to that specific topic.

- **AC-1.1** Given a text message arriving in a Telegram thread (`message_thread_id: 4242`), when the update is parsed, then the emitted channel event carries `meta.message_thread_id = "4242"` and `meta.thread_id = "4242"`.
- **AC-1.2** Given a bot command arriving in a Telegram thread (`message_thread_id: 4242`), when the update is parsed, then the emitted channel event carries `meta.message_thread_id = "4242"` and `meta.thread_id = "4242"`.
- **AC-1.3** Given an attachment arriving in a Telegram thread (`message_thread_id: 4242`), when the update is parsed, then the emitted channel event carries `meta.message_thread_id = "4242"` and `meta.thread_id = "4242"`.
- **AC-1.4** Given a button tap callback query on a message in a Telegram thread (`message_thread_id: 4242`), when the update is parsed, then the emitted channel event carries `meta.message_thread_id = "4242"` and `meta.thread_id = "4242"`.
- **AC-1.5** Given a voice note arriving in a Telegram thread (`message_thread_id: 4242`), when transcribed and emitted, then the voice channel event carries `meta.message_thread_id = "4242"` and `meta.thread_id = "4242"`.
- **AC-1.6** Given a user emoji reaction arriving on a message in a Telegram thread (`message_thread_id: 4242`), when the reaction event is emitted, then the reaction channel event carries `meta.message_thread_id = "4242"` and `meta.thread_id = "4242"`.

### US-2 Outbound Thread Confinement Without Configuration

As an operator interacting with an agent inside a forum topic, I want every outbound response (reply text, spoken voice note, question card, "Other" answer prompt, edit, and emoji reaction) to remain confined to that topic automatically without requiring configuration flags, so that messages never leak into the General topic or clutter other channels.

- **AC-2.1** Given an active conversation in a Telegram thread, when the agent invokes `reply({ text: "..." })` without specifying a thread or reply parameter, then the bot sends `sendMessage` with `message_thread_id` matching that active thread.
- **AC-2.2** Given an active conversation in a Telegram thread, when the agent invokes `reply({ text: "...", voice: true })`, then the bot sends `sendVoice` (and any overflow `sendMessage`) with `message_thread_id` matching that active thread.
- **AC-2.3** Given an active conversation in a Telegram thread, when the agent invokes `ask_user({ questions: [...] })` without specifying a thread, then the question card is sent via `sendMessage` with `message_thread_id` matching that active thread.
- **AC-2.4** Given an active question card in a Telegram thread, when the operator taps `✏️ Other`, then the resulting `force_reply` prompt is sent via `sendMessage` with `message_thread_id` matching that active thread.
- **AC-2.5** Given an incoming message in a Telegram thread, when the bot receives it or when the agent calls `react({ message_id, reaction })`, then the emoji reaction is set on that message directly in the thread.
- **AC-2.6** Given an existing card or message in a Telegram thread, when `edit_message({ message_id, text })` or card state update is invoked, then the message is updated in-place within that thread.

### US-3 Unthreaded Chats Backward Compatibility

As an operator using direct messages (private chats) or regular unthreaded group chats, I want standard unthreaded behaviour preserved exactly as before without synthetic thread IDs or invalid API parameters.

- **AC-3.1** Given a message arriving in an unthreaded chat (no `message_thread_id`), when the update is parsed, then `meta.message_thread_id` and `meta.thread_id` are absent.
- **AC-3.2** Given an unthreaded conversation, when the agent calls `reply` or `ask_user`, then outbound API requests omit `message_thread_id`.

### US-4 Thread Renaming via Tool Call

As an operator interacting with an agent in a forum topic or thread, I want Ida to be able to rename the thread to reflect the active conversation topic, task, or state, so that threads in chat carry meaningful names.

- **AC-4.1 Active Thread Renaming:** When the agent invokes `rename_thread({ name: "..." })` without specifying a thread or chat, the tool renames the active thread in the current chat using the Telegram Bot API (`editForumTopic`).
- **AC-4.2 Explicit Thread Target:** When the agent invokes `rename_thread({ message_thread_id: 1234, name: "New Name" })` (or alias `thread_id`), the tool renames that specific thread in the specified or default chat, optionally forwarding `icon_custom_emoji_id`.
- **AC-4.3 Input Validation & Clear Error Reporting:** When the agent invokes `rename_thread` with an invalid/missing thread ID, empty or missing name, name exceeding 128 characters, or when Telegram API rejects the rename, the tool returns a clear error (`{ success: false, error: "..." }`) rather than silently succeeding.
- **AC-4.4 Unthreaded Context Rejection:** When the agent invokes `rename_thread` in an unthreaded conversation without providing an explicit `message_thread_id`, the tool returns a clear error indicating that a thread ID is required.

### US-5 Routing When No Thread is Defined & Outbound Verification

As an operator interacting with an agent in a chat where no thread is defined (after a restart, or when writing messages outside any topic in a topics-enabled chat), I want outbound replies to reach a chat context I can open (attaching as replies to my inbound message) rather than landing in an unopenable General `#` topic, active thread memory preserved across restarts, and sends that land in an unexpected thread caught rather than reported as success.

- **AC-5.1 Unthreaded Reply Routing:** Given a message arriving outside a thread in a chat (no `message_thread_id`), when the agent calls `reply` without specifying a thread or reply parameter, then the bot sets `reply_parameters.message_id` to that inbound message ID and omits `message_thread_id`, delivering the response in the chat context where the user wrote.
- **AC-5.2 Persistent Thread Memory Across Restarts:** When the plugin restarts or reconnects, active thread, last inbound message, and topics-enabled state per chat are restored from durable storage (`chat_state.json` in `stateDir`), so sends after a restart stay in the active thread without configuration.
- **AC-5.3 Outbound Thread Verification:** When sending replies without an explicit thread parameter, the plugin compares the outbound thread against the inbound message's thread context (or its absence). If the message lands in an unexpected or unreadable thread (such as `#` / thread 1 when unthreaded was expected), the call returns `{ success: false, error: "..." }` rather than silently succeeding.
- **AC-5.4 Undefined Active Thread Check:** After a reconnect or restart, if a chat has topics enabled but no active thread or inbound message is defined, invoking `reply` without an explicit `message_thread_id` or `reply_to` returns a clear error (`{ success: false, error: "..." }`) rather than sending an unthreaded message to the forum root.
- **AC-5.5 Thread Observability in Tool Output:** When `reply` succeeds, the result payload includes `message_thread_id` reflecting the thread used, allowing callers and verification checks to confirm where the message landed.

### US-6 Thread Creation via Tool Call

As an operator conversing with Ida in the main chat or an existing thread, I want Ida to be able to open a new titled thread (forum topic) and continue our conversation directly inside that newly created thread, so that distinct discussions or tasks are organized into dedicated topics without manual topic setup.

- **AC-6.1 Thread Creation:** When the agent invokes `create_thread({ name: "..." })` (aliases `title`, `create_topic`, `create_forum_topic`), the tool opens a new topic in the current or specified chat via the Telegram Bot API (`createForumTopic`), updates the active thread for that chat to the newly created `message_thread_id`, and returns `{ success: true, chat_id, message_thread_id, thread_id, name }`.
- **AC-6.2 Outbound Thread Confinement After Creation:** Immediately following a successful `create_thread` invocation, subsequent outbound messages (`reply`, `ask_user`, `react`) sent to that chat automatically target the newly created thread without requiring explicit thread parameters from the agent.
- **AC-6.3 Optional Parameters:** The tool forwards optional `icon_color` (RGB integer) and `icon_custom_emoji_id` (string) to `createForumTopic` when provided.
- **AC-6.4 Input Validation & Clear Error Reporting:** When the agent invokes `create_thread` with an empty/whitespace name, a name exceeding 128 characters, missing chat context, or when the Telegram Bot API rejects topic creation (e.g. forum topics disabled, insufficient bot permissions, invalid chat), the tool returns a clear error (`{ success: false, error: "..." }`) rather than failing silently.

## Design

### 1. Inbound Routing and Context Tracking

1. **Update Parsing (`inbound.ts`):**
   `TelegramMessage` captures `message_thread_id?: number` and `is_topic_message?: boolean`. When present on incoming messages, bot commands, attachments, voice notes, or callback query messages, `parseInboundUpdate` and `buildVoiceInEvent` attach both `meta.message_thread_id` and `meta.thread_id` as formatted strings.
2. **Per-Chat Active Thread & Inbound Message Memory (`bot.ts` & `store.ts`):**
   `TelegramBotClient` maintains `lastThreadIdByChat = new Map<number, number>()`, `lastInboundMessageIdByChat = new Map<number, number>()`, `lastInboundThreadIdByChat = new Map<number, number>()`, `topicsEnabledChats = new Set<number>()`, and `messageThreads = new Map<number, number>()`. When a message or callback arrives from an authorized user:
   - If `message_thread_id` is present, the active thread for that chat is updated, the chat is marked topics-enabled, and the message is indexed.
   - If an unthreaded message arrives, the active thread is cleared, but the inbound message ID is recorded as the fallback reply target.
   - Active thread, inbound message tracking, and topics-enabled chat flags are persisted durably to `chat_state.json` via `PluginStore`, restoring state across process restarts.

### 2. Outbound Dispatch & Verification

1. **Effective Thread & Reply Resolution:**
   Outbound paths (`sendReply`, `sendQuestionCard`, `sendPermissionCard`) resolve the target thread and reply parameter using prioritized resolution:
   - Explicit `messageThreadId` passed by caller in options / tool arguments;
   - Inferred thread from `replyTo` via indexed `messageThreads`;
   - Active thread from `lastThreadIdByChat` for that chat;
   - When no thread is defined (`effectiveThreadId` is undefined): default `replyTo` to `lastInboundMessageIdByChat` for that chat so the outbound message attaches directly to the user's message via `reply_parameters`.
2. **API Dispatch:**
   When an effective thread ID is present, it is added to `sendMessage` payload and `sendVoice` multipart form data as `message_thread_id`. When absent (unthreaded chats or unthreaded replies), `message_thread_id` is omitted and `reply_parameters` attaches to the inbound message.
3. **Outbound Verification Check:**
   `sendReply` verifies that outbound messages land in the expected thread context:
   - If the inbound message was in a thread, the outbound message must land in that thread.
   - If the inbound message was unthreaded, the outbound message must not land in a thread (`result.message_thread_id` must be absent).
   - If a chat has topics enabled and no active thread or reply target is defined, `sendReply` fails fast with `{ success: false, error: "..." }` rather than sending a blind message to the unopenable General `#` topic.
   - Upon successful delivery, `reply` tool output includes `message_thread_id` for caller observability.
4. **Question Cards and Decision Flows:**
   Both `StdioMcpServer.executeTool("ask_user")` and the Unix domain socket bridge (`createBridgeServer`) pass the effective thread ID (or inbound reply target when unthreaded) to `broker.askUser` and `bot.sendQuestionCard`. Tapping `✏️ Other` preserves `message_thread_id` on the `force_reply` prompt. Resolving or closing questions emits channel events carrying the thread identity.

### 3. Thread Renaming

1. **Tool Definition & Schema (`tools.ts`):**
   `rename_thread` tool definition in `MCP_TOOLS` exposes `chat_id` (optional, defaults to primary chat), `message_thread_id` (optional, alias `thread_id`, defaults to active thread in chat via `bot.getLastThreadId`), `name` (required string, 1-128 characters), and `icon_custom_emoji_id` (optional custom emoji ID for topic icon).
2. **Bot API Dispatch (`bot.ts`):**
   `TelegramBotClient.editForumTopic(chatId, messageThreadId, name, iconCustomEmojiId)` dispatches `POST /bot<token>/editForumTopic` with `{ chat_id, message_thread_id, name, ... }`.
3. **Validation and Error Handling (`server.ts`):**
   Input validation rejects empty/whitespace names, names > 128 characters, or missing thread IDs immediately with `{ success: false, error: "<reason>" }`. When the Telegram Bot API returns `ok: false`, the tool returns `{ success: false, error: res.description || "Failed to rename thread" }` so callers receive explicit failure feedback.

### 4. Thread Creation

1. **Tool Definition & Schema (`tools.ts`):**
   `create_thread` tool definition in `MCP_TOOLS` exposes `chat_id` (optional, defaults to primary user), `name` (required string, 1-128 characters), `title` (optional alias for `name`), `icon_color` (optional integer RGB color), and `icon_custom_emoji_id` (optional custom emoji ID for topic icon).
2. **Bot API Dispatch & Active Thread Tracking (`bot.ts`):**
   `TelegramBotClient.createForumTopic(chatId, name, options)` dispatches `POST /bot<token>/createForumTopic` with `{ chat_id, name, ... }`. Upon receiving a successful response with `result.message_thread_id`, it records the thread ID in `lastThreadIdByChat` for that `chatId`, ensuring all subsequent outbound replies automatically land in the newly created thread.
3. **Validation and Error Handling (`server.ts`):**
   Input validation rejects empty/whitespace names, names > 128 characters, or missing chat IDs with `{ success: false, error: "<reason>" }`. When the Telegram Bot API returns `ok: false` or does not return `result.message_thread_id`, the tool returns `{ success: false, error: res.description || "Failed to create thread" }`.

## Outcome-Level Build Criteria Mapped to Checks

| Criterion | Target Requirement | Verification Check & Observable Proof |
| :- | :- | :- |
| **AC-1** | Called from the main chat or existing thread, `create_thread` opens a titled thread and Ida's next reply is sent inside it automatically without explicit thread parameters. | Integration test in `plugins/ida-telegram/test/threads.test.ts` showing `create_thread` tool call creates the topic via `createForumTopic`, sets active thread, and follow-up `reply` call sends `sendMessage` carrying `message_thread_id`. |
| **AC-2** | A failed create (empty title, name > 128 characters, chat where topics are unavailable, or Telegram API rejection) returns a clear error to the caller. | Unit tests in `plugins/ida-telegram/test/threads.test.ts` testing empty/whitespace name, name length limit, and Telegram API rejection (e.g. `FORUM_CLOSED`, `NOT_ENOUGH_RIGHTS`), verifying `{ success: false, error: "..." }` responses. |
| **AC-3** | The governing spec states the tool's contract and the `telegram` skill documents the tool for agents. | Inspection of diffs in `specs/telegram/threaded-conversations.md` and `plugins/ida-telegram/skills/telegram/SKILL.md`. |
| **AC-4** | Test suite and linter green; PR open into `release/v1.0-rc0` with each criterion mapped to its evidence. | Passing execution of `bun test` and `make lint`, plus git branch and draft PR open targeting `release/v1.0-rc0`. |
