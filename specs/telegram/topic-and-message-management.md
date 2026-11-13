---
title: Telegram Topic and Message Management Tools
status: ready
---

# Telegram Topic and Message Management Tools

This specification defines forum-topic lifecycle and message-management tools exposed via MCP in `ida-telegram` (`close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, `unpin_all_general_thread_messages`, `pin_message`, `unpin_message`, `unpin_all_messages`, `forward_messages`, `copy_messages`, `delete_messages`, and `edit_message_reply_markup`, alongside `create_thread` and `rename_thread`).

## Overview of Tool Classification

In the `ida-telegram` plugin, Telegram Bot API operations are partitioned into:

1. **Exposed MCP Tools (`MCP_TOOLS` -- 24 tools total):** Tools accessible to agents via `tools/list` and `tools/call`:
   - 4 core outbound tools: `reply`, `react`, `ask_user`, `edit_message`.
   - 13 forum-topic / thread tools: `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, `unpin_all_general_thread_messages`.
   - 7 message-management tools: `pin_message`, `unpin_message`, `unpin_all_messages`, `forward_messages`, `copy_messages`, `delete_messages`, `edit_message_reply_markup`.
2. **Internal `TelegramBotClient` Runtime Helpers (Not Exposed in `MCP_TOOLS`):** Polling, command registration, attachment fetch, callback acknowledgement, and permission UI helpers (`registerCommands`, `getRegisteredCommands`, `getUpdates`, `answerCallbackQuery`, `getFile`, `sendPermissionCard`) and Mini App HTTP endpoints that are **not** registered in `MCP_TOOLS` or dispatched through `SharedTelegramChannelCore.handleIpcMessage`.

## User stories

### US-1 Topic Lifecycle Management (Close, Reopen, Delete, Unpin Topic)

As an operator interacting with an agent in a forum supergroup or private chat with topics enabled, I want the agent to close resolved topics, reopen previously closed topics, unpin all topic messages, and delete obsolete topics on demand, so that forum topics reflect active work without manual management.

- **AC-1.1 (Topic Closure)** Given an active or specified forum topic in a topics-enabled chat, when the agent invokes `close_thread({ message_thread_id: 1234 })`, then the tool dispatches `closeForumTopic` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, thread_id: 1234, closed: true }`.
- **AC-1.2 (Active Topic Closure Default)** Given an active conversation in a forum topic, when the agent invokes `close_thread()` without an explicit thread parameter, then the tool resolves the active thread from session context and closes that topic.
- **AC-1.3 (Topic Reopening)** Given a closed forum topic, when the agent invokes `reopen_thread({ message_thread_id: 1234 })`, then the tool dispatches `reopenForumTopic` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, thread_id: 1234, reopened: true }`.
- **AC-1.4 (Topic Deletion and Active Thread Cleanup)** Given an active or specified forum topic, when the agent invokes `delete_thread({ message_thread_id: 1234 })`, then the tool dispatches `deleteForumTopic` via the Telegram Bot API, clears the active thread from session context if the deleted topic was active, and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, thread_id: 1234, deleted: true }`.
- **AC-1.5 (Topic Message Unpin & General Topic Guard)** Given a topic, `unpin_all_thread_messages({ message_thread_id })` dispatches `unpinAllForumTopicMessages`. Invocations of `rename_thread`, `close_thread`, `reopen_thread`, or `delete_thread` targeting General topic `#1`, empty chat context, missing thread ID, or Telegram API rejection (`TOPIC_NOT_MODIFIED`, `NOT_ENOUGH_RIGHTS`) return `{ success: false, error: "..." }` with `isError: true`.

### US-2 Message Pinning and Unpinning (Individual & Unpinned Batch)

As an operator managing important announcements or task decisions in Telegram, I want the agent to pin critical messages, unpin specific obsolete pins, and clear all pins in a chat or active topic, so that pinned headers remain uncluttered and current.

- **AC-2.1 (Pinning Specific Messages)** Given an existing `message_id`, `pin_message({ message_id, disable_notification })` dispatches `pinChatMessage` (defaulting `disable_notification` to `true`) and returns `{ success: true, chat_id, message_id, pinned: true }`.
- **AC-2.2 (Unpinning Specific Message)** Given an existing `message_id`, `unpin_message({ message_id })` dispatches `unpinChatMessage` with `message_id` and returns `{ success: true, chat_id, message_id, unpinned: true }`.
- **AC-2.3 (Unpinning Most Recent Message)** When `message_id` is omitted, `unpin_message()` dispatches `unpinChatMessage` without `message_id` to unpin the most recently pinned message.
- **AC-2.4 (Unpinning All Chat or Topic Messages)** In an unthreaded chat with no active thread, `unpin_all_messages()` dispatches `unpinAllChatMessages(chatId)`. When `message_thread_id` (or active topic context) is present, `unpin_all_messages()` dispatches `unpinAllForumTopicMessages(chatId, messageThreadId)` and returns `{ success: true, chat_id, message_thread_id, unpinned_all: true }`.

