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
      "Send a message to the user over Telegram with progressive disclosure, expandable blockquotes, and Details button.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary user)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram message thread ID (for forum supergroups or topics-enabled chats; defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        text: { type: "string", description: "Markdown text for chat (tier 1 and 2)" },
        detail: { type: "string", description: "Optional deep markdown for Details page (tier 3)" },
        buttons: {
          type: "array",
          description:
            "Inline option buttons. Can be a flat array of buttons (defaulting to 1 per row or arranged via button_layout / buttons_per_row) or an array of rows (array of button arrays) for custom multi-row grids.",
          items: {
            anyOf: [
              {
                type: "object",
                properties: {
                  label: { type: "string" },
                  callback_data: { type: "string" },
                  url: { type: "string" },
                  web_app: { type: "string" },
                  row: { type: "integer", description: "Optional row index (0-based)" },
                },
                required: ["label"],
              },
              {
                type: "array",
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
            ],
          },
        },
        button_layout: {
          description:
            "Optional custom row layout specifying button counts per row (e.g. [3, 3, 2] or [4, 4]), or a uniform row size integer.",
          anyOf: [
            { type: "array", items: { type: "integer" } },
            { type: "integer" },
          ],
        },
        buttons_per_row: {
          type: "integer",
          description: "Optional number of buttons per row to automatically arrange flat buttons into rows.",
        },
        predefined_row: {
          type: "boolean",
          description:
            "Put all predefined buttons (Details, Check logic, Explain, Reasons, Accept/Decline recommendation, and optional feedback/review) together on a single first row above the caller's rows.",
        },
        voice: { type: "boolean", description: "Send tier 1 as a spoken voice note" },
        reply_to: { type: "integer", description: "Telegram message ID to reply to" },
        feedback: { type: "boolean", description: "Whether to attach 👍/👎 buttons (default false)" },
        review: {
          type: "object",
          description: "Attach PR diff review card",
          properties: {
            repo: { type: "string" },
            pr: { type: "integer" },
          },
        },
        actions: {
          type: "boolean",
          description: "Attach message action buttons (Check logic, Explain, Reasons, Accept/Decline recommendation). Defaults to true.",
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
        reaction: {
          type: "string",
          description: "Emoji reaction string (e.g. 🐳 for polecat, 🕊 for subagent, or other shared legend reaction)",
        },
        message_thread_id: { type: "integer", description: "Optional thread ID" },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
      required: ["message_id", "reaction"],
    },
  },
  {
    name: "ask_user",
    description:
      "Post an asynchronous question to the user over Telegram or the Mini App with vertical choice buttons. Set mini_app_only: true (or chat: false) to route questions to the Mini App only without posting to chat. Pass detail on questions to attach fuller background opened via a Details button in the Mini App.",
    inputSchema: {
      type: "object",
      properties: {
        turn_id: { type: "string", description: "Turn ID for correlating the async answer event" },
        session_id: { type: "string", description: "Session ID for correlating with the asking session" },
        message_thread_id: {
          type: "integer",
          description: "Telegram message thread ID (for forum supergroups or topics-enabled chats; defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        chat: {
          type: "boolean",
          description:
            "Whether to post question cards to Telegram chat (default true). Set false (or mini_app_only: true) to route questions to the Mini App only.",
        },
        mini_app_only: {
          type: "boolean",
          description: "If true, posts questions to the Mini App only without sending cards to Telegram chat.",
        },
        questions: {
          type: "array",
          items: {
            type: "object",
            properties: {
              question: { type: "string" },
              header: { type: "string" },
              context: { type: "string", description: "Background context, evidence, or pointers bearing on the decision" },
              detail: {
                type: "string",
                description:
                  "Fuller background, evidence, logs, or deep context opened via the Details button in the Mini App (tier 3)",
              },
              recommendation: { type: "string", description: "Concrete recommendation with functional rationale" },
              options: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    label: { type: "string" },
                    description: { type: "string" },
                    recommended: { type: "boolean" },
                  },
                  required: ["label"],
                },
              },
              multi_select: { type: "boolean", description: "Whether multiple options may be selected" },
              multiSelect: { type: "boolean", description: "Alias for multi_select" },
              allow_custom: { type: "boolean", description: "Whether free-text responses are permitted" },
              allowOther: { type: "boolean", description: "Alias for allow_custom" },
              chat: {
                type: "boolean",
                description:
                  "Whether to post a card for this question to Telegram chat (default true). Set false to route to the Mini App only.",
              },
              mini_app_only: {
                type: "boolean",
                description: "If true, posts this question to the Mini App only without sending a card to chat.",
              },
              message_thread_id: { type: "integer" },
              thread_id: { type: "integer" },
              turn_id: { type: "string" },
              session_id: { type: "string" },
            },
            required: ["question", "options"],
          },
        },
      },
      required: ["questions"],
    },
  },
  {
    name: "answer_question",
    description: "Record an answer for a pending question (e.g. when answered directly in session). Sets the question status to answered and removes it from the outstanding list.",
    inputSchema: {
      type: "object",
      properties: {
        question_id: { type: "string", description: "ID of the pending question to answer" },
        choice: { type: "string", description: "The answer or choice provided by the user" },
        option_index: { type: "integer", description: "Optional 0-based index of the chosen option" },
      },
      required: ["question_id"],
    },
  },
  {
    name: "close_question",
    description: "Close a pending question with a stated reason (answered elsewhere, no longer needed, or replaced by a newer question).",
    inputSchema: {
      type: "object",
      properties: {
        question_id: { type: "string", description: "ID of the pending question to close" },
        reason: { type: "string", description: "Stated reason for closing the question" },
      },
      required: ["question_id", "reason"],
    },
  },
  {
    name: "list_questions",
    description: "List every pending Mini App question with its id, text, session, turn, and when it was asked.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "anchor",
    description: "Update the live cognitive anchor with Ida's current focus, task, and waiting-on state.",
    inputSchema: {
      type: "object",
      properties: {
        focus: { type: "string", description: "Current focus summary" },
        task_id: { type: "string", description: "Current PKB task ID" },
        waiting_on: { type: "array", items: { type: "string" } },
        delegations: { type: "array", items: { type: "string" } },
      },
      required: ["focus"],
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
        message_thread_id: { type: "integer" },
        thread_id: { type: "integer" },
      },
      required: ["message_id", "text"],
    },
  },
  {
    name: "rename_thread",
    description:
      "Rename a Telegram forum topic (thread). Defaults to the active thread in the current chat if message_thread_id is omitted.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary user)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram message thread ID (forum topic ID; defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        name: {
          type: "string",
          description: "New name for the thread (1-128 characters)",
        },
        title: {
          type: "string",
          description: "Alias for name",
        },
        icon_custom_emoji_id: {
          type: "string",
          description: "Optional custom emoji ID for the topic icon (pass empty string to remove)",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "create_thread",
    description:
      "Create a new Telegram forum topic (thread) with a given title. Sets the active thread so subsequent replies land inside it.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary user)" },
        name: {
          type: "string",
          description: "Name for the new thread (1-128 characters)",
        },
        title: {
          type: "string",
          description: "Alias for name",
        },
        icon_color: {
          type: "integer",
          description:
            "Optional RGB color of topic icon (e.g. 7322096, 16766590, 13338331, 9367192, 16749490, 16478047)",
        },
        icon_custom_emoji_id: {
          type: "string",
          description: "Optional custom emoji ID for the topic icon",
        },
      },
      required: ["name"],
    },
  },
  {
    name: "close_thread",
    description: "Close an active or specified forum topic (thread) in Telegram.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram forum topic ID (defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "reopen_thread",
    description: "Reopen a closed forum topic (thread) in Telegram.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram forum topic ID (defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "delete_thread",
    description: "Delete a forum topic (thread) and all its messages in Telegram.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram forum topic ID (defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "pin_message",
    description: "Pin a message in a Telegram chat or forum topic.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_id: { type: "integer", description: "Message ID to pin" },
        disable_notification: { type: "boolean", description: "Pin silently without notification (default true)" },
      },
      required: ["message_id"],
    },
  },
  {
    name: "unpin_message",
    description: "Unpin a specific message or the most recent pinned message in a Telegram chat.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_id: {
          type: "integer",
          description: "Optional message ID to unpin; if omitted, unpins the most recent pinned message",
        },
      },
    },
  },
  {
    name: "unpin_all_messages",
    description: "Unpin all messages in a Telegram chat or forum topic.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Optional topic ID; unpins topic messages if specified, or all chat messages if omitted",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
      },
    },
  },
  {
    name: "forward_messages",
    description: "Forward a batch of 1 to 100 messages into a target Telegram chat or forum topic.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Destination chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Destination forum topic ID (defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        from_chat_id: { type: "integer", description: "Source chat ID (defaults to destination chat)" },
        message_ids: {
          type: "array",
          items: { type: "integer" },
          description: "List of 1 to 100 message IDs to forward",
        },
        disable_notification: { type: "boolean", description: "Forward silently without notification" },
        protect_content: { type: "boolean", description: "Protect forwarded messages from forwarding and saving" },
      },
      required: ["message_ids"],
    },
  },
  {
    name: "copy_messages",
    description:
      "Copy a batch of 1 to 100 messages into a target Telegram chat or forum topic without forward headers.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Destination chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Destination forum topic ID (defaults to active thread)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        from_chat_id: { type: "integer", description: "Source chat ID (defaults to destination chat)" },
        message_ids: {
          type: "array",
          items: { type: "integer" },
          description: "List of 1 to 100 message IDs to copy",
        },
        disable_notification: { type: "boolean", description: "Copy silently without notification" },
        protect_content: { type: "boolean", description: "Protect copied messages from forwarding and saving" },
        remove_caption: { type: "boolean", description: "Remove media captions when copying" },
      },
      required: ["message_ids"],
    },
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
          description: "List of 1 to 100 message IDs to delete",
        },
      },
      required: ["message_ids"],
    },
  },
  {
    name: "edit_message_reply_markup",
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
                  row: { type: "integer" },
                },
                required: ["label"],
              },
              {
                type: "array",
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
            ],
          },
        },
        button_layout: {
          description:
            "Optional custom row layout specifying button counts per row (e.g. [3, 3, 2]) or uniform size integer",
          anyOf: [{ type: "array", items: { type: "integer" } }, { type: "integer" }],
        },
        buttons_per_row: { type: "integer", description: "Optional uniform number of buttons per row" },
      },
      required: ["message_id"],
    },
  },
  {
    name: "download_attachment",
    description: "Download a Telegram attachment or voice note to a local path.",
    inputSchema: {
      type: "object",
      properties: {
        file_id: { type: "string" },
        destination: { type: "string" },
      },
      required: ["file_id"],
    },
  },
];
