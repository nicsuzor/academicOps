import { getBareCommandBehavior, normalizeCommandName } from "./commands.js";

export interface TelegramUser {
  id: number;
  is_bot: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
}

export interface TelegramChat {
  id: number;
  type: "private" | "group" | "supergroup" | "channel";
}

export interface TelegramMessage {
  message_id: number;
  date: number;
  chat: TelegramChat;
  from?: TelegramUser;
  text?: string;
  caption?: string;
  reply_to_message?: TelegramMessage;
  quote?: { text: string };
  photo?: Array<{ file_id: string; file_size?: number }>;
  document?: { file_id: string; file_name?: string };
  voice?: { file_id: string; duration: number };
  audio?: { file_id: string; duration: number };
  reply_markup?: {
    inline_keyboard?: Array<Array<{ text: string; callback_data?: string }>>;
  };
}

export interface TelegramReactionUpdate {
  chat: TelegramChat;
  message_id: number;
  user?: TelegramUser;
  date: number;
  old_reaction: Array<{ type: string; emoji?: string }>;
  new_reaction: Array<{ type: string; emoji?: string }>;
}

export interface TelegramCallbackQuery {
  id: string;
  from: TelegramUser;
  message?: TelegramMessage;
  data?: string;
}

export interface TelegramUpdate {
  update_id: number;
  message?: TelegramMessage;
  edited_message?: TelegramMessage;
  message_reaction?: TelegramReactionUpdate;
  callback_query?: TelegramCallbackQuery;
}

export interface InboundChannelEvent {
  event: "message" | "reaction" | "button_tap" | "bot_command" | "voice" | "attachment" | "miniapp";
  content: string;
  meta: Record<string, string>;
}

export type TargetExcerptFetcher = (messageId: number) => string | undefined;

export function sanitizeChannelMeta(raw: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (value === undefined || value === null) continue;
    const replaced = key.replace(/[^a-zA-Z0-9_]/g, "_");
    if (!replaced) continue;
    const cleanKey = /^[0-9]/.test(replaced) ? `_${replaced}` : replaced;
    out[cleanKey] = typeof value === "string" ? value : String(value);
  }
  return out;
}

