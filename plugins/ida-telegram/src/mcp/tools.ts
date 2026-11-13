export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
}

export const MCP_TOOLS: ToolDefinition[] = [
  {
    name: "reply",
    description:
      "Send a message to the user over Telegram with progressive disclosure, expandable blockquotes, thread routing, and Details button.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary user)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram forum topic / thread ID (defaults to active thread when in a topics chat)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        text: { type: "string", description: "Markdown text for chat (tier 1 and 2)" },
        detail: { type: "string", description: "Optional deep markdown for Details page (tier 3)" },
        buttons: {
          type: "array",
          description:
            "Inline option buttons, one per row. Attach one per answer whenever the reply asks the user a question, recommendation first; a tap arrives as a button_tap channel event.",
          items: {
            type: "object",
            properties: {
              label: { type: "string" },
              callback_data: { type: "string" },
              url: { type: "string" },
              web_app: { type: "string" },
            },
            required: ["label"],
          },
        },
        voice: { type: "boolean", description: "Send tier 1 as a spoken voice note" },
        reply_to: { type: "integer", description: "Telegram message ID to reply to" },
        review: {
          type: "object",
          description: "Attach PR diff review card",
          properties: {
            repo: { type: "string" },
            pr: { type: "integer" },
          },
        },
      },
      required: ["text"],
    },
  },
  {
    name: "react",
    description: "Set an emoji reaction on a Telegram message.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID" },
        message_id: { type: "integer", description: "Message ID to react to" },
        reaction: { type: "string", description: "Emoji reaction string from allowed set" },
      },
      required: ["message_id", "reaction"],
    },
  },
  {
    name: "ask_user",
    description:
      "Post an asynchronous question to the user over Telegram or the Mini App with vertical choice buttons. Set mini_app_only: true (or chat: false) to queue questions in the Mini App without posting cards to chat. Pass detail on questions to attach fuller background opened via a Details button in the Mini App.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary user)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram forum topic / thread ID (defaults to active thread when in a topics chat)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        turn_id: { type: "string", description: "Turn ID for correlating the async answer event" },
        mini_app_only: {
          type: "boolean",
          description: "If true, queues questions in the Mini App only without sending cards to Telegram chat.",
        },
        chat: {
          type: "boolean",
          description: "If false, queues questions in the Mini App only without sending cards to Telegram chat.",
        },
        questions: {
          type: "array",
          items: {
            type: "object",
            properties: {
              question: { type: "string" },
              header: { type: "string" },
              options: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    label: { type: "string" },
                    description: { type: "string" },
                  },
                  required: ["label"],
                },
              },
              multi_select: { type: "boolean", description: "Whether multiple options may be selected" },
              multiSelect: { type: "boolean", description: "Alias for multi_select" },
              allow_custom: { type: "boolean", description: "Whether free-text responses are permitted" },
              allowOther: { type: "boolean", description: "Alias for allow_custom" },
              mini_app_only: {
                type: "boolean",
                description: "If true, queues this question in the Mini App only without sending a card to chat.",
              },
              chat: {
                type: "boolean",
                description: "If false, queues this question in the Mini App only without sending a card to chat.",
              },
              detail: { type: "string", description: "Fuller background for Details page in Mini App" },
              context: { type: "string", description: "Context shown above question options" },
              recommendation: { type: "string", description: "Recommended option or guidance" },
              message_thread_id: { type: "integer", description: "Per-question forum topic / thread ID override" },
              thread_id: { type: "integer", description: "Alias for message_thread_id" },
              turn_id: { type: "string" },
            },
            required: ["question", "options"],
          },
        },
      },
      required: ["questions"],
    },
  },
  {
    name: "edit_message",
    description: "Edit an existing Telegram message sent by the bot.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer" },
        message_id: { type: "integer" },
        text: { type: "string" },
      },
      required: ["message_id", "text"],
    },
  },
  {
    name: "create_thread",
    description:
      "Create a new forum topic thread in a Telegram supergroup or topics-enabled chat and activate it for subsequent replies.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        name: { type: "string", description: "Topic name (1-128 characters)" },
        icon_color: {
          type: "integer",
          description: "Optional RGB icon color (7322096, 16766590, 13338331, 9367192, 16749490, or 16478047)",
        },
        icon_custom_emoji_id: {
          type: "string",
          description: "Optional custom emoji ID from get_forum_topic_icon_stickers",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "rename_thread",
    description:
      "Rename a Telegram forum topic and/or update its custom icon (editForumTopic). Cannot rename General topic #1; use edit_general_thread instead.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Forum topic thread ID (defaults to active thread in session context)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        name: { type: "string", description: "New topic name (1-128 characters)" },
        icon_custom_emoji_id: {
          type: "string",
          description: "Optional custom emoji ID, or empty string to remove icon",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "close_thread",
    description: "Close an open Telegram forum topic (closeForumTopic). Cannot close General topic #1.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Forum topic thread ID (defaults to active thread in session context)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "reopen_thread",
    description: "Reopen a closed Telegram forum topic (reopenForumTopic). Cannot reopen General topic #1.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Forum topic thread ID (defaults to active thread in session context)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "delete_thread",
    description:
      "Permanently delete a Telegram forum topic and its message history (deleteForumTopic). Cannot delete General topic #1.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Forum topic thread ID (defaults to active thread in session context)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "unpin_all_thread_messages",
    description: "Unpin all pinned messages inside a Telegram forum topic (unpinAllForumTopicMessages).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Forum topic thread ID (defaults to active thread in session context)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "get_forum_topic_icon_stickers",
    description: "Get custom emoji stickers usable as Telegram forum topic icons (getForumTopicIconStickers).",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "edit_general_thread",
    description: "Rename the General forum topic in a Telegram supergroup (editGeneralForumTopic).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        name: { type: "string", description: "New General topic name (1-128 characters)" },
      },
      required: ["name"],
    },
  },
  {
    name: "close_general_thread",
    description: "Close the open General forum topic in a Telegram supergroup (closeGeneralForumTopic).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      },
    },
  },
  {
    name: "reopen_general_thread",
    description: "Reopen the closed General forum topic in a Telegram supergroup (reopenGeneralForumTopic).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      },
    },
  },
  {
    name: "hide_general_thread",
    description: "Hide the General forum topic in a Telegram supergroup (hideGeneralForumTopic).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      },
    },
  },
  {
    name: "unhide_general_thread",
    description: "Unhide the hidden General forum topic in a Telegram supergroup (unhideGeneralForumTopic).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      },
    },
  },
  {
    name: "unpin_all_general_thread_messages",
    description: "Unpin all pinned messages in the General forum topic (unpinAllGeneralForumTopicMessages).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
      },
    },
  },
  {
    name: "pin_message",
    description: "Pin a specific message in a Telegram chat (pinChatMessage).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_id: { type: "integer", description: "Message ID to pin" },
        disable_notification: {
          type: "boolean",
          description: "Pin silently without notifying chat members (defaults to true)",
        },
      },
      required: ["message_id"],
    },
  },
  {
    name: "unpin_message",
    description: "Unpin a specific message or the most recently pinned message in a Telegram chat (unpinChatMessage).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_id: { type: "integer", description: "Optional message ID to unpin (defaults to most recent pinned message)" },
      },
    },
  },
  {
    name: "unpin_all_messages",
    description:
      "Unpin all pinned messages in a Telegram chat (unpinAllChatMessages) or in the specified/active forum topic (unpinAllForumTopicMessages).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Optional forum topic thread ID to scope unpinning to a topic",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "forward_messages",
    description: "Forward 1-100 messages at once with attribution preserved (forwardMessages).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Target Telegram chat ID (defaults to primary chat)" },
        from_chat_id: { type: "integer", description: "Source Telegram chat ID (defaults to target chat_id)" },
        message_ids: {
          type: "array",
          items: { type: "integer" },
          description: "1 to 100 message IDs to forward",
        },
        message_thread_id: { type: "integer", description: "Optional destination forum topic thread ID" },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        disable_notification: { type: "boolean", description: "Send messages silently" },
        protect_content: { type: "boolean", description: "Protect forwarded content from forwarding/saving" },
      },
      required: ["message_ids"],
    },
  },
  {
    name: "copy_messages",
    description: "Copy 1-100 messages at once without forward attribution (copyMessages).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Target Telegram chat ID (defaults to primary chat)" },
        from_chat_id: { type: "integer", description: "Source Telegram chat ID (defaults to target chat_id)" },
        message_ids: {
          type: "array",
          items: { type: "integer" },
          description: "1 to 100 message IDs to copy",
        },
        message_thread_id: { type: "integer", description: "Optional destination forum topic thread ID" },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        disable_notification: { type: "boolean", description: "Send messages silently" },
        protect_content: { type: "boolean", description: "Protect copied content from forwarding/saving" },
        remove_caption: { type: "boolean", description: "Copy media messages without their captions" },
      },
      required: ["message_ids"],
    },
  },
  {
    name: "delete_messages",
    description: "Delete 1-100 messages simultaneously in a Telegram chat (deleteMessages).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_ids: {
          type: "array",
          items: { type: "integer" },
          description: "1 to 100 message IDs to delete",
        },
      },
      required: ["message_ids"],
    },
  },
  {
    name: "edit_message_reply_markup",
    description: "Add, update, or remove inline keyboard buttons on an existing Telegram message without changing its text (editMessageReplyMarkup).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_id: { type: "integer", description: "Message ID whose inline keyboard markup to edit" },
        buttons: {
          type: "array",
          description: "Inline buttons array (flat or 2D row layout), or empty/omitted to clear buttons",
        },
        button_layout: {
          description: "Explicit row sizes array or buttons-per-row integer for flat button arrays",
        },
        buttons_per_row: {
          type: "integer",
          description: "Buttons per row when auto-wrapping flat button arrays",
        },
      },
      required: ["message_id"],
    },
  },
];
