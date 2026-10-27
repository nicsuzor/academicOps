#!/usr/bin/env bun
import { loadConfig } from "./src/config.js";
import { PluginStore } from "./src/store.js";
import { QuestionBroker } from "./src/telegram/questions.js";
import { PermissionRelay } from "./src/mcp/permissions.js";
import { TelegramBotClient } from "./src/telegram/bot.js";
import { StdioMcpServer } from "./src/mcp/server.js";
import { startWebServer } from "./src/web/server.js";
import { createServer } from "node:net";
import { existsSync, unlinkSync, chmodSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

import { broadcastSseEvent } from "./src/web/routes.js";

async function main() {
  const config = loadConfig(process.env);
  const store = new PluginStore(config.stateDir);
  const broker = new QuestionBroker(config.stateDir);
  const permRelay = new PermissionRelay(config.stateDir);

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
    editTelegramCard: async (chatId: number, messageId: number, text: string, replyMarkup?: Record<string, unknown>) => {
      if (bot) {
        await bot.editMessage(chatId, messageId, text, replyMarkup || { inline_keyboard: [] });
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

  // Start Unix Domain Socket bridge for PreToolUse hooks (0600 permissions)
  if (existsSync(config.socketPath)) {
    try {
      unlinkSync(config.socketPath);
    } catch {
      // Ignore
    }
  }

  const socketServer = createBridgeServer(
    config,
    broker,
    bot,
    (content, meta) => mcpServer.emitChannelNotification(content, meta),
    store,
    broadcastSseEvent
  );

  socketServer.listen(config.socketPath, () => {
    try {
      chmodSync(config.socketPath, 0o600); // Strict local permissions per FR-4.1
    } catch (err) {
      console.warn("[ida-telegram] chmod socket failed:", err);
    }
  });

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

export function createBridgeServer(
  config: PluginConfig,
  broker: QuestionBroker,
  bot: TelegramBotClient | null,
  emitChannelNotification?: (content: string, meta: Record<string, unknown>) => void,
  store?: PluginStore,
  broadcastSse?: typeof broadcastSseEvent
) {
  return createServer((client) => {
    let raw = "";
    client.on("data", async (chunk) => {
      raw += chunk.toString();
      if (raw.includes("\n")) {
        const line = raw.trim();
        try {
          const req = JSON.parse(line);
          if (req.type === "ask_user") {
            const postedIds: string[] = [];
            const topMiniAppOnly = req.mini_app_only === true || req.chat === false;
            for (const q of req.questions || []) {
              const isMiniAppOnly = topMiniAppOnly || q.mini_app_only === true || q.chat === false;
              const result = await broker.askUser({
                question: q.question,
                header: q.header,
                context: q.context,
                detail: q.detail,
                mini_app_only: isMiniAppOnly,
                recommendation: q.recommendation,
                options: q.options,
                multiSelect: q.multiSelect,
                allowOther: q.allowOther,
                chatId: config.allowFrom[0],
                turnId: q.turnId || q.turn_id || req.turn_id || req.turnId,
                sessionId: q.sessionId || q.session_id || req.session_id || req.sessionId,
              });
              postedIds.push(result.questionId);

              if (bot && !isMiniAppOnly) {
                const card = broker.renderQuestionCard(result.questionId);
                if (card && config.allowFrom[0]) {
                  await bot.sendQuestionCard(config.allowFrom[0], result.questionId, card);
                }
              }
            }

            client.write(JSON.stringify({ status: "ok", questionId: postedIds[0], questionIds: postedIds }) + "\n");
          } else if (req.type === "close_question") {
            const questionId = req.question_id || req.questionId || req.id;
            const reason = typeof req.reason === "string" ? req.reason.trim() : "";
            if (!questionId) {
              client.write(JSON.stringify({ status: "error", error: "Missing question_id" }) + "\n");
              return;
            }
            if (!reason) {
              client.write(JSON.stringify({ status: "error", error: "Missing reason: closing a question requires an explicit stated reason" }) + "\n");
              return;
            }
            const result = await broker.closeQuestion(questionId, reason);
            if (result && bot && result.question.chatId && result.question.messageId) {
              await bot.editMessage(result.question.chatId, result.question.messageId, result.cardText, { inline_keyboard: [] });
            }
            if (result && emitChannelNotification) {
              emitChannelNotification(`Question closed: ${result.channelEvent.reason}`, {
                event: result.channelEvent.event,
                ...result.channelEvent,
              });
            }
            if (result && store && broadcastSse) {
              const seq = store.nextSeq("question_closed", {
                question_id: questionId,
                reason: result.channelEvent.reason,
                turn_id: result.channelEvent.turn_id,
                session_id: result.channelEvent.session_id,
              });
              broadcastSse("question_closed", {
                question_id: questionId,
                reason: result.channelEvent.reason,
                turn_id: result.channelEvent.turn_id,
                session_id: result.channelEvent.session_id,
              }, seq);
            }
            client.write(JSON.stringify({ status: result ? "ok" : "not_found", result }) + "\n");
          } else if (req.type === "answer_question") {
            const questionId = req.question_id || req.questionId || req.id;
            const choice = typeof req.choice === "string" ? req.choice.trim() : undefined;
            const optionIndex = typeof req.option_index === "number" ? req.option_index : undefined;
            if (!questionId) {
              client.write(JSON.stringify({ status: "error", error: "Missing question_id" }) + "\n");
              return;
            }
            if (!choice && optionIndex === undefined) {
              client.write(JSON.stringify({ status: "error", error: "Missing answer: provide choice or option_index" }) + "\n");
              return;
            }
            const result = await broker.resolveAnswer(questionId, optionIndex !== undefined ? optionIndex : "other", choice);
            if (result && bot && result.question.chatId && result.question.messageId) {
              await bot.editMessage(result.question.chatId, result.question.messageId, result.cardText, { inline_keyboard: [] });
            }
            if (result && emitChannelNotification) {
              emitChannelNotification(`Question answered: ${result.channelEvent.choice}`, {
                event: result.channelEvent.event,
                ...result.channelEvent,
              });
            }
            if (result && store && broadcastSse) {
              const seq = store.nextSeq("question_resolved", {
                question_id: questionId,
                choice: result.channelEvent.choice,
                turn_id: result.channelEvent.turn_id,
              });
              broadcastSse("question_resolved", {
                question_id: questionId,
                choice: result.channelEvent.choice,
                turn_id: result.channelEvent.turn_id,
              }, seq);
            }
            client.write(JSON.stringify({ status: result ? "ok" : "not_found", result }) + "\n");
          } else if (req.type === "list_questions") {
            const pending = broker.getPendingQuestions();
            client.write(JSON.stringify({ status: "ok", questions: pending }) + "\n");
          }
        } catch {
          client.write(JSON.stringify({ error: "malformed request" }) + "\n");
        }
      }
    });
  });
}

if (import.meta.main) {
  main().catch((err) => {
    console.error("[ida-telegram] Fatal error:", err);
    process.exit(1);
  });
}
