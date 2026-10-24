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
          description: "Attach message action buttons (Check logic, Explain). Defaults to true.",
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
    description: "Post an asynchronous question to the user over Telegram with vertical choice buttons.",
    inputSchema: {
      type: "object",
      properties: {
        turn_id: { type: "string", description: "Turn ID for correlating the async answer event" },
        session_id: { type: "string", description: "Session ID for correlating with the asking session" },
        questions: {
          type: "array",
          items: {
            type: "object",
            properties: {
              question: { type: "string" },
              header: { type: "string" },
              context: { type: "string", description: "Background context, evidence, or pointers bearing on the decision" },
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
              multiSelect: { type: "boolean" },
              allowOther: { type: "boolean" },
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
      },
      required: ["message_id", "text"],
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
