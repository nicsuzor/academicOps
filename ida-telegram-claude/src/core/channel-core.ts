import { PluginConfig } from "../config.js";
import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import {
  TelegramBotClient,
  buildInlineKeyboardRows,
  type ReplyButtonsInput,
} from "../telegram/bot.js";
import { PermissionRelay } from "../mcp/permissions.js";
import { normalizeReaction } from "../telegram/reactions.js";
import {
  extractRichMessageText,
  type InputRichMessageSpec,
  type RichMediaInputItem,
} from "../telegram/rich-message.js";
import { TurnManager } from "./turn-manager.js";

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
  kind?: "question" | "decision";
  stakes?: string;
  presentation?: "widget" | "rich";
  options: Array<{
    label: string;
    description?: string;
    recommended?: boolean;
    pros?: string[];
    cons?: string[];
  }>;
  multi_select?: boolean;
  multiSelect?: boolean;
  allow_custom?: boolean;
  allowOther?: boolean;
  allow_defer?: boolean;
  allowDefer?: boolean;
  turn_id?: string;
  turnId?: string;
  message_thread_id?: number;
  messageThreadId?: number;
  thread_id?: number;
  threadId?: number;
  mini_app_only?: boolean;
  miniapp_only?: boolean;
  miniAppOnly?: boolean;
  chat?: boolean;
  context?: string;
  detail?: string;
  details?: string;
  detailsId?: string;
  details_id?: string;
  recommendation?: string;
}

export interface OutboundAskUserParams {
  turn_id?: string;
  turnId?: string;
  presentation?: "widget" | "rich";
  questions: QuestionSpec[];
  chat_id?: number;
  message_thread_id?: number;
  messageThreadId?: number;
  thread_id?: number;
  threadId?: number;
  detail?: string;
  details?: string;
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
  presentation?: "widget" | "rich";
  message: string;
}

export interface OutboundEditMessageParams {
  message_id: number;
  markdown?: string;
  html?: string;
  blocks?: Array<Record<string, unknown>>;
  is_rtl?: boolean;
  skip_entity_detection?: boolean;
  buttons?: unknown;
  button_layout?: number[] | number;
  buttons_per_row?: number;
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
  emitChannelNotification?: (content: string, meta: Record<string, unknown>) => void;
}

export class SharedTelegramChannelCore {
  public config: PluginConfig;
  public store: PluginStore;
  public broker: QuestionBroker;
  public bot: TelegramBotClient | null;
  public permRelay: PermissionRelay;
  public turnManager?: TurnManager;
  public emitChannelNotification?: (content: string, meta: Record<string, unknown>) => void;

  constructor(options: ChannelCoreOptions) {
    this.config = options.config;
    this.store = options.store;
    this.broker = options.broker;
    this.bot = options.bot;
    this.permRelay = options.permRelay;
    this.turnManager = options.turnManager;
    this.emitChannelNotification = options.emitChannelNotification;
  }