### US-3 Batch Message Transfer (`forward_messages` & `copy_messages`)

As an operator moving context or consolidating discussions across chats or forum topics, I want the agent to batch-forward messages with attribution or batch-copy messages without attribution up to 100 messages at once, so that bulk message migration avoids noisy single-message loops and rate limits.

- **AC-3.1 (Batch Forward with Attribution)** Given 1-100 `message_ids`, `forward_messages` validates `1 <= message_ids.length <= 100`, defaults `from_chat_id` to `chat_id`, dispatches `forwardMessages`, and returns `{ success: true, chat_id, forwarded_count, message_ids }`.
- **AC-3.2 (Batch Copy Without Attribution)** Given 1-100 `message_ids`, `copy_messages` validates `1 <= message_ids.length <= 100`, forwards `remove_caption` / `disable_notification` / `protect_content` / `message_thread_id`, dispatches `copyMessages`, and returns `{ success: true, chat_id, copied_count, message_ids }`.
- **AC-3.3 (Batch Size Guard)** Passing `0` or `> 100` `message_ids` returns `{ success: false, error: "Batch size must be between 1 and 100 messages" }` locally without calling Telegram.

### US-4 Batch Message Deletion (`delete_messages`)

As an operator wanting clean channels after transient tool outputs, scaffolding, or accidental noise, I want the agent to delete multiple messages at once, so that cleanup is atomic, rate-limit compliant, and immediate.

- **AC-4.1 (Batch Delete)** Given 1-100 `message_ids`, `delete_messages` dispatches `deleteMessages(chatId, messageIds)` and returns `{ success: true, chat_id, deleted_count, message_ids }`.
- **AC-4.2 (Batch Bounds & API Rejection)** Out-of-bounds batches fail locally with `"Batch size must be between 1 and 100 messages"`; Telegram API rejections (such as messages older than 48h or missing permissions) propagate verbatim as `{ success: false, error }`.

### US-5 Editing Message Inline Markup (`edit_message_reply_markup`)

As an operator interacting with interactive Telegram workflows, checklists, or confirmations, I want the agent to attach, update, or remove inline keyboard buttons on existing messages without editing or re-sending message text, so that interactive controls reflect current state cleanly.

- **AC-5.1 (Button Replacement)** Given `message_id` and `buttons` (plus optional `button_layout` / `buttons_per_row`), `edit_message_reply_markup` builds the inline keyboard rows via `buildInlineKeyboardRows` and dispatches `editMessageReplyMarkup`, returning `{ success: true, chat_id, message_id, updated: true }`.
- **AC-5.2 (Clearing Buttons)** Passing `buttons: []` or omitting `buttons` dispatches `editMessageReplyMarkup` with an empty `inline_keyboard: []`.
- **AC-5.3 (No-op Modification Handling)** If Telegram responds with `"message is not modified"`, `edit_message_reply_markup` returns `{ success: true, chat_id, message_id, not_modified: true }`.

### US-6 General Forum Topic & Topic Icon Stickers

As an operator using forum supergroups, I want the agent to inspect available custom forum-topic icon stickers and manage the General topic `#1` directly, so that every Telegram Bot API forum-topic capability is available through the MCP server.

- **AC-6.1 (Icon Stickers Discovery)** When the agent invokes `get_forum_topic_icon_stickers()`, the tool dispatches `getForumTopicIconStickers` and returns `{ success: true, stickers: [...] }`.
- **AC-6.2 (General Topic Lifecycle)** `edit_general_thread({ name })`, `close_general_thread()`, `reopen_general_thread()`, `hide_general_thread()`, `unhide_general_thread()`, and `unpin_all_general_thread_messages()` dispatch the corresponding `*GeneralForumTopic*` Bot API methods and return `{ success: true, chat_id, ... }` or `{ success: false, error }`.

## Design

### 1. Exposed Topic & Message Management MCP Tool Schemas (`plugins/ida-telegram/src/mcp/tools.ts`)

`MCP_TOOLS` registers `24` tools in total:

- **Core (4):** `reply`, `react`, `ask_user`, `edit_message`
- **Topic & Thread Lifecycle (13):** `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, `unpin_all_general_thread_messages`
- **Message Management (7):** `pin_message`, `unpin_message`, `unpin_all_messages`, `forward_messages`, `copy_messages`, `delete_messages`, `edit_message_reply_markup`

### 2. Active Thread Context and State Tracking

1. **Active Thread Resolution:**
   Topic tools (`rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`) as well as `unpin_all_messages`, `forward_messages`, and `copy_messages` accept optional `message_thread_id` (or alias `thread_id`) and resolve active thread context via `resolveThreadContext(args)` when omitted.
2. **State Cleanup upon Topic Deletion:**
   When `delete_thread` successfully deletes a topic matching the active thread in session context for that chat, active thread tracking is cleared immediately so subsequent messages do not route into the deleted topic.
3. **General Topic `#1` Guard:**
   Invocations of `rename_thread`, `close_thread`, `reopen_thread`, or `delete_thread` targeting General topic (`message_thread_id: 1`) are rejected locally with `{ success: false, error: "Cannot modify or delete the General forum topic" }` before API dispatch. Callers manage General topic `#1` explicitly via `*_general_thread*` tools.

