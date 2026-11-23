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

describe("Reply Button Layout and Predefined Row (AC1, AC2)", () => {
  const allowFrom = 1111111111;

  function setupTest() {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-btn-layout-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: String(allowFrom),
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 3001 } }), { status: 200 });
    }) as typeof fetch;

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    });
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const cleanup = () => {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    };

    return { bot, broker, permRelay, mcp, emittedEvents, apiCalls, cleanup, config };
  }

  describe("AC1: Customisable caller button layout", () => {
    test("defect check: 8 caller buttons sent as a 2D array follow caller-chosen multi-row grid", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const eightButtons2D = [
          [
            { label: "Option 1", callback_data: "opt_1" },
            { label: "Option 2", callback_data: "opt_2" },
            { label: "Option 3", callback_data: "opt_3" },
            { label: "Option 4", callback_data: "opt_4" },
          ],
          [
            { label: "Option 5", callback_data: "opt_5" },
            { label: "Option 6", callback_data: "opt_6" },
            { label: "Option 7", callback_data: "opt_7" },
            { label: "Option 8", callback_data: "opt_8" },
          ],
        ];

        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: {
            name: "send_rich_message",
            arguments: {
              chat_id: allowFrom,
              markdown: "Please select an option from the grid:",
              buttons: eightButtons2D,
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(2);
        expect(kb[0].map((b: any) => b.text)).toEqual(["Option 1", "Option 2", "Option 3", "Option 4"]);
        expect(kb[1].map((b: any) => b.text)).toEqual(["Option 5", "Option 6", "Option 7", "Option 8"]);
      } finally {
        cleanup();
      }
    });

    test("defect check: 8 caller buttons with button_layout array [3, 3, 2] arrange into 3 rows", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const eightButtonsFlat = Array.from({ length: 8 }, (_, i) => ({
          label: `Skill ${i + 1}`,
          callback_data: `skill_${i + 1}`,
        }));

        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 2,
          method: "tools/call",
          params: {
            name: "send_rich_message",
            arguments: {
              chat_id: allowFrom,
              markdown: "Available skills:",
              buttons: eightButtonsFlat,
              button_layout: [3, 3, 2],
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(3);
        expect(kb[0].length).toBe(3);
        expect(kb[1].length).toBe(3);
        expect(kb[2].length).toBe(2);
        expect(kb[0].map((b: any) => b.text)).toEqual(["Skill 1", "Skill 2", "Skill 3"]);
        expect(kb[1].map((b: any) => b.text)).toEqual(["Skill 4", "Skill 5", "Skill 6"]);
        expect(kb[2].map((b: any) => b.text)).toEqual(["Skill 7", "Skill 8"]);
      } finally {
        cleanup();
      }
    });

    test("defect check: 8 caller buttons with buttons_per_row: 4 arrange into 2 rows of 4", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const eightButtonsFlat = Array.from({ length: 8 }, (_, i) => ({
          label: `Item ${i + 1}`,
          callback_data: `item_${i + 1}`,
        }));

        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: {
            name: "send_rich_message",
            arguments: {
              chat_id: allowFrom,
              markdown: "Choose an item:",
              buttons: eightButtonsFlat,
              buttons_per_row: 4,
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(2);
        expect(kb[0].length).toBe(4);
        expect(kb[1].length).toBe(4);
      } finally {
        cleanup();
      }
    });

    test("defect check: 8 caller buttons flat without layout parameters default to 1 button per row", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const eightButtonsFlat = Array.from({ length: 8 }, (_, i) => ({
          label: `Action ${i + 1}`,
          callback_data: `act_${i + 1}`,
        }));

        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 4,
          method: "tools/call",
          params: {
            name: "send_rich_message",
            arguments: {
              chat_id: allowFrom,
              markdown: "Vertical list:",
              buttons: eightButtonsFlat,
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(8);
        for (let i = 0; i < 8; i++) {
          expect(kb[i].length).toBe(1);
          expect(kb[i][0].text).toBe(`Action ${i + 1}`);
        }
      } finally {
        cleanup();
      }
    });
  });

  describe("AC3: Caller-supplied reply button tap acknowledgement (US-4)", () => {
    test("AC3: defect check: tapping caller-supplied reply button acknowledges callback, marks card, preserves Details button, and delivers event to session", async () => {
      const { bot, mcp, emittedEvents, apiCalls, cleanup } = setupTest();
      try {
        const messageText = "Please choose an action for the pending item:";
        await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 20,
          method: "tools/call",
          params: {
            name: "send_rich_message",
            arguments: {
              chat_id: allowFrom,
              markdown: messageText,
              buttons: [
                { label: "Run learn on example", callback_data: "laundry_learn" },
                { label: "Capture trace only", callback_data: "laundry_cap" },
              ],
            },
          },
        });

        const messageId = 3001;

        // Simulate tapping "Run learn on example"
        await (bot as any).handleUpdate({
          update_id: 601,
          callback_query: {
            id: "cb_caller_1",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: {
              message_id: messageId,
              date: Date.now(),
              chat: { id: allowFrom, type: "private" },
              text: messageText,
              reply_markup: {
                inline_keyboard: [
                  [{ text: "Run learn on example", callback_data: "laundry_learn" }],
                  [{ text: "Capture trace only", callback_data: "laundry_cap" }],
                  [{ text: "🔍 Details", web_app: { url: "https://example.com/app/index.html?d=d123" } }],
                ],
              },
            },
            data: "laundry_learn",
          },
        });

        // 1. Verify client acknowledgement
        const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
        expect(answerCall).toBeDefined();
        expect(answerCall?.body.callback_query_id).toBe("cb_caller_1");

        // 2. Verify card marked with chosen label
        const editCall = apiCalls.find((c) => c.method === "editMessageText");
        expect(editCall).toBeDefined();
        expect(editCall?.body.text).toContain("Selected: Run learn on example ✅");

        // 3. Verify caller buttons removed, but Details button preserved
        const remainingKb = editCall?.body.reply_markup?.inline_keyboard || [];
        const remainingFlat = remainingKb.flat();
        expect(remainingFlat.find((b: any) => b.callback_data === "laundry_learn")).toBeUndefined();
        expect(remainingFlat.find((b: any) => b.callback_data === "laundry_cap")).toBeUndefined();
        const preservedDetails = remainingFlat.find((b: any) => b.text === "🔍 Details");
        expect(preservedDetails).toBeDefined();
        expect(preservedDetails.web_app).toBeDefined();

        // 4. Verify tap still delivered to session
        expect(emittedEvents.length).toBe(1);
        const event = emittedEvents[0];
        expect(event.meta.event).toBe("button_tap");
        expect(event.meta.label).toBe("Run learn on example");
        expect(event.meta.payload).toBe("laundry_learn");
        expect(event.meta.target_message_id).toBe(String(messageId));
        expect(event.content).toBe("tapped Run learn on example");
      } finally {
        cleanup();
      }
    });

    test("AC3: defect check: tapping caller-supplied button on voice note message updates caption and acknowledges callback", async () => {
      const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-btn-"));
      const config = loadConfig({
        MINI_APP_URL: "https://ida.example.test",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: String(allowFrom),
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
        if (method === "editMessageText") {
          return new Response(
            JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: there is no text in the message to edit" }),
            { status: 400 }
          );
        }
        return new Response(JSON.stringify({ ok: true, result: { message_id: 3002 } }), { status: 200 });
      }) as typeof fetch;

      const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });

      try {
        const captionText = "Voice note transcript caption:";
        const messageId = 3002;

        await (bot as any).handleUpdate({
          update_id: 602,
          callback_query: {
            id: "cb_voice_btn_1",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: {
              message_id: messageId,
              date: Date.now(),
              chat: { id: allowFrom, type: "private" },
              caption: captionText,
              reply_markup: {
                inline_keyboard: [
                  [{ text: "Option A", callback_data: "opt_a" }],
                ],
              },
            },
            data: "opt_a",
          },
        });

        // Verify callback answered
        const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
        expect(answerCall).toBeDefined();

        // Verify editMessageCaption was called
        const captionCall = apiCalls.find((c) => c.method === "editMessageCaption");
        expect(captionCall).toBeDefined();
        expect(captionCall?.body.caption).toContain("Selected: Option A ✅");

        // Verify event delivered
        expect(emittedEvents.length).toBe(1);
        expect(emittedEvents[0].meta.event).toBe("button_tap");
        expect(emittedEvents[0].meta.label).toBe("Option A");
      } finally {
        globalThis.fetch = origFetch;
        rmSync(stateDir, { recursive: true, force: true });
      }
    });
  });

  describe("AC4: Universal callback acknowledgement across all button families (AC2)", () => {
    test("AC4: defect check: every callback-button family emitted by the plugin acknowledges callback query immediately", async () => {
      const { bot, broker, permRelay, apiCalls, cleanup } = setupTest();
      try {
        const messageId = 4001;

        // 1. Caller-supplied button
        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 701,
          callback_query: {
            id: "cb_family_caller",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "action:CustomAction",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_caller")).toBe(true);

        // 2. Predefined action buttons (logic_check, explain, reasons)
        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 702,
          callback_query: {
            id: "cb_family_lc",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "logic_check",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_lc")).toBe(true);

        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 703,
          callback_query: {
            id: "cb_family_explain",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "explain",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_explain")).toBe(true);

        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 704,
          callback_query: {
            id: "cb_family_reasons",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "reasons",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_reasons")).toBe(true);

        // 3. Recommendation buttons (accept_recommendation, decline_recommendation)
        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 705,
          callback_query: {
            id: "cb_family_accept",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "accept_recommendation",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_accept")).toBe(true);

        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 706,
          callback_query: {
            id: "cb_family_decline",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "decline_recommendation",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_decline")).toBe(true);

        // 4. Feedback buttons (fb:up, fb:down, fb:cancel, fb:critique)
        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 707,
          callback_query: {
            id: "cb_family_fb_up",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "fb:up",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_fb_up")).toBe(true);

        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 708,
          callback_query: {
            id: "cb_family_fb_down",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Prompt" },
            data: "fb:down",
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_fb_down")).toBe(true);

        // 5. Question buttons (pending question)
        const qResult = await broker.askUser({
          question: "Deploy now?",
          options: [{ label: "Yes" }, { label: "No" }],
          chatId: allowFrom,
        });
        const qid = qResult.questionId;

        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 709,
          callback_query: {
            id: "cb_family_q",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Question" },
            data: `q:${qid}:0:0`,
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_q")).toBe(true);

        // 6. Permission buttons
        const perm = permRelay.register("p123", "Bash", { command: "ls -la" }, () => {});
        apiCalls.length = 0;
        await (bot as any).handleUpdate({
          update_id: 710,
          callback_query: {
            id: "cb_family_perm",
            from: { id: allowFrom, is_bot: false, first_name: "Alex" },
            message: { message_id: messageId, chat: { id: allowFrom, type: "private" }, text: "Permission" },
            data: `perm:allow:${perm.id}`,
          },
        });
        expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.body.callback_query_id === "cb_family_perm")).toBe(true);
      } finally {
        cleanup();
      }
    });
  });

  describe("Advanced Telegram Bot API interactive options (copy_text, quote_rich_texts, message_effect_id)", () => {
    test("supports copy_text inline keyboard buttons, quote_rich_texts, and message_effect_id on send_rich_message", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 901,
          method: "tools/call",
          params: {
            name: "send_rich_message",
            arguments: {
              chat_id: allowFrom,
              markdown: "**Updated status** with ||spoiler|| and [docs](https://example.com)",
              reply_to_message_id: 42,
              quote_rich_texts: ["specific **quoted** part"],
              message_effect_id: "5104841245755180586",
              buttons: [
                { label: "📋 Copy cmd", copy_text: "bun test" },
                { label: "📋 Copy token", copy_text: { text: "tok_abc" } },
              ],
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);
        expect(apiCalls.length).toBe(1);

        const body = apiCalls[0].body;
        expect(body.message_effect_id).toBe("5104841245755180586");
        expect(body.reply_parameters).toEqual({
          message_id: 42,
          quote_rich_texts: ["specific **quoted** part"],
        });

        const kb = body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(2);
        expect(kb[0][0]).toEqual({ text: "📋 Copy cmd", copy_text: { text: "bun test" } });
        expect(kb[1][0]).toEqual({ text: "📋 Copy token", copy_text: { text: "tok_abc" } });
      } finally {
        cleanup();
      }
    });
  });
});
