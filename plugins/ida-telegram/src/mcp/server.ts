import { MCP_TOOLS } from "./tools.js";
import { PluginConfig } from "../config.js";
import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import { TelegramBotClient } from "../telegram/bot.js";
import { sanitizeChannelMeta } from "../telegram/inbound.js";
import { PermissionRelay } from "./permissions.js";
import { SharedTelegramChannelCore } from "../core/channel-core.js";

export class StdioMcpServer {
  private config: PluginConfig;
  private store: PluginStore;
  private broker: QuestionBroker;
  private _bot: TelegramBotClient | null;
  private permRelay: PermissionRelay;
  public channelCore: SharedTelegramChannelCore;

  constructor(
    config: PluginConfig,
    store: PluginStore,
    broker: QuestionBroker,
    bot: TelegramBotClient | null,
    permRelay: PermissionRelay,
    channelCore?: SharedTelegramChannelCore
  ) {
    this.config = config;
    this.store = store;
    this.broker = broker;
    this._bot = bot;
    this.permRelay = permRelay;
    this.channelCore =
      channelCore ||
      new SharedTelegramChannelCore({
        config,
        store,
        broker,
        bot,
        permRelay,
      });
  }

  public get bot(): TelegramBotClient | null {
    return this._bot;
  }

  public set bot(b: TelegramBotClient | null) {
    this._bot = b;
    if (this.channelCore) {
      this.channelCore.bot = b;
    }
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
    return this.channelCore.handleIpcMessage({ type: name, ...args });
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
