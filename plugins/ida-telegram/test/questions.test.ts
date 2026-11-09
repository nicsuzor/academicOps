import { describe, expect, test, afterEach } from "bun:test";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PluginStore } from "../src/store.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Questions are never assumed: Asynchronous Broker and Hook", () => {
  const testStateDir = join(tmpdir(), "ida-telegram-q-test-" + Math.random().toString(36).substring(7));

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  test("ask_user creates a persistent question, formats buttons with recommendation first, and returns immediately", async () => {
    const broker = new QuestionBroker(testStateDir);

    const questionInput = {
      question: "Which component should we prioritize?",
      options: [
        { label: "Port Formatter (Recommended)", description: "High impact on readability" },
        { label: "Refactor Poller", description: "Better backoff" },
      ],
      allowOther: false,
      turnId: "turn_123",
      chatId: 12345678,
    };

    const immediateResult = await broker.askUser(questionInput);

    expect(immediateResult.questionId).toBeDefined();
    expect(immediateResult.status).toBe("posted");
    expect(immediateResult.message).toContain("Do not assume an answer; continue other work or end your turn.");

    // Check keyboard structure
    const card = broker.renderQuestionCard(immediateResult.questionId);
    expect(card).not.toBeNull();
    expect(card?.buttons.length).toBe(2);
    // Vertical order preserved, recommendation first
    expect(card?.buttons[0].text).toContain("1. Port Formatter (Recommended)");
    expect(card?.buttons[1].text).toContain("2. Refactor Poller");
    // Callback data adheres to Telegram 64-byte limit
    expect(card?.buttons[0].callbackData.length).toBeLessThanOrEqual(64);
  });

  test("questions persist across restarts and can be resolved late", async () => {
    // Session 1: Create question
    const broker1 = new QuestionBroker(testStateDir);
    const result = await broker1.askUser({
      question: "Choose deployment strategy",
      options: [{ label: "Blue-Green" }, { label: "Canary" }],
      turnId: "turn_456",
      chatId: 12345678,
    });
    const qid = result.questionId;

    // Simulate restart (Session 2 reinstantiates broker with same state dir)
    const broker2 = new QuestionBroker(testStateDir);
    const pending = broker2.getPendingQuestions();
    expect(pending.some((q) => q.id === qid)).toBe(true);

    // The user taps option 2: Canary
    const resolution = await broker2.resolveAnswer(qid, 1); // index 1 is Canary
    expect(resolution).not.toBeNull();
    expect(resolution?.cardText).toContain("Selected: Canary ✅");
    expect(resolution?.channelEvent.choice).toBe("Canary");
    expect(resolution?.channelEvent.turn_id).toBe("turn_456");

    // Question is no longer pending
    expect(broker2.getPendingQuestions().some((q) => q.id === qid)).toBe(false);
  });

  test("handles multiSelect questions with toggles and Done button", async () => {
    const broker = new QuestionBroker(testStateDir);
    const result = await broker.askUser({
      question: "Select enabled features",
      options: [{ label: "Logging" }, { label: "Tracing" }, { label: "Metrics" }],
      multiSelect: true,
      turnId: "turn_789",
      chatId: 12345678,
    });

    const card = broker.renderQuestionCard(result.questionId);
    expect(card?.buttons.some((b) => b.text.includes("☐ Logging"))).toBe(true);
    expect(card?.buttons.some((b) => b.text.includes("Done"))).toBe(true);
  });

  test("batch of decisions and results renders as individual formatted cards in Telegram and resolves each in-app into channel events", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    let nextMessageId = 100;

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      channelEvents.push({ content, meta });
    });

    // Stub callApi to capture outbound Telegram payloads
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      if (method === "sendMessage") {
        return { ok: true, result: { message_id: ++nextMessageId } };
      }
      return { ok: true, result: true };
    };

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // 1. Send a batch of 3 decisions via ask_user (modeled on tg 1004 batch: value-model, polecat security, design proposal)
    const askResp = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              header: "Value model weight",
              question: "Raise `urgency` weight on cliff tasks?\n>! Facts: `demo_00000002` showed 3 cliff tasks ranked below routine cleanup.",
              options: [
                { label: "Raise to 2.5x (Recommended)", description: "Prioritizes due-within-48h tasks immediately" },
                { label: "Keep at 1.5x", description: "Preserve current focus balance" },
              ],
            },
            {
              header: "Polecat security scope",
              question: "Select network egress rules to enable for polecat containers:",
              options: [
                { label: "Allow GitHub API" },
                { label: "Allow PyPI / npm registries" },
                { label: "Block raw socket egress" },
              ],
              multiSelect: true,
            },
            {
              header: "Design proposal",
              question: "Adopt single-screen Question Canvas layout for Telegram mini-app?",
              options: [
                { label: "Approve v3 layout (Recommended)", description: "Matches native UI map" },
                { label: "Revise layout", description: "Keep multi-tab drawer" },
              ],
            },
          ],
        },
      },
    });

    const sentCards = apiCalls.filter((c) => c.method === "sendMessage");
    // Must render 3 separate Telegram cards (one per decision in batch)
    expect(sentCards.length).toBe(3);

    // Card 1 must have formatted UTF-16 entities (bold header, inline code, expandable_blockquote) and option descriptions
    const card1Payload = sentCards[0].payload;
    expect(card1Payload.text as string).toContain("Value model weight");
    expect(card1Payload.text as string).toContain("Prioritizes due-within-48h tasks immediately");
    expect(Array.isArray(card1Payload.entities)).toBe(true);
    expect((card1Payload.entities as any[]).some((e) => e.type === "bold")).toBe(true);
    expect((card1Payload.entities as any[]).some((e) => e.type === "expandable_blockquote")).toBe(true);

    // 2. Send a result card with custom action buttons and PR review via `reply`
    await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "reply",
        arguments: {
          text: "**PR #418 ready to merge** — `polecat/demo_00000003` passes all 40 tests.\n>! Changed `questions.ts`, `bot.ts`, `server.ts`.",
          detail: "## Full Diff Summary\n- Fixed batch truncation\n- Added entity formatting",
          review: { repo: "nicsuzor/academicOps", pr: 418 },
          buttons: [
            { label: "Merge PR #418 (Recommended)", callback_data: "decide:pr418:merge" },
            { label: "Hold for manual check", callback_data: "decide:pr418:hold" },
          ],
        },
      },
    });

    const resultCardCall = apiCalls[apiCalls.length - 1];
    expect(resultCardCall.method).toBe("sendMessage");
    const resultKb = (resultCardCall.payload.reply_markup as any).inline_keyboard as Array<Array<any>>;
    // Custom decision buttons appear on the result card alongside Details and Review diff buttons
    expect(resultKb.flat().some((b) => b.text === "Merge PR #418 (Recommended)" && b.callback_data === "decide:pr418:merge")).toBe(true);
    expect(resultKb.flat().some((b) => b.text === "🔍")).toBe(true);
    expect(resultKb.flat().some((b) => b.text.includes("🔍 Review diff"))).toBe(true);

    // 3. Resolve Card 1 (single-select tap on option 0)
    const pendingBefore = broker.getPendingQuestions();
    expect(pendingBefore.length).toBe(3);
    const q1 = pendingBefore[0];
    const q2 = pendingBefore[1];
    const q3 = pendingBefore[2];

    await (bot as any).handleUpdate({
      update_id: 501,
      callback_query: {
        id: "cb_1",
        from: { id: 999, first_name: "Alex" },
        message: { message_id: 101, chat: { id: 999, type: "private" }, text: card1Payload.text as string },
        data: `q:${q1.id}:0:0`,
      },
    });

    expect(channelEvents.length).toBe(1);
    expect(channelEvents[0].meta.event).toBe("question_answered");
    expect(channelEvents[0].meta.question_id).toBe(q1.id);
    expect(channelEvents[0].meta.choice).toBe("Raise to 2.5x (Recommended)");

    const edit1 = apiCalls.find((c) => c.method === "editMessageText" && c.payload.message_id === 101);
    expect(edit1).toBeDefined();
    expect(edit1?.payload.text as string).toContain("Selected: Raise to 2.5x (Recommended) ✅");
    expect((edit1?.payload.reply_markup as any)?.inline_keyboard).toEqual([]);

    // 4. Resolve Card 2 (multi-select: toggle option 0 and option 2, then tap Done)
    await (bot as any).handleUpdate({
      update_id: 502,
      callback_query: {
        id: "cb_2a",
        from: { id: 999, first_name: "Alex" },
        message: { message_id: 102, chat: { id: 999, type: "private" }, text: sentCards[1].payload.text as string },
        data: `q:${q2.id}:0:0`,
      },
    });
    // Must NOT have emitted channel event yet on multi-select toggle!
    expect(channelEvents.length).toBe(1);

    await (bot as any).handleUpdate({
      update_id: 503,
      callback_query: {
        id: "cb_2b",
        from: { id: 999, first_name: "Alex" },
        message: { message_id: 102, chat: { id: 999, type: "private" }, text: sentCards[1].payload.text as string },
        data: `q:${q2.id}:0:2`,
      },
    });
    expect(channelEvents.length).toBe(1);

    // Now tap Done on Card 2
    await (bot as any).handleUpdate({
      update_id: 504,
      callback_query: {
        id: "cb_2c",
        from: { id: 999, first_name: "Alex" },
        message: { message_id: 102, chat: { id: 999, type: "private" }, text: sentCards[1].payload.text as string },
        data: `q:${q2.id}:0:done`,
      },
    });
    expect(channelEvents.length).toBe(2);
    expect(channelEvents[1].meta.question_id).toBe(q2.id);
    expect(channelEvents[1].meta.choice).toBe("Allow GitHub API, Block raw socket egress");

    // 5. Resolve Card 3 via "✏️ Other" force_reply prompt and custom text reply
    await (bot as any).handleUpdate({
      update_id: 505,
      callback_query: {
        id: "cb_3_other",
        from: { id: 999, first_name: "Alex" },
        message: { message_id: 103, chat: { id: 999, type: "private" }, text: sentCards[2].payload.text as string },
        data: `q:${q3.id}:0:other`,
      },
    });
    // Tapping Other should send a force_reply prompt and NOT resolve with empty string
    expect(channelEvents.length).toBe(2);
    const forceReplyCall = apiCalls.find(
      (c) => c.method === "sendMessage" && (c.payload.reply_markup as any)?.force_reply === true
    );
    expect(forceReplyCall).toBeDefined();
    const promptMsgId = nextMessageId;

    // The user replies to the force_reply prompt with custom text
    await (bot as any).handleUpdate({
      update_id: 506,
      message: {
        message_id: 900,
        from: { id: 999, first_name: "Alex" },
        chat: { id: 999, type: "private" },
        date: 1700000000,
        text: "Approve v3 layout, but keep font size at 15px",
        reply_to_message: {
          message_id: promptMsgId,
          chat: { id: 999, type: "private" },
          text: forceReplyCall?.payload.text as string,
        },
      },
    });

    expect(channelEvents.length).toBe(3);
    expect(channelEvents[2].meta.event).toBe("question_answered");
    expect(channelEvents[2].meta.question_id).toBe(q3.id);
    expect(channelEvents[2].meta.choice).toBe("Approve v3 layout, but keep font size at 15px");

    // 6. Resolve Result Card (Card 4) by tapping custom inline button "Merge PR #418 (Recommended)"
    await (bot as any).handleUpdate({
      update_id: 507,
      callback_query: {
        id: "cb_4_merge",
        from: { id: 999, first_name: "Alex" },
        message: {
          message_id: 104,
          chat: { id: 999, type: "private" },
          text: resultCardCall.payload.text as string,
          reply_markup: resultCardCall.payload.reply_markup as any,
        },
        data: "decide:pr418:merge",
      },
    });

    expect(channelEvents.length).toBe(4);
    expect(channelEvents[3].meta.event).toBe("button_tap");
    expect(channelEvents[3].meta.payload).toBe("decide:pr418:merge");
    expect(channelEvents[3].meta.label).toBe("Merge PR #418 (Recommended)");
    const edit4 = apiCalls.find((c) => c.method === "editMessageText" && c.payload.message_id === 104);
    expect(edit4).toBeDefined();
    expect(edit4?.payload.text as string).toContain("Selected: Merge PR #418 (Recommended) ✅");
  });

  test("Mini App question answer settles pending question, edits the Telegram chat card, and emits channel event (FR-2.6)", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");
    const { PluginStore } = await import("../src/store.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);
    const posted = await broker.askUser({
      header: "Merge approval",
      question: "Ship `v0.10.16` to production?",
      options: [{ label: "Ship now (Recommended)" }, { label: "Wait for Monday" }],
      chatId: 999,
      turnId: "turn_999",
    });
    broker.setMessageId(posted.questionId, 777);

    const editedCards: Array<{ chatId: number; messageId: number; text: string }> = [];
    const emittedEvents: Array<{ event: string; content: string; meta: Record<string, unknown> }> = [];
    const sessionSecret = "test-secret-32-bytes-long-123456";
    const token = createSessionToken(999, sessionSecret, 3600);

    const req = new Request("http://127.0.0.1:8093/api/app/questions/answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `ida_session=${token}`,
      },
      body: JSON.stringify({
        questionId: posted.questionId,
        optionIndex: 0,
      }),
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: (event, content, meta) => {
        emittedEvents.push({ event, content, meta });
      },
      editTelegramCard: async (chatId, messageId, text) => {
        editedCards.push({ chatId, messageId, text });
      },
    } as any);

    expect(resp.status).toBe(200);
    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].meta.choice).toBe("Ship now (Recommended)");
    expect(editedCards.length).toBe(1);
    expect(editedCards[0].chatId).toBe(999);
    expect(editedCards[0].messageId).toBe(777);
    expect(editedCards[0].text).toContain("Selected: Ship now (Recommended) ✅");
  });

  test("PreToolUse hook on AskUserQuestion posts question to socket and returns a decision Claude Code accepts (block / permissionDecision deny)", async () => {
    const { createServer } = await import("node:net");
    const { spawn } = await import("node:child_process");
    const { mkdirSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const socketPath = join(testStateDir, "bridge.sock");
    let receivedSocketReq: any = null;

    const server = createServer((client) => {
      let buf = "";
      client.on("data", (chunk) => {
        buf += chunk.toString();
        if (buf.includes("\n")) {
          receivedSocketReq = JSON.parse(buf.trim());
          client.write(JSON.stringify({ status: "ok", questionId: "q_hook123", questionIds: ["q_hook123"] }) + "\n");
        }
      });
    });

    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      const stdout = await new Promise<string>((resolve, reject) => {
        const proc = spawn("node", [hookScript], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: socketPath,
          },
        });
        let out = "";
        proc.stdout.on("data", (d) => (out += d.toString()));
        proc.on("error", reject);
        proc.on("close", () => resolve(out));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_hook_42",
            tool_input: {
              questions: [
                {
                  question: "Proceed with deployment?",
                  options: [{ label: "Yes (Recommended)" }, { label: "No" }],
                },
              ],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      expect(receivedSocketReq).not.toBeNull();
      expect(receivedSocketReq.type).toBe("ask_user");

      const parsed = JSON.parse(stdout.trim());
      // Claude Code PreToolUse rejects decision: "deny"; valid top-level decisions are "approve" | "block"
      expect(["approve", "block"]).toContain(parsed.decision);
      expect(parsed.decision).toBe("block");
      expect(parsed.reason).toContain("q_hook123");
      expect(parsed.reason).toContain("posted to the user over Telegram");
      expect(parsed.reason).not.toContain("Nic");
      expect(parsed.hookSpecificOutput?.permissionDecision).toBe("deny");
    } finally {
      server.close();
    }
  });

  test("emits answered questions as question_answered carrying turn_id", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      channelEvents.push({ content, meta });
    });
    (bot as any).callApi = async () => ({ ok: true, result: { message_id: 301 } });

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 77,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          turn_id: "turn_req_77",
          questions: [
            {
              question: "Deploy hotfix now?",
              options: [{ label: "Deploy now (Recommended)" }, { label: "Defer" }],
            },
          ],
        },
      },
    });

    const pending = broker.getPendingQuestions();
    expect(pending.length).toBe(1);
    const q = pending[0];

    await (bot as any).handleUpdate({
      update_id: 800,
      callback_query: {
        id: "cb_800",
        from: { id: 999, is_bot: false, first_name: "Alex" },
        message: { message_id: 301, date: 1700000000, chat: { id: 999, type: "private" }, text: "Deploy hotfix now?" },
        data: `q:${q.id}:0:0`,
      },
    });

    expect(channelEvents.length).toBe(1);
    expect(channelEvents[0].meta.event).toBe("question_answered");
    expect(channelEvents[0].meta.question_id).toBe(q.id);
    expect(channelEvents[0].meta.choice).toBe("Deploy now (Recommended)");
    expect(channelEvents[0].meta.turn_id).toBe("turn_req_77");
  });

  test("does not fabricate synthetic turn_id when turn_id is omitted", async () => {
    const broker = new QuestionBroker(testStateDir);
    const result = await broker.askUser({
      question: "Continue work?",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 12345678,
    });
    expect(result.message).toContain("posted to the user");
    expect(result.message).not.toContain("Nic");

    const resolved = await broker.resolveAnswer(result.questionId, 0);
    expect(resolved).not.toBeNull();
    expect(resolved!.channelEvent.turn_id).toBeUndefined();
  });

  test("MCP tools descriptions use 'the user' and omit personal names, and scopes strictly to the four core tools", async () => {
    const { MCP_TOOLS } = await import("../src/mcp/tools.js");
    for (const tool of MCP_TOOLS) {
      expect(tool.description).not.toContain("Nic");
    }
    const toolNames = MCP_TOOLS.map((t) => t.name);
    expect(toolNames).toEqual(["reply", "react", "ask_user", "edit_message"]);

    const replyTool = MCP_TOOLS.find((t) => t.name === "reply");
    expect(replyTool?.description).toContain("the user");
    const askUserTool = MCP_TOOLS.find((t) => t.name === "ask_user");
    expect(askUserTool?.description).toContain("the user");
  });

  test("permission_request notification fails fast if request_id or tool_name is missing", async () => {
    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [12345678],
      maxChatChars: 1200,
      port: 8093,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "sock.sock"),
      voiceReplies: "off" as const,
      botCommands: [],
    };
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const mcp = new StdioMcpServer(config, store, broker, null, permRelay);

    // Missing request_id
    expect(
      mcp.handleMessage({
        jsonrpc: "2.0",
        method: "notifications/claude/channel/permission_request",
        params: { tool_name: "Bash" },
      })
    ).rejects.toThrow();

    // Disproved method name fails fast (not handled as permission)
    const disprovedRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 99,
      method: "claude/channel/permission",
      params: { id: "old_perm_1" },
    });
    // Should not be recognized as permission handler
    expect((disprovedRes as any)?.error?.code ?? -32601).toBe(-32601);
  });

  test("lists pending questions with origin fields: id, text, session, turn, and when asked", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);

    const askPayload = {
      question: "Which test strategy should we adopt?",
      options: [{ label: "Unit tests" }, { label: "Integration tests" }],
      turnId: "turn_session_001",
      sessionId: "session_abc_123",
      chatId: 999,
    };
    const posted = await broker.askUser(askPayload);

    // 1. Direct broker method test
    const pendingQuestions = broker.getPendingQuestions();
    expect(pendingQuestions.length).toBe(1);
    const qBroker = pendingQuestions[0];
    expect(qBroker.id).toBe(posted.questionId);
    expect(qBroker.text).toBe("Which test strategy should we adopt?");
    expect(qBroker.sessionId || qBroker.session_id).toBe("session_abc_123");
    expect(qBroker.turnId || qBroker.turn_id).toBe("turn_session_001");
    expect(qBroker.createdAt || qBroker.created_at).toBeDefined();

    // 2. HTTP route GET /api/app/questions
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: {
        Cookie: `ida_session=${token}`,
      },
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: () => {},
    } as any);

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.questions).toBeDefined();
    expect(data.questions.length).toBe(1);
    const q = data.questions[0];
    expect(q.id).toBe(posted.questionId);
    expect(q.text).toBe("Which test strategy should we adopt?");
    expect(q.sessionId || q.session_id).toBe("session_abc_123");
    expect(q.turnId || q.turn_id).toBe("turn_session_001");
    expect(q.createdAt || q.created_at).toBeDefined();
  });

  test("closing a pending question with a reason removes it from Mini App, edits chat card, and emits channel event", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);

    const posted = await broker.askUser({
      header: "Deployment",
      question: "Deploy release v1.0.0 to canary?",
      options: [{ label: "Deploy" }, { label: "Cancel" }],
      chatId: 999,
      turnId: "turn_close_test",
      sessionId: "session_close_test",
    });
    broker.setMessageId(posted.questionId, 888);

    const editedCards: Array<{ chatId: number; messageId: number; text: string }> = [];
    const emittedEvents: Array<{ event: string; content: string; meta: Record<string, unknown> }> = [];
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);

    // Call POST /api/app/questions/close with a reason
    const req = new Request("http://127.0.0.1:8093/api/app/questions/close", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `ida_session=${token}`,
      },
      body: JSON.stringify({
        question_id: posted.questionId,
        reason: "answered elsewhere",
      }),
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: (event, content, meta) => {
        emittedEvents.push({ event, content, meta });
      },
      editTelegramCard: async (chatId, messageId, text) => {
        editedCards.push({ chatId, messageId, text });
      },
    } as any);

    expect(resp.status).toBe(200);

    // 1. Removed from the Mini App (broker getPendingQuestions returns empty)
    expect(broker.getPendingQuestions().length).toBe(0);

    // 2. Chat card is edited to show the reason
    expect(editedCards.length).toBe(1);
    expect(editedCards[0].chatId).toBe(999);
    expect(editedCards[0].messageId).toBe(888);
    expect(editedCards[0].text).toContain("Closed: answered elsewhere");

    // 3. Emits channel event to the asking session
    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].event).toBe("question_closed");
    expect(emittedEvents[0].meta.question_id).toBe(posted.questionId);
    expect(emittedEvents[0].meta.reason).toBe("answered elsewhere");
    expect(emittedEvents[0].meta.turn_id).toBe("turn_close_test");
    expect(emittedEvents[0].meta.session_id).toBe("session_close_test");
  });

  test("closing a pending question without a reason is rejected with 400 Bad Request and broker throws", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);

    const posted = await broker.askUser({
      question: "Reject without reason test",
      options: [{ label: "A" }],
      chatId: 999,
    });

    // 1. Broker throws on empty or whitespace reason
    await expect(broker.closeQuestion(posted.questionId, "")).rejects.toThrow("Missing reason");
    await expect(broker.closeQuestion(posted.questionId, "   ")).rejects.toThrow("Missing reason");

    // 2. HTTP route returns 400 Bad Request
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions/close", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `ida_session=${token}`,
      },
      body: JSON.stringify({
        question_id: posted.questionId,
        reason: "   ",
      }),
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: () => {},
    } as any);

    expect(resp.status).toBe(400);
    const data = await resp.json();
    expect(data.error).toContain("Missing reason");

    // Question remains pending
    expect(broker.getPendingQuestions().length).toBe(1);
  });

  test("ask_user with mini_app_only: true or chat: false appears in Mini App and posts nothing to chat (AC1)", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, () => {});
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: 12345 } };
    };

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // Call ask_user with mini_app_only: true
    const res = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          mini_app_only: true,
          questions: [
            {
              header: "Background Task Priority",
              question: "Which background worker should handle data indexing?",
              options: [
                { label: "Worker A (Recommended)", description: "High-memory container" },
                { label: "Worker B", description: "Standard worker" },
              ],
            },
          ],
        },
      },
    });

    // 1. Posts NOTHING to chat (no sendMessage calls)
    const chatCards = apiCalls.filter((c) => c.method === "sendMessage");
    expect(chatCards.length).toBe(0);

    // 2. Appears in the pending questions list for Mini App
    const pending = broker.getPendingQuestions();
    expect(pending.length).toBe(1);
    expect(pending[0].question).toBe("Which background worker should handle data indexing?");
    expect(pending[0].status).toBe("pending");
    expect((pending[0] as any).mini_app_only || (pending[0] as any).miniAppOnly || (pending[0] as any).chat === false).toBe(true);

    // 3. Question can also be specified with per-question chat: false
    const res2 = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              chat: false,
              question: "Silent question for Mini App only?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    // Still no chat cards sent
    expect(apiCalls.filter((c) => c.method === "sendMessage").length).toBe(0);
    expect(broker.getPendingQuestions().length).toBe(2);
  });

  test("socket server handles ask_user with mini_app_only: true and detail, routing to Mini App without chat cards", async () => {
    const { createConnection } = await import("node:net");
    const { createBridgeServer } = await import("../server.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const socketPath = join(testStateDir, "test_server.sock");
    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [999],
      maxChatChars: 1200,
      port: 8094,
      stateDir: testStateDir,
      socketPath,
      voiceReplies: "off" as const,
      botCommands: [],
      miniAppUrl: "https://ida.example.ts.net",
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const sentCards: any[] = [];
    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    (bot as any).sendQuestionCard = async (chatId: number, qid: string, card: any) => {
      sentCards.push({ chatId, qid, card });
    };

    const server = createBridgeServer(config as any, broker, bot);
    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const client = createConnection(socketPath);
      const resPromise = new Promise<string>((resolve) => {
        client.on("data", (d) => resolve(d.toString()));
      });

      client.write(
        JSON.stringify({
          type: "ask_user",
          mini_app_only: true,
          questions: [
            {
              question: "Socket question for Mini App only?",
              header: "Socket Header",
              detail: "Deep socket background detail",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        }) + "\n"
      );

      const rawRes = await resPromise;
      const res = JSON.parse(rawRes.trim());
      expect(res.status).toBe("ok");

      // Verify no question cards sent to chat
      expect(sentCards.length).toBe(0);

      // Verify question is pending in broker with detail and mini_app_only
      const pending = broker.getPendingQuestions();
      const socketQ = pending.find((q) => q.question === "Socket question for Mini App only?");
      expect(socketQ).toBeDefined();
      expect(socketQ!.detail).toBe("Deep socket background detail");
      expect((socketQ as any).mini_app_only).toBe(true);
      expect(socketQ!.detailsId).toBeDefined();
    } finally {
      server.close();
    }
  });

  test("AC2: a question answered in the asking session leaves the outstanding list", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 8093,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const mcp = new StdioMcpServer(config, store, broker, null, permRelay);

    // 1. Post a question
    const postRes = await broker.askUser({
      question: "Which database should we use?",
      options: [{ label: "PostgreSQL" }, { label: "SQLite" }],
      turnId: "turn_sess_1",
      chatId: 999,
    });
    const qid = postRes.questionId;

    // Verify it is initially pending in broker and Mini App endpoint
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(true);

    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const reqBefore = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const respBefore = await handleApiRequest(reqBefore, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const dataBefore = await respBefore.json();
    expect(dataBefore.questions.some((q: any) => q.id === qid)).toBe(true);

    // 2. The asking agent learns the question was answered in its session and resolves it via answer_question tool
    const answerCall = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "answer_question",
        arguments: {
          question_id: qid,
          choice: "PostgreSQL",
        },
      },
    });

    expect(answerCall?.isError).toBeFalsy();

    // 3. Question must have left the outstanding list in broker and Mini App
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(false);

    const reqAfter = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const respAfter = await handleApiRequest(reqAfter, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const dataAfter = await respAfter.json();
    expect(dataAfter.questions.some((q: any) => q.id === qid)).toBe(false);
  });

  test("AC3: a question answered outside the Mini App and outside the asking session (e.g. a plain Telegram reply) leaves the outstanding list", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 8093,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const editedCards: Array<{ chatId: number; messageId: number; text: string }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    }, store);

    (bot as any).editMessage = async (chatId: number, messageId: number, text: string) => {
      editedCards.push({ chatId, messageId, text });
      return true;
    };

    // 1. Post a question that sends a card to Telegram with messageId 601
    const postRes = await broker.askUser({
      question: "Which items should go to Sara and Pauli?",
      options: [{ label: "Both items" }, { label: "Sara only" }],
      chatId: 999,
    });
    const qid = postRes.questionId;
    broker.setMessageId(qid, 601);

    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(true);

    // 2a. A non-matching conversational reply does not answer or dismiss the question
    await (bot as any).handleUpdate({
      update_id: 1233,
      message: {
        message_id: 6015,
        date: Math.floor(Date.now() / 1000),
        chat: { id: 999, type: "private" },
        from: { id: 999, is_bot: false, first_name: "User" },
        text: "What does this mean?",
        reply_to_message: {
          message_id: 601,
          date: Math.floor(Date.now() / 1000) - 10,
          chat: { id: 999, type: "private" },
          text: "Which items should go to Sara and Pauli?",
        },
      },
    });
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(true);
    expect(editedCards.length).toBe(0);

    // 2b. User in Telegram replies directly to message 601 with "Both items" (outside Mini App and outside asking session)
    await (bot as any).handleUpdate({
      update_id: 1234,
      message: {
        message_id: 602,
        date: Math.floor(Date.now() / 1000),
        chat: { id: 999, type: "private" },
        from: { id: 999, is_bot: false, first_name: "User" },
        text: "Both items",
        reply_to_message: {
          message_id: 601,
          date: Math.floor(Date.now() / 1000) - 10,
          chat: { id: 999, type: "private" },
          text: "Which items should go to Sara and Pauli?",
        },
      },
    });

    // 3. The question card in Telegram was edited to show resolved answer
    expect(editedCards.some((c) => c.messageId === 601 && c.text.includes("Selected: Both items ✅"))).toBe(true);

    // 4. Question must leave the outstanding list in broker and Mini App
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(false);

    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const resp = await handleApiRequest(req, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const data = await resp.json();
    expect(data.questions.some((q: any) => q.id === qid)).toBe(false);
  });

  test("AC4: an unanswered question stays listed", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 8093,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    // Post two questions: q1 (to be answered) and q2 (unanswered)
    const q1 = await broker.askUser({
      question: "Answered question",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 999,
    });
    const q2 = await broker.askUser({
      question: "Unanswered question waiting for operator",
      options: [{ label: "Option A" }, { label: "Option B" }],
      chatId: 999,
    });

    // Resolve q1
    await broker.resolveAnswer(q1.questionId, 0);

    // q2 remains unanswered
    const pending = broker.getPendingQuestions();
    expect(pending.some((q) => q.id === q1.questionId)).toBe(false);
    expect(pending.some((q) => q.id === q2.questionId)).toBe(true);

    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const resp = await handleApiRequest(req, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const data = await resp.json();

    expect(data.questions.some((q: any) => q.id === q1.questionId)).toBe(false);
    expect(data.questions.some((q: any) => q.id === q2.questionId)).toBe(true);
    const found = data.questions.find((q: any) => q.id === q2.questionId);
    expect(found.status).toBe("pending");
  });

  test("AC1: a test in which a question's delivery fails shows the failure surfaced to the asking agent", async () => {
    const { createBridgeServer } = await import("../server.js");
    const { spawn } = await import("node:child_process");
    const { mkdirSync, unlinkSync, existsSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const socketPath = join(testStateDir, "ac1_delivery_fail.sock");
    if (existsSync(socketPath)) unlinkSync(socketPath);

    const broker = new QuestionBroker(testStateDir);
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    // Mock bot whose delivery to Telegram fails
    const mockBot = {
      getLastThreadId: () => undefined,
      sendQuestionCard: async (chatId: number, qid: string) => {
        broker.markDeliveryFailed(qid, "Bad Request: chat not found");
        return { ok: false, error: "Bad Request: chat not found" };
      },
    } as any;

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath,
      port: 8093,
      miniAppUrl: "https://ida.example.test",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
      instance: "prime",
    };

    const server = createBridgeServer(
      config as any,
      broker,
      mockBot,
      (content, meta) => {
        channelEvents.push({ content, meta });
      }
    );

    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      const { stdout, stderr, exitCode } = await new Promise<{ stdout: string; stderr: string; exitCode: number | null }>((resolve) => {
        const proc = spawn("node", [hookScript], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: socketPath,
          },
        });
        let out = "";
        let err = "";
        proc.stdout.on("data", (d) => (out += d.toString()));
        proc.stderr.on("data", (d) => (err += d.toString()));
        proc.on("close", (code) => resolve({ stdout: out, stderr: err, exitCode: code }));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_ac1_fail",
            tool_input: {
              questions: [
                {
                  question: "Undelivered question?",
                  options: [{ label: "Yes" }, { label: "No" }],
                },
              ],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      expect(exitCode).not.toBe(0);
      expect(stderr).toContain("Bad Request: chat not found");
      expect(stdout).not.toContain("posted to the user over Telegram");
      expect(channelEvents.some((e) => e.meta.event === "question_delivery_failed")).toBe(true);

      const pending = broker.getPendingQuestions();
      expect(pending.some((q) => q.question === "Undelivered question?")).toBe(false);
    } finally {
      server.close();
      if (existsSync(socketPath)) unlinkSync(socketPath);
    }
  });

  test("PreToolUse hook surfaces delivery failure when bridge socket returns malformed or non-JSON data", async () => {
    const { createServer } = await import("node:net");
    const { spawn } = await import("node:child_process");
    const { mkdirSync, unlinkSync, existsSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const socketPath = join(testStateDir, "malformed_hook.sock");
    if (existsSync(socketPath)) unlinkSync(socketPath);

    const server = createServer((client) => {
      client.on("data", () => {
        client.write("MALFORMED_NON_JSON_RESPONSE\n");
      });
    });

    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      const { stdout, stderr, exitCode } = await new Promise<{ stdout: string; stderr: string; exitCode: number | null }>((resolve) => {
        const proc = spawn("node", [hookScript], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: socketPath,
          },
        });
        let out = "";
        let err = "";
        proc.stdout.on("data", (d) => (out += d.toString()));
        proc.stderr.on("data", (d) => (err += d.toString()));
        proc.on("close", (code) => resolve({ stdout: out, stderr: err, exitCode: code }));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_malformed_test",
            tool_input: {
              questions: [
                {
                  question: "Question with broken socket?",
                  options: [{ label: "Yes" }, { label: "No" }],
                },
              ],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      expect(exitCode).not.toBe(0);
      expect(stderr).toContain("failed to parse socket response");
      expect(stdout).not.toContain("posted to the user over Telegram");
    } finally {
      server.close();
      if (existsSync(socketPath)) unlinkSync(socketPath);
    }
  });

  test("AC2: a delivered question raises no such signal", async () => {
    const { createBridgeServer } = await import("../server.js");
    const { spawn } = await import("node:child_process");
    const { mkdirSync, unlinkSync, existsSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const socketPath = join(testStateDir, "ac2_delivery_ok.sock");
    if (existsSync(socketPath)) unlinkSync(socketPath);

    const broker = new QuestionBroker(testStateDir);
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    // Mock bot whose delivery to Telegram succeeds
    const mockBot = {
      getLastThreadId: () => undefined,
      sendQuestionCard: async (chatId: number, qid: string) => {
        broker.setMessageId(qid, 54321);
        return { ok: true, messageId: 54321, result: { message_id: 54321 } };
      },
    } as any;

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath,
      port: 8093,
      miniAppUrl: "https://ida.example.test",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
      instance: "prime",
    };

    const server = createBridgeServer(
      config as any,
      broker,
      mockBot,
      (content, meta) => {
        channelEvents.push({ content, meta });
      }
    );

    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      const stdout = await new Promise<string>((resolve, reject) => {
        const proc = spawn("node", [hookScript], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: socketPath,
          },
        });
        let out = "";
        proc.stdout.on("data", (d) => (out += d.toString()));
        proc.on("error", reject);
        proc.on("close", () => resolve(out));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_ac2_ok",
            tool_input: {
              questions: [
                {
                  question: "Delivered question?",
                  options: [{ label: "Yes" }, { label: "No" }],
                },
              ],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      const parsed = JSON.parse(stdout.trim());
      expect(parsed.decision).toBe("block");
      // Succeeded delivery reports posted to user and raises no failure signal
      expect(parsed.reason).toContain("posted to the user over Telegram");
      expect(parsed.reason).not.toContain("Failed to deliver");
      expect(channelEvents.some((e) => e.meta.event === "question_delivery_failed")).toBe(false);

      const pending = broker.getPendingQuestions();
      const found = pending.find((q) => q.question === "Delivered question?");
      expect(found).toBeDefined();
      expect(found?.messageId).toBe(54321);
      expect(found?.status).toBe("pending");
    } finally {
      server.close();
      if (existsSync(socketPath)) unlinkSync(socketPath);
    }
  });

  test("AC1 & AC2: reproduces vanished buttons when bridge server captures null bot at startup, and verifies fix delivers card with buttons and messageId", async () => {
    const { createConnection } = await import("node:net");
    const { createBridgeServer } = await import("../server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");

    const socketPath = join(testStateDir, "repro_bridge.sock");
    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [999],
      maxChatChars: 1200,
      port: 8095,
      stateDir: testStateDir,
      socketPath,
      voiceReplies: "off" as const,
      botCommands: [],
      miniAppUrl: "https://ida.example.ts.net",
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const sentCards: any[] = [];

    // Simulate startup sequence in server.ts:
    // bot starts as null, server is created with getter/bot, bot is instantiated shortly after
    let bot: TelegramBotClient | null = null;

    // Passing getter (() => bot) so createBridgeServer resolves live bot instance dynamically
    const server = createBridgeServer(config as any, broker, (() => bot) as any);
    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    // Bot is instantiated after server starts listening (exact server.ts startup lifecycle)
    bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    (bot as any).sendQuestionCard = async (chatId: number, qid: string, card: any) => {
      sentCards.push({ chatId, qid, card });
      broker.setMessageId(qid, 42001);
      return { ok: true, result: { message_id: 42001 } };
    };

    try {
      const client = createConnection(socketPath);
      const resPromise = new Promise<string>((resolve) => {
        client.on("data", (d) => resolve(d.toString()));
      });

      client.write(
        JSON.stringify({
          type: "ask_user",
          questions: [
            {
              question: "Confirm deployment of fix for vanished buttons?",
              header: "Deployment Question",
              options: [{ label: "Approve (Recommended)" }, { label: "Reject" }],
            },
          ],
        }) + "\n"
      );

      const rawRes = await resPromise;
      const res = JSON.parse(rawRes.trim());
      expect(res.status).toBe("ok");

      // Verify chat card WAS sent and buttons are present
      expect(sentCards.length).toBe(1);
      expect(sentCards[0].chatId).toBe(999);
      expect(sentCards[0].card.buttons.length).toBeGreaterThanOrEqual(2);
      expect(sentCards[0].card.buttons[0].text).toContain("Approve (Recommended)");

      // Verify messageId was recorded on the stored question
      const storedQ = broker.getQuestion(res.questionId);
      expect(storedQ).toBeDefined();
      expect(storedQ!.messageId).toBe(42001);
    } finally {
      server.close();
    }
  });

  test("AC2: ask_user returns error and does not report question posted when Telegram API fails", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "err_hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    // Simulate Telegram sendMessage failing
    (bot as any).callApi = async (method: string) => {
      if (method === "sendMessage") {
        return { ok: false, description: "Bad Request: chat not found" };
      }
      return { ok: true };
    };

    const mcp = new StdioMcpServer(config as any, store, broker, bot, permRelay);

    const askResp = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 88,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Will this fail?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    const parsed = typeof (askResp as any)?.result?.content?.[0]?.text === "string"
      ? JSON.parse((askResp as any).result.content[0].text)
      : (askResp as any)?.result;

    // Must NOT report "Question ... posted to the user" when send failed
    expect(parsed.success).toBe(false);
    expect(parsed.error).toContain("chat not found");
    expect((askResp as any)?.isError).toBe(true);
  });

  test("ask_user MCP tool surfaces failure when delivery fails and succeeds without failure signal when delivered", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "mcp_test.sock"),
      port: 8093,
      miniAppUrl: "https://ida.example.test",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
      instance: "prime",
    };

    // When bot fails delivery
    const failingBot = {
      getLastThreadId: () => undefined,
      sendQuestionCard: async (chatId: number, qid: string) => {
        broker.markDeliveryFailed(qid, "Telegram network error");
        return { ok: false, error: "Telegram network error" };
      },
    } as any;

    const failingServer = new StdioMcpServer(config as any, store, broker, failingBot, permRelay);
    failingServer.emitChannelNotification = (content, meta) => {
      channelEvents.push({ content, meta });
    };

    const failCall = await failingServer.handleMessage({
      jsonrpc: "2.0",
      id: "req_fail_1",
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Will this fail?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    expect(failCall?.isError).toBe(true);
    expect(failCall?.result?.content?.[0]?.text).toContain("Telegram network error");
    expect(channelEvents.some((e) => e.meta.event === "question_delivery_failed")).toBe(true);

    // When bot succeeds delivery
    channelEvents.length = 0;
    const succeedingBot = {
      getLastThreadId: () => undefined,
      sendQuestionCard: async (chatId: number, qid: string) => {
        broker.setMessageId(qid, 991122);
        return { ok: true, messageId: 991122, result: { message_id: 991122 } };
      },
    } as any;

    const succeedingServer = new StdioMcpServer(config as any, store, broker, succeedingBot, permRelay);
    succeedingServer.emitChannelNotification = (content, meta) => {
      channelEvents.push({ content, meta });
    };

    const okCall = await succeedingServer.handleMessage({
      jsonrpc: "2.0",
      id: "req_ok_1",
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Will this succeed?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    expect(okCall?.isError).toBeUndefined();
    expect(okCall?.result?.content?.[0]?.text).toContain("posted to the user");
    expect(okCall?.result?.content?.[0]?.text).not.toContain("Failed to deliver");
    expect(channelEvents.some((e) => e.meta.event === "question_delivery_failed")).toBe(false);
  });

  test("sweepUndeliveredQuestions detects legacy questions left pending with no messageId and marks them failed", async () => {
    const broker = new QuestionBroker(testStateDir);

    // Create a question stuck in pending with no messageId (legacy failure shape per issue 3415)
    const qStuck = await broker.askUser({
      question: "Legacy stuck question with no messageId?",
      options: [{ label: "Yes" }, { label: "No" }],
      turnId: "turn_legacy_stuck",
      chatId: 999,
      chat: true,
      mini_app_only: false,
    });

    // Create a delivered question with messageId
    const qDelivered = await broker.askUser({
      question: "Delivered question with messageId?",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 999,
    });
    broker.setMessageId(qDelivered.questionId, 882244);

    // Create a mini_app_only question with no messageId (valid, should stay pending)
    const qMiniApp = await broker.askUser({
      question: "Mini app only question?",
      options: [{ label: "Yes" }, { label: "No" }],
      mini_app_only: true,
    });

    const swept = broker.sweepUndeliveredQuestions();
    expect(swept.some((q) => q.id === qStuck.questionId)).toBe(true);
    expect(swept.some((q) => q.id === qDelivered.questionId)).toBe(false);
    expect(swept.some((q) => q.id === qMiniApp.questionId)).toBe(false);

    const pending = broker.getPendingQuestions();
    expect(pending.some((q) => q.id === qStuck.questionId)).toBe(false);
    expect(pending.some((q) => q.id === qDelivered.questionId)).toBe(true);
    expect(pending.some((q) => q.id === qMiniApp.questionId)).toBe(true);

    const stuckDoc = broker.getQuestion(qStuck.questionId);
    expect(stuckDoc?.status).toBe("failed");
    expect(stuckDoc?.deliveryError).toContain("no Telegram messageId");
  });

  test("AC2: PreToolUse hook on AskUserQuestion fails fast when socket does not exist or connection fails", async () => {
    const { spawn } = await import("node:child_process");
    const { mkdirSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const missingSocketPath = join(testStateDir, "nonexistent.sock");
    const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");

    const { stderr, exitCode } = await new Promise<{ stderr: string; exitCode: number | null }>((resolve) => {
      const proc = spawn("node", [hookScript], {
        env: {
          ...process.env,
          IDA_TELEGRAM_ROLE: "primary",
          STATE_DIR: testStateDir,
          SOCKET_PATH: missingSocketPath,
        },
      });
      let stderrData = "";
      proc.stderr.on("data", (d) => (stderrData += d.toString()));
      proc.on("close", (code) => resolve({ stderr: stderrData, exitCode: code }));
      proc.stdin.write(
        JSON.stringify({
          tool_name: "AskUserQuestion",
          turn_id: "turn_missing_sock",
          tool_input: {
            questions: [{ question: "Missing socket test?", options: [{ label: "OK" }] }],
          },
        }) + "\n"
      );
      proc.stdin.end();
    });

    expect(exitCode).not.toBe(0);
    expect(stderr).toContain("Telegram bridge socket not found");
  });

  test("AC2: PreToolUse hook on AskUserQuestion fails fast on socket delivery error instead of claiming delivery", async () => {
    const { createServer } = await import("node:net");
    const { spawn } = await import("node:child_process");
    const { mkdirSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const socketPath = join(testStateDir, "err_bridge.sock");

    // Server returns an error response indicating delivery failure
    const server = createServer((client) => {
      let buf = "";
      client.on("data", (chunk) => {
        buf += chunk.toString();
        if (buf.includes("\n")) {
          client.write(JSON.stringify({ status: "error", error: "Failed to deliver question card over Telegram: chat not found" }) + "\n");
        }
      });
    });

    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      const { stdout, stderr, exitCode } = await new Promise<{ stdout: string; stderr: string; exitCode: number | null }>((resolve) => {
        const proc = spawn("node", [hookScript], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: socketPath,
          },
        });
        let stdoutData = "";
        let stderrData = "";
        proc.stdout.on("data", (d) => (stdoutData += d.toString()));
        proc.stderr.on("data", (d) => (stderrData += d.toString()));
        proc.on("close", (code) => resolve({ stdout: stdoutData, stderr: stderrData, exitCode: code }));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_err_99",
            tool_input: {
              questions: [
                {
                  question: "Failing question test",
                  options: [{ label: "Option 1" }],
                },
              ],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      // Hook must fail fast (exit non-zero) and surface error on stderr
      expect(exitCode).not.toBe(0);
      expect(stderr).toContain("Failed to deliver question card over Telegram");
      // Must NOT claim question was posted to user
      expect(stdout).not.toContain("posted to the user over Telegram");
    } finally {
      server.close();
    }
  });

  test("AC1.3: sendQuestionCard falls back to plain text send when formatted entities are rejected", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "fallback_hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const calls: Array<{ method: string; payload: any }> = [];

    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    (bot as any).callApi = async (method: string, payload: any) => {
      calls.push({ method, payload });
      // First sendMessage with entities fails
      if (method === "sendMessage" && payload.entities) {
        return { ok: false, description: "Bad Request: can't parse entities" };
      }
      // Fallback sendMessage without entities succeeds
      if (method === "sendMessage" && !payload.entities) {
        return { ok: true, result: { message_id: 88888 } };
      }
      return { ok: true };
    };

    const q = await broker.askUser({
      question: "Fallback test question?",
      options: [{ label: "OK" }],
      chatId: 999,
    });

    const card = broker.renderQuestionCard(q.questionId)!;
    const sendRes = await bot.sendQuestionCard(999, q.questionId, card);

    expect(sendRes.ok).toBe(true);
    expect(sendRes.result.message_id).toBe(88888);
    // Verified fallback plain text call was made with keyboard intact
    expect(calls.length).toBe(2);
    expect(calls[1].payload.entities).toBeUndefined();
    expect(calls[1].payload.reply_markup.inline_keyboard.length).toBeGreaterThanOrEqual(1);
    expect(broker.getQuestion(q.questionId)!.messageId).toBe(88888);
  });
});
