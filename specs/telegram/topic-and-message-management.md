---
title: Telegram Topic and Message Management Tools
status: ready
---

# Telegram Topic and Message Management Tools

This specification defines topic lifecycle management (closing, reopening, and deleting forum topics, complementing topic creation in `create_thread`), message pinning, batch message transfer (forwarding, copying, deleting), and sent message inline keyboard button editing tools for the `ida-telegram` plugin. It enables conversational agents to manage forum topic lifecycles, pin key reference messages, reorganise conversations by transferring message batches into dedicated topics with original cleanup, and dynamically update inline keyboards on previously sent messages in private chats and forum supergroups.

## Overview of Tool Classification

In the `ida-telegram` plugin, conversational agent capabilities are strictly partitioned into:

1. **Exposed MCP Tools:** Tools accessible to agents via `MCP_TOOLS` (including the 4 core outbound tools `reply`, `react`, `ask_user`, `edit_message` and the 13 thread/topic lifecycle tools `create_thread`, `rename_thread`, `close_thread`, `reopen_thread`, `delete_thread`, `unpin_all_thread_messages`, `get_forum_topic_icon_stickers`, `edit_general_thread`, `close_general_thread`, `reopen_general_thread`, `hide_general_thread`, `unhide_general_thread`, `unpin_all_general_thread_messages`).
2. **Internal Bot Client Methods / Unexposed API Helpers:** Helper methods implemented in `TelegramBotClient` or Mini App HTTP APIs that remain NOT exposed as MCP tools to agents (such as `pinChatMessage`, `unpinChatMessage`, chat-wide `unpinAllChatMessages`, `forwardMessages`, `copyMessages`, `deleteMessages`, `editMessageReplyMarkup`, along with dropped plugin-local question/anchor tools like `answer_question`, `close_question`, `list_questions`, `anchor`).

## User stories

### US-1 Topic Lifecycle Management (Close, Reopen, Delete)

As an operator interacting with an agent in a forum supergroup or private chat with topics enabled, I want Ida to be able to close resolved topics, reopen previously closed topics, and delete obsolete topics on demand, so that forum topics reflect current active work without manual management.

- **AC-1.1 (Topic Closure)** Given an active or specified forum topic in a topics-enabled chat, when the agent invokes `close_thread({ message_thread_id: 1234 })` (aliases `close_topic`, `close_forum_topic`), then the tool dispatches `closeForumTopic` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, closed: true }`.
- **AC-1.2 (Active Topic Closure Default)** Given an active conversation in a forum topic, when the agent invokes `close_thread()` without an explicit thread parameter, then the tool resolves the active thread from session context and closes that topic.
- **AC-1.3 (Topic Reopening)** Given a closed forum topic, when the agent invokes `reopen_thread({ message_thread_id: 1234 })` (aliases `reopen_topic`, `reopen_forum_topic`), then the tool dispatches `reopenForumTopic` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, reopened: true }`.
- **AC-1.4 (Topic Deletion and Active Thread Cleanup)** Given an active or specified forum topic, when the agent invokes `delete_thread({ message_thread_id: 1234 })` (aliases `delete_topic`, `delete_forum_topic`), then the tool dispatches `deleteForumTopic` via the Telegram Bot API, clears the active thread from session context if the deleted topic was active, and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, deleted: true }`.
- **AC-1.5 (Topic Error Reporting)** Given invalid parameters (empty chat context, missing thread ID when unthreaded, attempt to delete/close the General topic `#1`, or Telegram API rejection such as `TOPIC_NOT_MODIFIED` or `NOT_ENOUGH_RIGHTS`), when `close_thread`, `reopen_thread`, or `delete_thread` is invoked, then the tool returns a clear error (`{ success: false, error: "..." }`) rather than failing silently.

### US-2 Message Pinning and Unpinning

As an operator reading and tracking important decisions, cards, or reference messages in chat, I want Ida to pin essential messages to the chat or topic header and unpin them when resolved, so that critical reference items remain immediately visible.

