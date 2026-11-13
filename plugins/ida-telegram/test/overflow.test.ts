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

  test("FR-1.3: a reply sent with detail carries a 🔍 Details button whose link opens that detailsId under the configured MINI_APP_URL", async () => {
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
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
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
            chat_id: 1111111111,
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
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍");
      expect(detailsButton).toBeDefined();
      expect(detailsButton?.web_app?.url).toMatch(/^https:\/\/.+\/app\/index\.html\?d=/);
      expect(detailsButton?.web_app?.url).toContain(`/app/index.html?d=${parsedResult.detailsId}`);

      const stored = store.getDetails(parsedResult.detailsId);
      expect(stored?.markdown).toBe("## Q1 Specs\n\n- Detailed specification and source links.");

      // FR-1.3 & acceptance: Details page is fetchable over HTTP without authentication
      const { startWebServer } = await import("../src/web/server.js");
      const appDir = join(import.meta.dir, "..", "app");
      const webContext: any = {
        store,
        broker,
        permRelay,
        config,
        sessionSecret: "test-secret-key-32-characters!!",
      };
      const server = startWebServer(webContext, appDir);
      try {
        const detailsRes = await origFetch(`http://127.0.0.1:${server.port}/api/app/details/${parsedResult.detailsId}`);
        expect(detailsRes.status).toBe(200);
        const detailsJson: any = await detailsRes.json();
        expect(detailsJson.markdown).toBe("## Q1 Specs\n\n- Detailed specification and source links.");
      } finally {
        server.stop();
      }
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
      ALLOWED_USER_IDS: "1111111111",
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
            chat_id: 1111111111,
            text: "Summary with configured IDA_WEB_URL.",
            detail: "Full details markdown.",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍");
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
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
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
            chat_id: 1111111111,
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
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍 Details" || b.text === "🔍");
      expect(detailsButton).toBeUndefined();
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("Regression: reply with detail (and details alias) attaches instance-scoped Details link that app.js resolves and renders in-app", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { startWebServer } = await import("../src/web/server.js");
    const { mkdtempSync, rmSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");
    const vm = await import("node:vm");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-details-e2e-"));
    const config = loadConfig({
      MINI_APP_URL: "https://dash.example.test",
      IDA_NAME: "prime",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
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

      // 1. Verify reply with `detail` (and `details` alias) stores Details and attaches instance-scoped button
      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 10,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 1111111111,
            text: "**Headline:** Summary in chat.",
            detail: "## Deep Audit Trail\n\n- Point alpha\n- Point beta",
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.detailsId).toMatch(/^d_[a-f0-9]+$/);

      const aliasResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 101,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 1111111111,
            text: "**Headline:** Summary with details alias.",
            details: "## Alias Detail Content\n\n- Item one",
          },
        },
      });
      const aliasResult = JSON.parse((aliasResp?.result as any)?.content?.[0]?.text || "{}");
      expect(aliasResult.detailsId).toMatch(/^d_[a-f0-9]+$/);
      expect(store.getDetails(aliasResult.detailsId)?.markdown).toBe("## Alias Detail Content\n\n- Item one");

      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍");
      expect(detailsButton).toBeDefined();
      const buttonUrl = new URL(detailsButton.web_app.url);
      expect(buttonUrl.origin + buttonUrl.pathname).toBe("https://dash.example.test/app/index.html");
      expect(buttonUrl.searchParams.get("instance")).toBe("prime");
      expect(buttonUrl.searchParams.get("d")).toBe(parsedResult.detailsId);

      // 2. Start web server and verify both /api/app/instances/:instance/details/:id and /api/app/details/:id resolve
      const appDir = join(import.meta.dir, "..", "app");
      const server = startWebServer(
        {
          store,
          broker,
          permRelay,
          config,
          sessionSecret: "test-secret-key-32-characters!!",
          emitChannelEvent: () => {},
        },
        appDir
      );

      try {
        const instanceRes = await origFetch(
          `http://127.0.0.1:${server.port}/api/app/instances/prime/details/${parsedResult.detailsId}`
        );
        expect(instanceRes.status).toBe(200);
        const instanceJson: any = await instanceRes.json();
        expect(instanceJson.markdown).toBe("## Deep Audit Trail\n\n- Point alpha\n- Point beta");

        // 3. Execute app/app.js against the button's query string (?instance=prime&d=<detailsId>)
        const elements: Record<string, any> = {
          "details-content": { innerHTML: "Loading details...", textContent: "", style: {}, classList: { add() {}, remove() {} } },
          "view-details": { classList: { add() {}, remove() {} } },
          "view-questions": { classList: { add() {}, remove() {} } },
          "view-review": { classList: { add() {}, remove() {} } },
          "view-anchor": { classList: { add() {}, remove() {} } },
        };
        const fetchedUrls: string[] = [];
        const sandboxFetch = async (relUrl: string, init?: RequestInit) => {
          fetchedUrls.push(relUrl);
          const resolved = new URL(relUrl, `http://127.0.0.1:${server.port}/app/index.html`);
          return origFetch(resolved.toString(), init);
        };

        const appJsCode = readFileSync(join(appDir, "app.js"), "utf-8");
        const sandbox: Record<string, any> = {
          URLSearchParams,
          Date,
          Math,
          Number,
          String,
          Boolean,
          Array,
          Object,
          JSON,
          RegExp,
          Error,
          encodeURIComponent,
          decodeURIComponent,
          console,
          fetch: sandboxFetch,
          window: {
            location: { search: buttonUrl.search },
            Telegram: { WebApp: { expand() {}, initData: "" } },
          },
          document: {
            querySelectorAll: () => [],
            querySelector: () => ({ classList: { add() {}, remove() {} } }),
            getElementById: (id: string) =>
              elements[id] || {
                innerHTML: "",
                textContent: "",
                style: {},
                classList: { add() {}, remove() {} },
                addEventListener() {},
              },
          },
        };
        sandbox.window.window = sandbox.window;
        vm.runInNewContext(appJsCode, sandbox);

        // Wait for async init() -> loadDetails() to settle
        await new Promise((r) => setTimeout(r, 50));

        expect(fetchedUrls.some((u) => u.includes("instance=prime") || u.includes("/instances/prime/details/"))).toBe(true);
        expect(elements["details-content"].innerHTML).toContain("<h2>Deep Audit Trail</h2>");
        expect(elements["details-content"].innerHTML).toContain("<li>Point alpha</li>");
      } finally {
        server.stop();
      }
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("Regression: ask_user with detail stores Details page and attaches instance-scoped 🔍 Details button", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ask-details-"));
    const config = loadConfig({
      MINI_APP_URL: "https://dash.example.test",
      IDA_NAME: "prime",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
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
        id: 11,
        method: "tools/call",
        params: {
          name: "ask_user",
          arguments: {
            chat_id: 1111111111,
            questions: [
              {
                header: "Architecture",
                question: "Which transport should we adopt?",
                detail: "## Transport Trade-offs\n\nFull comparison table and benchmarks.",
                options: [{ label: "Option A" }, { label: "Option B" }],
              },
            ],
          },
        },
      });

      expect(apiCalls.length).toBe(1);
      const flatButtons = (apiCalls[0].body.reply_markup?.inline_keyboard || []).flat();
      const detailsButton = flatButtons.find((b: any) => b.text === "🔍 Details");
      expect(detailsButton).toBeDefined();

      const btnUrl = new URL(detailsButton.web_app.url);
      expect(btnUrl.searchParams.get("instance")).toBe("prime");
      const dParam = btnUrl.searchParams.get("d");
      expect(dParam).toMatch(/^d_[a-f0-9]+$/);

      const stored = store.getDetails(dParam!);
      expect(stored?.markdown).toBe("## Transport Trade-offs\n\nFull comparison table and benchmarks.");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });
});