### 3. Telegram API Constraints & Limits

| Exposed MCP Tool | Telegram Bot API Method | Constraints & Error Handling |
| :- | :- | :- |
| `create_thread` | `createForumTopic` | Validates trimmed `name` (1-128 chars) and integer `icon_color`; forwards optional `icon_custom_emoji_id`. Surfaces API errors verbatim. |
| `rename_thread` | `editForumTopic` | Requires active/explicit non-General thread; validates `name` (1-128 chars). Rejects `#1` locally. |
| `close_thread` | `closeForumTopic` | Requires `can_manage_topics`; rejects General topic `#1` locally. Propagates `TOPIC_NOT_MODIFIED` / `NOT_ENOUGH_RIGHTS`. |
| `reopen_thread` | `reopenForumTopic` | Requires `can_manage_topics`; rejects General topic `#1` locally. |
| `delete_thread` | `deleteForumTopic` | Requires `can_delete_messages` and `can_manage_topics`; rejects `#1`; clears active thread state on success. |
| `unpin_all_thread_messages` | `unpinAllForumTopicMessages` | Requires `can_pin_messages`; unpins all messages in specified/active topic. |
| `get_forum_topic_icon_stickers` | `getForumTopicIconStickers` | Returns sticker array for custom topic icons. |
| `edit_general_thread` | `editGeneralForumTopic` | Validates `name` (1-128 chars); renames General topic `#1`. |
| `close_general_thread` | `closeGeneralForumTopic` | Closes General topic `#1`. |
| `reopen_general_thread` | `reopenGeneralForumTopic` | Reopens General topic `#1`. |
| `hide_general_thread` | `hideGeneralForumTopic` | Hides General topic `#1`. |
| `unhide_general_thread` | `unhideGeneralForumTopic` | Unhides General topic `#1`. |
| `unpin_all_general_thread_messages` | `unpinAllGeneralForumTopicMessages` | Unpins all pinned messages in General topic `#1`. |
| `pin_message` | `pinChatMessage` | Requires integer `message_id`; `disable_notification` defaults to `true`. |
| `unpin_message` | `unpinChatMessage` | Optional `message_id`; unpins target or most recent pinned message. |
| `unpin_all_messages` | `unpinAllChatMessages` / `unpinAllForumTopicMessages` | Routes to topic-scoped unpin if `message_thread_id` / active thread resolves, otherwise chat-wide unpin. |
| `forward_messages` | `forwardMessages` | Enforces 1-100 `message_ids` batch limit locally (`"Batch size must be between 1 and 100 messages"`); `from_chat_id` defaults to target `chat_id`. |
| `copy_messages` | `copyMessages` | Enforces 1-100 `message_ids` batch limit locally; forwards `remove_caption`. |
| `delete_messages` | `deleteMessages` | Enforces 1-100 `message_ids` batch limit locally; propagates API errors (e.g., 48h window) verbatim. |
| `edit_message_reply_markup` | `editMessageReplyMarkup` | Builds inline keyboard rows via `buildInlineKeyboardRows`; treats `"message is not modified"` as `{ success: true, not_modified: true }`. |

## Outcome-Level Build Criteria Mapped to Checks

| Criterion | Target Requirement | Verification Check & Observable Proof |
| :- | :- | :- |
| **AC-1** | `close_thread`, `reopen_thread`, and `delete_thread` manage topic lifecycles; `delete_thread` clears active thread; General topic `#1` is guarded; `pin_message`, `unpin_message`, `unpin_all_messages`, `forward_messages`, `copy_messages`, `delete_messages`, and `edit_message_reply_markup` enforce bounds and dispatch to Telegram Bot API. | Integration tests in `plugins/ida-telegram/test/topic-and-message-management.test.ts` (`US-1`..`US-5`) verify all 10 topic-lifecycle + message-management tools and error/bounds handling. |
| **AC-2** | All 13 forum-topic / thread tools and all 7 message-management tools are exposed in `MCP_TOOLS` (`24` total with the 4 core tools) while removed question/anchor tools remain excluded. | Unit/integration tests in `plugins/ida-telegram/test/threads.test.ts` (`AC6`) and `plugins/ida-telegram/test/shared-channel.test.ts` verify `tools/list` (`24` tools), dispatch behaviour, and exclusion of dropped non-API tools. |
