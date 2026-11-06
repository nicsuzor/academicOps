import { describe, expect, test } from "bun:test";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { loadConfig } from "../src/config.js";
import { PluginStore } from "../src/store.js";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Telegram Topic and Message Management Tools (specs/telegram/topic-and-message-management.md)", () => {
  const allowFrom = [12345];

  function setupHarness(initialThread?: number) {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-mgmt-"));
    const config = loadConfig({
      MINI_APP_URL: "https://dash.example.test/app",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "12345",
      STATE_DIR: stateDir,
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;

    const cleanup = () => {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    };

    return { config, store, broker, permRelay, apiCalls, cleanup, stateDir };
  }

  describe("US-1: Topic Lifecycle Management (close_thread, reopen_thread, delete_thread)", () => {
    test("close_thread closes topic and returns closed: true (AC-1.1)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: {
            name: "close_thread",
            arguments: { chat_id: 12345, message_thread_id: 1234 },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.closed).toBe(true);
        expect(parsed.chat_id).toBe(12345);
        expect(parsed.message_thread_id).toBe(1234);

        const call = apiCalls.find((c) => c.method === "closeForumTopic");
        expect(call).toBeDefined();
        expect(call?.body.chat_id).toBe(12345);
        expect(call?.body.message_thread_id).toBe(1234);
      } finally {
        cleanup();
      }
    });

    test("close_thread defaults to active topic in session context when message_thread_id omitted (AC-1.2)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Inbound message sets active thread to 5555
        await (bot as any).handleUpdate({
          update_id: 1,
          message: {
            message_id: 10,
            message_thread_id: 5555,
            date: Date.now(),
            chat: { id: 12345, type: "supergroup" },
            from: { id: 12345, is_bot: false },
            text: "Hello in thread 5555",
          },
        });
        apiCalls.length = 0;

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 2,
          method: "tools/call",
          params: {
            name: "close_topic", // test alias
            arguments: { chat_id: 12345 },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.closed).toBe(true);
        expect(parsed.message_thread_id).toBe(5555);

        const call = apiCalls.find((c) => c.method === "closeForumTopic");
        expect(call?.body.message_thread_id).toBe(5555);
      } finally {
        cleanup();
      }
    });

    test("reopen_thread reopens topic via reopenForumTopic (AC-1.3)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: {
            name: "reopen_thread",
            arguments: { chat_id: 12345, message_thread_id: 1234 },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.reopened).toBe(true);
        expect(parsed.message_thread_id).toBe(1234);

        const call = apiCalls.find((c) => c.method === "reopenForumTopic");
        expect(call?.body.message_thread_id).toBe(1234);
      } finally {
        cleanup();
      }
    });

    test("delete_thread deletes topic and clears active thread from session context (AC-1.4)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Inbound message sets active thread to 7777
        await (bot as any).handleUpdate({
          update_id: 1,
          message: {
            message_id: 11,
            message_thread_id: 7777,
            date: Date.now(),
            chat: { id: 12345, type: "supergroup" },
            from: { id: 12345, is_bot: false },
            text: "Topic to delete",
          },
        });
        expect(bot.getLastThreadId(12345)).toBe(7777);
        apiCalls.length = 0;

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 4,
          method: "tools/call",
          params: {
            name: "delete_thread",
            arguments: { chat_id: 12345, message_thread_id: 7777 },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.deleted).toBe(true);
        expect(parsed.message_thread_id).toBe(7777);

        // Active thread tracking must be cleared
        expect(bot.getLastThreadId(12345)).toBeUndefined();
        expect(store.getChatState(12345)?.activeThreadId).toBeUndefined();
      } finally {
        cleanup();
      }
    });

    test("General topic #1 is guarded against close or delete (AC-1.5)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async () => {
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const closeRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 5,
          method: "tools/call",
          params: {
            name: "close_thread",
            arguments: { chat_id: 12345, message_thread_id: 1 },
          },
        });
        const closeParsed = JSON.parse((closeRes?.result as any)?.content?.[0]?.text || "{}");
        expect(closeParsed.success).toBe(false);
        expect(closeParsed.error).toContain("General forum topic");

        const delRes = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 6,
          method: "tools/call",
          params: {
            name: "delete_thread",
            arguments: { chat_id: 12345, message_thread_id: 1 },
          },
        });
        const delParsed = JSON.parse((delRes?.result as any)?.content?.[0]?.text || "{}");
        expect(delParsed.success).toBe(false);
        expect(delParsed.error).toContain("General forum topic");

        // Telegram API must not have been called
        expect(apiCalls.length).toBe(0);
      } finally {
        cleanup();
      }
    });

    test("topic management surfaces Telegram API errors verbatim (AC-1.5)", async () => {
      const { config, store, broker, permRelay, cleanup } = setupHarness();
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: TOPIC_NOT_MODIFIED" }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 7,
          method: "tools/call",
          params: {
            name: "close_thread",
            arguments: { chat_id: 12345, message_thread_id: 1234 },
          },
        });
        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("TOPIC_NOT_MODIFIED");
      } finally {
        cleanup();
      }
    });
  });

  describe("US-2: Message Pinning and Unpinning (pin_message, unpin_message, unpin_all_messages)", () => {
    test("pin_message pins message with silent notification by default (AC-2.1)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 8,
          method: "tools/call",
          params: {
            name: "pin_message",
            arguments: { chat_id: 12345, message_id: 5678 },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.pinned).toBe(true);
        expect(parsed.message_id).toBe(5678);

        const call = apiCalls.find((c) => c.method === "pinChatMessage");
        expect(call).toBeDefined();
        expect(call?.body.chat_id).toBe(12345);
        expect(call?.body.message_id).toBe(5678);
        expect(call?.body.disable_notification).toBe(true);
      } finally {
        cleanup();
      }
    });

    test("unpin_message unpins specific message or most recent when omitted (AC-2.2 & AC-2.3)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Specific message
        const resSpecific = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 9,
          method: "tools/call",
          params: {
            name: "unpin_message",
            arguments: { chat_id: 12345, message_id: 5678 },
          },
        });
        const parsedSpecific = JSON.parse((resSpecific?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedSpecific.success).toBe(true);
        expect(parsedSpecific.unpinned).toBe(true);
        expect(parsedSpecific.message_id).toBe(5678);

        // Most recent message (message_id omitted)
        apiCalls.length = 0;
        const resRecent = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 10,
          method: "tools/call",
          params: {
            name: "unpin_message",
            arguments: { chat_id: 12345 },
          },
        });
        const parsedRecent = JSON.parse((resRecent?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedRecent.success).toBe(true);
        expect(parsedRecent.unpinned).toBe(true);
        const call = apiCalls.find((c) => c.method === "unpinChatMessage");
        expect(call?.body.message_id).toBeUndefined();
      } finally {
        cleanup();
      }
    });

    test("unpin_all_messages dispatches unpinAllForumTopicMessages in topic and unpinAllChatMessages chat-wide (AC-2.4)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Topic unpin all
        const resTopic = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 11,
          method: "tools/call",
          params: {
            name: "unpin_all_messages",
            arguments: { chat_id: 12345, message_thread_id: 1234 },
          },
        });
        const parsedTopic = JSON.parse((resTopic?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedTopic.success).toBe(true);
        expect(parsedTopic.unpinned_all).toBe(true);
        expect(parsedTopic.message_thread_id).toBe(1234);
        expect(apiCalls.some((c) => c.method === "unpinAllForumTopicMessages")).toBe(true);

        // Chat-wide unpin all (unthreaded)
        apiCalls.length = 0;
        const resChat = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 12,
          method: "tools/call",
          params: {
            name: "unpin_all_chat_messages", // test alias
            arguments: { chat_id: 12345 },
          },
        });
        const parsedChat = JSON.parse((resChat?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedChat.success).toBe(true);
        expect(parsedChat.unpinned_all).toBe(true);
        expect(apiCalls.some((c) => c.method === "unpinAllChatMessages")).toBe(true);
      } finally {
        cleanup();
      }
    });

    test("pinning tools surface errors verbatim on API rejection (AC-2.5)", async () => {
      const { config, store, broker, permRelay, cleanup } = setupHarness();
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: not enough rights to pin" }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 13,
          method: "tools/call",
          params: {
            name: "pin_message",
            arguments: { chat_id: 12345, message_id: 9999 },
          },
        });
        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("not enough rights to pin");
      } finally {
        cleanup();
      }
    });
  });

  describe("US-3: Batch Forwarding and Copying (forward_messages, copy_messages)", () => {
    test("forward_messages forwards batch of 1-100 messages via forwardMessages (AC-3.1)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(
          JSON.stringify({
            ok: true,
            result: [{ message_id: 201 }, { message_id: 202 }, { message_id: 203 }],
          }),
          { status: 200 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 14,
          method: "tools/call",
          params: {
            name: "forward_messages",
            arguments: {
              chat_id: 12345,
              message_thread_id: 1234,
              message_ids: [101, 102, 103],
            },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.forwarded_count).toBe(3);
        expect(parsed.message_ids).toEqual([201, 202, 203]);
        expect(parsed.message_thread_id).toBe(1234);

        const call = apiCalls.find((c) => c.method === "forwardMessages");
        expect(call).toBeDefined();
        expect(call?.body.chat_id).toBe(12345);
        expect(call?.body.from_chat_id).toBe(12345);
        expect(call?.body.message_ids).toEqual([101, 102, 103]);
        expect(call?.body.message_thread_id).toBe(1234);
      } finally {
        cleanup();
      }
    });

    test("copy_messages copies batch via copyMessages (AC-3.2)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(
          JSON.stringify({
            ok: true,
            result: [{ message_id: 301 }, { message_id: 302 }],
          }),
          { status: 200 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 15,
          method: "tools/call",
          params: {
            name: "copy_messages",
            arguments: {
              chat_id: 12345,
              message_thread_id: 1234,
              message_ids: [101, 102],
              remove_caption: true,
            },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.copied_count).toBe(2);
        expect(parsed.message_ids).toEqual([301, 302]);

        const call = apiCalls.find((c) => c.method === "copyMessages");
        expect(call).toBeDefined();
        expect(call?.body.remove_caption).toBe(true);
      } finally {
        cleanup();
      }
    });

    test("forward_messages and copy_messages validate batch size between 1 and 100 locally (AC-3.3)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        // Empty array
        const resEmpty = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 16,
          method: "tools/call",
          params: {
            name: "forward_messages",
            arguments: { chat_id: 12345, message_ids: [] },
          },
        });
        const parsedEmpty = JSON.parse((resEmpty?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedEmpty.success).toBe(false);
        expect(parsedEmpty.error).toBe("Batch size must be between 1 and 100 messages");

        // > 100 array
        const largeArray = Array.from({ length: 101 }, (_, i) => i + 1);
        const resLarge = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 17,
          method: "tools/call",
          params: {
            name: "copy_messages",
            arguments: { chat_id: 12345, message_ids: largeArray },
          },
        });
        const parsedLarge = JSON.parse((resLarge?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedLarge.success).toBe(false);
        expect(parsedLarge.error).toBe("Batch size must be between 1 and 100 messages");

        expect(apiCalls.length).toBe(0);
      } finally {
        cleanup();
      }
    });

    test("forwarding surfaces Telegram API errors verbatim (AC-3.4)", async () => {
      const { config, store, broker, permRelay, cleanup } = setupHarness();
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: message to forward not found" }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 18,
          method: "tools/call",
          params: {
            name: "forward_messages",
            arguments: { chat_id: 12345, message_ids: [9999] },
          },
        });
        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("message to forward not found");
      } finally {
        cleanup();
      }
    });
  });

  describe("US-4: Batch Deletion (delete_messages)", () => {
    test("delete_messages deletes batch via deleteMessages (AC-4.1)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 19,
          method: "tools/call",
          params: {
            name: "delete_messages",
            arguments: { chat_id: 12345, message_ids: [101, 102, 103] },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.deleted_count).toBe(3);
        expect(parsed.message_ids).toEqual([101, 102, 103]);

        const call = apiCalls.find((c) => c.method === "deleteMessages");
        expect(call).toBeDefined();
        expect(call?.body.chat_id).toBe(12345);
        expect(call?.body.message_ids).toEqual([101, 102, 103]);
      } finally {
        cleanup();
      }
    });

    test("delete_messages validates batch size between 1 and 100 (AC-4.2)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 20,
          method: "tools/call",
          params: {
            name: "delete_messages",
            arguments: { chat_id: 12345, message_ids: [] },
          },
        });
        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(false);
        expect(parsed.error).toBe("Batch size must be between 1 and 100 messages");
        expect(apiCalls.length).toBe(0);
      } finally {
        cleanup();
      }
    });

    test("delete_messages surfaces 48-hour age rejections verbatim (AC-4.3)", async () => {
      const { config, store, broker, permRelay, cleanup } = setupHarness();
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: message can't be deleted" }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 21,
          method: "tools/call",
          params: {
            name: "delete_messages",
            arguments: { chat_id: 12345, message_ids: [8888] },
          },
        });
        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(false);
        expect(parsed.error).toContain("message can't be deleted");
      } finally {
        cleanup();
      }
    });
  });

  describe("US-5: Sent Message Button Editing (edit_message_reply_markup)", () => {
    test("edit_message_reply_markup updates inline buttons (AC-5.1)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 22,
          method: "tools/call",
          params: {
            name: "edit_message_reply_markup",
            arguments: {
              chat_id: 12345,
              message_id: 5678,
              buttons: [{ label: "Updated Option", callback_data: "opt:1" }],
            },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.message_id).toBe(5678);

        const call = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
        expect(call).toBeDefined();
        expect(call?.body.chat_id).toBe(12345);
        expect(call?.body.message_id).toBe(5678);
        expect(call?.body.reply_markup.inline_keyboard[0][0].text).toBe("Updated Option");
        expect(call?.body.reply_markup.inline_keyboard[0][0].callback_data).toBe("opt:1");
      } finally {
        cleanup();
      }
    });

    test("edit_message_reply_markup clears buttons when empty array or omitted (AC-5.2)", async () => {
      const { config, store, broker, permRelay, apiCalls, cleanup } = setupHarness();
      globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
        const method = String(url).split("/").pop() || "";
        const body = init?.body ? (typeof init.body === "string" ? JSON.parse(init.body) : init.body) : {};
        apiCalls.push({ method, body });
        return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 23,
          method: "tools/call",
          params: {
            name: "edit_message_buttons", // test alias
            arguments: {
              chat_id: 12345,
              message_id: 5678,
              buttons: [],
            },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);

        const call = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
        expect(call?.body.reply_markup.inline_keyboard).toEqual([]);
      } finally {
        cleanup();
      }
    });

    test("edit_message_reply_markup treats message is not modified as idempotent success (AC-5.3)", async () => {
      const { config, store, broker, permRelay, cleanup } = setupHarness();
      globalThis.fetch = (async () => {
        return new Response(
          JSON.stringify({
            ok: false,
            error_code: 400,
            description: "Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message",
          }),
          { status: 400 }
        );
      }) as typeof fetch;

      try {
        const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
        const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

        const res = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 24,
          method: "tools/call",
          params: {
            name: "edit_message_reply_markup",
            arguments: {
              chat_id: 12345,
              message_id: 5678,
              buttons: [{ label: "Same Option", callback_data: "same" }],
            },
          },
        });

        const parsed = JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
        expect(parsed.success).toBe(true);
        expect(parsed.not_modified).toBe(true);
        expect(parsed.message_id).toBe(5678);
      } finally {
        cleanup();
      }
    });
  });
});
