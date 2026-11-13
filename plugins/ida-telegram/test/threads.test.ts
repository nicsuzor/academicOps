import { describe, expect, test } from "bun:test";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { loadConfig } from "../src/config.js";
import { PluginStore } from "../src/store.js";
import { buildVoiceInEvent } from "../src/telegram/voice.js";
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Threaded Conversations Support", () => {
  const allowFrom = [12345678];

  describe("AC1: Inbound messages arriving in a thread carry thread identity", () => {
    test("text message arriving in a thread delivers message_thread_id and thread_id in meta", () => {
      const update: TelegramUpdate = {
        update_id: 1,
        message: {
          message_id: 101,
          message_thread_id: 4242,
          date: Date.now(),
          chat: { id: 12345678, type: "supergroup" },
          from: { id: 12345678, is_bot: false, first_name: "Alex" },
          text: "Message in thread 4242",
        },
      };

      const result = parseInboundUpdate(update, allowFrom);
      expect(result).not.toBeNull();
      expect(result?.event).toBe("message");
      expect(result?.meta.message_thread_id).toBe("4242");
      expect(result?.meta.thread_id).toBe("4242");
    });

    test("bot command arriving in a thread delivers message_thread_id and thread_id in meta", () => {
      const update: TelegramUpdate = {
        update_id: 2,
        message: {
          message_id: 102,
          message_thread_id: 4242,
          date: Date.now(),
          chat: { id: 12345678, type: "supergroup" },
          from: { id: 12345678, is_bot: false, first_name: "Alex" },
          text: "/q new task idea",
        },
      };

      const result = parseInboundUpdate(update, allowFrom);
      expect(result).not.toBeNull();
      expect(result?.event).toBe("bot_command");
      expect(result?.meta.message_thread_id).toBe("4242");
      expect(result?.meta.thread_id).toBe("4242");
    });

    test("attachment arriving in a thread delivers message_thread_id and thread_id in meta", () => {
      const update: TelegramUpdate = {
        update_id: 3,
        message: {
          message_id: 103,
          message_thread_id: 4242,
          date: Date.now(),
          chat: { id: 12345678, type: "supergroup" },
          from: { id: 12345678, is_bot: false, first_name: "Alex" },
          document: { file_id: "doc123", file_name: "report.pdf" },
          caption: "Here is the report",
        },
      };

      const result = parseInboundUpdate(update, allowFrom);
      expect(result).not.toBeNull();
      expect(result?.event).toBe("attachment");
      expect(result?.meta.message_thread_id).toBe("4242");
      expect(result?.meta.thread_id).toBe("4242");
    });

    test("callback query on a threaded message delivers message_thread_id and thread_id in meta", () => {
      const update: TelegramUpdate = {
        update_id: 4,
        callback_query: {
          id: "cb_1",
          from: { id: 12345678, is_bot: false, first_name: "Alex" },
          message: {
            message_id: 200,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            text: "Question card",
          },
          data: "custom_action:continue",
        },
      };

      const result = parseInboundUpdate(update, allowFrom);
      expect(result).not.toBeNull();
      expect(result?.event).toBe("button_tap");
      expect(result?.meta.message_thread_id).toBe("4242");
      expect(result?.meta.thread_id).toBe("4242");
    });

    test("voice in event carries message_thread_id and thread_id in meta", () => {
      const voiceEvent = buildVoiceInEvent({
        transcript: "Voice transcript",
        duration: 5,
        messageId: 104,
        messageThreadId: 4242,
      });

      expect(voiceEvent.meta.message_thread_id).toBe("4242");
      expect(voiceEvent.meta.thread_id).toBe("4242");
    });
  });

  describe("AC2: Every outbound path stays in thread with no configuration", () => {
    test("reply tool call stays in thread by default without explicit thread setting", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-reply-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 501 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Simulate inbound message in thread 4242
        await (bot as any).handleUpdate({
          update_id: 10,
          message: {
            message_id: 100,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Let's discuss in this thread",
          },
        });

        // Clear initial reaction call from handleUpdate
        apiCalls.length = 0;

        // 2. Outbound reply call with NO thread configuration
        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Here is my response in thread.",
            },
          },
        });

        const parsedResult = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const sendMsgCall = apiCalls.find((c) => c.method === "sendMessage");
        expect(sendMsgCall).toBeDefined();
        expect(sendMsgCall?.body.chat_id).toBe(12345678);
        expect(sendMsgCall?.body.message_thread_id).toBe(4242);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("voice reply stays in thread by default without explicit thread setting", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-voice-"));
      // Create mock speak script
      const mockSpeakScript = join(stateDir, "mock-speak.sh");
      writeFileSync(mockSpeakScript, "#!/bin/sh\necho 'audio' > \"$2\"\nexit 0\n");
      chmodSync(mockSpeakScript, 0o755);

      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_SPEAK_CMD: mockSpeakScript,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        let body: any = {};
        if (init?.body instanceof FormData) {
          body = {
            chat_id: init.body.get("chat_id"),
            message_thread_id: init.body.get("message_thread_id"),
            caption: init.body.get("caption"),
          };
        } else if (init?.body) {
          body = JSON.parse(String(init.body));
        }
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 502 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Simulate inbound message in thread 4242
        await (bot as any).handleUpdate({
          update_id: 11,
          message: {
            message_id: 101,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Send voice note in this thread",
          },
        });

        apiCalls.length = 0;

        // 2. Outbound voice reply call with NO thread configuration
        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 2,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Spoken update.",
              voice: true,
            },
          },
        });

        const parsedResult = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const voiceCall = apiCalls.find((c) => c.method === "sendVoice");
        expect(voiceCall).toBeDefined();
        expect(voiceCall?.body.chat_id).toBe("12345678");
        expect(Number(voiceCall?.body.message_thread_id)).toBe(4242);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("ask_user question card stays in thread by default without explicit thread setting", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-q-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 503 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Simulate inbound message in thread 4242
        await (bot as any).handleUpdate({
          update_id: 12,
          message: {
            message_id: 102,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Need your recommendation",
          },
        });

        apiCalls.length = 0;

        // 2. Outbound ask_user call with NO thread configuration
        const askRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: {
            name: "ask_user",
            arguments: {
              questions: [
                {
                  question: "Which approach should we take?",
                  options: [{ label: "Approach A" }, { label: "Approach B" }],
                },
              ],
            },
          },
        });

        expect(askRes?.result).toBeDefined();

        const sendMsgCall = apiCalls.find((c) => c.method === "sendMessage");
        expect(sendMsgCall).toBeDefined();
        expect(sendMsgCall?.body.chat_id).toBe(12345678);
        expect(sendMsgCall?.body.message_thread_id).toBe(4242);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("force_reply prompt for other in question card stays in thread", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-other-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const qResult = await broker.askUser({
        question: "Select option",
        options: [{ label: "A" }],
        allowOther: true,
        chatId: 12345678,
      });
      broker.setMessageId(qResult.questionId, 504);

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 505 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);

        // User taps "✏️ Other" in thread 4242
        await (bot as any).handleUpdate({
          update_id: 13,
          callback_query: {
            id: "cb_other",
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            message: {
              message_id: 504,
              message_thread_id: 4242,
              date: Date.now(),
              chat: { id: 12345678, type: "supergroup" },
              text: "Select option",
            },
            data: `q:${qResult.questionId}:0:other`,
          },
        });

        const promptCall = apiCalls.find(
          (c) => c.method === "sendMessage" && c.body.reply_markup?.force_reply === true
        );
        expect(promptCall).toBeDefined();
        expect(promptCall?.body.message_thread_id).toBe(4242);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("react tool call and status reaction stay on the threaded message with no configuration", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-react-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Simulate inbound message in thread 4242
        await (bot as any).handleUpdate({
          update_id: 16,
          message: {
            message_id: 106,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message to react to",
          },
        });

        // Verify status reaction 👀 was placed on message 106
        const statusRxCall = apiCalls.find((c) => c.method === "setMessageReaction");
        expect(statusRxCall).toBeDefined();
        expect(statusRxCall?.body.chat_id).toBe(12345678);
        expect(statusRxCall?.body.message_id).toBe(106);
        expect(statusRxCall?.body.reaction?.[0]?.emoji).toBe("👀");

        apiCalls.length = 0;

        // 2. Outbound react tool call with no chat_id configuration
        const reactRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 4,
          method: "tools/call",
          params: {
            name: "react",
            arguments: {
              message_id: 106,
              reaction: "👍",
            },
          },
        });

        const parsedResult = JSON.parse((reactRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const reactCall = apiCalls.find((c) => c.method === "setMessageReaction");
        expect(reactCall).toBeDefined();
        expect(reactCall?.body.chat_id).toBe(12345678);
        expect(reactCall?.body.message_id).toBe(106);
        expect(reactCall?.body.reaction?.[0]?.emoji).toBe("👍");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("edit_message tool call edits threaded message in-place without configuration", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-edit-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 107 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Simulate inbound message in thread 4242
        await (bot as any).handleUpdate({
          update_id: 17,
          message: {
            message_id: 107,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message to edit",
          },
        });

        apiCalls.length = 0;

        // Outbound edit_message call
        const editRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 5,
          method: "tools/call",
          params: {
            name: "edit_message",
            arguments: {
              message_id: 107,
              text: "Edited content in thread",
            },
          },
        });

        const parsedResult = JSON.parse((editRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const editCall = apiCalls.find((c) => c.method === "editMessageText");
        expect(editCall).toBeDefined();
        expect(editCall?.body.chat_id).toBe(12345678);
        expect(editCall?.body.message_id).toBe(107);
        expect(editCall?.body.text).toBe("Edited content in thread");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("inbound reaction event in a thread carries thread identity", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-rx-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const emittedEvents: Array<{ content: string; meta: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async () => {
        return new Response(JSON.stringify({ ok: true, result: {} }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(
          config,
          broker,
          permRelay,
          (content, meta) => emittedEvents.push({ content, meta }),
          store
        );

        // 1. Initial message in thread 4242
        await (bot as any).handleUpdate({
          update_id: 14,
          message: {
            message_id: 105,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message to react to",
          },
        });

        emittedEvents.length = 0;

        // 2. Reaction arrives for message 105
        await (bot as any).handleUpdate({
          update_id: 15,
          message_reaction: {
            chat: { id: 12345678, type: "supergroup" },
            message_id: 105,
            user: { id: 12345678, is_bot: false, first_name: "Alex" },
            date: Date.now(),
            old_reaction: [],
            new_reaction: [{ type: "emoji", emoji: "👍" }],
          },
        });

        expect(emittedEvents.length).toBe(1);
        expect(emittedEvents[0].meta.message_thread_id).toBe("4242");
        expect(emittedEvents[0].meta.thread_id).toBe("4242");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });

  describe("AC3: Unthreaded chats behave as before", () => {
    test("unthreaded message does not attach message_thread_id and outbound reply remains unthreaded", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-unth-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 601 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Inbound unthreaded message (private chat or regular group)
        const unthreadedUpdate: TelegramUpdate = {
          update_id: 20,
          message: {
            message_id: 201,
            date: Date.now(),
            chat: { id: 12345678, type: "private" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Direct unthreaded message",
          },
        };

        const parsed = parseInboundUpdate(unthreadedUpdate, allowFrom);
        expect(parsed?.meta.message_thread_id).toBeUndefined();
        expect(parsed?.meta.thread_id).toBeUndefined();

        await (bot as any).handleUpdate(unthreadedUpdate);
        apiCalls.length = 0;

        // 2. Outbound reply call
        await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 10,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Unthreaded reply",
            },
          },
        });

        const sendMsgCall = apiCalls.find((c) => c.method === "sendMessage");
        expect(sendMsgCall).toBeDefined();
        expect(sendMsgCall?.body.message_thread_id).toBeUndefined();
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });

  describe("AC4: Thread Renaming (rename_thread)", () => {
    test("rename_thread renames the active thread in the chat via editForumTopic", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-rename-act-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Simulate inbound message in thread 4242 to set active thread
        await (bot as any).handleUpdate({
          update_id: 30,
          message: {
            message_id: 301,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message in thread 4242",
          },
        });
        apiCalls.length = 0;

        // 2. Call rename_thread without explicit thread_id (should use active thread 4242)
        const response = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 11,
          method: "tools/call",
          params: {
            name: "rename_thread",
            arguments: {
              name: "Renamed Active Thread",
            },
          },
        });

        const renameCall = apiCalls.find((c) => c.method === "editForumTopic");
        expect(renameCall).toBeDefined();
        expect(renameCall?.body.chat_id).toBe(12345678);
        expect(renameCall?.body.message_thread_id).toBe(4242);
        expect(renameCall?.body.name).toBe("Renamed Active Thread");

        expect(response?.result).toBeDefined();
        const contentText = (response?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(true);
        expect(parsed.message_thread_id).toBe(4242);
        expect(parsed.name).toBe("Renamed Active Thread");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("rename_thread renames an explicitly specified thread ID with optional icon", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-rename-exp-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const response = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 12,
          method: "tools/call",
          params: {
            name: "rename_thread",
            arguments: {
              chat_id: 12345678,
              message_thread_id: 8888,
              name: "Explicitly Targeted Thread",
              icon_custom_emoji_id: "54321",
            },
          },
        });

        const renameCall = apiCalls.find((c) => c.method === "editForumTopic");
        expect(renameCall).toBeDefined();
        expect(renameCall?.body.chat_id).toBe(12345678);
        expect(renameCall?.body.message_thread_id).toBe(8888);
        expect(renameCall?.body.name).toBe("Explicitly Targeted Thread");
        expect(renameCall?.body.icon_custom_emoji_id).toBe("54321");

        const contentText = (response?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(true);
        expect(parsed.message_thread_id).toBe(8888);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("rename_thread returns clear error when name is empty or missing", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-rename-err-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const response = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 13,
          method: "tools/call",
          params: {
            name: "rename_thread",
            arguments: {
              message_thread_id: 1234,
              name: "   ",
            },
          },
        });

        const contentText = (response?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("Missing name");
      } finally {
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("rename_thread returns clear error when no thread ID can be resolved", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-rename-noth-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const response = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 14,
          method: "tools/call",
          params: {
            name: "rename_thread",
            arguments: {
              name: "Valid Name But No Thread",
            },
          },
        });

        const contentText = (response?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("Missing thread ID");
      } finally {
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("rename_thread returns clear error when Telegram Bot API rejects rename", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-rename-rej-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const origFetch = globalThis.fetch;
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({
            ok: false,
            error_code: 400,
            description: "Bad Request: TOPIC_ID_INVALID",
          }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const response = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 15,
          method: "tools/call",
          params: {
            name: "rename_thread",
            arguments: {
              message_thread_id: 99999,
              name: "Invalid Thread Topic",
            },
          },
        });

        const contentText = (response?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(false);
        expect(parsed.error).toBe("Bad Request: TOPIC_ID_INVALID");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });

  describe("US-5: Routing When No Thread is Defined & Outbound Verification", () => {
    test("AC1: reply to a message sent outside a thread targets inbound message via reply_parameters", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-unth-reply-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 116 } }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Simulate inbound message outside any thread (message 115)
        await (bot as any).handleUpdate({
          update_id: 40,
          message: {
            message_id: 115,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message sent outside any topic",
          },
        });

        apiCalls.length = 0;

        // 2. Outbound reply call with no thread configuration
        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 41,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Reply to message outside topic",
            },
          },
        });

        const parsed = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);

        const sendCall = apiCalls.find((c) => c.method === "sendMessage");
        expect(sendCall).toBeDefined();
        // Must attach to message 115 via reply_parameters and omit message_thread_id
        expect(sendCall?.body.reply_parameters?.message_id).toBe(115);
        expect(sendCall?.body.message_thread_id).toBeUndefined();
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("AC1: send after a restart preserves the active thread from persistent state", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-restart-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: { message_id: 502 } }), { status: 200 });
      }) as typeof fetch;

      try {
        // Session 1: Receive message in thread 4242
        const store1 = new PluginStore(config.stateDir);
        const broker1 = new QuestionBroker(config.stateDir);
        const permRelay1 = new PermissionRelay();
        const bot1 = new TelegramBotClient(config, broker1, permRelay1, () => {}, store1);

        await (bot1 as any).handleUpdate({
          update_id: 50,
          message: {
            message_id: 201,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Threaded conversation setup",
          },
        });

        // Simulate host restart: new store and bot client on SAME stateDir
        const store2 = new PluginStore(config.stateDir);
        const broker2 = new QuestionBroker(config.stateDir);
        const permRelay2 = new PermissionRelay();
        const bot2 = new TelegramBotClient(config, broker2, permRelay2, () => {}, store2);
        const mcp2 = new StdioMcpServer(config, store2, broker2, bot2, permRelay2);

        apiCalls.length = 0;

        // Session 2: Send reply after restart without specifying thread
        const replyRes = await mcp2.handleMessage({
          jsonrpc: "2.0",
          id: 51,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Sending after restart",
            },
          },
        });

        const parsed = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);

        const sendCall = apiCalls.find((c) => c.method === "sendMessage");
        expect(sendCall).toBeDefined();
        expect(sendCall?.body.message_thread_id).toBe(4242);
        expect(parsed.message_thread_id).toBe(4242);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("AC3: catches when outbound message lands in thread 1 (#) when unthreaded was expected", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-unopenable-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      // Mock Telegram returning message placed in thread 1 (the General / "#" thread)
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_id: 118,
              message_thread_id: 1, // Landed in thread 1 ("#")
            },
          }),
          { status: 200 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Inbound message outside any thread
        await (bot as any).handleUpdate({
          update_id: 60,
          message: {
            message_id: 115,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message outside thread",
          },
        });

        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 61,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Attempted reply",
            },
          },
        });

        const parsed = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        // Check #3463: MUST be caught as failure rather than reported as success!
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("mismatch");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("AC3: after reconnect with no active thread or inbound message, fails fast in topics chat", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-no-active-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      // Mark chat 12345678 as topics enabled
      (store as any).updateChatState?.(12345678, { topicsEnabled: true });
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Attempt reply without message_thread_id, with no active thread and no inbound message
        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 70,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              chat_id: 12345678,
              text: "Blind send in topics chat",
            },
          },
        });

        const parsed = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("Active thread is not defined");
      } finally {
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("AC3 & AC2: reply tool result reports message_thread_id for caller observability", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-obs-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
        VOICE_REPLIES: "off",
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const origFetch = globalThis.fetch;
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_id: 701,
              message_thread_id: 4242,
            },
          }),
          { status: 200 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        await (bot as any).handleUpdate({
          update_id: 80,
          message: {
            message_id: 700,
            message_thread_id: 4242,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Thread 4242 message",
          },
        });

        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 81,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Observability reply",
            },
          },
        });

        const parsed = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.message_thread_id).toBe(4242);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });

  describe("AC5: Thread Creation (create_thread)", () => {
    test("create_thread opens a titled thread from main chat and subsequent reply is sent inside it", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-create-act-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        if (method === "createForumTopic") {
          return new Response(
            JSON.stringify({
              ok: true,
              result: {
                message_thread_id: 7777,
                name: "New Research Discussion",
                icon_color: 7322096,
              },
            }),
            { status: 200 }
          );
        }
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_id: 901,
              ...(body?.message_thread_id !== undefined ? { message_thread_id: body.message_thread_id } : {}),
            },
          }),
          { status: 200 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // 1. Inbound unthreaded message from main chat
        await (bot as any).handleUpdate({
          update_id: 40,
          message: {
            message_id: 401,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Let's move to a new topic",
          },
        });
        apiCalls.length = 0;

        // 2. Agent invokes create_thread
        const createRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 20,
          method: "tools/call",
          params: {
            name: "create_thread",
            arguments: {
              name: "New Research Discussion",
            },
          },
        });

        const createCall = apiCalls.find((c) => c.method === "createForumTopic");
        expect(createCall).toBeDefined();
        expect(createCall?.body.chat_id).toBe(12345678);
        expect(createCall?.body.name).toBe("New Research Discussion");

        expect(createRes?.result).toBeDefined();
        const contentText = (createRes?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(true);
        expect(parsed.message_thread_id).toBe(7777);
        expect(parsed.thread_id).toBe(7777);
        expect(parsed.name).toBe("New Research Discussion");

        apiCalls.length = 0;

        // 3. Subsequent reply without thread parameter lands in thread 7777
        const replyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 21,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              text: "Carrying on inside the new thread.",
            },
          },
        });

        const replyParsed = JSON.parse((replyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(replyParsed.success).toBe(true);

        const sendMsgCall = apiCalls.find((c) => c.method === "sendMessage");
        expect(sendMsgCall).toBeDefined();
        expect(sendMsgCall?.body.chat_id).toBe(12345678);
        expect(sendMsgCall?.body.message_thread_id).toBe(7777);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("create_thread forwards optional icon_color and icon_custom_emoji_id", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-create-opt-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const apiCalls: Array<{ method: string; body: any }> = [];
      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        apiCalls.push({ method, body });
        return new Response(
          JSON.stringify({
            ok: true,
            result: {
              message_thread_id: 8888,
              name: "Styled Topic",
              icon_color: 9367192,
              icon_custom_emoji_id: "emoji_123",
            },
          }),
          { status: 200 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 22,
          method: "tools/call",
          params: {
            name: "create_thread",
            arguments: {
              chat_id: 12345678,
              name: "Styled Topic",
              icon_color: 9367192,
              icon_custom_emoji_id: "emoji_123",
            },
          },
        });

        const createCall = apiCalls.find((c) => c.method === "createForumTopic");
        expect(createCall).toBeDefined();
        expect(createCall?.body.chat_id).toBe(12345678);
        expect(createCall?.body.name).toBe("Styled Topic");
        expect(createCall?.body.icon_color).toBe(9367192);
        expect(createCall?.body.icon_custom_emoji_id).toBe("emoji_123");

        const contentText = (res?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(true);
        expect(parsed.message_thread_id).toBe(8888);
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("create_thread returns clear error when name is empty or missing or exceeds 128 characters", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-create-val-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Empty name
        const emptyRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 23,
          method: "tools/call",
          params: {
            name: "create_thread",
            arguments: {
              name: "   ",
            },
          },
        });
        const emptyParsed = JSON.parse((emptyRes?.result as any)?.content?.[0]?.text || "{}");
        expect(emptyParsed.success).toBe(false);
        expect(emptyParsed.error).toContain("Missing name");

        // Too long name (> 128 chars)
        const longRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 24,
          method: "tools/call",
          params: {
            name: "create_thread",
            arguments: {
              name: "a".repeat(129),
            },
          },
        });
        const longParsed = JSON.parse((longRes?.result as any)?.content?.[0]?.text || "{}");
        expect(longParsed.success).toBe(false);
        expect(longParsed.error).toContain("128 characters");
      } finally {
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("create_thread returns clear error when Telegram Bot API rejects creation", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-create-rej-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();

      const origFetch = globalThis.fetch;
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({
            ok: false,
            error_code: 400,
            description: "Bad Request: not enough rights to create a topic",
          }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 25,
          method: "tools/call",
          params: {
            name: "create_thread",
            arguments: {
              name: "Forbidden Topic",
            },
          },
        });

        const contentText = (res?.result as any)?.content?.[0]?.text;
        const parsed = JSON.parse(contentText);
        expect(parsed.success).toBe(false);
        expect(parsed.error).toBe("Bad Request: not enough rights to create a topic");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });

  describe("AC6: Complete Forum-Topic & Thread MCP Tool Surface", () => {
    test("tools/list exposes all 13 Telegram thread tools and core thread parameters while keeping dropped non-thread tools excluded", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-list-"));
      try {
        const config = loadConfig({
          MINI_APP_URL: "https://ida.example.test",
          TELEGRAM_BOT_TOKEN: "test-token",
          IDA_TELEGRAM_ROLE: "primary",
          ALLOWED_USER_IDS: "12345678",
          STATE_DIR: stateDir,
        });
        const store = new PluginStore(config.stateDir);
        const broker = new QuestionBroker(config.stateDir);
        const permRelay = new PermissionRelay();
        const mcp = new StdioMcpServer(config, store, broker, null, permRelay);

        const listRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 100,
          method: "tools/list",
        });

        const tools = ((listRes?.result as any)?.tools || []) as Array<{
          name: string;
          inputSchema?: { properties?: Record<string, unknown> };
        }>;
        const toolNames = tools.map((t) => t.name);

        const expectedThreadTools = [
          "create_thread",
          "rename_thread",
          "close_thread",
          "reopen_thread",
          "delete_thread",
          "unpin_all_thread_messages",
          "get_forum_topic_icon_stickers",
          "edit_general_thread",
          "close_general_thread",
          "reopen_general_thread",
          "hide_general_thread",
          "unhide_general_thread",
          "unpin_all_general_thread_messages",
        ];

        for (const name of expectedThreadTools) {
          expect(toolNames).toContain(name);
        }

        const replyTool = tools.find((t) => t.name === "reply");
        expect(replyTool?.inputSchema?.properties?.message_thread_id).toBeDefined();
        expect(replyTool?.inputSchema?.properties?.thread_id).toBeDefined();

        const reactTool = tools.find((t) => t.name === "react");
        expect(reactTool?.inputSchema?.properties?.message_thread_id).toBeUndefined();

        const askTool = tools.find((t) => t.name === "ask_user");
        expect(askTool?.inputSchema?.properties?.message_thread_id).toBeDefined();
        expect(askTool?.inputSchema?.properties?.thread_id).toBeDefined();

        const exposedMessageTools = [
          "pin_message",
          "unpin_message",
          "unpin_all_messages",
          "forward_messages",
          "copy_messages",
          "delete_messages",
          "edit_message_reply_markup",
        ];
        for (const name of exposedMessageTools) {
          expect(toolNames).toContain(name);
        }
        const excludedTools = [
          "answer_question",
          "close_question",
          "list_questions",
          "anchor",
        ];
        for (const name of excludedTools) {
          expect(toolNames).not.toContain(name);
        }
      } finally {
        rmSync(stateDir, { recursive: true, force: true });
      }
    });

    test("tools/call dispatches unpin_all_thread_messages, get_forum_topic_icon_stickers, and all general thread tools to Telegram Bot API", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-th-general-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "12345678",
        STATE_DIR: stateDir,
      });

      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();
      const apiCalls: Array<{ method: string; body: Record<string, unknown> }> = [];

      const origFetch = globalThis.fetch;
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
        apiCalls.push({ method, body });
        if (method === "getForumTopicIconStickers") {
          return new Response(
            JSON.stringify({ ok: true, result: [{ custom_emoji_id: "5373141891321699086", emoji: "🔥" }] }),
            { status: 200 }
          );
        }
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        await (bot as any).handleUpdate({
          update_id: 300,
          message: {
            message_id: 301,
            message_thread_id: 777,
            date: Date.now(),
            chat: { id: 12345678, type: "supergroup" },
            from: { id: 12345678, is_bot: false, first_name: "Alex" },
            text: "Message in thread 777",
          },
        });
        apiCalls.length = 0;
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const unpinTopicRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 201,
          method: "tools/call",
          params: { name: "unpin_all_thread_messages", arguments: {} },
        });
        expect(JSON.parse((unpinTopicRes?.result as any).content[0].text)).toMatchObject({
          success: true,
          message_thread_id: 777,
          unpinned_all: true,
        });

        const stickersRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 202,
          method: "tools/call",
          params: { name: "get_forum_topic_icon_stickers", arguments: {} },
        });
        const stickersParsed = JSON.parse((stickersRes?.result as any).content[0].text);
        expect(stickersParsed.success).toBe(true);
        expect(stickersParsed.stickers).toHaveLength(1);

        const editGeneralRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 203,
          method: "tools/call",
          params: { name: "edit_general_thread", arguments: { name: "Main Hub" } },
        });
        expect(JSON.parse((editGeneralRes?.result as any).content[0].text)).toMatchObject({
          success: true,
          name: "Main Hub",
        });

        for (const [idx, op] of [
          ["close_general_thread", { closed: true }],
          ["reopen_general_thread", { reopened: true }],
          ["hide_general_thread", { hidden: true }],
          ["unhide_general_thread", { unhidden: true }],
          ["unpin_all_general_thread_messages", { unpinned_all: true }],
        ].entries()) {
          const [toolName, expected] = op as [string, Record<string, unknown>];
          const res = await mcp.handleMessage({
            jsonrpc: "2.0",
            id: 204 + idx,
            method: "tools/call",
            params: { name: toolName, arguments: {} },
          });
          expect(JSON.parse((res?.result as any).content[0].text)).toMatchObject({
            success: true,
            ...expected,
          });
        }

        expect(apiCalls.map((c) => c.method)).toEqual([
          "unpinAllForumTopicMessages",
          "getForumTopicIconStickers",
          "editGeneralForumTopic",
          "closeGeneralForumTopic",
          "reopenGeneralForumTopic",
          "hideGeneralForumTopic",
          "unhideGeneralForumTopic",
          "unpinAllGeneralForumTopicMessages",
        ]);
        expect(apiCalls[0].body).toEqual({ chat_id: 12345678, message_thread_id: 777 });
        expect(apiCalls[2].body).toEqual({ chat_id: 12345678, name: "Main Hub" });

        // Validate empty General thread name rejection
        const invalidRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 220,
          method: "tools/call",
          params: { name: "edit_general_thread", arguments: { name: "   " } },
        });
        expect(invalidRes?.isError).toBe(true);
        expect(JSON.parse((invalidRes?.result as any).content[0].text).success).toBe(false);

        // Validate non-integer icon_color rejection on create_thread
        const invalidColorRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 221,
          method: "tools/call",
          params: { name: "create_thread", arguments: { name: "Bad Color", icon_color: "not-an-int" } },
        });
        expect(invalidColorRes?.isError).toBe(true);
        const invalidColorParsed = JSON.parse((invalidColorRes?.result as any).content[0].text);
        expect(invalidColorParsed.success).toBe(false);
        expect(invalidColorParsed.error).toContain("icon_color");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });
});
