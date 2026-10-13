import { MCP_TOOLS } from "./tools.js";
import { PluginConfig } from "../config.js";
import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import { processReplyOverflow } from "../telegram/overflow.js";
import { formatMarkdownToEntities, normalizeReaction } from "../telegram/format.js";
import { TelegramBotClient } from "../telegram/bot.js";
import { PermissionRelay } from "./permissions.js";

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
    const notification = {
      jsonrpc: "2.0",
      method: "notifications/claude/channel",
      params: {
        content,
        meta,
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

    // Permission request from Claude Code channel relay
    if (method === "claude/channel/permission") {
      const p = params as { id: string; tool_name: string; tool_input: Record<string, unknown> };
      // Forward permission prompt to Telegram with Review button
      if (this.bot) {
        await this.bot.sendPermissionCard(p.id, p.tool_name, p.tool_input);
      }
      // Hold permission resolution until Nic approves in chat or Mini App
      const decision = await new Promise<"allow" | "deny">((resolve) => {
        this.permRelay.register(p.id, p.tool_name, p.tool_input, resolve);
      });
      return {
        jsonrpc: "2.0",
        id,
        result: { decision },
      };
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
      const isVoice = !!args.voice;
      const replyTo = args.reply_to as number | undefined;
      const feedback = args.feedback !== false;

      // 1. Process overflow
      const overflowRes = processReplyOverflow({
        text,
        detail,
        maxChatChars: this.config.maxChatChars,
      });

      let detailsId: string | undefined;
      if (overflowRes.combinedDetail) {
        detailsId = this.store.storeDetails(overflowRes.combinedDetail);
      }

      // 2. Format entities
      const formatted = formatMarkdownToEntities(overflowRes.chatText);

      // 3. Send via bot
      if (this.bot) {
        const sendRes = await this.bot.sendReply({
          chatId,
          formatted,
          detailsId,
          voice: isVoice,
          replyTo,
          feedback,
          review: args.review as { repo: string; pr?: number } | undefined,
        });
        return { success: true, messageId: sendRes?.messageId, detailsId };
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
      const questions = (args.questions as Array<{
        question: string;
        header?: string;
        options: Array<{ label: string; description?: string }>;
        multiSelect?: boolean;
        allowOther?: boolean;
      }>) || [];

      if (questions.length === 0) {
        return { success: false, error: "No questions provided" };
      }

      const q = questions[0];
      const result = await this.broker.askUser({
        question: q.question,
        header: q.header,
        options: q.options,
        multiSelect: q.multiSelect,
        allowOther: q.allowOther,
        chatId: defaultChatId,
      });

      if (this.bot) {
        const card = this.broker.renderQuestionCard(result.questionId);
        if (card) {
          await this.bot.sendQuestionCard(defaultChatId, result.questionId, card);
        }
      }

      return result.message;
    }

    if (name === "anchor") {
      const focus = args.focus as string;
      const taskId = args.task_id as string | undefined;
      const waitingOn = args.waiting_on as string[] | undefined;
      const delegations = args.delegations as string[] | undefined;

      this.store.setAnchor({
        focus,
        taskId,
        waitingOn,
        delegations,
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