- **AC-2.1 (Pin Message)** Given a message in a chat or forum topic, when the agent invokes `pin_message({ message_id: 5678 })` (alias `pin_chat_message`), then the tool dispatches `pinChatMessage` via the Telegram Bot API with silent notification by default (`disable_notification: true`) and returns `{ success: true, chat_id: 12345, message_id: 5678, pinned: true }`.
- **AC-2.2 (Unpin Specific Message)** Given a pinned message, when the agent invokes `unpin_message({ message_id: 5678 })` (alias `unpin_chat_message`), then the tool dispatches `unpinChatMessage` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_id: 5678, unpinned: true }`.
- **AC-2.3 (Unpin Most Recent Message)** Given pinned messages in a chat, when the agent invokes `unpin_message()` without `message_id`, then the tool dispatches `unpinChatMessage` with no message ID to unpin the most recently pinned message and returns `{ success: true, chat_id: 12345, unpinned: true }`.
- **AC-2.4 (Unpin All Messages in Chat or Topic)** Given pinned messages in a forum topic or chat, when the agent invokes `unpin_all_messages({ message_thread_id: 1234 })` (alias `unpin_all_chat_messages`), then the tool dispatches `unpinAllForumTopicMessages` for forum topics (or `unpinAllChatMessages` when unthreaded) via the Telegram Bot API and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, unpinned_all: true }`.
- **AC-2.5 (Pinning Error Reporting)** Given an invalid message ID or Telegram API rejection (such as missing `can_pin_messages` admin rights or message not found), when a pin tool is invoked, then the tool returns `{ success: false, error: "..." }`.

### US-3 Batch Message Forwarding and Copying

As an operator organising an active discussion into a separate forum topic, I want Ida to forward or copy batches of existing messages into a thread (up to 100 messages per call), so that conversation context is preserved in the destination topic without manual copy-pasting.

- **AC-3.1 (Batch Forward Messages into Thread)** Given a list of 1 to 100 message IDs in a chat, when the agent invokes `forward_messages({ message_ids: [101, 102, 103], message_thread_id: 1234 })`, then the tool dispatches `forwardMessages` via the Telegram Bot API to the destination chat and thread, and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, forwarded_count: 3, message_ids: [201, 202, 203] }`.
- **AC-3.2 (Batch Copy Messages into Thread)** Given a list of 1 to 100 message IDs in a chat, when the agent invokes `copy_messages({ message_ids: [101, 102, 103], message_thread_id: 1234 })`, then the tool dispatches `copyMessages` via the Telegram Bot API without forward attribution headers, and returns `{ success: true, chat_id: 12345, message_thread_id: 1234, copied_count: 3, message_ids: [201, 202, 203] }`.
- **AC-3.3 (Batch Size Limits Validation)** Given an empty `message_ids` array or an array exceeding 100 message IDs, when `forward_messages` or `copy_messages` is invoked, then the tool validates the count locally before calling the Telegram API and returns `{ success: false, error: "Batch size must be between 1 and 100 messages" }`.
- **AC-3.4 (Forwarding and Copying Error Reporting)** Given invalid source message IDs, protected content restrictions, or Telegram API errors, then the tool surfaces the Telegram error description verbatim in `{ success: false, error: "..." }`.

### US-4 Batch Message Deletion with Age Constraints

As an operator cleaning up original messages after migrating them into a thread or pruning stale turns, I want Ida to delete batches of messages (up to 100 messages per call) sent within the 48-hour Telegram deletion window, with explicit error reporting if deletion is forbidden, so that chat history stays tidy without silent failures.

- **AC-4.1 (Batch Delete Messages)** Given a list of 1 to 100 message IDs in a chat that were sent within the last 48 hours, when the agent invokes `delete_messages({ message_ids: [101, 102, 103] })`, then the tool dispatches `deleteMessages` via the Telegram Bot API and returns `{ success: true, chat_id: 12345, deleted_count: 3, message_ids: [101, 102, 103] }`.
- **AC-4.2 (Batch Deletion Size Limits)** Given an empty `message_ids` array or an array exceeding 100 message IDs, when `delete_messages` is invoked, then the tool validates the count before calling the Telegram API and returns `{ success: false, error: "Batch size must be between 1 and 100 messages" }`.
- **AC-4.3 (48-Hour Age Limit and Permission Rejections)** Given messages older than 48 hours in a private chat or non-supergroup, or given insufficient bot deletion rights, when the Telegram Bot API rejects deletion (`MESSAGE_DELETE_FORBIDDEN` or `message can't be deleted`), then the tool returns `{ success: false, error: "..." }` containing the Telegram API error description rather than reporting false success.

