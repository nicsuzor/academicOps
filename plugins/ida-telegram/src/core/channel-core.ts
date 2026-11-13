import { PluginConfig } from "../config.js";
import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import { TelegramBotClient, buildInlineKeyboardRows, type ReplyButtonsInput } from "../telegram/bot.js";
import { PermissionRelay } from "../mcp/permissions.js";
import { processReplyOverflow } from "../telegram/overflow.js";
import { formatMarkdownToEntities, normalizeReaction } from "../telegram/format.js";
import { splitVoiceTier2Quotes } from "../telegram/voice.js";
import { TurnManager } from "./turn-manager.js";

export interface OutboundReplyParams {
  text: string;
  chat_id?: number;
  reply_to?: number;
  voice?: boolean;
  detail?: string;
  buttons?: any;
  button_layout?: number[] | number;
  buttonLayout?: number[] | number;
  buttons_per_row?: number;
  buttonsPerRow?: number;
  predefined_row?: boolean;
  predefinedRow?: boolean;
  feedback?: boolean;
  actions?: boolean;
  message_thread_id?: number;
  messageThreadId?: number;
  thread_id?: number;
  threadId?: number;
  review?: { repo: string; pr?: number; base?: string; head?: string };
}

export interface OutboundReplyResult {
  success: boolean;
  message_id?: number;
  messageId?: number;
  voice_message_id?: number;
  voiceMessageId?: number;
  voiceSent?: boolean;
  voiceError?: string;
  detailsId?: string;
  preview?: string;
}

export interface OutboundReactParams {
  message_id: number;
  reaction: string;
  chat_id?: number;
}

export interface OutboundReactResult {
  success: boolean;
  reaction?: string;
  error?: string;
}

export interface QuestionSpec {
  question: string;
  header?: string;
  options: Array<{ label: string; description?: string; recommended?: boolean }>;
  multi_select?: boolean;
  multiSelect?: boolean;
  allow_custom?: boolean;
  allowOther?: boolean;
  turn_id?: string;
  turnId?: string;
  mini_app_only?: boolean;
  miniapp_only?: boolean;
  miniAppOnly?: boolean;
  chat?: boolean;
  context?: string;
  detail?: string;
  details?: string;
  recommendation?: string;
}

export interface OutboundAskUserParams {
  turn_id?: string;
  turnId?: string;
  questions: QuestionSpec[];
  chat_id?: number;
  mini_app_only?: boolean;
  miniapp_only?: boolean;
  miniAppOnly?: boolean;
  chat?: boolean;
}

export interface OutboundAskUserResult {
  success?: boolean;
  error?: string;
  question_ids: string[];
  status: "posted" | "failed";
  message: string;
}

export interface OutboundEditMessageParams {
  message_id: number;
  text: string;
  chat_id?: number;
}

export interface OutboundEditMessageResult {
  success: boolean;
  error?: string;
}

export interface ChannelCoreOptions {
  config: PluginConfig;
  store: PluginStore;
  broker: QuestionBroker;
  bot: TelegramBotClient | null;
  permRelay: PermissionRelay;
  turnManager?: TurnManager;
}

export class SharedTelegramChannelCore {
  public config: PluginConfig;
  public store: PluginStore;
  public broker: QuestionBroker;
  public bot: TelegramBotClient | null;
  public permRelay: PermissionRelay;
  public turnManager?: TurnManager;

  constructor(options: ChannelCoreOptions) {
    this.config = options.config;
    this.store = options.store;
    this.broker = options.broker;
    this.bot = options.bot;
    this.permRelay = options.permRelay;
    this.turnManager = options.turnManager;
  }

  public getDefaultChatId(): number {
    return this.config.allowFrom[0] || 0;
  }

