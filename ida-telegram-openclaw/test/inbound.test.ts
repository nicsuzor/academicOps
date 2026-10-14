import { describe, expect, test } from "bun:test";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";

describe("Inbound completeness: Updates routing and parsing", () => {
  const allowFrom = [12345678];

  test("drops updates from users not in allowFrom", () => {
    const update: TelegramUpdate = {
      update_id: 1,
      message: {
        message_id: 101,
        date: Date.now(),
        chat: { id: 99999999, type: "private" },
        from: { id: 99999999, is_bot: false, first_name: "Attacker" },
        text: "Hello",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).toBeNull();
  });

  test("processes text message from allowFrom user into channel event", () => {
    const update: TelegramUpdate = {
      update_id: 2,
      message: {
        message_id: 102,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        text: "Please inspect the latest commit.",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("message");
    expect(result?.content).toBe("Please inspect the latest commit.");
    expect(result?.meta.message_id).toBe("102");
    expect(result?.meta.chat_id).toBe("12345678");
    expect(result?.meta.user_id).toBe("12345678");
  });

  test("extracts quoted_text for quote-replies", () => {
    const update: TelegramUpdate = {
      update_id: 3,
      message: {
        message_id: 103,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        text: "Yes, proceed with option A.",
        reply_to_message: {
          message_id: 99,
          date: Date.now() - 60000,
          chat: { id: 12345678, type: "private" },
          text: "Here are the two proposals for review:\nOption A: Proceed immediately\nOption B: Postpone",
        },
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.meta.reply_to_message_id).toBe("99");
    expect(result?.meta.quoted_text).toContain("Option A: Proceed immediately");
  });

  test("delivers message reaction updates with target excerpt", () => {
    const update: TelegramUpdate = {
      update_id: 4,
      message_reaction: {
        chat: { id: 12345678, type: "private" },
        message_id: 88,
        user: { id: 12345678, is_bot: false, first_name: "Nic" },
        date: Date.now(),
        old_reaction: [],
        new_reaction: [{ type: "emoji", emoji: "🔥" }],
      },
    };

    const result = parseInboundUpdate(update, allowFrom, (msgId) => `Previous message text for ${msgId}`);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("reaction");
    expect(result?.content).toBe("reacted 🔥 to 88");
    expect(result?.meta.added).toBe("🔥");
    expect(result?.meta.target_message_id).toBe("88");
    expect(result?.meta.target_excerpt).toBe("Previous message text for 88");
  });

  test("delivers non-question button tap events", () => {
    const update: TelegramUpdate = {
      update_id: 5,
      callback_query: {
        id: "cb_1",
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 77,
          date: Date.now(),
          chat: { id: 12345678, type: "private" },
          text: "Actions",
        },
        data: "custom_action:deploy_test",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("button_tap");
    expect(result?.meta.callback_prefix).toBe("custom_action");
    expect(result?.meta.payload).toBe("deploy_test");
    expect(result?.meta.target_message_id).toBe("77");
    expect(result?.meta.user_id).toBe("12345678");
  });

  test("delivers bot commands as channel events", () => {
    const update: TelegramUpdate = {
      update_id: 6,
      message: {
        message_id: 104,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        text: "/status detailed",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("bot_command");
    expect(result?.content).toBe("/status detailed");
    expect(result?.meta.command).toBe("/status");
    expect(result?.meta.message_id).toBe("104");
    expect(result?.meta.chat_id).toBe("12345678");
    expect(result?.meta.user_id).toBe("12345678");
  });

  test("delivers photo and document updates as channel events with string meta", () => {
    const photoUpdate: TelegramUpdate = {
      update_id: 7,
      message: {
        message_id: 105,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        caption: "Screenshot of the terminal",
        photo: [{ file_id: "photo_small", file_size: 100 }, { file_id: "photo_large", file_size: 900 }],
      },
    };

    const photoResult = parseInboundUpdate(photoUpdate, allowFrom);
    expect(photoResult).not.toBeNull();
    expect(photoResult?.event).toBe("attachment");
    expect(photoResult?.content).toBe("Screenshot of the terminal");
    expect(photoResult?.meta.message_id).toBe("105");
    expect(photoResult?.meta.chat_id).toBe("12345678");
    expect(photoResult?.meta.user_id).toBe("12345678");
    expect(photoResult?.meta.file_id).toBe("photo_large");

    const docUpdate: TelegramUpdate = {
      update_id: 8,
      message: {
        message_id: 106,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        document: { file_id: "doc_file_1", file_name: "report.pdf" },
      },
    };

    const docResult = parseInboundUpdate(docUpdate, allowFrom);
    expect(docResult).not.toBeNull();
    expect(docResult?.event).toBe("attachment");
    expect(docResult?.content).toContain("report.pdf");
    expect(docResult?.meta.message_id).toBe("106");
    expect(docResult?.meta.file_id).toBe("doc_file_1");
    expect(docResult?.meta.file_name).toBe("report.pdf");
  });

  test("every notifications/claude/channel emitted across all inbound message kinds passes Claude Code's Record<string, string> schema", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { FeedbackManager } = await import("../src/telegram/feedback.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-schema-"));
    const config = {
      botToken: "test-token",
      role: "primary",
      isPrimary: true,
      allowFrom: [12345678],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 8093,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const feedback = new FeedbackManager(stateDir);
    const permRelay = new PermissionRelay();

    const emittedNotifications: Array<Record<string, unknown>> = [];
    const origStdoutWrite = process.stdout.write.bind(process.stdout);
    (process.stdout as any).write = (chunk: string | Uint8Array) => {
      const str = typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf-8");
      for (const line of str.split("\n")) {
        if (line.trim().startsWith("{")) {
          const parsed = JSON.parse(line.trim());
          if (parsed.method === "notifications/claude/channel") {
            emittedNotifications.push(parsed);
          }
        }
      }
      return true;
    };

    try {
      const bot = new TelegramBotClient(config, broker, feedback, permRelay, (content, meta) => {
        mcpServer.emitChannelNotification(content, meta);
      });
      (bot as any).callApi = async () => ({ ok: true, result: { message_id: 500, file_path: "voice/file.ogg" } });

      const mcpServer = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Text message with reply quote
      await (bot as any).handleUpdate({
        update_id: 1,
        message: {
          message_id: 201,
          date: 1700000000,
          chat: { id: 12345678, type: "private" },
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
          text: "Hello Ida",
          reply_to_message: {
            message_id: 199,
            date: 1699999900,
            chat: { id: 12345678, type: "private" },
            text: "Earlier message",
          },
        },
      });

      // 2. Bot command (bare and with args)
      await (bot as any).handleUpdate({
        update_id: 2,
        message: {
          message_id: 202,
          date: 1700000001,
          chat: { id: 12345678, type: "private" },
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
          text: "/decide",
        },
      });

      // 3. Reaction update
      await (bot as any).handleUpdate({
        update_id: 3,
        message_reaction: {
          chat: { id: 12345678, type: "private" },
          message_id: 201,
          user: { id: 12345678, is_bot: false, first_name: "Nic" },
          date: 1700000002,
          old_reaction: [],
          new_reaction: [{ type: "emoji", emoji: "🔥" }],
        },
      });

      // 4. Custom button tap
      await (bot as any).handleUpdate({
        update_id: 4,
        callback_query: {
          id: "cb_100",
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
          message: {
            message_id: 203,
            date: 1700000003,
            chat: { id: 12345678, type: "private" },
            text: "Card text",
          },
          data: "decide:pr1:merge",
        },
      });

      // 5. Question answer via Telegram button
      const q = await broker.askUser({
        question: "Proceed?",
        options: [{ label: "Yes" }, { label: "No" }],
        chatId: 12345678,
      });
      await (bot as any).handleUpdate({
        update_id: 5,
        callback_query: {
          id: "cb_101",
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
          message: {
            message_id: 204,
            date: 1700000004,
            chat: { id: 12345678, type: "private" },
            text: "Proceed?",
          },
          data: `q:${q.questionId}:0:0`,
        },
      });

      // 6. Feedback critique
      await (bot as any).handleUpdate({
        update_id: 6,
        callback_query: {
          id: "cb_102",
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
          message: {
            message_id: 205,
            date: 1700000005,
            chat: { id: 12345678, type: "private" },
            text: "Some reply",
          },
          data: "fb:critique:205:Too verbose",
        },
      });

      // 7. Photo / document attachment
      await (bot as any).handleUpdate({
        update_id: 7,
        message: {
          message_id: 206,
          date: 1700000006,
          chat: { id: 12345678, type: "private" },
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
          caption: "Here is a photo",
          photo: [{ file_id: "ph_1", file_size: 1234 }],
        },
      });

      // 8. Mini App PR review action
      const sessionSecret = "test-secret-32-bytes-long-123456";
      const token = createSessionToken(12345678, sessionSecret, 3600);
      await handleApiRequest(
        new Request("http://127.0.0.1:8093/api/app/review/pr", {
          method: "POST",
          headers: { "Content-Type": "application/json", Cookie: `ida_session=${token}` },
          body: JSON.stringify({ action: "approve", repo: "nicsuzor/academicOps", pr: 420 }),
        }),
        {
          store,
          broker,
          config,
          sessionSecret,
          emitChannelEvent: (event, content, meta) => mcpServer.emitChannelNotification(content, { event, ...meta }),
        }
      );

      // 9. Voice message (via buildVoiceInEvent -> emitChannelNotification)
      const { buildVoiceInEvent } = await import("../src/telegram/voice.js");
      const voiceEvent = buildVoiceInEvent({
        transcript: "Hello from voice",
        messageId: 207,
        chatId: 12345678,
        userId: 12345678,
        userName: "Nic",
        durationSec: 12,
        replyToMessageId: 201,
      });
      mcpServer.emitChannelNotification(voiceEvent.content, voiceEvent.meta);

      expect(emittedNotifications.length).toBe(9);

      for (const notif of emittedNotifications) {
        const params = notif.params as { content: unknown; meta: Record<string, unknown> };
        expect(typeof params.content).toBe("string");
        expect(typeof params.meta).toBe("object");
        expect(params.meta).not.toBeNull();

        for (const [k, v] of Object.entries(params.meta)) {
          expect(k).toMatch(/^[a-zA-Z_][a-zA-Z0-9_]*$/);
          expect(typeof v).toBe("string");
        }
      }
    } finally {
      process.stdout.write = origStdoutWrite;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });
});

