import { describe, test, expect } from "bun:test";
import { loadConfig } from "../src/config.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Message Actions: Logic Check and Explain Buttons (AC1, AC2)", () => {
  const allowFrom = [8860530746];

  test("reply attaches [🧐 Check logic] and [💡 Explain] buttons by default", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-actions-def-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
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
            text: "**Key finding:** The database migration completed with 0 errors.",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.messageId).toBe(2001);

      expect(apiCalls.length).toBe(1);
      expect(apiCalls[0].method).toBe("sendMessage");

      const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
      const flatButtons = kb.flat();
      const logicCheckBtn = flatButtons.find((b: any) => b.text === "🧐 Check logic");
      const explainBtn = flatButtons.find((b: any) => b.text === "💡 Explain");

      expect(logicCheckBtn).toBeDefined();
      expect(logicCheckBtn.callback_data).toBe("logic_check");
      expect(explainBtn).toBeDefined();
      expect(explainBtn.callback_data).toBe("explain");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("reply with actions: false suppresses action buttons", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-actions-off-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2002 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "System notification without action buttons.",
            actions: false,
          },
        },
      });

      expect(apiCalls.length).toBe(1);
      const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
      expect(kb.flat()).toEqual([]);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("AC1: pressing logic-check button delivers request naming message and Ida replies with premise-check verdict", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ac1-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2003 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Ida sends a message with conclusions
      const messageText = "**Conclusion:** Migrating the schema now will eliminate duplicate records.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 10,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: messageText,
          },
        },
      });

      // 2. User presses the logic-check button on that message (message_id: 2003)
      await (bot as any).handleUpdate({
        update_id: 501,
        callback_query: {
          id: "cb_lc_1",
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          message: {
            message_id: 2003,
            date: Date.now(),
            chat: { id: 8860530746, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [[{ text: "🧐 Check logic", callback_data: "logic_check" }, { text: "💡 Explain", callback_data: "explain" }]],
            },
          },
          data: "logic_check",
        },
      });

      // 3. Verify channel event delivered to session naming that message
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("logic_check");
      expect(event.meta.target_message_id).toBe("2003");
      expect(event.meta.target_excerpt).toContain("Migrating the schema now");
      expect(event.content).toContain("2003");
      expect(event.content).toContain("logic check");
      expect(event.content).toContain("receiving it from a peer");

      // Verify button tap answered and message edited
      const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
      expect(answerCall).toBeDefined();

      const editCall = apiCalls.find((c) => c.method === "editMessageText");
      expect(editCall).toBeDefined();
      expect(editCall?.body.text).toContain("Selected: 🧐 Check logic ✅");

      // 4. Ida's reply is a premise-check verdict with its reason
      const verdictText = [
        "**Verdict: PASS**",
        "",
        ">! **Premise Check:**",
        "> Judged: Conclusion follows from deduplication premise",
        "> Valid: Passes deductive inference",
        "> Supported: Supported by migration dry-run output",
        "> Answered: Answers ask on deduplication effectiveness",
        "> Sufficient: No unbacked high-stakes warrants",
        "> Waived: None",
        "> Relay: Verified for upstream reporting",
      ].join("\n");

      const verdictResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 11,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: verdictText,
            reply_to: 2003,
          },
        },
      });

      const parsedVerdict = JSON.parse((verdictResp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedVerdict.success).toBe(true);

      const lastSendMessage = apiCalls.filter((c) => c.method === "sendMessage").pop();
      expect(lastSendMessage?.body.text).toContain("Verdict: PASS");
      expect(lastSendMessage?.body.text).toContain("Judged");
      expect(lastSendMessage?.body.text).toContain("Supported");
      expect(lastSendMessage?.body.reply_parameters?.message_id).toBe(2003);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("AC2: pressing explain button delivers request naming message and Ida replies expanding that message", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ac2-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "8860530746",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2004 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Ida sends a message
      const messageText = "**Policy:** We defer non-critical dependencies to stage 2.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 20,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: messageText,
          },
        },
      });

      // 2. User presses the explain button on message 2004
      await (bot as any).handleUpdate({
        update_id: 502,
        callback_query: {
          id: "cb_exp_1",
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          message: {
            message_id: 2004,
            date: Date.now(),
            chat: { id: 8860530746, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [[{ text: "🧐 Check logic", callback_data: "logic_check" }, { text: "💡 Explain", callback_data: "explain" }]],
            },
          },
          data: "explain",
        },
      });

      // 3. Verify channel event delivered to session naming that message
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("explain");
      expect(event.meta.target_message_id).toBe("2004");
      expect(event.meta.target_excerpt).toContain("We defer non-critical dependencies");
      expect(event.content).toContain("2004");
      expect(event.content).toContain("explain");
      expect(event.content).toContain("in more detail");

      // 4. Ida's reply expands that message
      const explanationText = [
        "**Detailed Explanation:**",
        "",
        "Deferring non-critical dependencies protects the current delivery deadline by:",
        "1. Keeping the immediate execution graph acyclic and small.",
        "2. Preventing speculative work from compounding review load.",
        "3. Allowing empirical feedback from stage 1 to reshape stage 2 requirements.",
      ].join("\n");

      const explainResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 21,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: explanationText,
            reply_to: 2004,
          },
        },
      });

      const parsedExplain = JSON.parse((explainResp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedExplain.success).toBe(true);

      const lastSendMessage = apiCalls.filter((c) => c.method === "sendMessage").pop();
      expect(lastSendMessage?.body.text).toContain("Detailed Explanation");
      expect(lastSendMessage?.body.text).toContain("Deferring non-critical dependencies");
      expect(lastSendMessage?.body.reply_parameters?.message_id).toBe(2004);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("parseInboundUpdate parses logic_check and explain callback queries", () => {
    const updateLogicCheck: TelegramUpdate = {
      update_id: 503,
      callback_query: {
        id: "cb_lc_2",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 3001,
          date: Date.now(),
          chat: { id: 8860530746, type: "private" },
          text: "Here is statement A.",
        },
        data: "logic_check",
      },
    };

    const resultLc = parseInboundUpdate(updateLogicCheck, allowFrom);
    expect(resultLc).not.toBeNull();
    expect(resultLc?.event).toBe("logic_check");
    expect(resultLc?.meta.target_message_id).toBe("3001");
    expect(resultLc?.meta.target_excerpt).toBe("Here is statement A.");
    expect(resultLc?.content).toContain("3001");
    expect(resultLc?.content).toContain("logic check");

    const updateExplain: TelegramUpdate = {
      update_id: 504,
      callback_query: {
        id: "cb_exp_2",
        from: { id: 8860530746, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 3002,
          date: Date.now(),
          chat: { id: 8860530746, type: "private" },
          text: "Here is statement B.",
        },
        data: "explain",
      },
    };

    const resultExp = parseInboundUpdate(updateExplain, allowFrom);
    expect(resultExp).not.toBeNull();
    expect(resultExp?.event).toBe("explain");
    expect(resultExp?.meta.target_message_id).toBe("3002");
    expect(resultExp?.meta.target_excerpt).toBe("Here is statement B.");
    expect(resultExp?.content).toContain("3002");
    expect(resultExp?.content).toContain("explain");
  });
});