  /**
   * Outbound tool contract: reply
   * Formats with rich typography (expandable blockquotes),
   * splits at whole-paragraph boundaries at 1,200 chars with continuation notices,
   * synthesizes voice when requested or mirrored.
   */
  public async reply(params: OutboundReplyParams): Promise<OutboundReplyResult> {
    const text = params.text || "";
    const detail = params.detail;
    const chatId = params.chat_id || this.getDefaultChatId();
    const replyTo = params.reply_to;

    // Check voice reply
    let isVoice = false;
    if (typeof params.voice === "boolean") {
      isVoice = params.voice;
    } else if (this.config.voiceReplies === "always") {
      isVoice = true;
    } else if (this.config.voiceReplies === "mirror" && this.bot?.isLastInboundVoice(chatId)) {
      isVoice = true;
    }

    let effectiveText = text;
    let effectiveDetail = detail;
    if (isVoice) {
      const { tier1Text, tier2Quotes } = splitVoiceTier2Quotes(text);
      if (tier2Quotes) {
        effectiveText = tier1Text;
        effectiveDetail = detail ? `${tier2Quotes}\n\n---\n\n${detail}` : tier2Quotes;
      }
    }

    // 1. Process paragraph overflow at 1,200 chars
    const overflowRes = processReplyOverflow({
      text: effectiveText,
      detail: effectiveDetail,
      maxChatChars: this.config.maxChatChars || 1200,
    });

    let detailsId: string | undefined;
    if (overflowRes.combinedDetail) {
      detailsId = this.store.storeDetails(overflowRes.combinedDetail);
    }

    if (params.review?.repo) {
      this.store.addReview(params.review);
    }
    this.store.recordTurn("out", overflowRes.chatText);

    // 2. Format rich typography and entities
    const formatted = formatMarkdownToEntities(overflowRes.chatText);

    // 3. Deliver to Telegram
    if (this.bot) {
      const sendRes = await this.bot.sendReply({
        chatId,
        formatted,
        detailsId,
        buttons: params.buttons,
        buttonLayout: params.buttonLayout ?? params.button_layout,
        buttonsPerRow: params.buttonsPerRow ?? params.buttons_per_row,
        predefinedRow: params.predefinedRow ?? params.predefined_row,
        voice: isVoice,
        replyTo,
        feedback: params.feedback,
        actions: params.actions,
        messageThreadId: params.message_thread_id ?? params.messageThreadId ?? params.thread_id ?? params.threadId,
        review: params.review,
      });

      if (!sendRes || sendRes.ok === false || sendRes.success === false) {
        return {
          success: false,
          error: sendRes?.error || "Failed to deliver reply",
          message_id: sendRes?.messageId,
          messageId: sendRes?.messageId,
        };
      }

      const out: OutboundReplyResult & { message_thread_id?: number } = {
        success: true,
        messageId: sendRes.messageId,
        message_id: sendRes.messageId,
        message_thread_id: sendRes.messageThreadId,
      };
      if (detailsId !== undefined) {
        out.detailsId = detailsId;
      }
      if (sendRes?.voiceSent !== undefined) {
        out.voiceSent = sendRes.voiceSent;
      }
      if (sendRes?.voiceMessageId !== undefined) {
        out.voiceMessageId = sendRes.voiceMessageId;
        out.voice_message_id = sendRes.voiceMessageId;
      }
      if (sendRes?.voiceError !== undefined) {
        out.voiceError = sendRes.voiceError;
      }
      return out;
    }

    return {
      success: true,
      preview: formatted.plainText,
      detailsId,
      message_id: 0,
      messageId: 0,
    };
  }

  /**
   * Outbound tool contract: react
   * Sets emoji reaction from supported set.
   */
  public async react(params: OutboundReactParams): Promise<OutboundReactResult> {
    const chatId = params.chat_id || this.getDefaultChatId();
    const messageId = params.message_id;
    const norm = normalizeReaction(params.reaction);

    if (!norm) {
      return { success: false, error: `Invalid reaction: ${params.reaction}` };
    }

    if (this.bot) {
      const res = await this.bot.setReaction(chatId, messageId, norm);
      if (!res.ok) {
        return { success: false, error: res.error || "Reaction failed" };
      }
    }
    return { success: true, reaction: norm };
  }