### US-5 Sent Message Button Editing

As an operator interacting with dynamic message cards in chat, I want Ida to update inline keyboard buttons on previously sent messages without reposting the entire message, so that cards reflect updated options in-place.

- **AC-5.1 (Edit Message Buttons / Reply Markup)** Given a message previously sent by the bot, when the agent invokes `edit_message_reply_markup({ message_id: 5678, buttons: [...] })` (alias `edit_message_buttons`), then the tool formats the inline keyboard and dispatches `editMessageReplyMarkup` via the Telegram Bot API, returning `{ success: true, chat_id: 12345, message_id: 5678 }`.
- **AC-5.2 (Clear Message Buttons)** Given a message with existing buttons, when the agent invokes `edit_message_reply_markup({ message_id: 5678, buttons: [] })` (or with buttons omitted), then the tool dispatches `editMessageReplyMarkup` with an empty inline keyboard (`inline_keyboard: []`), clearing all buttons from the message card.
- **AC-5.3 (Idempotent Edit Protection)** Given an edit call whose new buttons are identical to the message's current buttons, when Telegram returns `message is not modified`, then the tool treats this response as an idempotent success and returns `{ success: true, chat_id: 12345, message_id: 5678, not_modified: true }`.

## Design

### 1. Tool Definitions and Schemas

The plugin registers the following MCP tools:

```typescript
// 1. Topic Lifecycle
{
  name: "close_thread", // aliases: close_topic, close_forum_topic
  description: "Close an active or specified forum topic (thread) in Telegram.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_thread_id: { type: "integer", description: "Telegram forum topic ID (defaults to active thread)" },
      thread_id: { type: "integer", description: "Alias for message_thread_id" }
    }
  }
},
{
  name: "reopen_thread", // aliases: reopen_topic, reopen_forum_topic
  description: "Reopen a closed forum topic (thread) in Telegram.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_thread_id: { type: "integer", description: "Telegram forum topic ID (defaults to active thread)" },
      thread_id: { type: "integer", description: "Alias for message_thread_id" }
    }
  }
},
{
  name: "delete_thread", // aliases: delete_topic, delete_forum_topic
  description: "Delete a forum topic (thread) and all its messages in Telegram.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_thread_id: { type: "integer", description: "Telegram forum topic ID (defaults to active thread)" },
      thread_id: { type: "integer", description: "Alias for message_thread_id" }
    }
  }
},

// 2. Message Pinning
{
  name: "pin_message", // alias: pin_chat_message
  description: "Pin a message in a Telegram chat or forum topic.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_id: { type: "integer", description: "Message ID to pin" },
      disable_notification: { type: "boolean", description: "Pin silently without notification (default true)" }
    },
    required: ["message_id"]
  }
},
{
  name: "unpin_message", // alias: unpin_chat_message
  description: "Unpin a specific message or the most recent pinned message in a Telegram chat.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_id: { type: "integer", description: "Optional message ID to unpin; if omitted, unpins the most recent pinned message" }
    }
  }
},
{
  name: "unpin_all_messages", // alias: unpin_all_chat_messages
  description: "Unpin all messages in a Telegram chat or forum topic.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_thread_id: { type: "integer", description: "Optional topic ID; unpins topic messages if specified, or all chat messages if omitted" },
      thread_id: { type: "integer", description: "Alias for message_thread_id" }
    }
  }
},

// 3. Batch Forward, Copy, and Delete
{
  name: "forward_messages",
  description: "Forward a batch of 1 to 100 messages into a target Telegram chat or forum topic.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Destination chat ID (defaults to primary chat)" },
      message_thread_id: { type: "integer", description: "Destination forum topic ID (defaults to active thread)" },
      thread_id: { type: "integer", description: "Alias for message_thread_id" },
      from_chat_id: { type: "integer", description: "Source chat ID (defaults to destination chat)" },
      message_ids: {
        type: "array",
        items: { type: "integer" },
        description: "List of 1 to 100 message IDs to forward"
      },
      disable_notification: { type: "boolean", description: "Forward silently without notification" },
      protect_content: { type: "boolean", description: "Protect forwarded messages from forwarding and saving" }
    },
    required: ["message_ids"]
  }
},
{
  name: "copy_messages",
  description: "Copy a batch of 1 to 100 messages into a target Telegram chat or forum topic without forward headers.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Destination chat ID (defaults to primary chat)" },
      message_thread_id: { type: "integer", description: "Destination forum topic ID (defaults to active thread)" },
      thread_id: { type: "integer", description: "Alias for message_thread_id" },
      from_chat_id: { type: "integer", description: "Source chat ID (defaults to destination chat)" },
      message_ids: {
        type: "array",
        items: { type: "integer" },
        description: "List of 1 to 100 message IDs to copy"
      },
      disable_notification: { type: "boolean", description: "Copy silently without notification" },
      protect_content: { type: "boolean", description: "Protect copied messages from forwarding and saving" },
      remove_caption: { type: "boolean", description: "Remove media captions when copying" }
    },
    required: ["message_ids"]
  }
},
{
  name: "delete_messages",
  description: "Delete a batch of 1 to 100 messages from a Telegram chat (messages under 48 hours old).",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_ids: {
        type: "array",
        items: { type: "integer" },
        description: "List of 1 to 100 message IDs to delete"
      }
    },
    required: ["message_ids"]
  }
},

// 4. Message Editing (Buttons)
{
  name: "edit_message_reply_markup", // alias: edit_message_buttons
  description: "Update or remove inline keyboard buttons on an existing sent Telegram message.",
  inputSchema: {
    type: "object",
    properties: {
      chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      message_id: { type: "integer", description: "Telegram message ID to edit" },
      buttons: {
        type: "array",
        description: "Updated inline keyboard buttons. Pass empty array or omit to clear buttons.",
        items: {
          anyOf: [
            {
              type: "object",
              properties: {
                label: { type: "string" },
                callback_data: { type: "string" },
                url: { type: "string" },
                web_app: { type: "string" },
                row: { type: "integer" }
              },
              required: ["label"]
            },
            {
              type: "array",
              items: {
                type: "object",
                properties: {
                  label: { type: "string" },
                  callback_data: { type: "string" },
                  url: { type: "string" },
                  web_app: { type: "string" }
                },
                required: ["label"]
              }
            }
          ]
        }
      },
      button_layout: {
        description: "Optional custom row layout specifying button counts per row (e.g. [3, 3, 2]) or uniform size integer",
        anyOf: [
          { type: "array", items: { type: "integer" } },
          { type: "integer" }
        ]
      },
      buttons_per_row: { type: "integer", description: "Optional uniform number of buttons per row" }
    },
    required: ["message_id"]
  }
}
```

### 2. Active Thread Context and State Tracking

1. **Active Thread Resolution:**
   Tools requiring a topic target (`close_thread`, `reopen_thread`, `delete_thread`, `forward_messages`, `copy_messages`, `unpin_all_messages`) accept optional `message_thread_id` (or alias `thread_id`). When omitted, the target defaults to the active thread tracked in session context for that chat.
2. **State Cleanup upon Topic Deletion:**
   When `delete_thread` successfully deletes a topic, if `message_thread_id` matches the current active thread in session context for that chat, the active thread tracking is cleared immediately, preventing subsequent messages (`reply`, `ask_user`) from routing into the deleted topic.
3. **General Topic `#1` Guard:**
   Telegram's General topic (`message_thread_id: 1`) cannot be closed, reopened, or deleted. Invocations attempting to close or delete thread 1 are rejected locally with `{ success: false, error: "Cannot modify or delete the General forum topic" }` before API dispatch.

### 3. Telegram API Constraints & Validation Limits

