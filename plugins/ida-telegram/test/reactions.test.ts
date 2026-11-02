import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { normalizeReaction } from "../src/telegram/format.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { PluginConfig } from "../src/config.js";
import { PluginStore } from "../src/store.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mkdtempSync, rmSync } from "node:fs";

describe("Telegram Reactions & Shared Legend (specs/telegram/reactions.md)", () => {
  let tempDir: string;
  let config: PluginConfig;
  let origFetch: typeof globalThis.fetch;
  let apiCalls: Array<{ url: string; method: string; body?: any }> = [];
  let apiResponses: Map<string, any> = new Map();

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), "ida-tg-reaction-test-"));
    config = {
      botToken: "test-token",
      allowFrom: [12345],
      pairingSecret: "secret",
      pollIntervalSec: 1,
      idleTimeoutSec: 3600,
      stateDir: tempDir,
      maxChatChars: 4096,
      voiceReplies: "never",
      isPrimary: true,
      apiBaseUrl: "https://api.telegram.test",
    };
    apiCalls = [];
    apiResponses.clear();
    origFetch = globalThis.fetch;

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr = String(input);
      let body: any;
      if (init?.body && typeof init.body === "string") {
        try {
          body = JSON.parse(init.body);
        } catch {
          body = init.body;
        }
      }
      apiCalls.push({ url: urlStr, method: init?.method || "GET", body });

      const methodName = urlStr.split("/").pop();
      if (methodName && apiResponses.has(methodName)) {
        return new Response(JSON.stringify(apiResponses.get(methodName)), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify({ ok: true, result: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }) as any;
  });

  afterEach(() => {
    globalThis.fetch = origFetch;
    try {
      rmSync(tempDir, { recursive: true, force: true });
    } catch {}
  });

  test("BC-2: Normalization & Single-Grapheme Validation accepts arbitrary valid single emojis and strips VS16", () => {
    // Strips VS16 variation selector
    expect(normalizeReaction("✍️")).toBe("✍");
    // Maps canonical equivalent
    expect(normalizeReaction("❤️")).toBe("❤");
    // Trims whitespace
    expect(normalizeReaction("  👍  ")).toBe("👍");
    // Accepts arbitrary valid single emojis without static allowlist restriction
    expect(normalizeReaction("🚀")).toBe("🚀");
    expect(normalizeReaction("🐱")).toBe("🐱");
    expect(normalizeReaction("🕊")).toBe("🕊");
    expect(normalizeReaction("🎉")).toBe("🎉");

    // Rejects multi-emoji strings upfront
    expect(normalizeReaction("💩🦄")).toBeNull();
    // Rejects non-emoji text
    expect(normalizeReaction("hello")).toBeNull();
    expect(normalizeReaction("a")).toBeNull();
    expect(normalizeReaction("1")).toBeNull();
    expect(normalizeReaction("")).toBeNull();
  });

  test("BC-3: Authoritative Error Propagation surfaces Telegram API errors verbatim to react tool", async () => {
    const store = new PluginStore(tempDir);
    const broker = new QuestionBroker(tempDir);
    const permRelay = new PermissionRelay();
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    const server = new StdioMcpServer(config, store, broker, bot, permRelay);

    // Mock Telegram API returning 400 Bad Request: REACTION_INVALID
    apiResponses.set("setMessageReaction", {
      ok: false,
      error_code: 400,
      description: "Bad Request: REACTION_INVALID",
    });

    const response = await (server as any).executeTool("react", {
      chat_id: 12345,
      message_id: 999,
      reaction: "👾",
    });

    expect(response).toEqual({
      success: false,
      error: "Bad Request: REACTION_INVALID",
    });
  });

  test("AC-2a: react tool accepts cat (🐱) for polecat and dove (🕊) for subagent when Telegram accepts both", async () => {
    const store = new PluginStore(tempDir);
    const broker = new QuestionBroker(tempDir);
    const permRelay = new PermissionRelay();
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    const server = new StdioMcpServer(config, store, broker, bot, permRelay);

    apiResponses.set("setMessageReaction", { ok: true, result: true });

    // Test cat reaction for polecat
    const polecatRes = await (server as any).executeTool("react", {
      chat_id: 12345,
      message_id: 101,
      reaction: "🐱",
    });
    expect(polecatRes).toEqual({ success: true, reaction: "🐱" });

    // Test dove reaction for subagent
    const subagentRes = await (server as any).executeTool("react", {
      chat_id: 12345,
      message_id: 102,
      reaction: "🕊",
    });
    expect(subagentRes).toEqual({ success: true, reaction: "🕊" });

    const reactionCalls = apiCalls.filter((c) => c.url.endsWith("/setMessageReaction"));
    expect(reactionCalls.length).toBe(2);
    expect(reactionCalls[0].body).toEqual({
      chat_id: 12345,
      message_id: 101,
      reaction: [{ type: "emoji", emoji: "🐱" }],
    });
    expect(reactionCalls[1].body).toEqual({
      chat_id: 12345,
      message_id: 102,
      reaction: [{ type: "emoji", emoji: "🕊" }],
    });
  });

  test("AC-1.3: react tool fails fast on multi-emoji without calling Telegram API", async () => {
    const store = new PluginStore(tempDir);
    const broker = new QuestionBroker(tempDir);
    const permRelay = new PermissionRelay();
    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    const server = new StdioMcpServer(config, store, broker, bot, permRelay);

    const response = await (server as any).executeTool("react", {
      chat_id: 12345,
      message_id: 999,
      reaction: "💩🦄",
    });

    expect(response).toEqual({
      success: false,
      error: "Invalid reaction: 💩🦄",
    });
    expect(apiCalls.filter((c) => c.url.endsWith("/setMessageReaction")).length).toBe(0);
  });
});
