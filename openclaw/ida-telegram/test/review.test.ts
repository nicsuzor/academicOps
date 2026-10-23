import { describe, expect, test } from "bun:test";
import { parsePermissionRequest, formatPrDiff, type PermissionRequest } from "../src/web/review.js";

describe("Review: Permission diffs and PR reviews", () => {
  test("parses Edit tool permission request into unified diff", () => {
    const perm: PermissionRequest = {
      id: "perm_1",
      tool_name: "Edit",
      tool_input: {
        file_path: "/workspace/src/example.ts",
        old_string: "const x = 1;\nconsole.log(x);",
        new_string: "const x = 2;\nconsole.log(x * 2);",
      },
    };

    const parsed = parsePermissionRequest(perm);
    expect(parsed.type).toBe("diff");
    expect(parsed.filePath).toBe("/workspace/src/example.ts");
    expect(parsed.diff).toContain("-const x = 1;");
    expect(parsed.diff).toContain("+const x = 2;");
  });

  test("parses Write tool permission request", () => {
    const perm: PermissionRequest = {
      id: "perm_2",
      tool_name: "Write",
      tool_input: {
        file_path: "/workspace/config.json",
        content: '{\n  "mode": "production"\n}',
      },
    };

    const parsed = parsePermissionRequest(perm);
    expect(parsed.filePath).toBe("/workspace/config.json");
    expect(parsed.diff).toContain("+{\n+  \"mode\": \"production\"\n+}");
  });

  test("parses Bash tool permission request into monospace script", () => {
    const perm: PermissionRequest = {
      id: "perm_3",
      tool_name: "Bash",
      tool_input: {
        command: "bun run build && bun test",
      },
    };

    const parsed = parsePermissionRequest(perm);
    expect(parsed.type).toBe("script");
    expect(parsed.script).toBe("bun run build && bun test");
  });

  test("formats PR diff without writing to GitHub directly", () => {
    const rawDiff = `diff --git a/file.ts b/file.ts
--- a/file.ts
+++ b/file.ts
@@ -1,3 +1,3 @@
-oldLine
+newLine`;

    const formatted = formatPrDiff(rawDiff, "owner/repo", 42);
    expect(formatted.repo).toBe("owner/repo");
    expect(formatted.prNumber).toBe(42);
    expect(formatted.files.length).toBe(1);
    expect(formatted.files[0].path).toBe("file.ts");
  });

  test("permission relay declares claude/channel/permission capability, handles notifications/claude/channel/permission_request, and emits notifications/claude/channel/permission", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-perm-"));
    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [12345678],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 0,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();
    const sentMessages: Array<Record<string, unknown>> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, () => {});
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      if (method === "sendMessage") sentMessages.push(payload);
      return { ok: true, result: { message_id: 601 } };
    };

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    const emittedStdout: Array<Record<string, unknown>> = [];
    const origWrite = process.stdout.write.bind(process.stdout);
    (process.stdout as any).write = (chunk: string | Uint8Array) => {
      const str = typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf-8");
      for (const line of str.split("\n")) {
        if (line.trim().startsWith("{")) {
          emittedStdout.push(JSON.parse(line.trim()));
        }
      }
      return true;
    };

    try {
      const initResp = (await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {},
      })) as any;

      expect(initResp?.result?.capabilities?.experimental?.["claude/channel"]).toEqual({});
      expect(initResp?.result?.capabilities?.experimental?.["claude/channel/permission"]).toEqual({});

      const notifResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        method: "notifications/claude/channel/permission_request",
        params: {
          request_id: "req_abc123",
          tool_name: "Bash",
          description: "Run test suite",
          input_preview: '{ command: "bun test" }',
        },
      });

      expect(notifResp).toBeNull();
      expect(permRelay.get("req_abc123")).toBeDefined();
      expect(sentMessages.length).toBe(1);

      permRelay.resolve("req_abc123", "allow");

      const permNotif = emittedStdout.find(
        (m) => m.method === "notifications/claude/channel/permission"
      ) as any;
      expect(permNotif).toBeDefined();
      expect(permNotif?.params).toEqual({
        request_id: "req_abc123",
        behavior: "allow",
      });
    } finally {
      process.stdout.write = origWrite;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("feeds real context-window usage from session transcript via CLAUDE_TRANSCRIPT_PATH without test backdoor or fake defaults", async () => {
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");
    const { mkdtempSync, rmSync, writeFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ctx-"));
    const originalEnvPath = process.env.CLAUDE_TRANSCRIPT_PATH;
    try {
      const transcriptPath = join(stateDir, "session_test.jsonl");
      writeFileSync(
        transcriptPath,
        [
          JSON.stringify({ type: "user", message: { role: "user", content: "Hello" } }),
          JSON.stringify({
            type: "assistant",
            context_window_size: 1000000,
            message: {
              model: "claude-opus-4-6",
              usage: {
                input_tokens: 12000,
                cache_creation_input_tokens: 18000,
                cache_read_input_tokens: 50000,
                output_tokens: 4000,
              },
            },
          }),
        ].join("\n") + "\n",
        "utf-8"
      );

      // 1. Without CLAUDE_TRANSCRIPT_PATH, stateDir/transcript.jsonl backdoor is NOT read
      const backdoorFile = join(stateDir, "transcript.jsonl");
      writeFileSync(backdoorFile, "malformed or test backdoor\n", "utf-8");
      delete process.env.CLAUDE_TRANSCRIPT_PATH;

      const store = new PluginStore(stateDir);
      const broker = new QuestionBroker(stateDir);
      const sessionSecret = "super-secret-session-key";
      const token = createSessionToken(12345678, sessionSecret, 3600);

      const respBackdoor = await handleApiRequest(
        new Request("http://127.0.0.1:8093/api/app/anchor", {
          method: "GET",
          headers: { Cookie: `ida_session=${token}` },
        }),
        {
          store,
          broker,
          config: {
            botToken: "test-token",
            apiBaseUrl: "https://api.telegram.org",
            role: "primary",
            isPrimary: true,
            allowFrom: [12345678],
            maxChatChars: 1200,
            voiceReplies: "off",
            voiceTranscribeCmd: "",
            voiceSpeakCmd: "",
            port: 8093,
            stateDir,
            socketPath: join(stateDir, "hook.sock"),
            botCommands: [],
          },
          sessionSecret,
          emitChannelEvent: () => {},
        }
      );
      const dataBackdoor = (await respBackdoor.json()) as any;
      expect(dataBackdoor.contextTokens).toBeUndefined();

      // 2. Pointing CLAUDE_TRANSCRIPT_PATH to real transcript reads exact usage and context_window_size
      process.env.CLAUDE_TRANSCRIPT_PATH = transcriptPath;
      const resp = await handleApiRequest(
        new Request("http://127.0.0.1:8093/api/app/anchor", {
          method: "GET",
          headers: { Cookie: `ida_session=${token}` },
        }),
        {
          store,
          broker,
          config: {
            botToken: "test-token",
            apiBaseUrl: "https://api.telegram.org",
            role: "primary",
            isPrimary: true,
            allowFrom: [12345678],
            maxChatChars: 1200,
            voiceReplies: "off",
            voiceTranscribeCmd: "",
            voiceSpeakCmd: "",
            port: 8093,
            stateDir,
            socketPath: join(stateDir, "hook.sock"),
            botCommands: [],
          },
          sessionSecret,
          emitChannelEvent: () => {},
        }
      );

      expect(resp.status).toBe(200);
      const data = (await resp.json()) as any;
      expect(data.contextTokens).toBeDefined();
      expect(data.contextTokens.usedTokens).toBe(84000);
      expect(data.contextTokens.totalTokens).toBe(1000000);
      expect(data.contextTokens.percentage).toBe(8);

      // 3. If context_window_size is absent, fail-fast without inventing a 200000 default
      const noSizeFile = join(stateDir, "no_size.jsonl");
      writeFileSync(
        noSizeFile,
        JSON.stringify({
          type: "assistant",
          message: {
            usage: { input_tokens: 1000, output_tokens: 500 },
          },
        }) + "\n",
        "utf-8"
      );
      process.env.CLAUDE_TRANSCRIPT_PATH = noSizeFile;
      expect(store.resolveContextTokens()).toBeNull();
    } finally {
      if (originalEnvPath !== undefined) {
        process.env.CLAUDE_TRANSCRIPT_PATH = originalEnvPath;
      } else {
        delete process.env.CLAUDE_TRANSCRIPT_PATH;
      }
      rmSync(stateDir, { recursive: true, force: true });
    }
  });
});
