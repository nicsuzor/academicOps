import { describe, test, expect } from "bun:test";
import { loadConfig } from "../src/config.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Message Actions: Recommendation Buttons (AC1, AC2)", () => {
  const allowFrom = 8860530746;

  function setupTest() {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-rec-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: String(allowFrom),
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 3001 } }), { status: 200 });
    }) as typeof fetch;

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const cleanup = () => {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    };

    return { bot, mcp, emittedEvents, apiCalls, cleanup };
  }

  test("AC1: defect check: reply attaches accept-recommendation and decline-recommendation buttons by default", async () => {
    const { mcp, apiCalls, cleanup } = setupTest();
    try {
      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: allowFrom,
            text: "**Recommendation:** Deploy migration 0042 to production.",
          },
        },
      });

      const parsed = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsed.success).toBe(true);

      expect(apiCalls.length).toBe(1);
      expect(apiCalls[0].method).toBe("sendMessage");

      const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
      const flatButtons = kb.flat();

      const acceptBtn = flatButtons.find((b: any) =>
        b.callback_data === "accept_recommendation" || b.text.includes("Accept recommendation")
      );
      const declineBtn = flatButtons.find((b: any) =>
        b.callback_data === "decline_recommendation" || b.text.includes("Decline recommendation")
      );

      expect(acceptBtn).toBeDefined();
      expect(acceptBtn.callback_data).toBe("accept_recommendation");
      expect(acceptBtn.text).toContain("Accept recommendation");

      expect(declineBtn).toBeDefined();
      expect(declineBtn.callback_data).toBe("decline_recommendation");
      expect(declineBtn.text).toContain("Decline recommendation");
    } finally {
      cleanup();
    }
  });

  test("AC1: defect check: actions: false suppresses recommendation buttons along with existing default buttons", async () => {
    const { mcp, apiCalls, cleanup } = setupTest();
    try {
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: allowFrom,
            text: "Informational message without action buttons.",
            actions: false,
          },
        },
      });

      expect(apiCalls.length).toBe(1);
      const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
      const flatButtons = kb.flat();
      expect(flatButtons.find((b: any) => b.callback_data === "accept_recommendation")).toBeUndefined();
      expect(flatButtons.find((b: any) => b.callback_data === "decline_recommendation")).toBeUndefined();
      expect(flatButtons.find((b: any) => b.callback_data === "logic_check")).toBeUndefined();
      expect(flatButtons.find((b: any) => b.callback_data === "explain")).toBeUndefined();
    } finally {
      cleanup();
    }
  });

  test("AC1: defect check: predefined_row: true consolidates recommendation buttons onto row 0 with Details and action buttons", async () => {
    const { mcp, apiCalls, cleanup } = setupTest();
    try {
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 3,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: allowFrom,
            text: "**Recommendation:** Apply configuration update.",
            detail: "Extended detail payload.",
            predefined_row: true,
            buttons: [{ label: "Custom 1", callback_data: "c1" }],
          },
        },
      });

      expect(apiCalls.length).toBe(1);
      const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
      expect(kb.length).toBeGreaterThanOrEqual(2);

      const firstRow = kb[0];
      const detailsBtn = firstRow.find((b: any) => b.text === "🔍 Details");
      const logicCheckBtn = firstRow.find((b: any) => b.callback_data === "logic_check");
      const explainBtn = firstRow.find((b: any) => b.callback_data === "explain");
      const acceptBtn = firstRow.find((b: any) => b.callback_data === "accept_recommendation");
      const declineBtn = firstRow.find((b: any) => b.callback_data === "decline_recommendation");

      expect(detailsBtn).toBeDefined();
      expect(logicCheckBtn).toBeDefined();
      expect(explainBtn).toBeDefined();
      expect(acceptBtn).toBeDefined();
      expect(declineBtn).toBeDefined();

      const callerRow = kb[1];
      expect(callerRow.map((b: any) => b.text)).toEqual(["Custom 1"]);
    } finally {
      cleanup();
    }
  });

  test("AC2: defect check: tapping accept recommendation marks card and delivers event naming message and acceptance", async () => {
    const { bot, mcp, emittedEvents, apiCalls, cleanup } = setupTest();
    try {
      const messageText = "**Recommendation:** Proceed with deployment plan.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 4,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: allowFrom,
            text: messageText,
            detail: "Plan details",
          },
        },
      });

      const messageId = 3001;

      // Simulate tapping accept recommendation
      await (bot as any).handleUpdate({
        update_id: 101,
        callback_query: {
          id: "cb_acc_1",
          from: { id: allowFrom, is_bot: false, first_name: "Nic" },
          message: {
            message_id: messageId,
            date: Date.now(),
            chat: { id: allowFrom, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [
                [
                  { text: "🔍 Details", web_app: { url: "https://example.com" } },
                  { text: "🧐 Check logic", callback_data: "logic_check" },
                  { text: "💡 Explain", callback_data: "explain" },
                  { text: "✅ Accept recommendation", callback_data: "accept_recommendation" },
                  { text: "❌ Decline recommendation", callback_data: "decline_recommendation" },
                ],
              ],
            },
          },
          data: "accept_recommendation",
        },
      });

      // 1. Verify card marked with choice
      const editCall = apiCalls.find((c) => c.method === "editMessageText");
      expect(editCall).toBeDefined();
      expect(editCall?.body.text).toContain("Selected: ");
      expect(editCall?.body.text).toContain("Accept recommendation");

      // Verify recommendation buttons removed, other buttons (Details, Check logic, Explain) preserved
      const remainingKb = editCall?.body.reply_markup?.inline_keyboard || [];
      const remainingFlat = remainingKb.flat();
      expect(remainingFlat.find((b: any) => b.callback_data === "accept_recommendation")).toBeUndefined();
      expect(remainingFlat.find((b: any) => b.callback_data === "decline_recommendation")).toBeUndefined();
      expect(remainingFlat.find((b: any) => b.text === "🔍 Details")).toBeDefined();
      expect(remainingFlat.find((b: any) => b.callback_data === "logic_check")).toBeDefined();
      expect(remainingFlat.find((b: any) => b.callback_data === "explain")).toBeDefined();

      // 2. Verify channel event delivered to Ida naming message and acceptance
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("accept_recommendation");
      expect(event.meta.target_message_id).toBe(String(messageId));
      expect(event.content).toContain(String(messageId));
      expect(event.content).toMatch(/Nic accepted (the )?recommendation/i);
    } finally {
      cleanup();
    }
  });

  test("AC2: defect check: tapping decline recommendation marks card and delivers event naming message and declination", async () => {
    const { bot, mcp, emittedEvents, apiCalls, cleanup } = setupTest();
    try {
      const messageText = "**Recommendation:** Revert transaction immediately.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 5,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: allowFrom,
            text: messageText,
            detail: "Transaction trace",
          },
        },
      });

      const messageId = 3001;

      // Simulate tapping decline recommendation
      await (bot as any).handleUpdate({
        update_id: 102,
        callback_query: {
          id: "cb_dec_1",
          from: { id: allowFrom, is_bot: false, first_name: "Nic" },
          message: {
            message_id: messageId,
            date: Date.now(),
            chat: { id: allowFrom, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [
                [
                  { text: "🔍 Details", web_app: { url: "https://example.com" } },
                  { text: "🧐 Check logic", callback_data: "logic_check" },
                  { text: "💡 Explain", callback_data: "explain" },
                  { text: "✅ Accept recommendation", callback_data: "accept_recommendation" },
                  { text: "❌ Decline recommendation", callback_data: "decline_recommendation" },
                ],
              ],
            },
          },
          data: "decline_recommendation",
        },
      });

      // 1. Verify card marked with choice
      const editCall = apiCalls.find((c) => c.method === "editMessageText");
      expect(editCall).toBeDefined();
      expect(editCall?.body.text).toContain("Selected: ");
      expect(editCall?.body.text).toContain("Decline recommendation");

      // Verify recommendation buttons removed, other buttons preserved
      const remainingKb = editCall?.body.reply_markup?.inline_keyboard || [];
      const remainingFlat = remainingKb.flat();
      expect(remainingFlat.find((b: any) => b.callback_data === "accept_recommendation")).toBeUndefined();
      expect(remainingFlat.find((b: any) => b.callback_data === "decline_recommendation")).toBeUndefined();
      expect(remainingFlat.find((b: any) => b.text === "🔍 Details")).toBeDefined();
      expect(remainingFlat.find((b: any) => b.callback_data === "logic_check")).toBeDefined();
      expect(remainingFlat.find((b: any) => b.callback_data === "explain")).toBeDefined();

      // 2. Verify channel event delivered to Ida naming message and declination
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("decline_recommendation");
      expect(event.meta.target_message_id).toBe(String(messageId));
      expect(event.content).toContain(String(messageId));
      expect(event.content).toMatch(/Nic declined (the )?recommendation/i);
    } finally {
      cleanup();
    }
  });
});