  /**
   * Outbound tool contract: ask_user
   * Posts non-blocking question cards supporting single-select, multi-select,
   * and custom reply, acknowledging immediately without blocking the agent turn.
   */
  public async askUser(params: OutboundAskUserParams): Promise<OutboundAskUserResult> {
    const defaultChatId = params.chat_id || this.getDefaultChatId();
    const topTurnId = params.turn_id || params.turnId;
    const questions = params.questions || [];
    const topMiniAppOnly = Boolean(
      params.mini_app_only || params.miniapp_only || params.miniAppOnly || params.chat === false
    );
    const topThreadId = (params.message_thread_id ?? params.messageThreadId ?? params.thread_id ?? params.threadId) as number | undefined;

    if (questions.length === 0) {
      throw new Error("No questions provided");
    }

    const postedIds: string[] = [];
    for (const q of questions) {
      const multiSelect = q.multi_select !== undefined ? q.multi_select : q.multiSelect;
      const allowOther = q.allow_custom !== undefined ? q.allow_custom : q.allowOther;
      const isMiniAppOnly = Boolean(
        topMiniAppOnly || q.mini_app_only || q.miniapp_only || q.miniAppOnly || q.chat === false
      );
      const effectiveThreadId = (q.message_thread_id ?? q.messageThreadId ?? q.thread_id ?? q.threadId ?? topThreadId) ?? this.bot?.getLastThreadId(defaultChatId);

      const result = await this.broker.askUser({
        question: q.question,
        header: q.header,
        options: q.options,
        multiSelect,
        allowOther,
        turnId: q.turn_id || q.turnId || topTurnId,
        chatId: defaultChatId,
        mini_app_only: isMiniAppOnly,
        context: q.context,
        detail: q.detail || q.details,
        recommendation: q.recommendation,
        messageThreadId: effectiveThreadId,
      });

      postedIds.push(result.questionId);
      this.store.recordTurn("out", q.header ? `${q.header}: ${q.question}` : q.question);

      if (this.bot && !isMiniAppOnly) {
        const card = this.broker.renderQuestionCard(result.questionId, this.config.miniAppUrl);
        if (card && defaultChatId) {
          const sendRes = await this.bot.sendQuestionCard(defaultChatId, result.questionId, card, effectiveThreadId);
          if (!sendRes?.ok || !sendRes?.result?.message_id) {
            const errorMsg = sendRes?.error || sendRes?.description || "Failed to deliver question card";
            this.broker.markDeliveryFailed(result.questionId, errorMsg);
            return {
              success: false,
              error: errorMsg,
              question_ids: postedIds,
              status: "failed",
              message: `Question delivery failed: ${errorMsg}`,
            };
          }
        }
      }
    }

    let message: string;
    if (topMiniAppOnly) {
      message =
        postedIds.length === 1
          ? `Question ${postedIds[0]} queued in Mini App (mini_app_only: true; no chat cards sent). The user will see it upon opening the Mini App.`
          : `Questions ${postedIds.join(", ")} queued in Mini App (mini_app_only: true; no chat cards sent). The user will see them upon opening the Mini App.`;
    } else {
      message =
        postedIds.length === 1
          ? `Question ${postedIds[0]} posted to the user. Do not assume an answer; continue other work or end your turn.`
          : `Questions ${postedIds.join(", ")} posted to the user. Do not assume an answer; continue other work or end your turn.`;
    }

    return {
      question_ids: postedIds,
      status: "posted",
      message,
    };
  }

  /**
   * Outbound tool contract: edit_message
   * Modifies the text of an agent-sent message.
   */
  public async editMessage(params: OutboundEditMessageParams): Promise<OutboundEditMessageResult> {
    const chatId = params.chat_id || this.getDefaultChatId();
    const messageId = params.message_id;
    const text = params.text;

    if (this.bot) {
      await this.bot.editMessage(chatId, messageId, text);
    }
    return { success: true };
  }

  private resolveThreadContext(args: Record<string, unknown>): { chatId: number; messageThreadId?: number; error?: string } {
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const messageThreadId = ((args.message_thread_id ?? args.messageThreadId ?? args.thread_id ?? args.threadId) as number | undefined) ?? this.bot?.getLastThreadId(chatId);
    return { chatId, messageThreadId };
  }

  private validateThreadName(name: unknown): { name?: string; error?: string } {
    if (typeof name !== "string") {
      return { error: "Missing name: thread name must be a non-empty string" };
    }
    const trimmed = name.trim();
    if (!trimmed) {
      return { error: "Missing name: thread name must be a non-empty string" };
    }
    if (trimmed.length > 128) {
      return { error: "Thread name cannot exceed 128 characters" };
    }
    return { name: trimmed };
  }

  private checkGeneralTopic(messageThreadId?: number): { error?: string } | undefined {
    if (messageThreadId === 1) {
      return { error: "Cannot modify or delete the General forum topic" };
    }
    return undefined;
  }

