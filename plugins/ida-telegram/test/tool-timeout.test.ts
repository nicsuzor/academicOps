import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadConfig } from "../src/config.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { MCP_TOOLS } from "../src/mcp/tools.js";
import { TelegramBotClient, buildInlineKeyboardRows } from "../src/telegram/bot.js";
import { LONG_RUNNING_TOOLS, ToolTimeoutError, withToolDeadline } from "../src/mcp/timeout.js";

describe("Tool call deadline for basically-instant tools", () => {
  test("every exempt tool is a real tool", () => {
    const names = new Set(MCP_TOOLS.map((t) => t.name));
    for (const t of LONG_RUNNING_TOOLS) expect(names.has(t)).toBe(true);
  });

  test("a covered tool that never answers rejects once the deadline passes", async () => {
    const started = Date.now();
    const p = withToolDeadline("close_thread", () => new Promise(() => {}), 50);
    await expect(p).rejects.toBeInstanceOf(ToolTimeoutError);
    expect(Date.now() - started).toBeLessThan(1000);
  });

  test("a covered tool that answers in time returns its result", async () => {
    const r = await withToolDeadline("react", async () => ({ success: true }), 50);
    expect(r).toEqual({ success: true });
  });

  test("an exempt tool is not cut off by the deadline", async () => {
    const r = await withToolDeadline(
      "send_photo",
      () => new Promise((resolve) => setTimeout(() => resolve("late"), 120)),
      50
    );
    expect(r).toBe("late");
  });

  test("reply is bounded by the deadline when it hangs", async () => {
    const started = Date.now();
    const p = withToolDeadline("reply", () => new Promise(() => {}), 50);
    await expect(p).rejects.toBeInstanceOf(ToolTimeoutError);
    expect(Date.now() - started).toBeLessThan(1000);
  });

  test("MCP tools/call returns an error result naming the tool when a covered tool hangs", async () => {
    const dir = mkdtempSync(join(tmpdir(), "tool-timeout-"));
    try {
      const config = loadConfig({
        TELEGRAM_BOT_TOKEN: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "1111111111",
        STATE_DIR: dir,
        MINI_APP_URL: "https://miniapp.example.com",
      });
      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const mcp = new StdioMcpServer(config, store, broker, null, new PermissionRelay());
      mcp.toolTimeoutMs = 50;
      mcp.channelCore.handleIpcMessage = () => new Promise(() => {});
      const res = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 7,
        method: "tools/call",
        params: { name: "close_thread", arguments: { message_thread_id: 1 } },
      });
      const result = res?.result as { isError?: boolean; content: Array<{ text: string }> };
      expect("isError" in (res || {})).toBe(false);
      expect(Object.keys(res || {}).sort()).toEqual(["id", "jsonrpc", "result"]);
      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain("close_thread");
      expect(result.content[0].text).toContain("timed out");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("MCP tools/call returns an error result naming reply when reply hangs", async () => {
    const dir = mkdtempSync(join(tmpdir(), "tool-timeout-"));
    try {
      const config = loadConfig({
        TELEGRAM_BOT_TOKEN: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "1111111111",
        STATE_DIR: dir,
        MINI_APP_URL: "https://miniapp.example.com",
      });
      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const mcp = new StdioMcpServer(config, store, broker, null, new PermissionRelay());
      mcp.toolTimeoutMs = 50;
      mcp.channelCore.handleIpcMessage = () => new Promise(() => {});
      const res = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 8,
        method: "tools/call",
        params: { name: "reply", arguments: { text: "hello" } },
      });
      const result = res?.result as { isError?: boolean; content: Array<{ text: string }> };
      expect("isError" in (res || {})).toBe(false);
      expect(Object.keys(res || {}).sort()).toEqual(["id", "jsonrpc", "result"]);
      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain("reply");
      expect(result.content[0].text).toContain("timed out");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("close_thread and reply abort hung Bot API fetch calls and return structured timeout or Bot API errors", async () => {
    const dir = mkdtempSync(join(tmpdir(), "tool-timeout-"));
    const origFetch = globalThis.fetch;
    try {
      const config = loadConfig({
        TELEGRAM_BOT_TOKEN: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        IDA_TELEGRAM_ROLE: "primary",
        ALLOWED_USER_IDS: "1111111111",
        STATE_DIR: dir,
        MINI_APP_URL: "https://miniapp.example.com",
      });
      const store = new PluginStore(config.stateDir);
      const broker = new QuestionBroker(config.stateDir);
      const permRelay = new PermissionRelay();
      const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
      bot.apiTimeoutMs = 50;
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Hung fetch aborts via AbortSignal and surfaces timeout error
      globalThis.fetch = ((_url: string | URL | Request, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            const err = new Error("The operation was aborted");
            err.name = "AbortError";
            reject(err);
          });
        })) as typeof fetch;

      const closeTimeoutRes = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 9,
        method: "tools/call",
        params: { name: "close_thread", arguments: { message_thread_id: 42 } },
      });
      const closeTimeoutPayload = JSON.parse(
        ((closeTimeoutRes?.result as { content: Array<{ text: string }> }).content[0].text)
      );
      expect(closeTimeoutPayload.success).toBe(false);
      expect(closeTimeoutPayload.error).toContain("closeForumTopic");
      expect(closeTimeoutPayload.error).toContain("timed out");

      const replyTimeoutRes = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 10,
        method: "tools/call",
        params: { name: "reply", arguments: { text: "hello" } },
      });
      const replyTimeoutPayload = JSON.parse(
        ((replyTimeoutRes?.result as { content: Array<{ text: string }> }).content[0].text)
      );
      expect(replyTimeoutPayload.success).toBe(false);
      expect(replyTimeoutPayload.error).toContain("sendMessage");
      expect(replyTimeoutPayload.error).toContain("timed out");

      // 2. Bot API error response is preserved verbatim on reply and close_thread
      globalThis.fetch = (async () =>
        new Response(
          JSON.stringify({ ok: false, error_code: 400, description: "Bad Request: TOPIC_NOT_MODIFIED" }),
          { status: 400, headers: { "Content-Type": "application/json" } }
        )) as typeof fetch;

      const closeApiErrRes = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 11,
        method: "tools/call",
        params: { name: "close_thread", arguments: { message_thread_id: 42 } },
      });
      const closeApiErrPayload = JSON.parse(
        ((closeApiErrRes?.result as { content: Array<{ text: string }> }).content[0].text)
      );
      expect(closeApiErrPayload.success).toBe(false);
      expect(closeApiErrPayload.error).toContain("TOPIC_NOT_MODIFIED");

      const replyApiErrRes = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 12,
        method: "tools/call",
        params: { name: "reply", arguments: { text: "hello" } },
      });
      const replyApiErrPayload = JSON.parse(
        ((replyApiErrRes?.result as { content: Array<{ text: string }> }).content[0].text)
      );
      expect(replyApiErrPayload.success).toBe(false);
      expect(replyApiErrPayload.error).toContain("TOPIC_NOT_MODIFIED");
      expect("isError" in (closeApiErrRes || {})).toBe(false);
      expect("isError" in (replyApiErrRes || {})).toBe(false);
      expect((closeApiErrRes?.result as { isError?: boolean }).isError).toBe(true);
      expect((replyApiErrRes?.result as { isError?: boolean }).isError).toBe(true);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("buildInlineKeyboardRows accepts string buttons and text-keyed button objects", () => {
    const stringRows = buildInlineKeyboardRows([
      ["Try neon again", "Hydrogen xhigh instead"],
      ["Defer"],
    ]);
    expect(stringRows).toEqual([
      [
        { text: "Try neon again", callback_data: "action:Try neon again" },
        { text: "Hydrogen xhigh instead", callback_data: "action:Hydrogen xhigh instead" },
      ],
      [{ text: "Defer", callback_data: "action:Defer" }],
    ]);

    const textKeyedRows = buildInlineKeyboardRows([
      { text: "Approve", callback_data: "approve" } as unknown as { label: string; callback_data: string },
    ]);
    expect(textKeyedRows).toEqual([[{ text: "Approve", callback_data: "approve" }]]);
  });
});
