export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
}

const OUTBOUND_THREAD_ROUTING_PROPS: Record<string, unknown> = {
  chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
  message_thread_id: {
    type: "integer",
    description: "Telegram message thread ID (for forum supergroups or topics-enabled chats; defaults to active thread)",
  },
  thread_id: { type: "integer", description: "Alias for message_thread_id" },
};

const OUTBOUND_MESSAGE_ROUTING_PROPS: Record<string, unknown> = {
  ...OUTBOUND_THREAD_ROUTING_PROPS,
  reply_to: { type: "integer", description: "Optional message ID to reply to" },
  disable_notification: { type: "boolean", description: "Send the message silently" },
};

const OUTBOUND_KEYBOARD_PROPS: Record<string, unknown> = {
  buttons: {
    type: "array",
    description: "Optional custom inline buttons (flat or 2D row array of { label, url?, callback_data?, web_app? })",
  },
  button_layout: {
    description: "Optional explicit row sizes array (e.g. [2, 1]) or buttons-per-row integer for flat button arrays",
  },
  buttons_per_row: {
    type: "integer",
    description: "Optional buttons per row when auto-wrapping flat button arrays",
  },
};

export const MCP_TOOLS: ToolDefinition[] = [
  {
    name: "reply",
    description:
      "Send a message to the user over Telegram with progressive disclosure, expandable blockquotes, thread routing, and Details button.",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_thread_id: {
          type: "integer",
          description: "Telegram forum topic / thread ID (defaults to active thread when in a topics chat)",
        },
        thread_id: { type: "integer", description: "Alias for message_thread_id" },
        text: { type: "string", description: "Markdown text for chat (tier 1 and 2)" },
        detail: { type: "string", description: "Optional deep markdown for Details page (tier 3)" },
        details: { type: "string", description: "Alias for detail" },
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
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
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
              details: { type: "string", description: "Alias for detail" },
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
  {
    name: "send_photo",
    description:
      "Send an image or photo to the Telegram chat and active thread via local file path, file_id, or HTTP(S) URL (sendPhoto).",
    inputSchema: {
      type: "object",
      properties: {
        photo: { type: "string", description: "Local file path, Telegram file_id, or HTTP(S) URL for the photo" },
        caption: { type: "string", description: "Optional Markdown caption" },
        has_spoiler: { type: "boolean", description: "Cover the photo with a spoiler animation" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["photo"],
    },
  },
  {
    name: "send_document",
    description:
      "Send a document or arbitrary file to the Telegram chat and active thread via local file path, file_id, or HTTP(S) URL (sendDocument).",
    inputSchema: {
      type: "object",
      properties: {
        document: { type: "string", description: "Local file path, Telegram file_id, or HTTP(S) URL for the document" },
        caption: { type: "string", description: "Optional Markdown caption" },
        disable_content_type_detection: {
          type: "boolean",
          description: "Disable server-side content type detection for uploaded files",
        },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["document"],
    },
  },
  {
    name: "send_video",
    description:
      "Send a video file to the Telegram chat and active thread via local file path, file_id, or HTTP(S) URL (sendVideo).",
    inputSchema: {
      type: "object",
      properties: {
        video: { type: "string", description: "Local file path, Telegram file_id, or HTTP(S) URL for the video" },
        caption: { type: "string", description: "Optional Markdown caption" },
        duration: { type: "integer", description: "Duration of the video in seconds" },
        width: { type: "integer", description: "Video width in pixels" },
        height: { type: "integer", description: "Video height in pixels" },
        has_spoiler: { type: "boolean", description: "Cover the video with a spoiler animation" },
        supports_streaming: { type: "boolean", description: "Pass true if the uploaded video is suitable for streaming" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["video"],
    },
  },
  {
    name: "send_animation",
    description:
      "Send an animation (GIF or H.264/MPEG-4 AVC video without sound) to the Telegram chat and active thread (sendAnimation).",
    inputSchema: {
      type: "object",
      properties: {
        animation: {
          type: "string",
          description: "Local file path, Telegram file_id, or HTTP(S) URL for the animation",
        },
        caption: { type: "string", description: "Optional Markdown caption" },
        duration: { type: "integer", description: "Duration of the animation in seconds" },
        width: { type: "integer", description: "Animation width in pixels" },
        height: { type: "integer", description: "Animation height in pixels" },
        has_spoiler: { type: "boolean", description: "Cover the animation with a spoiler animation" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["animation"],
    },
  },
  {
    name: "send_media_group",
    description:
      "Send a group of 2 to 10 photos, videos, documents, or audio files as an album to the Telegram chat and active thread (sendMediaGroup).",
    inputSchema: {
      type: "object",
      properties: {
        media: {
          type: "array",
          description: "2 to 10 media items to include in the album",
          items: {
            type: "object",
            properties: {
              type: {
                type: "string",
                enum: ["photo", "video", "document", "animation", "audio"],
                description: "Media item type",
              },
              media: {
                type: "string",
                description: "Local file path, Telegram file_id, or HTTP(S) URL for the item",
              },
              caption: { type: "string", description: "Optional Markdown caption for this item" },
              has_spoiler: { type: "boolean", description: "Optional spoiler flag for photo/video/animation items" },
            },
            required: ["type", "media"],
          },
        },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
      },
      required: ["media"],
    },
  },
  {
    name: "send_audio",
    description:
      "Send an audio file to be displayed in the music player in the Telegram chat and active thread (sendAudio).",
    inputSchema: {
      type: "object",
      properties: {
        audio: { type: "string", description: "Local file path, Telegram file_id, or HTTP(S) URL for the audio file" },
        caption: { type: "string", description: "Optional Markdown caption" },
        duration: { type: "integer", description: "Duration of the audio in seconds" },
        performer: { type: "string", description: "Performer of the audio track" },
        title: { type: "string", description: "Track title" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["audio"],
    },
  },
  {
    name: "send_video_note",
    description:
      "Send a rounded square MPEG4 video note message to the Telegram chat and active thread (sendVideoNote).",
    inputSchema: {
      type: "object",
      properties: {
        video_note: {
          type: "string",
          description: "Local file path, Telegram file_id, or HTTP(S) URL for the video note",
        },
        duration: { type: "integer", description: "Duration of the video note in seconds" },
        length: { type: "integer", description: "Video width and height (diameter of the video message) in pixels" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["video_note"],
    },
  },
  {
    name: "send_location",
    description: "Send a geographic point on the map to the Telegram chat and active thread (sendLocation).",
    inputSchema: {
      type: "object",
      properties: {
        latitude: { type: "number", description: "Latitude of the location (-90 to 90)" },
        longitude: { type: "number", description: "Longitude of the location (-180 to 180)" },
        horizontal_accuracy: { type: "number", description: "Radius of uncertainty for the location in meters (0-1500)" },
        live_period: {
          type: "integer",
          description: "Period in seconds during which the location can be updated (60-86400, or 0x7FFFFFFF)",
        },
        heading: { type: "integer", description: "Direction in which the user is moving in degrees (1-360)" },
        proximity_alert_radius: {
          type: "integer",
          description: "Maximum distance for proximity alerts in meters (1-100000)",
        },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["latitude", "longitude"],
    },
  },
  {
    name: "send_venue",
    description: "Send information about a venue to the Telegram chat and active thread (sendVenue).",
    inputSchema: {
      type: "object",
      properties: {
        latitude: { type: "number", description: "Latitude of the venue (-90 to 90)" },
        longitude: { type: "number", description: "Longitude of the venue (-180 to 180)" },
        title: { type: "string", description: "Name of the venue" },
        address: { type: "string", description: "Address of the venue" },
        foursquare_id: { type: "string", description: "Optional Foursquare identifier of the venue" },
        foursquare_type: { type: "string", description: "Optional Foursquare venue type" },
        google_place_id: { type: "string", description: "Optional Google Places identifier of the venue" },
        google_place_type: { type: "string", description: "Optional Google Places venue type" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["latitude", "longitude", "title", "address"],
    },
  },
  {
    name: "send_contact",
    description: "Send a phone contact to the Telegram chat and active thread (sendContact).",
    inputSchema: {
      type: "object",
      properties: {
        phone_number: { type: "string", description: "Contact's phone number" },
        first_name: { type: "string", description: "Contact's first name" },
        last_name: { type: "string", description: "Optional contact's last name" },
        vcard: { type: "string", description: "Optional additional data about the contact in the form of a vCard" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["phone_number", "first_name"],
    },
  },
  {
    name: "send_dice",
    description:
      "Send an animated emoji that displays a random value (🎲, 🎯, 🏀, ⚽, 🎳, or 🎰) to the Telegram chat and active thread (sendDice).",
    inputSchema: {
      type: "object",
      properties: {
        emoji: {
          type: "string",
          enum: ["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"],
          description: "Emoji on which the dice throw animation is based (defaults to 🎲)",
        },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
    },
  },
  {
    name: "send_chat_action",
    description:
      "Broadcast a transient chat activity status (such as typing or upload_document) to the Telegram chat and active thread (sendChatAction).",
    inputSchema: {
      type: "object",
      properties: {
        action: {
          type: "string",
          enum: [
            "typing",
            "upload_photo",
            "record_video",
            "upload_video",
            "record_voice",
            "upload_voice",
            "upload_document",
            "choose_sticker",
            "find_location",
            "record_video_note",
            "upload_video_note",
          ],
          description: "Type of chat action to broadcast",
        },
        ...OUTBOUND_THREAD_ROUTING_PROPS,
      },
      required: ["action"],
    },
  },
  {
    name: "send_message_draft",
    description:
      "Stream a partial message draft to the user in the Telegram chat and active thread while generating a response (sendMessageDraft).",
    inputSchema: {
      type: "object",
      properties: {
        draft_id: {
          type: "integer",
          description: "Non-zero integer identifier for the message draft being streamed",
        },
        text: { type: "string", description: "Current draft text in Markdown" },
        ...OUTBOUND_THREAD_ROUTING_PROPS,
      },
      required: ["draft_id", "text"],
    },
  },
  {
    name: "send_poll",
    description: "Send a native regular or quiz poll with 2-12 options to the Telegram chat and active thread (sendPoll).",
    inputSchema: {
      type: "object",
      properties: {
        question: { type: "string", description: "Poll question (1-300 characters)" },
        options: {
          type: "array",
          description: "2 to 12 answer options (each a string or { text: string }, 1-100 characters)",
          items: {
            description: "Answer option text or object with text property",
          },
        },
        is_anonymous: { type: "boolean", description: "True if the poll needs to be anonymous (defaults to true)" },
        type: {
          type: "string",
          enum: ["regular", "quiz"],
          description: "Poll type: regular or quiz (defaults to regular)",
        },
        allows_multiple_answers: {
          type: "boolean",
          description: "True if the regular poll allows multiple answers",
        },
        correct_option_id: {
          type: "integer",
          description: "0-based identifier of the correct answer option (required for quiz polls)",
        },
        explanation: {
          type: "string",
          description: "Optional Markdown explanation shown when a user answers a quiz poll (0-200 characters)",
        },
        open_period: {
          type: "integer",
          description: "Amount of time in seconds the poll will be active after creation (5-600)",
        },
        close_date: {
          type: "integer",
          description: "Point in time (Unix timestamp) when the poll will be automatically closed",
        },
        is_closed: { type: "boolean", description: "Pass true if the poll needs to be immediately closed" },
        ...OUTBOUND_MESSAGE_ROUTING_PROPS,
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["question", "options"],
    },
  },
  {
    name: "stop_poll",
    description: "Stop an active poll previously sent by the bot and return the final poll results (stopPoll).",
    inputSchema: {
      type: "object",
      properties: {
        chat_id: { type: "integer", description: "Telegram chat ID (defaults to primary chat)" },
        message_id: { type: "integer", description: "Identifier of the original message with the poll" },
        ...OUTBOUND_KEYBOARD_PROPS,
      },
      required: ["message_id"],
    },
  },
];