  public async createThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId } = this.resolveThreadContext(args);
    const nameVal = this.validateThreadName(args.name || args.title);
    if (nameVal.error) {
      return { success: false, error: nameVal.error };
    }
    const options: { iconColor?: number; iconCustomEmojiId?: string } = {};
    if (args.icon_color !== undefined || args.iconColor !== undefined) {
      const rawColor = args.icon_color ?? args.iconColor;
      const parsedColor = typeof rawColor === "number" ? rawColor : Number(rawColor);
      if (!Number.isInteger(parsedColor)) {
        return { success: false, error: "Invalid icon_color: must be an integer RGB value" };
      }
      options.iconColor = parsedColor;
    }
    if (args.icon_custom_emoji_id !== undefined || args.iconCustomEmojiId !== undefined) {
      options.iconCustomEmojiId = String(args.icon_custom_emoji_id ?? args.iconCustomEmojiId);
    }
    const res = await this.bot.createForumTopic(chatId, nameVal.name!, options);
    if (!res?.ok || !res?.result) {
      return { success: false, error: res?.description || "Failed to create forum topic" };
    }
    const tid = res.result.message_thread_id;
    return {
      success: true,
      chat_id: chatId,
      message_thread_id: tid,
      thread_id: tid,
      name: res.result.name || nameVal.name!,
    };
  }

  public async renameThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    if (messageThreadId === undefined) {
      return { success: false, error: "Missing thread ID" };
    }
    const genCheck = this.checkGeneralTopic(messageThreadId);
    if (genCheck) {
      return { success: false, error: genCheck.error };
    }
    const nameVal = this.validateThreadName(args.name || args.title);
    if (nameVal.error) {
      return { success: false, error: nameVal.error };
    }
    const emojiId = (args.icon_custom_emoji_id ?? args.iconCustomEmojiId) as string | undefined;
    const res = await this.bot.editForumTopic(chatId, messageThreadId, nameVal.name!, emojiId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to rename forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_thread_id: messageThreadId,
      thread_id: messageThreadId,
      name: nameVal.name!,
    };
  }

  public async closeThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    if (messageThreadId === undefined) {
      return { success: false, error: "Missing message_thread_id for thread operation" };
    }
    const genCheck = this.checkGeneralTopic(messageThreadId);
    if (genCheck) {
      return { success: false, error: genCheck.error };
    }
    const res = await this.bot.closeForumTopic(chatId, messageThreadId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to close forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_thread_id: messageThreadId,
      thread_id: messageThreadId,
      closed: true,
    };
  }

  public async reopenThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    if (messageThreadId === undefined) {
      return { success: false, error: "Missing message_thread_id for thread operation" };
    }
    const genCheck = this.checkGeneralTopic(messageThreadId);
    if (genCheck) {
      return { success: false, error: genCheck.error };
    }
    const res = await this.bot.reopenForumTopic(chatId, messageThreadId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to reopen forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_thread_id: messageThreadId,
      thread_id: messageThreadId,
      reopened: true,
    };
  }

  public async deleteThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    if (messageThreadId === undefined) {
      return { success: false, error: "Missing message_thread_id for thread operation" };
    }
    const genCheck = this.checkGeneralTopic(messageThreadId);
    if (genCheck) {
      return { success: false, error: genCheck.error };
    }
    const res = await this.bot.deleteForumTopic(chatId, messageThreadId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to delete forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_thread_id: messageThreadId,
      thread_id: messageThreadId,
      deleted: true,
    };
  }

  public async unpinAllThreadMessages(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    if (messageThreadId === undefined) {
      return { success: false, error: "Missing message_thread_id for thread operation" };
    }
    const res = await this.bot.unpinAllForumTopicMessages(chatId, messageThreadId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to unpin all forum topic messages" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_thread_id: messageThreadId,
      thread_id: messageThreadId,
      unpinned_all: true,
    };
  }

  public async getForumTopicIconStickers(): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const res = await this.bot.getForumTopicIconStickers();
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to get forum topic icon stickers" };
    }
    return {
      success: true,
      stickers: res.result || [],
    };
  }

  public async editGeneralThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const nameVal = this.validateThreadName(args.name || args.title);
    if (nameVal.error) {
      return { success: false, error: nameVal.error };
    }
    const res = await this.bot.editGeneralForumTopic(chatId, nameVal.name!);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to edit general forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      name: nameVal.name!,
    };
  }

  public async closeGeneralThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.closeGeneralForumTopic(chatId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to close general forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      closed: true,
    };
  }

  public async reopenGeneralThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.reopenGeneralForumTopic(chatId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to reopen general forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      reopened: true,
    };
  }

  public async hideGeneralThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.hideGeneralForumTopic(chatId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to hide general forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      hidden: true,
    };
  }

  public async unhideGeneralThread(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.unhideGeneralForumTopic(chatId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to unhide general forum topic" };
    }
    return {
      success: true,
      chat_id: chatId,
      unhidden: true,
    };
  }

  public async unpinAllGeneralThreadMessages(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.unpinAllGeneralForumTopicMessages(chatId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to unpin all general forum topic messages" };
    }
    return {
      success: true,
      chat_id: chatId,
      unpinned_all: true,
    };
  }

  private validateMessageIdBatch(rawIds: unknown): { messageIds?: number[]; error?: string } {
    if (
      !Array.isArray(rawIds) ||
      rawIds.length < 1 ||
      rawIds.length > 100 ||
      !rawIds.every((id) => typeof id === "number" && Number.isInteger(id))
    ) {
      return { error: "Batch size must be between 1 and 100 messages" };
    }
    return { messageIds: rawIds };
  }

  private async transferBatchMessages(
    kind: "forward" | "copy",
    args: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const batch = this.validateMessageIdBatch(args.message_ids);
    if (batch.error || !batch.messageIds) {
      return { success: false, error: batch.error || "Batch size must be between 1 and 100 messages" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    const fromChatId = typeof args.from_chat_id === "number" ? args.from_chat_id : chatId;
    const disableNotification = args.disable_notification !== undefined ? Boolean(args.disable_notification) : undefined;
    const protectContent = args.protect_content !== undefined ? Boolean(args.protect_content) : undefined;

    const res =
      kind === "forward"
        ? await this.bot.forwardMessages({
            chatId,
            fromChatId,
            messageIds: batch.messageIds,
            messageThreadId,
            disableNotification,
            protectContent,
          })
        : await this.bot.copyMessages({
            chatId,
            fromChatId,
            messageIds: batch.messageIds,
            messageThreadId,
            disableNotification,
            protectContent,
            removeCaption: args.remove_caption !== undefined ? Boolean(args.remove_caption) : undefined,
          });

    if (!res?.ok) {
      return { success: false, error: res?.description || `Failed to ${kind} messages` };
    }
    const returnedIds = Array.isArray(res.result) ? res.result.map((r) => r.message_id) : [];
    return {
      success: true,
      chat_id: chatId,
      ...(messageThreadId !== undefined ? { message_thread_id: messageThreadId } : {}),
      [kind === "forward" ? "forwarded_count" : "copied_count"]: returnedIds.length,
      message_ids: returnedIds,
    };
  }

  public async pinMessage(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const messageId = args.message_id as number;
    if (!messageId || typeof messageId !== "number") {
      return { success: false, error: "Missing required message_id" };
    }
    const disableNotification = args.disable_notification !== undefined ? Boolean(args.disable_notification) : true;
    const res = await this.bot.pinChatMessage(chatId, messageId, disableNotification);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to pin message" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_id: messageId,
      pinned: true,
    };
  }

  public async unpinMessage(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const messageId = typeof args.message_id === "number" ? args.message_id : undefined;
    const res = await this.bot.unpinChatMessage(chatId, messageId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to unpin message" };
    }
    return {
      success: true,
      chat_id: chatId,
      ...(messageId !== undefined ? { message_id: messageId } : {}),
      unpinned: true,
    };
  }

  public async unpinAllMessages(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const { chatId, messageThreadId } = this.resolveThreadContext(args);
    if (messageThreadId !== undefined) {
      const res = await this.bot.unpinAllForumTopicMessages(chatId, messageThreadId);
      if (!res?.ok) {
        return { success: false, error: res?.description || "Failed to unpin all forum topic messages" };
      }
      return {
        success: true,
        chat_id: chatId,
        message_thread_id: messageThreadId,
        unpinned_all: true,
      };
    }
    const res = await this.bot.unpinAllChatMessages(chatId);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to unpin all chat messages" };
    }
    return {
      success: true,
      chat_id: chatId,
      unpinned_all: true,
    };
  }

  public async forwardMessages(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.transferBatchMessages("forward", args);
  }

  public async copyMessages(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.transferBatchMessages("copy", args);
  }

  public async deleteMessages(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const batch = this.validateMessageIdBatch(args.message_ids);
    if (batch.error || !batch.messageIds) {
      return { success: false, error: batch.error || "Batch size must be between 1 and 100 messages" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.deleteMessages(chatId, batch.messageIds);
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to delete messages" };
    }
    return {
      success: true,
      chat_id: chatId,
      deleted_count: batch.messageIds.length,
      message_ids: batch.messageIds,
    };
  }

  public async editMessageReplyMarkup(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const messageId = args.message_id as number;
    if (!messageId || typeof messageId !== "number") {
      return { success: false, error: "Missing required message_id" };
    }
    const inlineKeyboard = buildInlineKeyboardRows(
      args.buttons as ReplyButtonsInput | undefined,
      (args.button_layout ?? args.buttonLayout) as number[] | number | undefined,
      (args.buttons_per_row ?? args.buttonsPerRow) as number | undefined,
    );
    const res = await this.bot.editMessageReplyMarkup(chatId, messageId, inlineKeyboard);
    if (!res?.ok) {
      if (typeof res?.description === "string" && res.description.toLowerCase().includes("message is not modified")) {
        return {
          success: true,
          chat_id: chatId,
          message_id: messageId,
          not_modified: true,
        };
      }
      return { success: false, error: res?.description || "Failed to edit message reply markup" };
    }
    return {
      success: true,
      chat_id: chatId,
      message_id: messageId,
      updated: true,
    };
  }

  /**
   * Dispatches IPC requests across local Unix domain socket bridge.
   */
  public async handleIpcMessage(msg: Record<string, unknown>): Promise<Record<string, unknown>> {
    const type = msg.type || msg.name;

    switch (type) {
      case "reply":
        return (await this.reply(msg as unknown as OutboundReplyParams)) as unknown as Record<string, unknown>;

      case "react":
        return (await this.react(msg as unknown as OutboundReactParams)) as unknown as Record<string, unknown>;

      case "ask_user": {
        const res = await this.askUser(msg as unknown as OutboundAskUserParams);
        return {
          status: "ok",
          questionId: res.question_ids[0],
          questionIds: res.question_ids,
          ...res,
        };
      }

      case "edit_message":
        return (await this.editMessage(msg as unknown as OutboundEditMessageParams)) as unknown as Record<string, unknown>;

      case "pin_message":
      case "pin_chat_message":
        return await this.pinMessage(msg);

      case "unpin_message":
      case "unpin_chat_message":
        return await this.unpinMessage(msg);

      case "unpin_all_messages":
      case "unpin_all_chat_messages":
        return await this.unpinAllMessages(msg);

      case "forward_messages":
        return await this.forwardMessages(msg);

      case "copy_messages":
        return await this.copyMessages(msg);

      case "delete_messages":
        return await this.deleteMessages(msg);

      case "edit_message_reply_markup":
      case "edit_message_buttons":
        return await this.editMessageReplyMarkup(msg);

      case "create_thread":
      case "create_topic":
      case "create_forum_topic":
        return await this.createThread(msg);

      case "rename_thread":
      case "rename_topic":
      case "edit_thread":
      case "edit_forum_topic":
        return await this.renameThread(msg);

      case "close_thread":
      case "close_topic":
      case "close_forum_topic":
        return await this.closeThread(msg);

      case "reopen_thread":
      case "reopen_topic":
      case "reopen_forum_topic":
        return await this.reopenThread(msg);

      case "delete_thread":
      case "delete_topic":
      case "delete_forum_topic":
        return await this.deleteThread(msg);

      case "unpin_all_thread_messages":
      case "unpin_all_topic_messages":
      case "unpin_all_forum_topic_messages":
        return await this.unpinAllThreadMessages(msg);

      case "get_forum_topic_icon_stickers":
      case "get_thread_icon_stickers":
        return await this.getForumTopicIconStickers();

      case "edit_general_thread":
      case "rename_general_thread":
      case "edit_general_forum_topic":
        return await this.editGeneralThread(msg);

      case "close_general_thread":
      case "close_topic_general":
      case "close_general_topic":
      case "close_general_forum_topic":
        return await this.closeGeneralThread(msg);

      case "reopen_general_thread":
      case "reopen_general_topic":
      case "reopen_general_forum_topic":
        return await this.reopenGeneralThread(msg);

      case "hide_general_thread":
      case "hide_general_topic":
      case "hide_general_forum_topic":
        return await this.hideGeneralThread(msg);

      case "unhide_general_thread":
      case "unhide_general_topic":
      case "unhide_general_forum_topic":
        return await this.unhideGeneralThread(msg);

      case "unpin_all_general_thread_messages":
      case "unpin_all_general_topic_messages":
      case "unpin_all_general_forum_topic_messages":
        return await this.unpinAllGeneralThreadMessages(msg);

      default:
        throw new Error(`Unsupported IPC tool: ${String(type)}`);
    }
  }
}
