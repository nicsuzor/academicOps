import { describe, expect, test } from "bun:test";
import { processReplyOverflow } from "../src/telegram/overflow.js";

describe("Progressive disclosure: Overflow handling", () => {
  test("short reply under max_chat_chars stays in chat with no overflow", () => {
    const text = "A concise update under budget.\nWith two paragraphs.";
    const result = processReplyOverflow({
      text,
      detail: undefined,
      maxChatChars: 1200,
    });

    expect(result.chatText).toBe(text);
    expect(result.hasOverflow).toBe(false);
    expect(result.combinedDetail).toBeUndefined();
    expect(result.hasDetailsButton).toBe(false);
  });

  test("reply with explicit detail adds Details button and keeps detail", () => {
    const text = "A concise headline and bullet.";
    const detail = "# Extensive Investigation Details\nFull log output...";
    const result = processReplyOverflow({
      text,
      detail,
      maxChatChars: 1200,
    });

    expect(result.chatText).toBe(text);
    expect(result.hasOverflow).toBe(false);
    expect(result.combinedDetail).toBe(detail);
    expect(result.hasDetailsButton).toBe(true);
  });

  test("overflow > max_chat_chars moves remaining text to Details without dropping a single character", () => {
    const p1 = "Paragraph 1: Summary of key events. " + "A".repeat(400);
    const p2 = "Paragraph 2: Additional context. " + "B".repeat(500);
    const p3 = "Paragraph 3: Deep methodology. " + "C".repeat(600);
    const fullText = `${p1}\n\n${p2}\n\n${p3}`;

    const result = processReplyOverflow({
      text: fullText,
      detail: undefined,
      maxChatChars: 600,
    });

    expect(result.hasOverflow).toBe(true);
    expect(result.hasDetailsButton).toBe(true);
    expect(result.chatText).toContain("… continued in Details");
    expect(result.chatText.startsWith(p1)).toBe(true);

    // Verify character-for-character fidelity of the overflow in combinedDetail
    expect(result.combinedDetail).toBeDefined();
    expect(result.combinedDetail?.startsWith(p2)).toBe(true);
    expect(result.combinedDetail).toContain(p3);
  });

  test("overflow prepends character-for-character to existing detail", () => {
    const p1 = "Short lead paragraph.";
    const p2 = "Heavy paragraph that exceeds the budget: " + "X".repeat(1100);
    const existingDetail = "## Existing Deep Detail\nOriginal content";

    const result = processReplyOverflow({
      text: `${p1}\n\n${p2}`,
      detail: existingDetail,
      maxChatChars: 500,
    });

    expect(result.hasOverflow).toBe(true);
    expect(result.hasDetailsButton).toBe(true);
    expect(result.combinedDetail).toContain(p2);
    expect(result.combinedDetail).toContain(existingDetail);
  });

  test("FR-1.3: a reply sent with detail carries a 🔍 Details button whose link opens that detailsId even when MINI_APP_URL is unset", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-details-btn-"));
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 1973 } }), { status: 200 });
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
            text: "**Headline:** Summary in chat.\n\n>! Collapsible note. Tap Details for specs and sources.",
            detail: "## Q1 Specs\n\n- Detailed specification and source links.",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.messageId).toBe(1973);
      expect(parsedResult.detailsId).toMatch(/^d_[a-f0-9]+$/);

      expect(apiCalls.length).toBe(1);
      expect(apiCalls[0].method).toBe("sendMessage");

      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍 Details");
      expect(detailsButton).toBeDefined();
      expect(detailsButton?.web_app?.url).toMatch(/^https:\/\/.+\/app\/index\.html\?d=/);
      expect(detailsButton?.web_app?.url).toContain(`/app/index.html?d=${parsedResult.detailsId}`);

      const stored = store.getDetails(parsedResult.detailsId);
      expect(stored?.markdown).toBe("## Q1 Specs\n\n- Detailed specification and source links.");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("FR-1.3 & §6.6: loadConfig reads stateDir .env and IDA_WEB_URL for the 🔍 Details button link", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync, writeFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-details-env-"));
    writeFileSync(join(stateDir, ".env"), 'IDA_WEB_URL="https://ida.example.ts.net/"\n', "utf-8");

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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 1974 } }), { status: 200 });
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
            text: "Summary with configured IDA_WEB_URL.",
            detail: "Full details markdown.",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍 Details");
      expect(detailsButton).toBeDefined();
      expect(detailsButton?.web_app?.url).toBe(`https://ida.example.ts.net/app/index.html?d=${parsedResult.detailsId}`);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("FR-1.3: a reply without detail carries no 🔍 Details button", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-no-details-"));
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
      return new Response(JSON.stringify({ ok: true, result: { message_id: 1975 } }), { status: 200 });
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
            text: "**Short reply:** No detail attached and under maxChatChars.",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.messageId).toBe(1975);
      expect(parsedResult.detailsId).toBeUndefined();

      expect(apiCalls.length).toBe(1);
      expect(apiCalls[0].method).toBe("sendMessage");

      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍 Details");
      expect(detailsButton).toBeUndefined();
      expect(flatButtons).toEqual([]);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });
});

