#!/usr/bin/env bun
import { loadConfig } from "./src/config.js";
import { PluginStore } from "./src/store.js";
import { QuestionBroker } from "./src/telegram/questions.js";
import { FeedbackManager } from "./src/telegram/feedback.js";
import { PermissionRelay } from "./src/mcp/permissions.js";
import { TelegramBotClient } from "./src/telegram/bot.js";
import { StdioMcpServer } from "./src/mcp/server.js";
import { startWebServer } from "./src/web/server.js";
import { createServer } from "node:net";
import { existsSync, unlinkSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

async function main() {
  const config = loadConfig(process.env);
  const store = new PluginStore(config.stateDir);
  const broker = new QuestionBroker(config.stateDir);
  const feedback = new FeedbackManager(config.stateDir);
  const permRelay = new PermissionRelay();

  let bot: TelegramBotClient | null = null;

  // Stdio MCP server
  const mcpServer = new StdioMcpServer(config, store, broker, null, permRelay);

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
    editTelegramCard: async (chatId: number, messageId: number, text: string) => {
      if (bot) {
        await bot.editMessage(chatId, messageId, text, { inline_keyboard: [] });
      }
    },
  };

  // Start Mini App HTTP loopback server
  const appDir = join(import.meta.dir, "app");
  const httpServer = startWebServer(webContext, appDir);
  console.error(`[ida-telegram] Mini App server running at http://127.0.0.1:${config.port}/app/`);

  // Start Unix Domain Socket bridge for PreToolUse hooks (0600 permissions)
  if (existsSync(config.socketPath)) {
    try {
      unlinkSync(config.socketPath);
    } catch {
      // Ignore
    }
  }

  const socketServer = createServer((client) => {
    let raw = "";
    client.on("data", async (chunk) => {
      raw += chunk.toString();
      if (raw.includes("\n")) {
        const line = raw.trim();
        try {
          const req = JSON.parse(line);
          if (req.type === "ask_user") {
            const postedIds: string[] = [];
            for (const q of req.questions || []) {
              const result = await broker.askUser({
                question: q.question,
                header: q.header,
                options: q.options,
                multiSelect: q.multiSelect,
                allowOther: q.allowOther,
                chatId: config.allowFrom[0],
              });
              postedIds.push(result.questionId);

              if (bot) {
                const card = broker.renderQuestionCard(result.questionId);
                if (card && config.allowFrom[0]) {
                  await bot.sendQuestionCard(config.allowFrom[0], result.questionId, card);
                }
              }
            }

            client.write(JSON.stringify({ status: "ok", questionId: postedIds[0], questionIds: postedIds }) + "\n");
          }
        } catch {
          client.write(JSON.stringify({ error: "malformed request" }) + "\n");
        }
      }
    });
  });

  socketServer.listen(config.socketPath, () => {
    try {
      chmodSync(config.socketPath, 0o600); // Strict local permissions per FR-4.1
    } catch {
      // Ignore
    }
  });

  // Bot client
  if (config.botToken) {
    bot = new TelegramBotClient(
      config,
      broker,
      feedback,
      permRelay,
      (content, meta) => {
        mcpServer.emitChannelNotification(content, meta);
      }
    );

    // Start background polling
    bot.startPolling().catch((e) => console.error("[ida-telegram] Polling stopped:", e));
  }

  // Connect bot instance to McpServer
  (mcpServer as any).bot = bot;

  // Cleanup on shutdown
  const cleanup = () => {
    if (bot) bot.stopPolling();
    httpServer.stop();
    socketServer.close();
    if (existsSync(config.socketPath)) {
      try {
        unlinkSync(config.socketPath);
      } catch {
        // Ignore
      }
    }
    process.exit(0);
  };

  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  // Start MCP stdio loop
  mcpServer.startStdioLoop();
}

main().catch((err) => {
  console.error("[ida-telegram] Fatal error:", err);
  process.exit(1);
});
