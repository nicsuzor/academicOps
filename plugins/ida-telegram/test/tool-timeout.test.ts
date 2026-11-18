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
import { LONG_RUNNING_TOOLS, TOOL_TIMEOUT_MS, ToolTimeoutError, withToolDeadline } from "../src/mcp/timeout.js";

describe("Tool call deadline for basically-instant tools", () => {
  test("the deadline is 30 seconds", () => {
    expect(TOOL_TIMEOUT_MS).toBe(30_000);
  });

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
      "reply",
      () => new Promise((resolve) => setTimeout(() => resolve("late"), 120)),
      50
    );
    expect(r).toBe("late");
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
      expect(result.isError).toBe(true);
      expect(result.content[0].text).toContain("close_thread");
      expect(result.content[0].text).toContain("timed out");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