| Operation | Telegram Bot API Method | Telegram Constraints & Limits | Error Handling & Status |
| :- | :- | :- | :- |
| `close_thread` | `closeForumTopic` | Requires `can_manage_topics` admin right; cannot close General topic (`#1`); topic must currently be open. | Fails fast on General topic; propagates API errors (`TOPIC_NOT_MODIFIED`, `NOT_ENOUGH_RIGHTS`) as `{ success: false, error: "..." }`. |
| `reopen_thread` | `reopenForumTopic` | Requires `can_manage_topics` admin right; topic must currently be closed. | Propagates API errors as `{ success: false, error: "..." }`. |
| `delete_thread` | `deleteForumTopic` | Requires `can_delete_messages` and `can_manage_topics` admin rights; cannot delete General topic (`#1`). Irreversible. | Fails fast on General topic; clears active thread in state; surfaces errors verbatim. |
| `pin_message` | `pinChatMessage` | Requires `can_pin_messages` admin right in supergroups; message must exist. Silent by default (`disable_notification: true`). | Propagates API errors as `{ success: false, error: "..." }`. |
| `unpin_message` | `unpinChatMessage` | Requires `can_pin_messages` admin right. Omitted `message_id` unpins the most recent pin. | Propagates API errors as `{ success: false, error: "..." }`. |
| `unpin_all_messages` | `unpinAllForumTopicMessages` (in thread) / `unpinAllChatMessages` (chat-wide) | Requires `can_pin_messages` admin right. Routes dynamically based on presence of `message_thread_id`. | Propagates API errors as `{ success: false, error: "..." }`. |
| `forward_messages` | `forwardMessages` | Batch size: strictly 1 to 100 message IDs. Must all originate from `from_chat_id`. | Local validation rejects empty or > 100 counts with `{ success: false, error: "Batch size must be between 1 and 100 messages" }`; surfaces Telegram rejections. |
| `copy_messages` | `copyMessages` | Batch size: strictly 1 to 100 message IDs. Removes forward headers. | Local validation rejects empty or > 100 counts; surfaces Telegram rejections. |
| `delete_messages` | `deleteMessages` | Batch size: strictly 1 to 100 message IDs. In private chats and normal groups, messages can only be deleted if sent < 48 hours ago. | Local validation rejects empty or > 100 counts. Rejections (`MESSAGE_DELETE_FORBIDDEN`) surface verbatim. |
| `edit_message_reply_markup` | `editMessageReplyMarkup` | Message must have been sent by the bot and exist. Passing empty buttons clears markup. | Telegram error `message is not modified` is caught and treated as idempotent success (`{ success: true, not_modified: true }`). |

## Outcome-Level Build Criteria Mapped to Checks

| Criterion | Target Requirement | Verification Check & Observable Proof |
| :- | :- | :- |
| **AC-1** | `close_thread`, `reopen_thread`, and `delete_thread` manage topic lifecycles via `closeForumTopic`, `reopenForumTopic`, and `deleteForumTopic`; `delete_thread` clears active thread from session context; General topic `#1` is guarded against deletion or closure. | Integration tests verify topic close, reopen, delete, active thread clearing in session context, and General topic `#1` guard. |
| **AC-2** | `pin_message`, `unpin_message`, and `unpin_all_messages` manage pinned messages via `pinChatMessage`, `unpinChatMessage`, `unpinAllForumTopicMessages` (in threads), and `unpinAllChatMessages` (chat-wide), with silent notification by default. | Unit tests verify message pinning with `disable_notification: true`, unpinning specific/recent message, and thread vs chat unpin all. |
| **AC-3** | `forward_messages` and `copy_messages` transfer batches of 1 to 100 messages into target chats or topics via `forwardMessages` and `copyMessages`, validating batch sizes locally and propagating Telegram API rejections. | Unit tests verify batch forwarding and copying, 1-100 size validation, and API error handling. |
| **AC-4** | `delete_messages` deletes batches of 1 to 100 messages via `deleteMessages`, validating 1-100 counts and surfacing Telegram's 48-hour age limit rejections verbatim. | Unit tests verify batch deletion and 48-hour age rejection reporting. |
| **AC-5** | `edit_message_reply_markup` updates or clears inline keyboards, treating `message is not modified` as idempotent success. | Unit tests verify button modification/clearing and idempotent not-modified handling. |
