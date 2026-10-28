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
  const allowFrom = 8860530746;

  function setupTest() {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-btn-layout-"));
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

    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 3001 } }), { status: 200 });
    }) as typeof fetch;

    const bot = new TelegramBotClient(config, broker, permRelay, () => {});
    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const cleanup = () => {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    };

    return { mcp, apiCalls, cleanup };
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
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Please select an option from the grid:",
              actions: false,
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
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Available skills:",
              actions: false,
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
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Choose an item:",
              actions: false,
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
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Vertical list:",
              actions: false,
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

  describe("AC2: Consolidated predefined buttons on the first row", () => {
    test("defect check: Details alone sits on the first row with predefined_row: true", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 5,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Short summary with deep detail.",
              detail: "# Deeper analysis\nDetailed content here.",
              actions: false,
              predefined_row: true,
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(1);
        expect(kb[0].length).toBe(1);
        expect(kb[0][0].text).toBe("🔍 Details");
        expect(kb[0][0].web_app).toBeDefined();
      } finally {
        cleanup();
      }
    });

    test("defect check: Details with Check logic and Explain all sit together on row 0 with predefined_row: true", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 6,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Summary text for chat.",
              detail: "Deep detail here.",
              actions: true,
              predefined_row: true,
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        expect(kb.length).toBe(1);
        expect(kb[0].length).toBe(5);
        expect(kb[0][0].text).toBe("🔍 Details");
        expect(kb[0][1].text).toBe("🧐 Check logic");
        expect(kb[0][2].text).toBe("💡 Explain");
        expect(kb[0][3].text).toBe("✅ Accept recommendation");
        expect(kb[0][4].text).toBe("❌ Decline recommendation");
      } finally {
        cleanup();
      }
    });

    test("defect check: predefined buttons sit on row 0 above caller's multi-row buttons with predefined_row: true", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const eightButtons2D = [
          [
            { label: "B1", callback_data: "b1" },
            { label: "B2", callback_data: "b2" },
            { label: "B3", callback_data: "b3" },
            { label: "B4", callback_data: "b4" },
          ],
          [
            { label: "B5", callback_data: "b5" },
            { label: "B6", callback_data: "b6" },
            { label: "B7", callback_data: "b7" },
            { label: "B8", callback_data: "b8" },
          ],
        ];

        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 7,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Grid with predefined row:",
              detail: "More details",
              actions: true,
              predefined_row: true,
              buttons: eightButtons2D,
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        // Row 0: Predefined row [Details, Check logic, Explain, Accept recommendation, Decline recommendation]
        // Row 1: Caller row 1 [B1, B2, B3, B4]
        // Row 2: Caller row 2 [B5, B6, B7, B8]
        expect(kb.length).toBe(3);
        expect(kb[0].map((b: any) => b.text)).toEqual([
          "🔍 Details",
          "🧐 Check logic",
          "💡 Explain",
          "✅ Accept recommendation",
          "❌ Decline recommendation",
        ]);
        expect(kb[1].map((b: any) => b.text)).toEqual(["B1", "B2", "B3", "B4"]);
        expect(kb[2].map((b: any) => b.text)).toEqual(["B5", "B6", "B7", "B8"]);
      } finally {
        cleanup();
      }
    });

    test("defect check: without predefined_row, Details and actions remain on separate rows below caller buttons", async () => {
      const { mcp, apiCalls, cleanup } = setupTest();
      try {
        const resp = await mcp.handleMessage({
          jsonrpc: "2.0",
          id: 8,
          method: "tools/call",
          params: {
            name: "reply",
            arguments: {
              chat_id: allowFrom,
              text: "Default layout without predefined_row:",
              detail: "More details",
              actions: true,
              buttons: [{ label: "Caller Button", callback_data: "caller_1" }],
            },
          },
        });

        const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
        expect(parsedResult.success).toBe(true);

        const kb = apiCalls[0].body.reply_markup?.inline_keyboard || [];
        // Default behaviour:
        // Row 0: Caller buttons ([Caller Button])
        // Row 1: Details ([🔍 Details])
        // Row 2: Actions ([🧐 Check logic, 💡 Explain, ✅ Accept recommendation, ❌ Decline recommendation])
        expect(kb.length).toBe(3);
        expect(kb[0].map((b: any) => b.text)).toEqual(["Caller Button"]);
        expect(kb[1].map((b: any) => b.text)).toEqual(["🔍 Details"]);
        expect(kb[2].map((b: any) => b.text)).toEqual([
          "🧐 Check logic",
          "💡 Explain",
          "✅ Accept recommendation",
          "❌ Decline recommendation",
        ]);
      } finally {
        cleanup();
      }
    });
  });
});