export function parseInboundUpdate(
  update: TelegramUpdate,
  allowFrom: number[],
  getExcerpt?: TargetExcerptFetcher
): InboundChannelEvent | null {
  // 1. Text / Media Message
  if (update.message) {
    const msg = update.message;
    const userId = msg.from?.id;

    if (!userId || !allowFrom.includes(userId)) {
      // Disallowed user, drop update
      return null;
    }

    // Check for bot command (starts with '/')
    const text = msg.text || "";
    if (text.startsWith("/")) {
      const parts = text.trim().split(/\s+/);
      const rawCmdToken = parts[0] || "";
      const cmdName = normalizeCommandName(rawCmdToken);
      const cmd = `/${cmdName}`;
      const args = parts.slice(1).join(" ").trim();
      const cmdSpec = getBareCommandBehavior(cmdName);

      const meta: Record<string, string> = {
        event: "bot_command",
        message_id: String(msg.message_id),
        chat_id: String(msg.chat.id),
        command: cmd,
        args,
        user_id: String(userId),
      };

      if (msg.from?.first_name) {
        meta.user = msg.from.first_name;
      }

      if (cmdSpec) {
        meta.skill = cmdSpec.skill;
      }

      if (msg.reply_to_message) {
        meta.reply_to_message_id = String(msg.reply_to_message.message_id);
        if (msg.quote?.text) {
          meta.quoted_text = msg.quote.text;
        } else if (msg.reply_to_message.text) {
          meta.quoted_text = msg.reply_to_message.text.substring(0, 300);
        }
      }

      if (!args && cmdSpec) {
        meta.default_action = cmdSpec.bareAction;
        return {
          event: "bot_command",
          content: `${cmd} — ${cmdSpec.bareAction}`,
          meta,
        };
      }

      return {
        event: "bot_command",
        content: args ? `${cmd} ${args}` : cmd,
        meta,
      };
    }

    // Photo / document attachment
    if ((msg.photo && msg.photo.length > 0) || msg.document) {
      const meta: Record<string, string> = {
        event: "attachment",
        message_id: String(msg.message_id),
        chat_id: String(msg.chat.id),
        user_id: String(userId),
      };

      if (msg.from?.first_name) {
        meta.user = msg.from.first_name;
      }

      if (msg.reply_to_message) {
        meta.reply_to_message_id = String(msg.reply_to_message.message_id);
        if (msg.quote?.text) {
          meta.quoted_text = msg.quote.text;
        } else if (msg.reply_to_message.text) {
          meta.quoted_text = msg.reply_to_message.text.substring(0, 300);
        }
      }

      if (msg.photo && msg.photo.length > 0) {
        const largestPhoto = msg.photo[msg.photo.length - 1];
        if (largestPhoto?.file_id) {
          meta.file_id = largestPhoto.file_id;
        }
        return {
          event: "attachment",
          content: msg.caption || "[Photo attachment]",
          meta,
        };
      }

      if (msg.document) {
        meta.file_id = msg.document.file_id;
        if (msg.document.file_name) {
          meta.file_name = msg.document.file_name;
        }
        return {
          event: "attachment",
          content: msg.caption || `[Document: ${msg.document.file_name || msg.document.file_id}]`,
          meta,
        };
      }
    }

    // Text message
    if (msg.text) {
      const meta: Record<string, string> = {
        event: "message",
        message_id: String(msg.message_id),
        chat_id: String(msg.chat.id),
        user_id: String(userId),
      };

      if (msg.from?.first_name) {
        meta.user = msg.from.first_name;
      }

      if (msg.reply_to_message) {
        meta.reply_to_message_id = String(msg.reply_to_message.message_id);
        if (msg.quote?.text) {
          meta.quoted_text = msg.quote.text;
        } else if (msg.reply_to_message.text) {
          meta.quoted_text = msg.reply_to_message.text.substring(0, 300);
        }
      }

      return {
        event: "message",
        content: msg.text,
        meta,
      };
    }
  }

  // 2. Message Reaction
  if (update.message_reaction) {
    const rx = update.message_reaction;
    const userId = rx.user?.id;
    if (!userId || !allowFrom.includes(userId)) {
      return null;
    }

    const added = rx.new_reaction.map((r) => r.emoji).filter(Boolean).join(" ");
    const removed = rx.old_reaction.map((r) => r.emoji).filter(Boolean).join(" ");
    const targetExcerpt = getExcerpt ? getExcerpt(rx.message_id) : undefined;

    const meta: Record<string, string> = {
      event: "reaction",
      chat_id: String(rx.chat.id),
      target_message_id: String(rx.message_id),
      user_id: String(userId),
      added,
      removed,
    };

    if (targetExcerpt !== undefined) {
      meta.target_excerpt = targetExcerpt;
    }

    return {
      event: "reaction",
      content: `reacted ${added || "removed"} to ${rx.message_id}`,
      meta,
    };
  }

  // 3. Callback Query (Button tap)
  if (update.callback_query) {
    const cb = update.callback_query;
    const userId = cb.from.id;
    if (!allowFrom.includes(userId)) {
      return null;
    }

    const rawData = cb.data || "";
    const splitIndex = rawData.indexOf(":");
    const callbackPrefix = splitIndex !== -1 ? rawData.substring(0, splitIndex) : rawData;
    const payload = splitIndex !== -1 ? rawData.substring(splitIndex + 1) : "";

    const meta: Record<string, string> = {
      event: "button_tap",
      callback_id: cb.id,
      callback_prefix: callbackPrefix,
      payload,
      user_id: String(userId),
    };

    if (cb.message?.message_id !== undefined) {
      meta.target_message_id = String(cb.message.message_id);
    }
    if (cb.message?.chat.id !== undefined) {
      meta.chat_id = String(cb.message.chat.id);
    }

    return {
      event: "button_tap",
      content: `tapped ${payload || callbackPrefix}`,
      meta,
    };
  }

  return null;
}
