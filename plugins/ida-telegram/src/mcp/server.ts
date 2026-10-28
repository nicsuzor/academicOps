import { MCP_TOOLS } from "./tools.js";
import { PluginConfig } from "../config.js";
import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import { processReplyOverflow } from "../telegram/overflow.js";
import { formatMarkdownToEntities, normalizeReaction } from "../telegram/format.js";
import { TelegramBotClient } from "../telegram/bot.js";
import { sanitizeChannelMeta } from "../telegram/inbound.js";
import { splitVoiceTier2Quotes } from "../telegram/voice.js";
import { PermissionRelay } from "./permissions.js";
import { broadcastSseEvent } from "../web/routes.js";

export class StdioMcpServer {
  private config: PluginConfig;
  private store: PluginStore;
  private broker: QuestionBroker;
  private bot: TelegramBotClient | null;
  private permRelay: PermissionRelay;

  constructor(
    config: PluginConfig,
    store: PluginStore,
    broker: QuestionBroker,
    bot: TelegramBotClient | null,
    permRelay: PermissionRelay
  ) {
    this.config = config;
    this.store = store;
    this.broker = broker;
    this.bot = bot;
    this.permRelay = permRelay;
  }

  public emitChannelNotification(content: string, meta: Record<string, unknown>) {
    this.store.recordTurn("in", String(content));
    const notification = {
      jsonrpc: "2.0",
      method: "notifications/claude/channel",
      params: {
        content: String(content),
        meta: sanitizeChannelMeta(meta),
      },
    };
    process.stdout.write(JSON.stringify(notification) + "\n");
  }

  public emitPermissionDecision(requestId: string, behavior: "allow" | "deny") {
    const notification = {
      jsonrpc: "2.0",
      method: "notifications/claude/channel/permission",
      params: {
        request_id: String(requestId),
        behavior,
      },
    };
    process.stdout.write(JSON.stringify(notification) + "\n");
  }

