import { describe, expect, test, afterEach } from "bun:test";
import { SharedTelegramChannelCore } from "../src/core/channel-core.js";
import { TurnManager, TurnRunner } from "../src/core/turn-manager.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { ContainerGateway } from "../src/gateway.js";
import { PluginConfig } from "../src/config.js";
import { MCP_TOOLS } from "../src/mcp/tools.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createConnection } from "node:net";

describe("Shared Telegram Channel Core & Specification Compliance", () => {
  const testStateDir = join(tmpdir(), "ida-tg-shared-" + Math.random().toString(36).substring(7));
  const authorizedChatId = 12345678;
  const authorizedUserId = 12345678;
  const unauthorizedUserId = 99999999;

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  function createTestConfig(overrides: Partial<PluginConfig> = {}): PluginConfig {
    return {
      botToken: "test-bot-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [authorizedUserId],
      maxChatChars: 1200,
      voiceReplies: "mirror",
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 0,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "bridge.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
      autoInterrupt: true,
      ...overrides,
    };
  }

  // --- AC1: Inbound multi-turn conversation across runtimes ---

  test("AC-1.1 & AC-1.2: Acknowledges polled authorized messages with eyes reaction and drops unauthorized updates silently", async () => {
    const config = createTestConfig();
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    }, store);

    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: 200 } };
    };

    // 1. Unauthorized message attempt -> AC-1.2: Drop silently without invoking agent or emitting reply
    await (bot as any).handleUpdate({
      update_id: 1,
      message: {
        message_id: 101,
        chat: { id: 8888, type: "private" },
        from: { id: unauthorizedUserId, is_bot: false, first_name: "Intruder" },
        text: "Unauthorized attempt",
      },
    });

    expect(apiCalls.length).toBe(0);
    expect(emittedEvents.length).toBe(0);

    // 2. Unauthorized callback button tap -> AC-1.2: Drop silently without answering callback or editing
    await (bot as any).handleUpdate({
      update_id: 2,
      callback_query: {
        id: "cb_unauth",
        from: { id: unauthorizedUserId, is_bot: false, first_name: "Intruder" },
        message: { message_id: 50, chat: { id: 8888, type: "private" }, text: "Decision" },
        data: "q:q_1:0:0",
      },
    });

    expect(apiCalls.length).toBe(0);
    expect(emittedEvents.length).toBe(0);

    // 3. Authorized message -> AC-1.1: Places 👀 reaction and delivers normalized inbound event
    await (bot as any).handleUpdate({
      update_id: 3,
      message: {
        message_id: 102,
        chat: { id: authorizedChatId, type: "private" },
        from: { id: authorizedUserId, is_bot: false, first_name: "Nic" },
        text: "Run the data pipeline for chapter 2",
        reply_to_message: {
          message_id: 99,
          chat: { id: authorizedChatId, type: "private" },
          text: "Previous summary",
        },
      },
    });

    // Verified: Eyes reaction placed
    const rxCall = apiCalls.find((c) => c.method === "setMessageReaction");
    expect(rxCall).toBeDefined();
    expect(rxCall?.payload.message_id).toBe(102);
    expect((rxCall?.payload.reaction as any[])[0]?.emoji).toBe("👀");

    // Verified: Normalized inbound event delivered with sender identity, chat/message IDs, reply quotes
    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].content).toBe("Run the data pipeline for chapter 2");
    expect(emittedEvents[0].meta.user_id).toBe(String(authorizedUserId));
    expect(emittedEvents[0].meta.chat_id).toBe(String(authorizedChatId));
    expect(emittedEvents[0].meta.message_id).toBe("102");
    expect(emittedEvents[0].meta.reply_to_message_id).toBe("99");
    expect(emittedEvents[0].meta.quoted_text).toContain("Previous summary");
  });

  test("AC-1.3: Resumes existing session mappings for chats across turns and container restarts", async () => {
    // Session 1: chat has an established session
    const store1 = new PluginStore(testStateDir);
    store1.setSession(authorizedChatId, "sess_abc123_turn1");
    expect(store1.getSession(authorizedChatId)).toBe("sess_abc123_turn1");

    // Container / process restart (Session 2 reinstantiates store from same stateDir)
    const store2 = new PluginStore(testStateDir);
    expect(store2.getSession(authorizedChatId)).toBe("sess_abc123_turn1");

    // When turn manager dispatches an inbound message, it supplies the existing session ID
    let suppliedSessionId: string | undefined;
    const runner: TurnRunner = async (req) => {
      suppliedSessionId = req.sessionId;
      return { output: "Turn finished", sessionId: "sess_abc123_turn1" };
    };

    const turnManager = new TurnManager({ store: store2, runner });
    await turnManager.dispatchTurn({
      chatId: authorizedChatId,
      prompt: "Next question in thread",
    });

    expect(suppliedSessionId).toBe("sess_abc123_turn1");
  });

  test("AC-1.4: Cancels in-flight turns and starts combined follow-up turns when auto-interrupt is enabled", async () => {
    const store = new PluginStore(testStateDir);
    store.setSession(authorizedChatId, "sess_persistent_1");

    let firstTurnAborted = false;
    let turn1Resolve: () => void;
    const executedPrompts: string[] = [];

    const runner: TurnRunner = async (req, signal) => {
      executedPrompts.push(req.prompt);
      if (req.prompt === "First prompt running long...") {
        return new Promise((resolve) => {
          signal.addEventListener("abort", () => {
            firstTurnAborted = true;
            resolve({ output: "First turn aborted" });
          });
        });
      }
      return { output: "Second turn output" };
    };

    const turnManager = new TurnManager({
      store,
      autoInterrupt: true,
      runner,
    });

    // Start in-flight turn 1
    const turn1Promise = turnManager.dispatchTurn({
      chatId: authorizedChatId,
      prompt: "First prompt running long...",
    });

    expect(turnManager.isTurnRunning(authorizedChatId)).toBe(true);

    // User sends follow-up text while turn 1 is running
    const turn2Promise = turnManager.dispatchTurn({
      chatId: authorizedChatId,
      prompt: "Wait, also check the secondary hypothesis!",
    });

    // Verified: First turn was aborted via signal
    expect(firstTurnAborted).toBe(true);

    const turn2Result = await turn2Promise;
    expect(turn2Result.status).toBe("completed");

    // Verified: Replacement turn combined the interrupted prompt with the follow-up message
    expect(executedPrompts.length).toBe(2);
    expect(executedPrompts[1]).toBe("First prompt running long...\n\nWait, also check the secondary hypothesis!");
    expect(turn2Result.sessionId).toBe("sess_persistent_1");
  });

  // --- AC2: Progressive-disclosure replies, reactions, and voice responses ---

  test("AC-2.1: Formats rich typography with expandable blockquotes and splits replies at whole-paragraph boundaries at 1,200 chars with continuation notice", async () => {
    const config = createTestConfig({ maxChatChars: 1200 });
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);

    const core = new SharedTelegramChannelCore({
      config,
      store,
      broker,
      bot: null,
      permRelay,
    });

    const p1 = "First paragraph summarizing the core findings of the analysis with **bold emphasis** and `inline code`.";
    const p2 = ">! Expandable details blockquote with crucial intermediate evidence.";
    const p3 = "A".repeat(1200) + " Third long paragraph detailing statistical distributions.";
    const p4 = "Fourth paragraph with concluding recommendations.";
    const fullMarkdown = `${p1}\n\n${p2}\n\n${p3}\n\n${p4}`;

    expect(fullMarkdown.length).toBeGreaterThan(1200);

    const res = await core.reply({
      text: fullMarkdown,
      chat_id: authorizedChatId,
    });

    expect(res.success).toBe(true);
    // Verified: Paragraph overflow split under 1200 characters with continuation notice
    expect(res.preview).toBeDefined();
    expect(res.preview?.length).toBeLessThanOrEqual(1200);
    expect(res.preview).toContain("… continued in Details");
    expect(res.detailsId).toBeDefined();

    // Stored details preserves remaining paragraphs
    const details = store.getDetails(res.detailsId!);
    expect(details).not.toBeNull();
    expect(details?.markdown).toContain(p4);
  });

  // --- AC3: Asynchronous interactive questions ---

  test("AC-3.1 & AC-3.2: Posts non-blocking question cards acknowledging immediately, and resolves choices into continuation turns", async () => {
    const config = createTestConfig();
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);

    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    let msgIdCounter = 400;

    const bot = new TelegramBotClient(config, broker, permRelay, () => {}, store);
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      if (method === "sendMessage") {
        return { ok: true, result: { message_id: ++msgIdCounter } };
      }
      return { ok: true, result: true };
    };

    const core = new SharedTelegramChannelCore({
      config,
      store,
      broker,
      bot,
      permRelay,
    });

    // Agent invokes ask_user
    const askResult = await core.askUser({
      turn_id: "turn_q1",
      questions: [
        {
          question: "Which model checkpoint should we deploy?",
          header: "Deployment checkpoint",
          options: [
            { label: "Model v2.4 (Recommended)", description: "Passes regression tests" },
            { label: "Model v2.3", description: "Stable previous version" },
          ],
          multi_select: false,
          allow_custom: true,
        },
      ],
      chat_id: authorizedChatId,
    });

    // Verified AC-3.1: Tool acknowledges immediately with question_ids and status "posted"
    expect(askResult.status).toBe("posted");
    expect(askResult.question_ids.length).toBe(1);
    const qid = askResult.question_ids[0];

    // Card was sent to Telegram
    const sendCardCall = apiCalls.find((c) => c.method === "sendMessage");
    expect(sendCardCall).toBeDefined();

    // User taps option 0 on Telegram -> AC-3.2: delivered as continuation turn event
    const resolveRes = await broker.resolveAnswer(qid, 0);
    expect(resolveRes).not.toBeNull();
    expect(resolveRes?.channelEvent.event).toBe("question_answered");
    expect(resolveRes?.channelEvent.choice).toBe("Model v2.4 (Recommended)");
    expect(resolveRes?.channelEvent.turn_id).toBe("turn_q1");
  });

  // --- AC4: Background completion and strict error propagation ---

  test("AC-4.1: Wakes continuation turns when delegated background work finishes with undelivered results", async () => {
    const store = new PluginStore(testStateDir);
    store.setSession(authorizedChatId, "sess_research_789");

    let continuationPromptReceived = "";
    let continuationSessionId: string | undefined;

    const runner: TurnRunner = async (req) => {
      continuationPromptReceived = req.prompt;
      continuationSessionId = req.sessionId;
      return { output: "Agent handled background results", sessionId: req.sessionId };
    };

    const turnManager = new TurnManager({
      store,
      runner,
    });

    // Background task finishes
    const bgResult = await turnManager.onBackgroundWorkCompleted({
      chatId: authorizedChatId,
      taskId: "task_eval_bench",
      result: "All 12 benchmarks passed with 0 regressions.",
    });

    expect(bgResult.status).toBe("completed");
    expect(continuationSessionId).toBe("sess_research_789");
    expect(continuationPromptReceived).toContain("task_eval_bench completed");
    expect(continuationPromptReceived).toContain("All 12 benchmarks passed");
  });

  test("AC-4.2: Fails fast and halts immediately on HTTP 409 poller collision without retries", async () => {
    const config = createTestConfig();
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    let pollCount = 0;

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    }, store);

    // Telegram Bot API returns 409 Conflict
    (bot as any).callApi = async (method: string) => {
      if (method === "getUpdates") {
        pollCount++;
        return { ok: false, error_code: 409, description: "Conflict: terminated by other getUpdates request" };
      }
      return { ok: true, result: true };
    };

    // Start poller
    await bot.startPolling();

    // Verified: Poller halted immediately after first 409, no retry loop
    expect(pollCount).toBe(1);
    const collisionEvent = emittedEvents.find((e) => e.meta.event === "poller_collision" || e.meta.error_code === "409");
    expect(collisionEvent).toBeDefined();
    expect(collisionEvent?.content).toContain("409 Conflict");
  });

  test("AC-4.3: Turn non-zero exit or communication error halts turn immediately and surfaces verbatim error output", async () => {
    const store = new PluginStore(testStateDir);
    const capturedErrors: Array<{ error: Error | string; context: Record<string, unknown> }> = [];

    const runner: TurnRunner = async (req) => {
      return {
        output: "Partial trace before crash",
        exitCode: 137,
        error: "FATAL: Out of memory (SIGKILL 137)",
      };
    };

    const turnManager = new TurnManager({
      store,
      runner,
    });
    turnManager.onError((error, context) => {
      capturedErrors.push({ error, context });
    });

    const result = await turnManager.dispatchTurn({
      chatId: authorizedChatId,
      prompt: "Execute heavy simulation",
    });

    // Verified AC-4.3: Status failed, exit code 137, verbatim error surfaced
    expect(result.status).toBe("failed");
    expect(result.exitCode).toBe(137);
    expect(result.error).toContain("FATAL: Out of memory (SIGKILL 137)");
    expect(capturedErrors.length).toBe(1);
    expect(capturedErrors[0].error).toContain("FATAL: Out of memory");
  });

  // --- AC5: Four outbound transport tools adhering to parameter and return schemas ---

  test("AC5: StdioMcpServer exposes the four outbound transport tools adhering to parameter and return schemas", async () => {
    const config = createTestConfig();
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);

    const mcp = new StdioMcpServer(config, store, broker, null, permRelay);

    // 1. tools/list exposes reply, react, ask_user, edit_message
    const listRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
    });

    const toolNames = (listRes?.result as any)?.tools?.map((t: any) => t.name);
    expect(toolNames).toContain("reply");
    expect(toolNames).toContain("react");
    expect(toolNames).toContain("ask_user");
    expect(toolNames).toContain("edit_message");

    // 2. reply tool call returns message_id
    const replyRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "reply",
        arguments: {
          text: "Simple reply text",
        },
      },
    });
    const replyParsed = JSON.parse((replyRes?.result as any)?.content[0]?.text);
    expect(replyParsed.success).toBe(true);
    expect(replyParsed.message_id).toBeDefined();

    // 3. react tool call returns success and reaction
    const reactRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        name: "react",
        arguments: {
          message_id: 123,
          reaction: "👍",
        },
      },
    });
    const reactParsed = JSON.parse((reactRes?.result as any)?.content[0]?.text);
    expect(reactParsed.success).toBe(true);
    expect(reactParsed.reaction).toBe("👍");

    // 4. ask_user tool call returns question_ids and status "posted"
    const askRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          turn_id: "correlate_123",
          questions: [
            {
              question: "Confirm rollout?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });
    const askParsed = JSON.parse((askRes?.result as any)?.content[0]?.text);
    expect(Array.isArray(askParsed.question_ids)).toBe(true);
    expect(askParsed.status).toBe("posted");

    // 5. edit_message tool call returns success
    const editRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 5,
      method: "tools/call",
      params: {
        name: "edit_message",
        arguments: {
          message_id: 123,
          text: "Updated text",
        },
      },
    });
    const editParsed = JSON.parse((editRes?.result as any)?.content[0]?.text);
    expect(editParsed.success).toBe(true);
  });

  // --- Container Gateway Transport ---

  test("Container Gateway starts IPC bridge socket and handles outbound tool calls", async () => {
    const socketPath = join(testStateDir, "gw_bridge.sock");
    const config = createTestConfig({ socketPath, botToken: "" });
    const gateway = new ContainerGateway({ config });

    await gateway.start();

    // Send IPC tool call over Unix domain socket
    const ipcResponse = await new Promise<string>((resolve, reject) => {
      const client = createConnection(socketPath, () => {
        const payload = {
          type: "ask_user",
          questions: [
            {
              question: "Ready to proceed?",
              options: [{ label: "Proceed" }, { label: "Cancel" }],
            },
          ],
        };
        client.write(JSON.stringify(payload) + "\n");
      });

      client.on("data", (data) => {
        resolve(data.toString());
        client.end();
      });
      client.on("error", reject);
    });

    const parsed = JSON.parse(ipcResponse.trim());
    expect(parsed.status).toBe("posted");
    expect(parsed.question_ids.length).toBe(1);

    gateway.stop();
  });
});
