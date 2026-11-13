---
title: Telegram Topic and Message Management Tools
status: ready
---

# Telegram Topic and Message Management Tools

This specification defines forum topic lifecycle management tools exposed via MCP in `ida-telegram` (`close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, `unpin_all_general_thread_messages`, alongside `create_thread` and `rename_thread`), as well as the internal `TelegramBotClient` message-management methods that remain unexposed over MCP.

## Overview of Tool Classification

In the `ida-telegram` plugin, Telegram Bot API operations are partitioned into:

1. **Exposed MCP Tools (`MCP_TOOLS`):** Tools accessible to agents via `tools/list` and `tools/call`:
   - 4 core outbound tools: `reply`, `react`, `ask_user`, `edit_message`.
   - 13 forum-topic / thread tools: `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, `unpin_all_general_thread_messages`.
2. **Internal `TelegramBotClient` Helpers (Not Exposed in `MCP_TOOLS`):** Methods implemented on `TelegramBotClient` (`pinChatMessage`, `unpinChatMessage`, chat-wide `unpinAllChatMessages`, `forwardMessages`, `copyMessages`, `deleteMessages`, `editMessageReplyMarkup`, `registerCommands`, `getRegisteredCommands`, `getUpdates`, `answerCallbackQuery`, `getFile`, `sendPermissionCard`) and Mini App HTTP endpoints that are **not** registered in `MCP_TOOLS` or dispatched through `SharedTelegramChannelCore.handleIpcMessage`.

## User stories

### US-1 Topic Lifecycle Management (Close, Reopen, Delete, Unpin Topic)

As an operator interacting with an agent in a forum supergroup or private chat with topics enabled, I want the agent to close resolved topics, reopen previously closed topics, unpin all topic messages, and delete obsolete topics on demand, so that forum topics reflect active work without manual management.

- **AC-1.1 (Topic Closure)** Given an active or specified forum topic in a topics-enabled chat, when the agent invokes `close_thread({ message_thread_id: 1234 })`, then the tool dispatches `closeForumTopic` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, thread_id: 1234, closed: true }`.
- **AC-1.2 (Active Topic Closure Default)** Given an active conversation in a forum topic, when the agent invokes `close_thread()` without an explicit thread parameter, then the tool resolves the active thread from session context and closes that topic.
- **AC-1.3 (Topic Reopening)** Given a closed forum topic, when the agent invokes `reopen_thread({ message_thread_id: 1234 })`, then the tool dispatches `reopenForumTopic` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, thread_id: 1234, reopened: true }`.
- **AC-1.4 (Topic Deletion and Active Thread Cleanup)** Given an active or specified forum topic, when the agent invokes `delete_thread({ message_thread_id: 1234 })`, then the tool dispatches `deleteForumTopic` via the Telegram Bot API, clears the active thread from session context if the deleted topic was active, and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, thread_id: 1234, deleted: true }`.
- **AC-1.5 (Topic Message Unpin & General Topic Guard)** Given a topic, `unpin_all_thread_messages({ message_thread_id })` dispatches `unpinAllForumTopicMessages`. Invocations of `rename_thread`, `close_thread`, `reopen_thread`, or `delete_thread` targeting General topic `#1`, empty chat context, missing thread ID, or Telegram API rejection (`TOPIC_NOT_MODIFIED`, `NOT_ENOUGH_RIGHTS`) return `{ success: false, error: "..." }` with `isError: true`.

### US-2 General Forum Topic & Topic Icon Stickers

As an operator using forum supergroups, I want the agent to inspect available custom forum-topic icon stickers and manage the General topic `#1` directly, so that every Telegram Bot API forum-topic capability is available through the MCP server.

- **AC-2.1 (Icon Stickers Discovery)** When the agent invokes `get_forum_topic_icon_stickers()`, the tool dispatches `getForumTopicIconStickers` and returns `{ success: true, stickers: [...] }`.
- **AC-2.2 (General Topic Lifecycle)** `edit_general_thread({ name })`, `close_general_thread()`, `reopen_general_thread()`, `hide_general_thread()`, `unhide_general_thread()`, and `unpin_all_general_thread_messages()` dispatch the corresponding `*GeneralForumTopic*` Bot API methods and return `{ success: true, chat_id, ... }` or `{ success: false, error }`.

## Design

### 1. Exposed Topic MCP Tool Schemas (`plugins/ida-telegram/src/mcp/tools.ts`)

