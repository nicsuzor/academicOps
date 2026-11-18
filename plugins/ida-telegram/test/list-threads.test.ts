import { describe, expect, test } from "bun:test";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { MCP_TOOLS } from "../src/mcp/tools.js";
import { loadConfig } from "../src/config.js";
import { PluginStore } from "../src/store.js";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("list_threads (specs/telegram/topic-and-message-management.md US-7)", () => {
  function setup() {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-list-"));
    const config = loadConfig({
      MINI_APP_URL: "https://dash.example.test/app",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "12345",
      STATE_DIR: stateDir,
    });
    const store = new PluginStore(config.stateDir);
    const apiCalls: string[] = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      apiCalls.push(method);
      const body = init?.body && typeof init.body === "string" ? JSON.parse(init.body) : {};
      if (method === "createForumTopic") {
        return new Response(
          JSON.stringify({ ok: true, result: { message_thread_id: 700 + apiCalls.length, name: body.name } }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
    }) as typeof fetch;
    const bot = new TelegramBotClient(config, new QuestionBroker(config.stateDir), new PermissionRelay(), () => {}, store);
    const mcp = new StdioMcpServer(config, store, new QuestionBroker(config.stateDir), bot, new PermissionRelay());
    const cleanup = () => {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    };
    let id = 0;
    const call = async (name: string, args: Record<string, unknown>) => {
      const res = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: ++id,
        method: "tools/call",
        params: { name, arguments: args },
      });
      return JSON.parse((res?.result as any)?.content?.[0]?.text || "{}");
    };
    return { config, store, bot, call, apiCalls, cleanup };
  }

  test("tool is advertised and never calls a Telegram list method (AC-7.1)", async () => {
    const { call, apiCalls, cleanup } = setup();
    try {
      expect(MCP_TOOLS.some((t) => t.name === "list_threads")).toBe(true);
      const res = await call("list_threads", { chat_id: 12345 });
      expect(res.success).toBe(true);
      expect(res.threads).toEqual([]);
      expect(res.note).toContain("no method to list forum topics");
      expect(apiCalls).toEqual([]);
    } finally {
      cleanup();
    }
  });

  test("created, closed, reopened and deleted threads show their state (AC-7.2)", async () => {
    const { call, cleanup } = setup();
    try {
      const a = await call("create_thread", { chat_id: 12345, name: "Alpha" });
      const b = await call("create_thread", { chat_id: 12345, name: "Beta" });
      const c = await call("create_thread", { chat_id: 12345, name: "Gamma" });
      await call("close_thread", { chat_id: 12345, message_thread_id: a.message_thread_id });
      await call("close_thread", { chat_id: 12345, message_thread_id: c.message_thread_id });
      await call("reopen_thread", { chat_id: 12345, message_thread_id: c.message_thread_id });
      await call("delete_thread", { chat_id: 12345, message_thread_id: b.message_thread_id });
      await call("rename_thread", { chat_id: 12345, message_thread_id: c.message_thread_id, name: "Gamma 2" });

      const all = await call("list_threads", { chat_id: 12345 });
      const byId = Object.fromEntries(all.threads.map((t: any) => [t.message_thread_id, t]));
      expect(all.count).toBe(2);
      expect(byId[a.message_thread_id]).toMatchObject({ name: "Alpha", state: "closed" });
      expect(byId[c.message_thread_id]).toMatchObject({ name: "Gamma 2", state: "open" });
      expect(byId[b.message_thread_id]).toBeUndefined();

      const open = await call("list_threads", { chat_id: 12345, state: "open" });
      expect(open.threads.map((t: any) => t.message_thread_id)).toEqual([c.message_thread_id]);
      const closed = await call("list_threads", { chat_id: 12345, state: "closed" });
      expect(closed.threads.map((t: any) => t.message_thread_id)).toEqual([a.message_thread_id]);

      const bad = await call("list_threads", { chat_id: 12345, state: "bogus" });
      expect(bad.success).toBe(false);
    } finally {
      cleanup();
    }
  });

  test("Telegram service messages and posts in a topic update the record (AC-7.3)", async () => {
    const { bot, call, store, cleanup } = setup();
    const msg = (id: number, thread: number, extra: Record<string, unknown>) => ({
      update_id: id,
      message: {
        message_id: id,
        message_thread_id: thread,
        date: 1,
        chat: { id: 12345, type: "supergroup" },
        from: { id: 12345, is_bot: false, first_name: "N" },
        ...extra,
      },
    });
    try {
      await (bot as any).handleUpdate(msg(1, 50, { forum_topic_created: { name: "Made by hand" } }));
      await (bot as any).handleUpdate(msg(2, 51, { forum_topic_created: { name: "Closed by hand" } }));
      await (bot as any).handleUpdate(msg(3, 51, { forum_topic_closed: {} }));
      await (bot as any).handleUpdate(msg(4, 52, { text: "hello" }));
      await (bot as any).handleUpdate(msg(5, 50, { forum_topic_edited: { name: "Renamed by hand" } }));

      const res = await call("list_threads", { chat_id: 12345 });
      const byId = Object.fromEntries(res.threads.map((t: any) => [t.message_thread_id, t]));
      expect(byId[50]).toMatchObject({ name: "Renamed by hand", state: "open" });
      expect(byId[51]).toMatchObject({ name: "Closed by hand", state: "closed" });
      expect(byId[52]).toMatchObject({ name: null, state: "open", source: "seen" });

      // General topic is never recorded, and a seen post never reopens a closed topic.
      await (bot as any).handleUpdate(msg(6, 1, { text: "general" }));
      await (bot as any).handleUpdate(msg(7, 51, { text: "late post" }));
      const again = await call("list_threads", { chat_id: 12345 });
      expect(again.threads.some((t: any) => t.message_thread_id === 1)).toBe(false);
      expect(again.threads.find((t: any) => t.message_thread_id === 51).state).toBe("closed");
      expect(store.listThreads(12345).length).toBe(3);
    } finally {
      cleanup();
    }
  });

  test("the record survives a restart (AC-7.4)", async () => {
    const { config, call, cleanup } = setup();
    try {
      const a = await call("create_thread", { chat_id: 12345, name: "Persisted" });
      const reloaded = new PluginStore(config.stateDir);
      expect(reloaded.listThreads(12345).map((t) => t.threadId)).toContain(a.message_thread_id);
    } finally {
      cleanup();
    }
  });
});
