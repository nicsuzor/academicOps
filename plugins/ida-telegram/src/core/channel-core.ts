import { PluginConfig } from "../config.js";
import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import { TelegramBotClient } from "../telegram/bot.js";
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
  question_ids: string[];
  status: "posted";
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

export class SharedTelegramChannelCore {
  public config: PluginConfig;
  public store: PluginStore;
  public broker: QuestionBroker;
  public bot: TelegramBotClient | null;
  public permRelay: PermissionRelay;
  public turnManager?: TurnManager;

  constructor(options: {
    config: PluginConfig;
    store: PluginStore;
    broker: QuestionBroker;
    bot: TelegramBotClient | null;
    permRelay: PermissionRelay;
    turnManager?: TurnManager;
  }) {
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

      const out: OutboundReplyResult = {
        success: true,
        messageId: sendRes?.messageId,
        message_id: sendRes?.messageId,
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
      });

      postedIds.push(result.questionId);
      this.store.recordTurn("out", q.header ? `${q.header}: ${q.question}` : q.question);

      if (this.bot && !isMiniAppOnly) {
        const card = this.broker.renderQuestionCard(result.questionId, this.config.miniAppUrl);
        if (card) {
          await this.bot.sendQuestionCard(defaultChatId, result.questionId, card);
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

      default:
        throw new Error(`Unsupported IPC tool: ${String(type)}`);
    }
  }
}
