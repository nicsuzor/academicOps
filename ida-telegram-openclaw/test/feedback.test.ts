import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { rmSync, existsSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadConfig } from "../src/config.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";

describe("Feedback: vote buttons default and opt-in", () => {
  let testStateDir: string;

  beforeEach(() => {
    testStateDir = mkdtempSync(join(tmpdir(), "ida-telegram-fb-test-"));
  });

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  test("a reply call with no feedback argument sends a message with no vote buttons", async () => {
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: testStateDir,
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2001 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**Default feedback test**: No feedback arg specified.",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);

      expect(apiCalls.length).toBe(1);
      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      expect(flatButtons.some((b: any) => b.callback_data === "fb:up" || b.callback_data === "fb:down")).toBe(false);
      expect(flatButtons.some((b: any) => b.text === "👍" || b.text === "👎")).toBe(false);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("feedback: true still attaches the buttons", async () => {
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: testStateDir,
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2002 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**Opt-in feedback test**: feedback true specified.",
            feedback: true,
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);

      expect(apiCalls.length).toBe(1);
      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      expect(flatButtons.some((b: any) => b.text === "👍" && b.callback_data === "fb:up")).toBe(true);
      expect(flatButtons.some((b: any) => b.text === "👎" && b.callback_data === "fb:down")).toBe(true);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("feedback: false does not attach vote buttons", async () => {
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: testStateDir,
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2003 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 3,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**Explicit false feedback test**.",
            feedback: false,
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);

      expect(apiCalls.length).toBe(1);
      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      expect(flatButtons.some((b: any) => b.callback_data === "fb:up" || b.callback_data === "fb:down")).toBe(false);
      expect(flatButtons.some((b: any) => b.text === "👍" || b.text === "👎")).toBe(false);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("upvote callback records to trace and updates button", async () => {
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: testStateDir,
      VOICE_REPLIES: "off",
    });

    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; payload: any }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, () => {});
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    const initialKeyboard = [
      [{ text: "👍", callback_data: "fb:up" }, { text: "👎", callback_data: "fb:down" }],
    ];

    await (bot as any).handleUpdate({
      update_id: 101,
      callback_query: {
        id: "cb_up_1",
        from: { id: 8860530746, is_bot: false, first_name: "User" },
        message: {
          message_id: 501,
          date: 1700000000,
          chat: { id: 8860530746, type: "private" },
          text: "A brief message",
          reply_markup: { inline_keyboard: initialKeyboard },
        },
        data: "fb:up",
      },
    });

    const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
    expect(answerCall).toBeDefined();
    expect(answerCall?.payload.text).toBe("Noted 👍");

    const editCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(editCall).toBeDefined();
    expect(editCall?.payload.reply_markup.inline_keyboard).toEqual([
      [{ text: "👍 saved", callback_data: "noop" }],
    ]);
  });

  test("downvote callback opens critique keyboard and selecting critique emits channel event", async () => {
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: testStateDir,
      VOICE_REPLIES: "off",
    });

    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; payload: any }> = [];
    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    const initialKeyboard = [
      [{ text: "👍", callback_data: "fb:up" }, { text: "👎", callback_data: "fb:down" }],
    ];

    // 1. Tap fb:down
    await (bot as any).handleUpdate({
      update_id: 102,
      callback_query: {
        id: "cb_down_1",
        from: { id: 8860530746, is_bot: false, first_name: "User" },
        message: {
          message_id: 502,
          date: 1700000010,
          chat: { id: 8860530746, type: "private" },
          text: "A verbose reply card",
          reply_markup: { inline_keyboard: initialKeyboard },
        },
        data: "fb:down",
      },
    });

    const downEditCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(downEditCall).toBeDefined();
    const downKeyboard = downEditCall?.payload.reply_markup.inline_keyboard as Array<Array<Record<string, unknown>>>;
    const downFlat = downKeyboard.flat();
    expect(downFlat.some((b) => b.text === "💨 Too verbose" && b.callback_data === "fb:critique:502:Too verbose")).toBe(true);
    expect(downFlat.some((b) => b.text === "↩ Cancel" && b.callback_data === "fb:cancel:502")).toBe(true);

    apiCalls.length = 0;

    // 2. Select critique
    await (bot as any).handleUpdate({
      update_id: 103,
      callback_query: {
        id: "cb_critique_1",
        from: { id: 8860530746, is_bot: false, first_name: "User" },
        message: {
          message_id: 502,
          date: 1700000010,
          chat: { id: 8860530746, type: "private" },
          text: "A verbose reply card",
          reply_markup: { inline_keyboard: downKeyboard },
        },
        data: "fb:critique:502:Too verbose",
      },
    });

    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].meta.event).toBe("feedback_down");
    expect(emittedEvents[0].meta.critique).toBe("Too verbose");
  });

  test("unauthorized user attempting feedback callback is rejected with Unauthorized and no state changes", async () => {
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: testStateDir,
      VOICE_REPLIES: "off",
    });

    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; payload: any }> = [];
    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: true };
    };

    const initialKeyboard = [
      [{ text: "👍", callback_data: "fb:up" }, { text: "👎", callback_data: "fb:down" }],
    ];

    await (bot as any).handleUpdate({
      update_id: 104,
      callback_query: {
        id: "cb_unauth_1",
        from: { id: 9999999999, is_bot: false, first_name: "UnauthorizedUser" },
        message: {
          message_id: 503,
          date: 1700000020,
          chat: { id: 9999999999, type: "private" },
          text: "A message",
          reply_markup: { inline_keyboard: initialKeyboard },
        },
        data: "fb:up",
      },
    });

    const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
    expect(answerCall).toBeDefined();
    expect(answerCall?.payload.text).toBe("Unauthorized.");

    const editCall = apiCalls.find((c) => c.method === "editMessageReplyMarkup");
    expect(editCall).toBeUndefined();
    expect(emittedEvents.length).toBe(0);
  });
});
