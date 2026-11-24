#!/usr/bin/env bun
import { loadConfig } from "./src/config.js";
import { PluginStore } from "./src/store.js";
import { QuestionBroker } from "./src/telegram/questions.js";
import { PermissionRelay } from "./src/mcp/permissions.js";
import { TelegramBotClient } from "./src/telegram/bot.js";
import { StdioMcpServer } from "./src/mcp/server.js";
import { startWebServer } from "./src/web/server.js";
import { SharedTelegramChannelCore } from "./src/core/channel-core.js";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

import { broadcastSseEvent } from "./src/web/routes.js";

async function main() {
  const config = loadConfig(process.env);
  const store = new PluginStore(config.stateDir);
  const broker = new QuestionBroker(config.stateDir);
  const permRelay = new PermissionRelay(config.stateDir);

  let bot: TelegramBotClient | null = null;

  const channelCore = new SharedTelegramChannelCore({
    config,
    store,
    broker,
    bot: null,
    permRelay,
  });

  // Stdio MCP server
  const mcpServer = new StdioMcpServer(config, store, broker, null, permRelay, channelCore);

  if (!config.isPrimary) {
    console.error("[ida-telegram] Non-primary instance: registering 0 tools, no poller, no web server.");
    mcpServer.startStdioLoop();
    return;
  }

  // Session secret for Mini App tokens
  const sessionSecret = randomBytes(32).toString("hex");

  // Web server context
  const webContext = {
    store,
    broker,
    permRelay,
    config,
    sessionSecret,
    emitChannelEvent: (event: string, content: string, meta: Record<string, unknown>) => {
      mcpServer.emitChannelNotification(content, { event, ...meta });
    },
    resolvePermissionRelay: (id: string, decision: "allow" | "deny") => {
      permRelay.resolve(id, decision);
    },
    editTelegramCard: async (chatId: number, messageId: number, text: string, replyMarkup?: Record<string, unknown>) => {
      if (bot) {
        await bot.editCardText(chatId, messageId, text, replyMarkup || { inline_keyboard: [] });
      }
    },
    editTelegramWidgetData: async (chatId: number, messageId: number, chatData: string) => {
      if (bot) {
        await bot.editMessageWidgetData({ chatId, messageId, chatData });
      }
    },
    editTelegramReplyMarkup: async (chatId: number, messageId: number) => {
      if (bot) {
        await bot.editMessageReplyMarkup(chatId, messageId, []);
      }
    },
  };

  permRelay.onExpire((item) => {
    const seq = store.nextSeq("permission_resolved", {
      permission_id: item.id,
      outcome: "expired",
      decision: "expired",
    });
    broadcastSseEvent(
      "permission_resolved",
      {
        permission_id: item.id,
        outcome: "expired",
        decision: "expired",
      },
      seq
    );
  });

  // Start Mini App HTTP loopback server
  const appDir = join(import.meta.dir, "app");
  const httpServer = startWebServer(webContext, appDir);
  console.error(`[ida-telegram] Mini App server running at http://127.0.0.1:${config.port}/app/`);

  // Bot client
  if (config.botToken) {
    bot = new TelegramBotClient(
      config,
      broker,
      permRelay,
      (content, meta) => {
        mcpServer.emitChannelNotification(content, meta);
      },
      store
    );

    // Sweep permissions that were left pending before restart
    await permRelay.sweepRestartCutPermissions((chatId, messageId, text, replyMarkup) =>
      webContext.editTelegramCard(chatId, messageId, text, replyMarkup)
    );

    // Sweep undelivered questions that were left pending with no messageId
    const undelivered = broker.sweepUndeliveredQuestions();
    for (const q of undelivered) {
      mcpServer.emitChannelNotification(
        `Undelivered question ${q.id} detected: ${q.deliveryError || "No messageId recorded"}`,
        {
          event: "question_delivery_failed",
          question_id: q.id,
          error: q.deliveryError || "No messageId recorded",
          turn_id: q.turnId || q.turn_id,
          session_id: q.sessionId || q.session_id,
        }
      );
    }

    // Start background polling
    bot.startPolling().catch((e) => console.error("[ida-telegram] Polling stopped:", e));
  }

  channelCore.bot = bot;

  // Connect bot instance to McpServer
  (mcpServer as any).bot = bot;

  // Cleanup on shutdown
  const cleanup = () => {
    if (bot) bot.stopPolling();
    httpServer.stop();
    process.exit(0);
  };

  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  // Start MCP stdio loop
  mcpServer.startStdioLoop();
}

if (import.meta.main) {
  main().catch((err) => {
    console.error("[ida-telegram] Fatal error:", err);
    process.exit(1);
  });
}