  public getDefaultChatId(): number {
    return this.config.allowFrom[0] || 0;
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
    const topDetail = params.detail ?? params.details;
    const topPresentation = params.presentation ?? "rich";

    if (questions.length === 0) {
      throw new Error("No questions provided");
    }

    const postedIds: string[] = [];
    const usedPresentations = new Set<"widget" | "rich">();
    for (const q of questions) {
      const multiSelect = q.multi_select !== undefined ? q.multi_select : q.multiSelect;
      const allowOther = q.allow_custom !== undefined ? q.allow_custom : q.allowOther;
      const allowDefer = q.allow_defer !== undefined ? q.allow_defer : q.allowDefer;
      const presentation = q.presentation ?? topPresentation;
      const isMiniAppOnly = Boolean(
        topMiniAppOnly || q.mini_app_only || q.miniapp_only || q.miniAppOnly || q.chat === false
      );
      if (!isMiniAppOnly) {
        usedPresentations.add(presentation);
      }
      const effectiveThreadId = (q.message_thread_id ?? q.messageThreadId ?? q.thread_id ?? q.threadId ?? topThreadId) ?? this.bot?.getLastThreadId(defaultChatId);
      const detailText = q.detail ?? q.details ?? topDetail;
      let detailsId = q.detailsId ?? q.details_id;
      if (!detailsId && detailText) {
        detailsId = this.store.storeDetails(detailText);
      }

      const result = await this.broker.askUser({
        question: q.question,
        header: q.header,
        kind: q.kind,
        stakes: q.stakes,
        presentation,
        options: q.options,
        multiSelect,
        allowOther,
        allowDefer,
        turnId: q.turn_id || q.turnId || topTurnId,
        chatId: defaultChatId,
        mini_app_only: isMiniAppOnly,
        context: q.context,
        detail: detailText,
        detailsId,
        recommendation: q.recommendation,
        messageThreadId: effectiveThreadId,
      });

      postedIds.push(result.questionId);
      this.store.recordTurn("out", q.header ? `${q.header}: ${q.question}` : q.question);

      if (this.bot && !isMiniAppOnly) {
        const card = this.broker.renderQuestionCard(result.questionId, this.config.miniAppUrl, this.config.instance);
        if (card && defaultChatId) {
          const sendRes = await this.bot.sendQuestionCard(defaultChatId, result.questionId, card, effectiveThreadId);
          if (!sendRes?.ok || !sendRes?.result?.message_id) {
            const errorMsg = sendRes?.error || sendRes?.description || "Failed to deliver question card";
            this.broker.markDeliveryFailed(result.questionId, errorMsg);
            if (this.emitChannelNotification) {
              this.emitChannelNotification(`Question delivery failed: ${errorMsg}`, {
                event: "question_delivery_failed",
                question_id: result.questionId,
                error: errorMsg,
                turn_id: q.turn_id || q.turnId || topTurnId,
              });
            }
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

    const resolvedPresentation =
      usedPresentations.size === 1
        ? usedPresentations.values().next().value
        : usedPresentations.size > 0
          ? topPresentation
          : undefined;

    return {
      question_ids: postedIds,
      status: "posted",
      ...(resolvedPresentation ? { presentation: resolvedPresentation } : {}),
      message,
    };
  }

  /**
   * Outbound tool contract: edit_message
   * Modifies the rich_message of an agent-sent message.
   */
  public async editMessage(params: OutboundEditMessageParams): Promise<OutboundEditMessageResult> {
    const chatId = params.chat_id || this.getDefaultChatId();
    const messageId = params.message_id;
    const inlineKeyboard = this.extractInlineKeyboard(params as unknown as Record<string, unknown>);

    if ((params as unknown as Record<string, unknown>).text !== undefined) {
      return {
        success: false,
        error: "edit_message only supports Rich Messages (provide one of markdown, html, or blocks; plain text is not supported)",
      };
    }
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const res = await this.bot.editRichMessage({
      chatId,
      messageId,
      richMessage: {
        markdown: params.markdown,
        html: params.html,
        blocks: params.blocks,
        is_rtl: params.is_rtl,
        skip_entity_detection: params.skip_entity_detection,
      },
      ...(inlineKeyboard.length > 0 ? { inlineKeyboard } : {}),
    });
    if (!res?.ok) {
      return { success: false, error: res?.description || "Failed to edit rich message" };
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

  public async listThreads(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    const chatId = Number(args.chat_id) || this.getDefaultChatId();
    const filter = args.state === undefined ? "all" : String(args.state);
    if (filter !== "all" && filter !== "open" && filter !== "closed") {
      return { success: false, error: "Invalid state: must be one of all, open, closed" };
    }
    const threads = this.store
      .listThreads(chatId)
      .filter((t) => filter === "all" || t.state === filter)
      .map((t) => ({
        message_thread_id: t.threadId,
        thread_id: t.threadId,
        name: t.name ?? null,
        state: t.state,
        source: t.source,
        updated_at: t.updatedAt,
      }));
    return {
      success: true,
      chat_id: chatId,
      threads,
      count: threads.length,
      note:
        "The Telegram Bot API has no method to list forum topics, so this is the plugin's own record of topics it created, " +
        "or saw created, closed, reopened, renamed or posted in. Topics that predate the record and have been silent since are missing; " +
        "state unknown (null name) means only a post in the topic was seen and its open or closed state is unconfirmed; closes or deletions made by anyone else, or while the plugin was down, may be missed.",
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

  private extractExplicitThreadId(args: Record<string, unknown>): number | undefined {
    const raw = args.message_thread_id ?? args.messageThreadId ?? args.thread_id ?? args.threadId;
    return typeof raw === "number" ? raw : undefined;
  }

  private extractInlineKeyboard(args: Record<string, unknown>): Array<Array<Record<string, unknown>>> {
    if (!args.buttons) return [];
    return buildInlineKeyboardRows(
      args.buttons as ReplyButtonsInput | undefined,
      (args.button_layout ?? args.buttonLayout) as number[] | number | undefined,
      (args.buttons_per_row ?? args.buttonsPerRow) as number | undefined
    );
  }

  private async dispatchSingleMedia(
    method: "sendPhoto" | "sendDocument" | "sendVideo" | "sendAnimation" | "sendAudio" | "sendVideoNote",
    mediaField: "photo" | "document" | "video" | "animation" | "audio" | "video_note",
    args: Record<string, unknown>,
    extraKeys: string[] = []
  ): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const mediaVal = args[mediaField];
    if (typeof mediaVal !== "string" || !mediaVal.trim()) {
      return { success: false, error: `Missing required ${mediaField} parameter` };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const extraFields: Record<string, unknown> = {};
    for (const key of extraKeys) {
      if (args[key] !== undefined) {
        extraFields[key] = args[key];
      }
    }
    const res = await this.bot.sendSingleMedia({
      method,
      mediaField,
      media: mediaVal.trim(),
      chatId,
      caption: typeof args.caption === "string" ? args.caption : undefined,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      extraFields,
      inlineKeyboard: this.extractInlineKeyboard(args),
    });
    if (!res.ok) {
      return { success: false, error: res.description || `Failed to execute ${method}` };
    }
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendPhoto(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.dispatchSingleMedia("sendPhoto", "photo", args, ["has_spoiler", "show_caption_above_media"]);
  }

  public async sendDocument(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.dispatchSingleMedia("sendDocument", "document", args, ["disable_content_type_detection"]);
  }

  public async sendVideo(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.dispatchSingleMedia("sendVideo", "video", args, [
      "duration",
      "width",
      "height",
      "has_spoiler",
      "show_caption_above_media",
      "supports_streaming",
    ]);
  }

  public async sendAnimation(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.dispatchSingleMedia("sendAnimation", "animation", args, [
      "duration",
      "width",
      "height",
      "has_spoiler",
      "show_caption_above_media",
    ]);
  }

  public async sendAudio(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.dispatchSingleMedia("sendAudio", "audio", args, ["duration", "performer", "title"]);
  }

  public async sendVideoNote(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.dispatchSingleMedia("sendVideoNote", "video_note", args, ["duration", "length"]);
  }

  public async sendMediaGroup(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    if (!Array.isArray(args.media) || args.media.length < 2 || args.media.length > 10) {
      return { success: false, error: "send_media_group requires between 2 and 10 media items" };
    }
    const allowedTypes = new Set(["photo", "video", "document", "animation", "audio"]);
    const normalizedItems: Array<{
      type: "photo" | "video" | "document" | "animation" | "audio";
      media: string;
      caption?: string;
      has_spoiler?: boolean;
      show_caption_above_media?: boolean;
    }> = [];
    for (const item of args.media) {
      if (!item || typeof item !== "object") {
        return { success: false, error: "Each media item must be an object with type and media" };
      }
      const rec = item as Record<string, unknown>;
      const type = String(rec.type || "");
      const media = typeof rec.media === "string" ? rec.media.trim() : "";
      if (!allowedTypes.has(type) || !media) {
        return {
          success: false,
          error: "Each media item requires a valid type (photo, video, document, animation, audio) and non-empty media",
        };
      }
      normalizedItems.push({
        type: type as "photo" | "video" | "document" | "animation" | "audio",
        media,
        ...(typeof rec.caption === "string" ? { caption: rec.caption } : {}),
        ...(typeof rec.has_spoiler === "boolean" ? { has_spoiler: rec.has_spoiler } : {}),
        ...(typeof rec.show_caption_above_media === "boolean"
          ? { show_caption_above_media: rec.show_caption_above_media }
          : {}),
      });
    }

    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMediaGroup({
      chatId,
      media: normalizedItems,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send media group" };
    }
    const messageIds = Array.isArray(res.result) ? res.result.map((m: any) => m?.message_id).filter(Boolean) : [];
    return {
      success: true,
      message_ids: messageIds,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendLocation(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const latitude = args.latitude as number;
    const longitude = args.longitude as number;
    if (
      typeof latitude !== "number" ||
      !Number.isFinite(latitude) ||
      latitude < -90 ||
      latitude > 90 ||
      typeof longitude !== "number" ||
      !Number.isFinite(longitude) ||
      longitude < -180 ||
      longitude > 180
    ) {
      return {
        success: false,
        error: "send_location requires valid numeric latitude (-90..90) and longitude (-180..180)",
      };
    }
    const fields: Record<string, unknown> = { latitude, longitude };
    for (const key of ["horizontal_accuracy", "live_period", "heading", "proximity_alert_radius"]) {
      if (args[key] !== undefined) {
        fields[key] = args[key];
      }
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMessagePayload({
      method: "sendLocation",
      chatId,
      fields,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      inlineKeyboard: this.extractInlineKeyboard(args),
      excerptText: `[location ${latitude},${longitude}]`,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send location" };
    }
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendVenue(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const latitude = args.latitude as number;
    const longitude = args.longitude as number;
    const title = typeof args.title === "string" ? args.title.trim() : "";
    const address = typeof args.address === "string" ? args.address.trim() : "";
    if (
      typeof latitude !== "number" ||
      !Number.isFinite(latitude) ||
      latitude < -90 ||
      latitude > 90 ||
      typeof longitude !== "number" ||
      !Number.isFinite(longitude) ||
      longitude < -180 ||
      longitude > 180 ||
      !title ||
      !address
    ) {
      return {
        success: false,
        error: "send_venue requires valid latitude (-90..90), longitude (-180..180), title, and address",
      };
    }
    const fields: Record<string, unknown> = { latitude, longitude, title, address };
    for (const key of ["foursquare_id", "foursquare_type", "google_place_id", "google_place_type"]) {
      if (args[key] !== undefined) {
        fields[key] = args[key];
      }
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMessagePayload({
      method: "sendVenue",
      chatId,
      fields,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      inlineKeyboard: this.extractInlineKeyboard(args),
      excerptText: `[venue ${title}]`,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send venue" };
    }
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendContact(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const phoneNumber = typeof args.phone_number === "string" ? args.phone_number.trim() : "";
    const firstName = typeof args.first_name === "string" ? args.first_name.trim() : "";
    if (!phoneNumber || !firstName) {
      return { success: false, error: "send_contact requires phone_number and first_name" };
    }
    const fields: Record<string, unknown> = {
      phone_number: phoneNumber,
      first_name: firstName,
    };
    if (typeof args.last_name === "string" && args.last_name.trim()) {
      fields.last_name = args.last_name.trim();
    }
    if (typeof args.vcard === "string" && args.vcard.trim()) {
      fields.vcard = args.vcard;
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMessagePayload({
      method: "sendContact",
      chatId,
      fields,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      inlineKeyboard: this.extractInlineKeyboard(args),
      excerptText: `[contact ${firstName}]`,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send contact" };
    }
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendDice(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const allowedEmoji = new Set(["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"]);
    const fields: Record<string, unknown> = {};
    if (args.emoji !== undefined) {
      if (typeof args.emoji !== "string" || !allowedEmoji.has(args.emoji)) {
        return {
          success: false,
          error: "send_dice emoji must be one of 🎲, 🎯, 🏀, ⚽, 🎳, or 🎰",
        };
      }
      fields.emoji = args.emoji;
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMessagePayload({
      method: "sendDice",
      chatId,
      fields,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      inlineKeyboard: this.extractInlineKeyboard(args),
      excerptText: `[dice ${(fields.emoji as string) || "🎲"}]`,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send dice" };
    }
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.result?.dice?.value !== undefined ? { value: res.result.dice.value } : {}),
      ...(res.result?.dice?.emoji !== undefined ? { emoji: res.result.dice.emoji } : {}),
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendChatAction(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const allowedActions = new Set([
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
    ]);
    const action = typeof args.action === "string" ? args.action.trim() : "";
    if (!allowedActions.has(action)) {
      return {
        success: false,
        error: `Invalid chat action: ${String(args.action)}`,
      };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendChatAction({
      chatId,
      action,
      messageThreadId: this.extractExplicitThreadId(args),
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send chat action" };
    }
    return {
      success: true,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendMessageDraft(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const draftId = args.draft_id as number;
    if (typeof draftId !== "number" || !Number.isInteger(draftId) || draftId === 0) {
      return { success: false, error: "send_message_draft requires a non-zero integer draft_id" };
    }
    if (args.media !== undefined) {
      return { success: false, error: "Draft messages do not support media attachments" };
    }
    if (args.text !== undefined) {
      return {
        success: false,
        error: "send_message_draft only supports Rich Message drafts (provide one of markdown, html, or blocks)",
      };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMessageDraft({
      chatId,
      draftId,
      markdown: typeof args.markdown === "string" ? args.markdown : undefined,
      html: typeof args.html === "string" ? args.html : undefined,
      blocks: Array.isArray(args.blocks) ? (args.blocks as Array<Record<string, unknown>>) : undefined,
      isRtl: typeof args.is_rtl === "boolean" ? args.is_rtl : undefined,
      skipEntityDetection: typeof args.skip_entity_detection === "boolean" ? args.skip_entity_detection : undefined,
      canStop: typeof args.can_stop === "boolean" ? args.can_stop : undefined,
      keepOnStop: typeof args.keep_on_stop === "boolean" ? args.keep_on_stop : undefined,
      messageThreadId: this.extractExplicitThreadId(args),
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send message draft" };
    }
    return {
      success: true,
      draft_id: draftId,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async sendRichMessage(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const richMessage: InputRichMessageSpec = {
      markdown: typeof args.markdown === "string" ? args.markdown : undefined,
      html: typeof args.html === "string" ? args.html : undefined,
      blocks: Array.isArray(args.blocks) ? (args.blocks as Array<Record<string, unknown>>) : undefined,
      is_rtl: typeof args.is_rtl === "boolean" ? args.is_rtl : undefined,
      skip_entity_detection: typeof args.skip_entity_detection === "boolean" ? args.skip_entity_detection : undefined,
      media: Array.isArray(args.media) ? (args.media as RichMediaInputItem[]) : undefined,
    };
    const replyRaw = args.reply_to ?? args.reply_to_message_id ?? args.replyToMessageId;
    const replyTo = typeof replyRaw === "number" ? replyRaw : undefined;
    const quoteRichTexts = Array.isArray(args.quote_rich_texts)
      ? args.quote_rich_texts.map((q) => String(q))
      : undefined;

    const res = await this.bot.sendRichMessage({
      chatId,
      richMessage,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo,
      quoteRichTexts,
      inlineKeyboard: this.extractInlineKeyboard(args),
      feedbackButtons: typeof args.feedback_buttons === "boolean" ? args.feedback_buttons : undefined,
      voice: typeof args.voice === "boolean" ? args.voice : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      protectContent: typeof args.protect_content === "boolean" ? args.protect_content : undefined,
      messageEffectId: typeof args.message_effect_id === "string" ? args.message_effect_id : undefined,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send rich message" };
    }
    this.store.recordTurn("out", extractRichMessageText(richMessage));
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
      ...(res.voiceMessageId !== undefined ? { voice_message_id: res.voiceMessageId, voice_sent: true } : {}),
      ...(res.voiceError ? { voice_error: res.voiceError } : {}),
    };
  }

  public async sendWidget(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    if (typeof args.html !== "string") {
      return { success: false, error: "send_widget requires string html" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const replyRaw = args.reply_to ?? args.reply_to_message_id ?? args.replyToMessageId;
    const replyTo = typeof replyRaw === "number" ? replyRaw : undefined;
    const caption = typeof args.caption === "string" ? args.caption : undefined;
    const res = await this.bot.sendWidget({
      chatId,
      html: args.html,
      width: typeof args.width === "number" ? args.width : undefined,
      height: typeof args.height === "number" ? args.height : undefined,
      publicData: typeof args.public_data === "string" ? args.public_data : undefined,
      chatData: typeof args.chat_data === "string" ? args.chat_data : undefined,
      caption,
      parseMode: typeof args.parse_mode === "string" ? args.parse_mode : undefined,
      showCaptionAboveMedia:
        typeof args.show_caption_above_media === "boolean" ? args.show_caption_above_media : undefined,
      allowQueries: typeof args.allow_queries === "boolean" ? args.allow_queries : undefined,
      isShared: typeof args.is_shared === "boolean" ? args.is_shared : undefined,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      protectContent: typeof args.protect_content === "boolean" ? args.protect_content : undefined,
      messageEffectId: typeof args.message_effect_id === "string" ? args.message_effect_id : undefined,
      inlineKeyboard: this.extractInlineKeyboard(args),
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send widget" };
    }
    this.store.recordTurn("out", caption && caption.trim() ? caption : "Interactive widget");
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async editMessageWidgetData(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const inlineMessageId = typeof args.inline_message_id === "string" ? args.inline_message_id : undefined;
    const messageId = typeof args.message_id === "number" ? args.message_id : undefined;
    const chatId = inlineMessageId ? undefined : ((args.chat_id as number) || this.getDefaultChatId());
    if (!inlineMessageId && messageId === undefined) {
      return { success: false, error: "edit_message_widget_data requires message_id or inline_message_id" };
    }
    const res = await this.bot.editMessageWidgetData({
      chatId,
      messageId,
      inlineMessageId,
      publicData: typeof args.public_data === "string" ? args.public_data : undefined,
      chatData: typeof args.chat_data === "string" ? args.chat_data : undefined,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to update widget data" };
    }
    return {
      success: true,
      ...(res.not_modified ? { not_modified: true } : { updated: true }),
    };
  }

  public async answerWidgetQuery(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const widgetQueryId = typeof args.widget_query_id === "string" ? args.widget_query_id.trim() : "";
    if (!widgetQueryId) {
      return { success: false, error: "answer_widget_query requires widget_query_id" };
    }
    const res = await this.bot.answerWidgetQuery({
      widgetQueryId,
      data: typeof args.data === "string" ? args.data : undefined,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to answer widget query" };
    }
    return { success: true, answered: true };
  }

  public async sendPoll(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const question = typeof args.question === "string" ? args.question.trim() : "";
    if (!question || question.length > 300) {
      return { success: false, error: "send_poll requires a question between 1 and 300 characters" };
    }
    if (!Array.isArray(args.options) || args.options.length < 2 || args.options.length > 12) {
      return { success: false, error: "send_poll requires between 2 and 12 poll options" };
    }
    const normalizedOptions: Array<{ text: string }> = [];
    for (const opt of args.options) {
      const optText =
        typeof opt === "string"
          ? opt.trim()
          : opt && typeof opt === "object" && typeof (opt as Record<string, unknown>).text === "string"
            ? String((opt as Record<string, unknown>).text).trim()
            : "";
      if (!optText || optText.length > 100) {
        return { success: false, error: "Each poll option must be between 1 and 100 characters" };
      }
      normalizedOptions.push({ text: optText });
    }

    const fields: Record<string, unknown> = {
      question,
      options: normalizedOptions,
    };
    if (typeof args.is_anonymous === "boolean") {
      fields.is_anonymous = args.is_anonymous;
    }
    if (typeof args.allows_multiple_answers === "boolean") {
      fields.allows_multiple_answers = args.allows_multiple_answers;
    }
    if (args.type !== undefined) {
      if (args.type !== "regular" && args.type !== "quiz") {
        return { success: false, error: 'send_poll type must be "regular" or "quiz"' };
      }
      fields.type = args.type;
    }
    if (fields.type === "quiz" || args.correct_option_id !== undefined) {
      const cid = args.correct_option_id as number;
      if (typeof cid !== "number" || !Number.isInteger(cid) || cid < 0 || cid >= normalizedOptions.length) {
        return {
          success: false,
          error: `Quiz poll requires a valid 0-based correct_option_id between 0 and ${normalizedOptions.length - 1}`,
        };
      }
      fields.correct_option_id = cid;
    }
    if (typeof args.explanation === "string" && args.explanation.trim()) {
      const trimmedExp = args.explanation.trim();
      if (trimmedExp.length > 200) {
        return { success: false, error: "Poll explanation must be at most 200 characters" };
      }
      fields.explanation = trimmedExp;
    }
    if (typeof args.open_period === "number") {
      fields.open_period = args.open_period;
    }
    if (typeof args.close_date === "number") {
      fields.close_date = args.close_date;
    }
    if (typeof args.is_closed === "boolean") {
      fields.is_closed = args.is_closed;
    }

    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.sendMessagePayload({
      method: "sendPoll",
      chatId,
      fields,
      messageThreadId: this.extractExplicitThreadId(args),
      replyTo: typeof args.reply_to === "number" ? args.reply_to : undefined,
      disableNotification: typeof args.disable_notification === "boolean" ? args.disable_notification : undefined,
      inlineKeyboard: this.extractInlineKeyboard(args),
      excerptText: `[poll] ${question}`,
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to send poll" };
    }
    return {
      success: true,
      message_id: res.result?.message_id,
      ...(res.result?.poll?.id ? { poll_id: res.result.poll.id } : {}),
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
    };
  }

  public async stopPoll(args: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.bot) {
      return { success: false, error: "Telegram bot client is not available" };
    }
    const messageId = args.message_id as number;
    if (typeof messageId !== "number" || !Number.isInteger(messageId) || messageId <= 0) {
      return { success: false, error: "stop_poll requires a positive integer message_id" };
    }
    const chatId = (args.chat_id as number) || this.getDefaultChatId();
    const res = await this.bot.stopPoll({
      chatId,
      messageId,
      inlineKeyboard: this.extractInlineKeyboard(args),
    });
    if (!res.ok) {
      return { success: false, error: res.description || "Failed to stop poll" };
    }
    return {
      success: true,
      message_id: messageId,
      ...(res.effectiveThreadId !== undefined ? { message_thread_id: res.effectiveThreadId } : {}),
      ...(res.result
        ? {
            poll: {
              id: res.result.id,
              question: res.result.question,
              options: res.result.options,
              total_voter_count: res.result.total_voter_count,
              is_closed: res.result.is_closed,
            },
          }
        : {}),
    };
  }

  /**
   * Dispatches an outbound tool call by name.
   */
  public async handleIpcMessage(msg: Record<string, unknown>): Promise<Record<string, unknown>> {
    const type = msg._toolName || msg.type || msg.name;

    switch (type) {
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

      case "list_threads":
      case "list_topics":
      case "list_forum_topics":
        return await this.listThreads(msg);

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

      case "answer_question": {
        const questionId = (msg.question_id as string) || (msg.questionId as string) || (msg.id as string);
        const choice = typeof msg.choice === "string" ? msg.choice.trim() : undefined;
        const optionIndex = typeof msg.option_index === "number" ? msg.option_index : undefined;
        if (!questionId) {
          return { success: false, error: "Missing question_id" };
        }
        if (!choice && optionIndex === undefined) {
          return { success: false, error: "Missing answer: provide choice or option_index" };
        }
        const result = await this.broker.resolveAnswer(
          questionId,
          optionIndex !== undefined ? optionIndex : "other",
          choice
        );
        if (!result) {
          return { success: false, error: "Question not found or not pending" };
        }
        if (this.bot && result.question.chatId && result.question.messageId) {
          await this.bot.settleQuestionMessage(
            result.question,
            result.cardText,
            "answered",
            result.channelEvent.choice
          );
        }
        if (this.emitChannelNotification) {
          this.emitChannelNotification(`Question answered: ${result.channelEvent.choice}`, {
            event: result.channelEvent.event,
            ...result.channelEvent,
          });
        }
        return { success: true, question_id: questionId, choice: result.channelEvent.choice };
      }

      case "close_question": {
        const questionId = (msg.question_id as string) || (msg.questionId as string) || (msg.id as string);
        const reason = typeof msg.reason === "string" ? msg.reason.trim() : "";
        if (!questionId) {
          return { success: false, error: "Missing question_id" };
        }
        if (!reason) {
          return {
            success: false,
            error: "Missing reason: closing a question requires an explicit stated reason",
          };
        }
        const result = await this.broker.closeQuestion(questionId, reason);
        if (!result) {
          return { success: false, error: "Question not found or not pending" };
        }
        if (this.bot && result.question.chatId && result.question.messageId) {
          await this.bot.settleQuestionMessage(
            result.question,
            result.cardText,
            "closed",
            result.channelEvent.reason
          );
        }
        if (this.emitChannelNotification) {
          this.emitChannelNotification(`Question closed: ${result.channelEvent.reason}`, {
            event: result.channelEvent.event,
            ...result.channelEvent,
          });
        }
        return { success: true, question_id: questionId, reason: result.channelEvent.reason };
      }

      case "list_questions": {
        const pending = this.broker.getPendingQuestions();
        return { success: true, count: pending.length, questions: pending };
      }

      case "send_photo":
      case "sendPhoto":
        return await this.sendPhoto(msg);

      case "send_document":
      case "sendDocument":
        return await this.sendDocument(msg);

      case "send_video":
      case "sendVideo":
        return await this.sendVideo(msg);

      case "send_animation":
      case "sendAnimation":
        return await this.sendAnimation(msg);

      case "send_media_group":
      case "sendMediaGroup":
        return await this.sendMediaGroup(msg);

      case "send_audio":
      case "sendAudio":
        return await this.sendAudio(msg);

      case "send_video_note":
      case "sendVideoNote":
        return await this.sendVideoNote(msg);

      case "send_location":
      case "sendLocation":
        return await this.sendLocation(msg);

      case "send_venue":
      case "sendVenue":
        return await this.sendVenue(msg);

      case "send_contact":
      case "sendContact":
        return await this.sendContact(msg);

      case "send_dice":
      case "sendDice":
        return await this.sendDice(msg);

      case "send_chat_action":
      case "sendChatAction":
        return await this.sendChatAction(msg);

      case "send_message_draft":
      case "sendMessageDraft":
        return await this.sendMessageDraft(msg);

      case "send_rich_message":
      case "sendRichMessage":
        return await this.sendRichMessage(msg);

      case "send_widget":
      case "sendWidget":
        return await this.sendWidget(msg);

      case "edit_message_widget_data":
      case "editMessageWidgetData":
        return await this.editMessageWidgetData(msg);

      case "answer_widget_query":
      case "answerWidgetQuery":
        return await this.answerWidgetQuery(msg);

      case "send_poll":
      case "sendPoll":
        return await this.sendPoll(msg);

      case "stop_poll":
      case "stopPoll":
        return await this.stopPoll(msg);

      default:
        throw new Error(`Unsupported tool: ${String(type)}`);
    }
  }
}
