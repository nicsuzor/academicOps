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

## Design

### 1. Inbound Routing and Context Tracking

1. **Update Parsing (`inbound.ts`):**
   `TelegramMessage` captures `message_thread_id?: number`. When present on incoming messages, bot commands, attachments, voice notes, or callback query messages, `parseInboundUpdate` and `buildVoiceInEvent` attach both `meta.message_thread_id` and `meta.thread_id` as formatted strings.
2. **Per-Chat Active Thread Memory (`bot.ts`):**
   `TelegramBotClient` maintains `lastThreadIdByChat = new Map<number, number>()` and `messageThreads = new Map<number, number>()`. When a message or callback arrives from an authorized user with `message_thread_id`, the active thread for that chat is updated and the message is indexed. If an unthreaded message arrives, the active thread for that chat is cleared.

### 2. Outbound Dispatch

1. **Effective Thread Resolution:**
   Outbound paths (`sendReply`, `sendQuestionCard`, `sendPermissionCard`) resolve the target thread using prioritized resolution:
   - Explicit `messageThreadId` passed by caller in options / tool arguments;
   - Inferred thread from `replyTo` via indexed `messageThreads`;
   - Active thread from `lastThreadIdByChat` for that chat.
2. **API Dispatch:**
   When an effective thread ID is present, it is added to `sendMessage` payload and `sendVoice` multipart form data as `message_thread_id`. When absent (unthreaded chats), the parameter is omitted.
3. **Question Cards and Decision Flows:**
   Both `StdioMcpServer.executeTool("ask_user")` and the Unix domain socket bridge (`createBridgeServer`) pass the effective thread ID to `broker.askUser` and `bot.sendQuestionCard`. Tapping `✏️ Other` preserves `message_thread_id` on the `force_reply` prompt. Resolving or closing questions emits channel events carrying the thread identity.