  public async handleMessage(msg: Record<string, unknown>): Promise<Record<string, unknown> | null> {
    const { id, method, params } = msg;

    if (method === "initialize") {
      // FR-5.2: Non-primary instances register no tools and no channel capabilities
      if (!this.config.isPrimary) {
        return {
          jsonrpc: "2.0",
          id,
          result: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            serverInfo: {
              name: "ida-telegram",
              version: "0.1.0",
            },
          },
        };
      }

      return {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2024-11-05",
          capabilities: {
            tools: {},
            experimental: {
              "claude/channel": {},
              "claude/channel/permission": {},
            },
          },
          serverInfo: {
            name: "ida-telegram",
            version: "0.1.0",
          },
        },
      };
    }

    if (method === "notifications/initialized") {
      return null;
    }

    if (method === "tools/list") {
      if (!this.config.isPrimary) {
        return {
          jsonrpc: "2.0",
          id,
          result: { tools: [] },
        };
      }
      return {
        jsonrpc: "2.0",
        id,
        result: { tools: MCP_TOOLS },
      };
    }

    if (method === "tools/call") {
      if (!this.config.isPrimary) {
        return {
          jsonrpc: "2.0",
          id,
          error: { code: -32601, message: "Tools not available on non-primary instance" },
        };
      }

      const toolParams = params as { name: string; arguments?: Record<string, unknown> };
      const toolName = toolParams.name;
      const args = toolParams.arguments || {};

      try {
        const result = await this.executeTool(toolName, args);
        return {
          jsonrpc: "2.0",
          id,
          result: {
            content: [{ type: "text", text: typeof result === "string" ? result : JSON.stringify(result) }],
          },
        };
      } catch (err) {
        return {
          jsonrpc: "2.0",
          id,
          isError: true,
          result: {
            content: [{ type: "text", text: `Error executing ${toolName}: ${String(err)}` }],
          },
        };
      }
    }

    // Claude Code channel permission request notification (notifications/claude/channel/permission_request)
    if (method === "notifications/claude/channel/permission_request") {
      const p = (params || {}) as {
        request_id?: string;
        tool_name?: string;
        description?: string;
        input_preview?: string;
        tool_input?: Record<string, unknown>;
      };
      if (!p.request_id || !p.tool_name) {
        throw new Error("Malformed permission_request notification: missing request_id or tool_name");
      }
      const reqId = p.request_id;
      const toolInput: Record<string, unknown> = p.tool_input || {
        ...(p.description ? { description: p.description } : {}),
        ...(p.input_preview ? { input_preview: p.input_preview } : {}),
      };

      this.permRelay.register(reqId, p.tool_name, toolInput, (decision) => {
        this.emitPermissionDecision(reqId, decision);
      });

      if (this.bot) {
        await this.bot.sendPermissionCard(reqId, p.tool_name, toolInput, p.description, p.input_preview);
      }

      return null;
    }

    return {
      jsonrpc: "2.0",
      id,
      error: { code: -32601, message: `Method not found: ${method}` },
    };
  }

  private async executeTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    const defaultChatId = this.config.allowFrom[0] || 0;

    if (name === "reply") {
      const text = (args.text as string) || "";
      const detail = args.detail as string | undefined;
      const chatId = (args.chat_id as number) || defaultChatId;
      const replyTo = args.reply_to as number | undefined;

      // FR-7.1: Determine whether voice reply is requested explicitly or via voice_replies setting
      let isVoice = false;
      if (typeof args.voice === "boolean") {
        isVoice = args.voice;
      } else if (this.config.voiceReplies === "always") {
        isVoice = true;
      } else if (this.config.voiceReplies === "mirror" && this.bot?.isLastInboundVoice(chatId)) {
        isVoice = true;
      }

      // FR-7.2 & FR-7.3: For voice replies, Tier 2 quotes go behind Details along with Tier 3
      let effectiveText = text;
      let effectiveDetail = detail;
      if (isVoice) {
        const { tier1Text, tier2Quotes } = splitVoiceTier2Quotes(text);
        if (tier2Quotes) {
          effectiveText = tier1Text;
          effectiveDetail = detail ? `${tier2Quotes}\n\n---\n\n${detail}` : tier2Quotes;
        }
      }

      // 1. Process overflow
      const overflowRes = processReplyOverflow({
        text: effectiveText,
        detail: effectiveDetail,
        maxChatChars: this.config.maxChatChars,
      });

      let detailsId: string | undefined;
      if (overflowRes.combinedDetail) {
        detailsId = this.store.storeDetails(overflowRes.combinedDetail);
      }

      const reviewArg = args.review as { repo: string; pr?: number; base?: string; head?: string } | undefined;
      if (reviewArg?.repo) {
        this.store.addReview(reviewArg);
      }
      this.store.recordTurn("out", overflowRes.chatText);

      // 2. Format entities
      const formatted = formatMarkdownToEntities(overflowRes.chatText);

      // 3. Send via bot
      if (this.bot) {
        const sendRes = await this.bot.sendReply({
          chatId,
          formatted,
          detailsId,
          buttons: args.buttons as any,
          buttonLayout: (args.button_layout ?? args.buttonLayout) as number[] | number | undefined,
          buttonsPerRow: (args.buttons_per_row ?? args.buttonsPerRow) as number | undefined,
          predefinedRow: (args.predefined_row ?? args.predefined_buttons_row ?? args.predefinedRow) as boolean | undefined,
          voice: isVoice,
          replyTo,
          feedback: typeof args.feedback === "boolean" ? args.feedback : undefined,
          review: reviewArg,
          actions: args.actions as boolean | undefined,
        });

        const out: Record<string, unknown> = {
          success: true,
          messageId: sendRes?.messageId,
        };
        if (detailsId !== undefined) {
          out.detailsId = detailsId;
        }
        if (sendRes?.voiceSent !== undefined) {
          out.voiceSent = sendRes.voiceSent;
        }
        if (sendRes?.voiceMessageId !== undefined) {
          out.voiceMessageId = sendRes.voiceMessageId;
        }
        if (sendRes?.voiceError !== undefined) {
          out.voiceError = sendRes.voiceError;
        }
        return out;
      }

      return { success: true, preview: formatted.plainText, detailsId };
    }

    if (name === "react") {
      const chatId = (args.chat_id as number) || defaultChatId;
      const messageId = args.message_id as number;
      const rawReaction = args.reaction as string;
      const norm = normalizeReaction(rawReaction);

      if (!norm) {
        return { success: false, error: `Invalid reaction: ${rawReaction}` };
      }

      if (this.bot) {
        await this.bot.setReaction(chatId, messageId, norm);
      }
      return { success: true, reaction: norm };
    }

    if (name === "ask_user") {
      const topTurnId = (args.turn_id as string | undefined) || (args.turnId as string | undefined);
      const topSessionId =
        (args.session_id as string | undefined) ||
        (args.sessionId as string | undefined) ||
        ((args._session as any)?.session_id as string | undefined);
      const topMiniAppOnly = Boolean(
        args.mini_app_only || args.miniapp_only || args.miniAppOnly || args.chat === false
      );
      const topDetail = (args.detail as string | undefined) || (args.details as string | undefined);
      const questions = (args.questions as Array<{
        question: string;
        header?: string;
        context?: string;
        recommendation?: string;
        options: Array<{ label: string; description?: string; recommended?: boolean }>;
        multiSelect?: boolean;
        allowOther?: boolean;
        turn_id?: string;
        turnId?: string;
        session_id?: string;
        sessionId?: string;
        detail?: string;
        details?: string;
        detailsId?: string;
        details_id?: string;
        mini_app_only?: boolean;
        miniapp_only?: boolean;
        miniAppOnly?: boolean;
        chat?: boolean;
      }>) || [];

      if (questions.length === 0) {
        return { success: false, error: "No questions provided" };
      }

      const postedIds: string[] = [];
      for (const q of questions) {
        const isMiniAppOnly = Boolean(
          topMiniAppOnly ||
          q.mini_app_only === true ||
          q.miniapp_only === true ||
          q.miniAppOnly === true ||
          q.chat === false
        );
        const detailText = q.detail || q.details || topDetail;

        let detailsId = q.detailsId || q.details_id;
        if (!detailsId && detailText) {
          detailsId = this.store.storeDetails(detailText);
        }

        const result = await this.broker.askUser({
          question: q.question,
          header: q.header,
          context: q.context,
          recommendation: q.recommendation,
          options: q.options,
          multiSelect: q.multiSelect,
          allowOther: q.allowOther,
          turnId: q.turn_id || q.turnId || topTurnId,
          sessionId: q.session_id || q.sessionId || topSessionId,
          chatId: defaultChatId,
          detail: detailText,
          detailsId,
          mini_app_only: isMiniAppOnly,
          chat: !isMiniAppOnly,
        });
        postedIds.push(result.questionId);
        this.store.recordTurn("out", q.header ? `${q.header}: ${q.question}` : q.question);

        if (!isMiniAppOnly && this.bot) {
          const card = this.broker.renderQuestionCard(result.questionId, this.config.miniAppUrl);
          if (card) {
            await this.bot.sendQuestionCard(defaultChatId, result.questionId, card);
          }
        }
      }

      if (postedIds.length === 1) {
        return `Question ${postedIds[0]} posted to the user. Do not assume an answer; continue other work or end your turn.`;
      }
      return `Questions ${postedIds.join(", ")} posted to the user. Do not assume an answer; continue other work or end your turn.`;
    }

    if (name === "answer_question") {
      const questionId = (args.question_id as string) || (args.questionId as string) || (args.id as string);
      const choice = typeof args.choice === "string" ? args.choice.trim() : undefined;
      const optionIndex = typeof args.option_index === "number" ? args.option_index : undefined;
      if (!questionId) {
        return { success: false, error: "Missing question_id" };
      }
      if (!choice && optionIndex === undefined) {
        return { success: false, error: "Missing answer: provide choice or option_index" };
      }
      const result = await this.broker.resolveAnswer(questionId, optionIndex !== undefined ? optionIndex : "other", choice);
      if (!result) {
        return { success: false, error: "Question not found or not pending" };
      }
      if (this.bot && result.question.chatId && result.question.messageId) {
        await this.bot.editMessage(result.question.chatId, result.question.messageId, result.cardText, { inline_keyboard: [] });
      }
      this.emitChannelNotification(`Question answered: ${result.channelEvent.choice}`, {
        event: result.channelEvent.event,
        ...result.channelEvent,
      });
      if (this.store) {
        const seq = this.store.nextSeq("question_resolved", {
          question_id: questionId,
          choice: result.channelEvent.choice,
          turn_id: result.channelEvent.turn_id,
        });
        broadcastSseEvent("question_resolved", {
          question_id: questionId,
          choice: result.channelEvent.choice,
          turn_id: result.channelEvent.turn_id,
        }, seq);
      }
      return { success: true, question_id: questionId, choice: result.channelEvent.choice };
    }

    if (name === "close_question") {
      const questionId = (args.question_id as string) || (args.questionId as string) || (args.id as string);
      const reason = typeof args.reason === "string" ? args.reason.trim() : "";
      if (!questionId) {
        return { success: false, error: "Missing question_id" };
      }
      if (!reason) {
        return { success: false, error: "Missing reason: closing a question requires an explicit stated reason" };
      }
      const result = await this.broker.closeQuestion(questionId, reason);
      if (!result) {
        return { success: false, error: "Question not found or not pending" };
      }
      if (this.bot && result.question.chatId && result.question.messageId) {
        await this.bot.editMessage(result.question.chatId, result.question.messageId, result.cardText, { inline_keyboard: [] });
      }
      this.emitChannelNotification(`Question closed: ${result.channelEvent.reason}`, {
        event: result.channelEvent.event,
        ...result.channelEvent,
      });
      if (this.store) {
        const seq = this.store.nextSeq("question_closed", {
          question_id: questionId,
          reason: result.channelEvent.reason,
          turn_id: result.channelEvent.turn_id,
          session_id: result.channelEvent.session_id,
        });
        broadcastSseEvent("question_closed", {
          question_id: questionId,
          reason: result.channelEvent.reason,
          turn_id: result.channelEvent.turn_id,
          session_id: result.channelEvent.session_id,
        }, seq);
      }
      return { success: true, question_id: questionId, reason: result.channelEvent.reason };
    }

    if (name === "list_questions") {
      const pending = this.broker.getPendingQuestions();
      return { success: true, count: pending.length, questions: pending };
    }

    if (name === "anchor") {
      const focus = args.focus as string;
      const taskId = args.task_id as string | undefined;
      const waitingOn = args.waiting_on as string[] | undefined;
      const delegations = args.delegations as string[] | undefined;
      const ctxRaw = args.context_tokens as
        | { used_tokens?: number; total_tokens?: number; percentage?: number }
        | undefined;
      let contextTokens: { usedTokens: number; totalTokens: number; percentage: number } | undefined;
      if (ctxRaw) {
        const usedTokens = Number(ctxRaw.used_tokens || 0);
        const totalTokens = Number(ctxRaw.total_tokens || 200000);
        const percentage =
          typeof ctxRaw.percentage === "number"
            ? ctxRaw.percentage
            : totalTokens > 0
              ? Math.round((usedTokens / totalTokens) * 100)
              : 0;
        contextTokens = { usedTokens, totalTokens, percentage };
      }

      this.store.setAnchor({
        focus,
        taskId,
        waitingOn,
        delegations,
        ...(contextTokens ? { contextTokens } : {}),
      });

      return { success: true, focus };
    }

    if (name === "edit_message") {
      const chatId = (args.chat_id as number) || defaultChatId;
      const messageId = args.message_id as number;
      const text = args.text as string;
      if (this.bot) {
        await this.bot.editMessage(chatId, messageId, text);
      }
      return { success: true };
    }

    throw new Error(`Unknown tool: ${name}`);
  }

  public startStdioLoop() {
    let buffer = "";
    process.stdin.setEncoding("utf-8");

    process.stdin.on("data", async (chunk) => {
      buffer += chunk;
      let newlineIdx = buffer.indexOf("\n");
      while (newlineIdx !== -1) {
        const line = buffer.substring(0, newlineIdx).trim();
        buffer = buffer.substring(newlineIdx + 1);
        if (line.length > 0) {
          try {
            const parsed = JSON.parse(line);
            const response = await this.handleMessage(parsed);
            if (response) {
              process.stdout.write(JSON.stringify(response) + "\n");
            }
          } catch (e) {
            console.error("Failed to parse JSON-RPC message:", e);
          }
        }
        newlineIdx = buffer.indexOf("\n");
      }
    });
  }
}