The plugin registers the following topic-lifecycle MCP tools in `MCP_TOOLS` (alongside `reply`, `react`, `ask_user`, `edit_message`, `create_thread`, and `rename_thread`):

```typescript
{
  name: "close_thread",
  description: "Close an open Telegram forum topic (closeForumTopic). Cannot close General topic #1.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer" },
      message_thread_id: { type: "integer" },
      thread_id: { type: "integer" }
    }
  }
},
{
  name: "reopen_thread",
  description: "Reopen a closed Telegram forum topic (reopenForumTopic). Cannot reopen General topic #1.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer" },
      message_thread_id: { type: "integer" },
      thread_id: { type: "integer" }
    }
  }
},
{
  name: "delete_thread",
  description: "Permanently delete a Telegram forum topic and its message history (deleteForumTopic). Cannot delete General topic #1.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer" },
      message_thread_id: { type: "integer" },
      thread_id: { type: "integer" }
    }
  }
},
{
  name: "unpin_all_thread_messages",
  description: "Unpin all pinned messages inside a Telegram forum topic (unpinAllForumTopicMessages).",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer" },
      message_thread_id: { type: "integer" },
      thread_id: { type: "integer" }
    }
  }
},
{
  name: "get_forum_topic_icon_stickers",
  description: "Get custom emoji stickers usable as Telegram forum topic icons (getForumTopicIconStickers).",
  inputSchema: { type: "object", properties: {} }
},
{
  name: "edit_general_thread",
  description: "Rename the General forum topic in a Telegram supergroup (editGeneralForumTopic).",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer" },
      name: { type: "string" }
    },
    required: ["name"]
  }
},
{ name: "close_general_thread", inputSchema: { type: "object", properties: { chat_id: { type: "integer" } } } },
{ name: "reopen_general_thread", inputSchema: { type: "object", properties: { chat_id: { type: "integer" } } } },
{ name: "hide_general_thread", inputSchema: { type: "object", properties: { chat_id: { type: "integer" } } } },
{ name: "unhide_general_thread", inputSchema: { type: "object", properties: { chat_id: { type: "integer" } } } },
{ name: "unpin_all_general_thread_messages", inputSchema: { type: "object", properties: { chat_id: { type: "integer" } } } }
```

### 2. Active Thread Context and State Tracking

1. **Active Thread Resolution:**
   Tools requiring a topic target (`rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`) accept optional `message_thread_id` (or alias `thread_id`). When omitted, the target defaults to the active thread tracked in session context for that chat.
2. **State Cleanup upon Topic Deletion:**
   When `delete_thread` successfully deletes a topic, if `message_thread_id` matches the current active thread in session context for that chat, the active thread tracking is cleared immediately, preventing subsequent messages (`reply`, `ask_user`) from routing into the deleted topic.
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

### 4. Internal Bot Client Message Helpers (Not Exposed via MCP)

`TelegramBotClient` (`plugins/ida-telegram/src/telegram/bot.ts`) retains internal helper methods for message pinning, batch transfer, batch deletion, and inline keyboard editing (`pinChatMessage`, `unpinChatMessage`, `unpinAllChatMessages`, `forwardMessages`, `copyMessages`, `deleteMessages`, `editMessageReplyMarkup`). These methods are intentionally excluded from `MCP_TOOLS` and `SharedTelegramChannelCore.handleIpcMessage`.

## Outcome-Level Build Criteria Mapped to Checks

| Criterion | Target Requirement | Verification Check & Observable Proof |
| :- | :- | :- |
| **AC-1** | `close_thread`, `reopen_thread`, and `delete_thread` manage topic lifecycles via `closeForumTopic`, `reopenForumTopic`, and `deleteForumTopic`; `delete_thread` clears active thread from session context; General topic `#1` is guarded against modification/deletion. | Integration tests in `plugins/ida-telegram/test/topic-and-message-management.test.ts` (`US-1`) verify close, reopen, delete, active thread clearing, and General topic `#1` guard. |
| **AC-2** | All 13 forum-topic / thread MCP tools (`tools/list`) dispatch cleanly to their backing Telegram Bot API methods (`tools/call`) while internal message-management helpers (`pinChatMessage`, `forwardMessages`, `copyMessages`, `deleteMessages`, `editMessageReplyMarkup`) remain excluded from `MCP_TOOLS`. | Unit tests in `plugins/ida-telegram/test/threads.test.ts` (`AC6`) verify `tools/list` exposes all 13 thread tools (plus 4 core tools), excludes non-thread tools, and dispatches `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, and all 6 `*_general_thread*` tools to Telegram Bot API. |
