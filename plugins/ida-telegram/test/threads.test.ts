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
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
          from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            user: { id: 12345678, is_bot: false, first_name: "Nic" },
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
            from: { id: 12345678, is_bot: false, first_name: "Nic" },
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
});
